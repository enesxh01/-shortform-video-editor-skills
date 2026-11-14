from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
from fractions import Fraction
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas" / "edit-decision-list.schema.json"
TIMESTAMP_RE = re.compile(r"^(?:(\d+):)?([0-5]?\d):([0-5]\d)(?:\.(\d{1,6}))?$")


class PipelineError(RuntimeError):
    pass


def require_tool(name: str) -> str:
    executable = shutil.which(name)
    if not executable:
        raise PipelineError(f"Required executable not found on PATH: {name}")
    return executable


def run_checked(args: list[str]) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(args, check=True, text=True, capture_output=True)
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or exc.stdout or str(exc)).strip()
        raise PipelineError(f"Command failed ({exc.returncode}): {detail}") from exc


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def probe_media(source: Path) -> dict[str, Any]:
    source = source.expanduser().resolve(strict=True)
    if not source.is_file():
        raise PipelineError(f"Source is not a regular file: {source}")
    ffprobe = require_tool("ffprobe")
    result = run_checked([
        ffprobe, "-v", "error", "-show_format", "-show_streams",
        "-show_entries", "format=filename,format_name,duration,size,start_time:stream=index,codec_type,codec_name,width,height,pix_fmt,r_frame_rate,avg_frame_rate,time_base,start_time,duration,channels,channel_layout,sample_rate",
        "-of", "json", str(source)
    ])
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise PipelineError("ffprobe returned invalid JSON") from exc
    streams = data.get("streams", [])
    if not streams or not any(s.get("codec_type") == "video" for s in streams):
        raise PipelineError("Input contains no readable video stream")
    digest = sha256_file(source)
    data["source"] = {
        "path": str(source),
        "size_bytes": source.stat().st_size,
        "sha256": digest,
        "fingerprint": f"sha256:{digest}",
    }
    data["tool_versions"] = {
        "ffprobe": run_checked([ffprobe, "-version"]).stdout.splitlines()[0]
    }
    return data


def timestamp_seconds(value: str) -> float:
    match = TIMESTAMP_RE.fullmatch(value)
    if not match:
        raise ValueError(f"Invalid timestamp: {value!r}; expected MM:SS or HH:MM:SS[.ffffff]")
    hours, minutes, seconds, fraction = match.groups()
    total = int(hours or 0) * 3600 + int(minutes) * 60 + int(seconds)
    if fraction:
        total += float("0." + fraction)
    return total


def load_schema() -> dict[str, Any]:
    try:
        return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PipelineError(f"Cannot load EDL schema at {SCHEMA_PATH}: {exc}") from exc


def validate_edl(edl: dict[str, Any], source_duration: float | None = None, source_fingerprint: str | None = None) -> list[str]:
    try:
        from jsonschema import Draft202012Validator
    except ImportError as exc:
        raise PipelineError("Install project dependencies first: pip install -e .") from exc

    errors = sorted(Draft202012Validator(load_schema()).iter_errors(edl), key=lambda e: list(e.absolute_path))
    messages = [
        f"{'.'.join(map(str, err.absolute_path)) or '<root>'}: {err.message}"
        for err in errors
    ]
    if messages:
        return messages

    render = edl["render"]
    ratio = render["width"] / render["height"]
    if source_fingerprint is not None and edl["source"]["fingerprint"] != source_fingerprint:
        messages.append("EDL source fingerprint does not match the supplied source media")
    if abs(ratio - (9 / 16)) > 0.002:
        messages.append("render dimensions must be portrait 9:16 (within 0.2% tolerance)")
    try:
        fps = Fraction(render["fps_target"])
        time_base = Fraction(edl["source"]["time_base"])
        if fps <= 0 or time_base <= 0:
            raise ValueError("rational values must be positive")
        if edl["source"].get("frame_rate"):
            if Fraction(edl["source"]["frame_rate"]) <= 0:
                raise ValueError("frame rate must be positive")
    except (ValueError, ZeroDivisionError):
        messages.append("frame rate and time_base values must be valid positive rational numbers")

    ids: set[str] = set()
    previous_timeline_start = -1.0
    for index, segment in enumerate(edl["segments"]):
        if segment["id"] in ids:
            messages.append(f"segments[{index}].id duplicates {segment['id']!r}")
        ids.add(segment["id"])
        try:
            start = timestamp_seconds(segment["source_in"])
            end = timestamp_seconds(segment["source_out"])
            if end <= start:
                messages.append(f"segments[{index}] source_out must be greater than source_in")
            if source_duration is not None and end > source_duration + 0.05:
                messages.append(f"segments[{index}] source_out exceeds source duration ({source_duration:.3f}s)")
            timeline = segment.get("timeline_start")
            if timeline is not None:
                timeline_value = timestamp_seconds(timeline)
                if timeline_value < previous_timeline_start:
                    messages.append(f"segments[{index}].timeline_start must be nondecreasing")
                previous_timeline_start = timeline_value
        except ValueError as exc:
            messages.append(f"segments[{index}]: {exc}")

    if edl["approval"]["status"] == "approved" and not edl["approval"]["approved_by_user"]:
        messages.append("approved EDL must have approved_by_user=true")
    return messages


