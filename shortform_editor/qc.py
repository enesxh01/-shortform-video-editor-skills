from __future__ import annotations

import re
from fractions import Fraction
from pathlib import Path
from typing import Any

from .cli import PipelineError, probe_media, require_tool, run_checked


BLACK_RE = re.compile(r"black_start:([0-9.]+).*?black_end:([0-9.]+).*?black_duration:([0-9.]+)")
FREEZE_START_RE = re.compile(r"freeze_start:([0-9.]+)")\nFREEZE_END_RE = re.compile(r"freeze_end:([0-9.]+)")
VOLUME_RE = re.compile(r"(mean_volume|max_volume):\s*(-?[0-9.]+) dB")


def assess_probe(report: dict[str, Any], ffmpeg_log: str, expected_width: int = 1080,
                 expected_height: int = 1920, expected_fps: str = "60/1") -> dict[str, Any]:
    video = next((s for s in report.get("streams", []) if s.get("codec_type") == "video"), None)
    audio = next((s for s in report.get("streams", []) if s.get("codec_type") == "audio"), None)
    checks = []
    failures = []
    warnings = []
    if not video:
        checks.append({"name": "video_stream", "status": "critical", "detail": "No video stream found"})
        failures.append("No video stream")
    else:
        width, height = int(video.get("width", 0)), int(video.get("height", 0))
        checks.append({
            "name": "dimensions",
            "status": "passed" if (width, height) == (expected_width, expected_height) else "major",
            "detail": f"Actual {width}x{height}; expected {expected_width}x{expected_height}"
        })
        if (width, height) != (expected_width, expected_height):
            failures.append("Unexpected frame dimensions")
        try:
            actual_fps = Fraction(video.get("avg_frame_rate", "0/1"))
            target_fps = Fraction(expected_fps)
            fps_ok = actual_fps == target_fps
        except (ValueError, ZeroDivisionError):
            actual_fps, fps_ok = Fraction(0, 1), False
        checks.append({
            "name": "frame_rate",
            "status": "passed" if fps_ok else "major",
            "detail": f"Average frame rate {actual_fps}; expected {target_fps}"
        })
        if not fps_ok:
            failures.append("Unexpected average frame rate")
        checks.append({
            "name": "video_codec",
            "status": "passed" if video.get("codec_name") == "h264" else "major",
            "detail": f"Video codec: {video.get('codec_name')}"
        })
        if video.get("codec_name") != "h264":
            failures.append("Unexpected video codec")

    if audio:
        checks.append({
            "name": "audio_stream",
            "status": "passed",
            "detail": f"Audio codec {audio.get('codec_name')}, {audio.get('channels')} channels"
        })
    else:
        checks.append({"name": "audio_stream", "status": "warning", "detail": "No audio stream found"})
        warnings.append("No audio stream")

    black_regions = [
        {"start": float(match.group(1)), "end": float(match.group(2)), "duration": float(match.group(3))}
        for match in BLACK_RE.finditer(ffmpeg_log)
    ]
    freeze_starts = [float(match.group(1)) for match in FREEZE_START_RE.finditer(ffmpeg_log)]
    freeze_ends = [float(match.group(1)) for match in FREEZE_END_RE.finditer(ffmpeg_log)]
    freeze_events = [
        {"start": start, "end": end}
        for start, end in zip(freeze_starts, freeze_ends)
        if end >= start
    ]
    checks.append({
        "name": "black_frames",
        "status": "major" if any(item["duration"] >= 0.5 for item in black_regions) else "passed",
        "detail": f"{len(black_regions)} black intervals detected",
        "events": black_regions
    })
    if any(item["duration"] >= 0.5 for item in black_regions):
        failures.append("Black interval at least 0.5 seconds")
    checks.append({
        "name": "frozen_frames",
        "status": "major" if freeze_events else "passed",
        "detail": f"{len(freeze_events)} frozen intervals detected",
        "events": freeze_events
    })
    if freeze_events:
        failures.append("Frozen-frame interval detected")

    volumes = {name: float(value) for name, value in VOLUME_RE.findall(ffmpeg_log)}
    if audio and "max_volume" in volumes:
        peak = volumes["max_volume"]
        checks.append({
            "name": "audio_peak",
            "status": "major" if peak >= -0.1 else "passed",
            "detail": f"Measured sample peak {peak:.1f} dBFS; this is not true-peak measurement"
        })
        if peak >= -0.1:
            failures.append("Audio sample peak is at or near digital clipping")
    elif audio:
        checks.append({"name": "audio_peak", "status": "warning", "detail": "Volume detector did not report a peak"})
        warnings.append("Audio peak measurement unavailable")

    status = "critical" if any(item["status"] == "critical" for item in checks) else (
        "fail" if failures else ("warning" if warnings else "passed")
    )
    return {
        "status": status,
        "checks": checks,
        "failures": failures,
        "warnings": warnings,
        "black_regions": black_regions,
        "freeze_regions": freeze_events,
        "audio_volume": volumes,
        "limitations": [
            "Black/freeze filters can flag intentional pauses, static scenes or fades; inspect the marked intervals.",
            "Volume detection measures sample peak, not true peak or perceived loudness.",
            "This pass does not verify caption spelling, safe areas, story comprehension, crop quality, humor or audio/video sync by listening.",
            "No automatic repair is performed by QC."
        ]
    }


def run_qc(source: Path, expected_width: int = 1080, expected_height: int = 1920,
           expected_fps: str = "60/1") -> dict[str, Any]:
    source = source.expanduser().resolve(strict=True)
    report = probe_media(source)
    ffmpeg = require_tool("ffmpeg")
    video_filters = "blackdetect=d=0.5:pix_th=0.10,freezedetect=n=-50dB:d=1.0"
    args = [ffmpeg, "-hide_banner", "-i", str(source), "-vf", video_filters]
    if any(s.get("codec_type") == "audio" for s in report.get("streams", [])):
        args += ["-af", "volumedetect"]
    args += ["-f", "null", "-"]
    result = run_checked(args)
    assessed = assess_probe(report, result.stderr, expected_width, expected_height, expected_fps)
    assessed["source"] = {
        "path": str(source),
        "fingerprint": report["source"]["fingerprint"],
        "duration_seconds": report.get("format", {}).get("duration")
    }
    assessed["tool"] = run_checked([ffmpeg, "-version"]).stdout.splitlines()[0]
    return assessed
