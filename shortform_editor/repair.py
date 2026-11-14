from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path
from typing import Any

from .cli import PipelineError, probe_media, require_tool, run_checked
from .qc import run_qc


def repair_technical_export(source: Path, output: Path, width: int = 1080,
                            height: int = 1920, fps: str = "60/1",
                            crf: int = 18, preset: str = "medium",
                            overwrite: bool = False) -> dict[str, Any]:
    source = source.expanduser().resolve(strict=True)
    output = output.expanduser().resolve()
    if source == output:
        raise PipelineError("Repair output must be a new file; source media is never overwritten")
    if output.suffix.lower() != ".mp4":
        raise PipelineError("Repair output must use the .mp4 extension")
    if width < 360 or height < 640 or width % 2 or height % 2:
        raise PipelineError("Repair dimensions must be even and at least 360x640")
    if not 0 <= crf <= 51:
        raise PipelineError("CRF must be between 0 and 51")
    if preset not in {"ultrafast", "fast", "medium", "slow", "veryslow"}:
        raise PipelineError("Unsupported x264 preset")
    if output.exists() and not overwrite:
        raise PipelineError(f"Output already exists (use --overwrite): {output}")

    source_probe = probe_media(source)
    duration = float(source_probe.get("format", {}).get("duration") or 0)
    if duration <= 0:
        raise PipelineError("Cannot repair media with unknown duration")
    ffmpeg = require_tool("ffmpeg")
    output.parent.mkdir(parents=True, exist_ok=True)
    vf = (
        f"scale={width}:{height}:force_original_aspect_ratio=increase,"
        f"crop={width}:{height},setsar=1,fps={fps},format=yuv420p"
    )
    staged = None
    try:
        with tempfile.NamedTemporaryFile(prefix=".shortform-repair-", suffix=".mp4",
                                         dir=output.parent, delete=False) as handle:
            staged = Path(handle.name)
        run_checked([
            ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
            "-i", str(source), "-map", "0:v:0", "-map", "0:a?",
            "-vf", vf, "-c:v", "libx264", "-preset", preset, "-crf", str(crf),
            "-pix_fmt", "yuv420p", "-r", fps, "-fps_mode", "cfr",
            "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
            "-movflags", "+faststart", str(staged)
        ])
        run_checked([ffmpeg, "-hide_banner", "-v", "error", "-i", str(staged), "-f", "null", "-"])
        final_probe = probe_media(staged)
        os.replace(staged, output)
        staged = None
    finally:
        if staged is not None:
            staged.unlink(missing_ok=True)

    qc = run_qc(output, width, height, fps)
    return {
        "source": str(source),
        "source_fingerprint": source_probe["source"]["fingerprint"],
        "output": str(output),
        "output_fingerprint": final_probe["source"]["fingerprint"],
        "repair_actions": [
            "Re-encoded video as H.264 with libx264.",
            f"Normalized frame size to {width}x{height} and frame rate to {fps} CFR.",
            "Normalized audio to AAC 48 kHz where an audio stream exists.",
            "Preserved source file and wrote a separate output."
        ],
        "qc_after_repair": qc,
        "unresolved": [
            "Black/frozen source intervals are not synthesized or removed.",
            "Clipping, true-peak, perceived loudness, caption spelling, crop/story quality and A/V sync by listening are not repaired."
        ]
    }