def command_probe(args: argparse.Namespace) -> int:
    source = Path(args.source).expanduser().resolve(strict=True)
    report = probe_media(source)
    output = json.dumps(report, indent=2) + "\n"
    if args.output:
        destination = Path(args.output).expanduser().resolve()
        if destination == source:
            raise PipelineError("Probe report cannot overwrite the source media")
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(output, encoding="utf-8")
    else:
        print(output, end="")
    return 0


def command_validate(args: argparse.Namespace) -> int:
    edl = json.loads(Path(args.edl).read_text(encoding="utf-8"))
    duration = None
    source_fingerprint = None
    if args.probe:
        probe = json.loads(Path(args.probe).read_text(encoding="utf-8"))
        source_fingerprint = probe.get("source", {}).get("fingerprint")
        raw_duration = probe.get("format", {}).get("duration")
        if raw_duration is not None:
            duration = float(raw_duration)
            if not math.isfinite(duration) or duration <= 0:
                raise PipelineError("Probe report contains an invalid source duration")
    errors = validate_edl(edl, duration, source_fingerprint)
    if errors:
        print("EDL INVALID:")
        for error in errors:
            print(f"- {error}")
        return 2
    print("EDL VALID")
    return 0


def command_render(args: argparse.Namespace) -> int:
    edl_path = Path(args.edl).expanduser().resolve(strict=True)
    edl = json.loads(edl_path.read_text(encoding="utf-8"))
    source = Path(args.source).expanduser().resolve(strict=True)
    output = Path(args.output).expanduser().resolve()
    if output in {source, edl_path}:
        raise PipelineError("Output must not overwrite the source media or EDL")
    if output.suffix.lower() != ".mp4":
        raise PipelineError("The current renderer produces MP4; use an output filename ending in .mp4")
    if not 0 <= args.crf <= 51:
        raise PipelineError("--crf must be between 0 and 51")
    if any(segment.get("layout") != "fullscreen" for segment in edl.get("segments", [])):
        raise PipelineError("This MVP renderer supports fullscreen only; split_vertical and blurred_bars_20_60_20 are not implemented")
    if edl.get("render", {}).get("fps_mode") != "cfr":
        raise PipelineError("This MVP renderer supports fps_mode=cfr only")
    if edl.get("render", {}).get("fps_conversion") != "duplicate_drop":
        raise PipelineError("This MVP renderer supports fps_conversion=duplicate_drop only")
    if edl.get("render", {}).get("video_codec") not in (None, "h264"):
        raise PipelineError("This MVP renderer supports H.264 video only")
    if edl.get("render", {}).get("audio_codec") not in (None, "aac"):
        raise PipelineError("This MVP renderer supports AAC audio only")

    probe = probe_media(source)
    raw_duration = probe.get("format", {}).get("duration")
    duration = float(raw_duration) if raw_duration is not None else None
    errors = validate_edl(edl, duration, probe.get("source", {}).get("fingerprint"))
    if errors:
        raise PipelineError("Refusing to render invalid EDL:\n- " + "\n- ".join(errors))
    if edl["approval"]["status"] != "approved" or not edl["approval"]["approved_by_user"]:
        raise PipelineError("Rendering final output requires explicit user approval in the EDL")

    ffmpeg = require_tool("ffmpeg")
    render = edl["render"]
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists() and not args.overwrite:
        raise PipelineError(f"Output already exists (use --overwrite): {output}")

    with tempfile.TemporaryDirectory(prefix="shortform-render-") as tmp:
        tmpdir = Path(tmp)
        parts: list[Path] = []
        for index, segment in enumerate(edl["segments"]):
            start = timestamp_seconds(segment["source_in"])
            end = timestamp_seconds(segment["source_out"])
            part = tmpdir / f"part-{index:04d}.mp4"
            width, height = render["width"], render["height"]
            fps = render["fps_target"]
            vf = (
                f"scale={width}:{height}:force_original_aspect_ratio=increase,"
                f"crop={width}:{height},setsar=1,fps={fps},format=yuv420p"
            )
            cmd = [
                ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
                "-ss", f"{start:.6f}", "-i", str(source), "-t", f"{end-start:.6f}",
                "-map", "0:v:0", "-map", "0:a?", "-vf", vf,
                "-c:v", "libx264", "-preset", args.preset, "-crf", str(args.crf),
                "-pix_fmt", "yuv420p", "-r", fps, "-fps_mode", "cfr",
                "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
                "-movflags", "+faststart", str(part)
            ]
            run_checked(cmd)
            parts.append(part)

        concat_file = tmpdir / "concat.txt"
        concat_file.write_text("".join(f"file '{p.as_posix()}'\n" for p in parts), encoding="utf-8")
        assembled = tmpdir / "assembled.mp4"
        run_checked([
            ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
            "-f", "concat", "-safe", "0", "-i", str(concat_file),
            "-c", "copy", "-movflags", "+faststart", str(assembled)
        ])
        run_checked([ffmpeg, "-hide_banner", "-v", "error", "-i", str(assembled), "-f", "null", "-"])
        staged_output = None
        try:
            with tempfile.NamedTemporaryFile(prefix=".shortform-", suffix=output.suffix or ".mp4", dir=output.parent, delete=False) as handle:
                staged_output = Path(handle.name)
            shutil.copy2(assembled, staged_output)
            final_probe = probe_media(staged_output)
            os.replace(staged_output, output)
        except Exception:
            if staged_output is not None:
                staged_output.unlink(missing_ok=True)
            raise

    print(json.dumps({
        "output": str(output),
        "source_sha256": probe["source"]["sha256"],
        "output_sha256": final_probe["source"]["sha256"],
        "render": render,
        "segments": len(edl["segments"]),
        "status": "rendered_and_decode_checked",
        "limitations": [
            "MVP renderer applies center-crop fullscreen framing only.",
            "Split-screen, blurred-bars, captions, tracking, transitions and automated QC are not implemented yet.",
            "60 fps CFR conversion does not create native 60 fps motion from lower-frame-rate footage."
        ]
    }, indent=2))
    return 0


def command_analyze_audio(args: argparse.Namespace) -> int:
    from .audio import analyze_audio

    source = Path(args.source).expanduser().resolve(strict=True)
    report = analyze_audio(
        source,
        model_size=args.model,
        device=args.device,
        language=args.language,
        transcribe=not args.no_transcribe,
        silence_dbfs=args.silence_dbfs
    )
    output = json.dumps(report, indent=2, ensure_ascii=False) + "\\n"
    if args.output:
        destination = Path(args.output).expanduser().resolve()
        if destination == source:
            raise PipelineError("Audio report cannot overwrite the source media")
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(output, encoding="utf-8")
    else:
        print(output, end="")
    return 0


def command_find_moments(args: argparse.Namespace) -> int:
    from .moments import detect_moments_file

    result = detect_moments_file(
        Path(args.analysis).expanduser().resolve(strict=True),
        Path(args.output).expanduser().resolve(),
        min_duration=args.min_duration,
        max_duration=args.max_duration,
        limit=args.limit
    )
    print(json.dumps({
        "output": str(Path(args.output).expanduser().resolve()),
        "candidate_count": result["candidate_count"],
        "method": result["method"],
        "human_review_required": True
    }, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="shortform-editor", description="Local-first short-form video pipeline foundation")
    sub = parser.add_subparsers(dest="command", required=True)
    probe = sub.add_parser("probe", help="inspect a video with ffprobe and fingerprint the source")
    probe.add_argument("source")
    probe.add_argument("-o", "--output")
    probe.set_defaults(func=command_probe)
    validate = sub.add_parser("validate-edl", help="validate EDL schema and semantic constraints")
    validate.add_argument("edl")
    validate.add_argument("--probe", help="optional ffprobe JSON report for duration checking")
    validate.set_defaults(func=command_validate)
    audio = sub.add_parser("analyze-audio", help="extract audio, detect silence candidates and optionally transcribe speech")
    audio.add_argument("source")
    audio.add_argument("-o", "--output")
    audio.add_argument("--model", default="small", choices=["tiny", "base", "small", "medium", "large-v3"])
    audio.add_argument("--device", default="auto", choices=["auto", "cpu", "cuda"])
    audio.add_argument("--language", help="optional ISO language code; omit for automatic detection")
    audio.add_argument("--no-transcribe", action="store_true", help="run audio energy/silence analysis without loading ASR")
    audio.add_argument("--silence-dbfs", type=float, default=-38.0)
    audio.set_defaults(func=command_analyze_audio)
    moments = sub.add_parser("find-moments", help="rank transcript-led candidate moments with transparent heuristic evidence")
    moments.add_argument("analysis", help="JSON report from analyze-audio")
    moments.add_argument("-o", "--output", required=True)
    moments.add_argument("--min-duration", type=float, default=12.0)
    moments.add_argument("--max-duration", type=float, default=55.0)
    moments.add_argument("--limit", type=int, default=10)
    moments.set_defaults(func=command_find_moments)
    render = sub.add_parser("render", help="render approved EDL segments into a vertical MP4")
    render.add_argument("source")
    render.add_argument("edl")
    render.add_argument("output")
    render.add_argument("--preset", default="medium", choices=["ultrafast", "fast", "medium", "slow", "veryslow"])
    render.add_argument("--crf", type=int, default=18)
    render.add_argument("--overwrite", action="store_true")
    render.set_defaults(func=command_render)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        if getattr(args, "silence_dbfs", -38.0) < -80 or getattr(args, "silence_dbfs", -38.0) > -10:
            raise PipelineError("--silence-dbfs must be between -80 and -10 dBFS")
        return args.func(args)
    except (PipelineError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
