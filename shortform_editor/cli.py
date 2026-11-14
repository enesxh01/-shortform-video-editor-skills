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
            for split_key in ("split_top", "split_bottom"):
                split_source = segment.get(split_key)
                if split_source:
                    split_start = timestamp_seconds(split_source["source_in"])
                    split_end = timestamp_seconds(split_source["source_out"])
                    if split_end <= split_start:
                        messages.append(f"segments[{index}].{split_key}.source_out must be greater than source_in")
                    if abs((split_end - split_start) - (end - start)) > 0.1:
                        messages.append(f"segments[{index}].{split_key} duration must match the primary segment within 100 ms")
            for caption_index, caption in enumerate(segment.get("captions", [])):
                caption_start = timestamp_seconds(caption["start"])
                caption_end = timestamp_seconds(caption["end"])
                if caption_end <= caption_start:
                    messages.append(f"segments[{index}].captions[{caption_index}] end must be after start")
                if caption_start < start or caption_end > end:
                    messages.append(f"segments[{index}].captions[{caption_index}] must fit inside the segment source range")
                previous_word_end = caption_start
                for word_index, word in enumerate(caption.get("words", [])):
                    word_start = timestamp_seconds(word["start"])
                    word_end = timestamp_seconds(word["end"])
                    if word_end <= word_start or word_start < previous_word_end or word_start < caption_start or word_end > caption_end:
                        messages.append(f"segments[{index}].captions[{caption_index}].words[{word_index}] has invalid or unordered timing")
                    previous_word_end = word_end
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


def _resolve_edl_path(edl_path: Path, raw_path: str) -> Path:
    candidate = Path(raw_path).expanduser()
    if not candidate.is_absolute():
        candidate = edl_path.parent / candidate
    return candidate.resolve(strict=True)


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
    if edl.get("render", {}).get("fps_mode") != "cfr":
        raise PipelineError("The current renderer supports fps_mode=cfr only")
    if edl.get("render", {}).get("fps_conversion") != "duplicate_drop":
        raise PipelineError("The current renderer supports fps_conversion=duplicate_drop only")
    if edl.get("render", {}).get("video_codec") not in (None, "h264"):
        raise PipelineError("The current renderer supports H.264 video only")
    if edl.get("render", {}).get("audio_codec") not in (None, "aac"):
        raise PipelineError("The current renderer supports AAC audio only")

    probe = probe_media(source)
    raw_duration = probe.get("format", {}).get("duration")
    duration = float(raw_duration) if raw_duration is not None else None
    errors = validate_edl(edl, duration, probe.get("source", {}).get("fingerprint"))
    if errors:
        raise PipelineError("Refusing to render invalid EDL:\\n- " + "\\n- ".join(errors))
    if edl["approval"]["status"] != "approved" or not edl["approval"]["approved_by_user"]:
        raise PipelineError("Rendering final output requires explicit user approval in the EDL")

    ffmpeg = require_tool("ffmpeg")
    render = edl["render"]
    width, height, fps = render["width"], render["height"], render["fps_target"]
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists() and not args.overwrite:
        raise PipelineError(f"Output already exists (use --overwrite): {output}")

    # Validate and fingerprint both secondary sources before any render work begins.
    split_paths: dict[tuple[int, str], Path] = {}
    for index, segment in enumerate(edl["segments"]):
        if segment["layout"] != "split_vertical":
            continue
        for key in ("split_top", "split_bottom"):
            spec = segment[key]
            path = _resolve_edl_path(edl_path, spec["path"])
            if path in {source, output, edl_path}:
                raise PipelineError(f"segments[{index}].{key} must not alias the primary source, EDL or output")
            secondary_probe = probe_media(path)
            if secondary_probe["source"]["fingerprint"] != spec["fingerprint"]:
                raise PipelineError(f"segments[{index}].{key} fingerprint does not match its file")
            secondary_duration = float(secondary_probe.get("format", {}).get("duration") or 0)
            if timestamp_seconds(spec["source_out"]) > secondary_duration + 0.05:
                raise PipelineError(f"segments[{index}].{key} source_out exceeds secondary source duration")
            split_paths[(index, key)] = path

    from .captions import ffmpeg_subtitles_filter, write_ass_subtitles

    with tempfile.TemporaryDirectory(prefix="shortform-render-") as tmp:
        tmpdir = Path(tmp)
        parts: list[Path] = []
        for index, segment in enumerate(edl["segments"]):
            clip_start = timestamp_seconds(segment["source_in"])
            clip_end = timestamp_seconds(segment["source_out"])
            clip_duration = clip_end - clip_start
            part = tmpdir / f"part-{index:04d}.mp4"
            layout = segment["layout"]
            ass_path = tmpdir / f"captions-{index:04d}.ass"
            subtitle_path = write_ass_subtitles(segment, layout, clip_start, ass_path)
            subtitle_filter = ffmpeg_subtitles_filter(subtitle_path) if subtitle_path else None

            cmd = [ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
                   "-ss", f"{clip_start:.6f}", "-i", str(source)]
            if layout == "split_vertical":
                top = segment["split_top"]
                bottom = segment["split_bottom"]
                cmd += ["-ss", f"{timestamp_seconds(top['source_in']):.6f}", "-i", str(split_paths[(index, "split_top")])]
                cmd += ["-ss", f"{timestamp_seconds(bottom['source_in']):.6f}", "-i", str(split_paths[(index, "split_bottom")])]
            cmd += ["-t", f"{clip_duration:.6f}"]

            if layout == "fullscreen":
                vf = (
                    f"scale={width}:{height}:force_original_aspect_ratio=increase,"
                    f"crop={width}:{height},setsar=1,fps={fps},format=yuv420p"
                )
                if subtitle_filter:
                    vf += f",{subtitle_filter}"
                cmd += ["-map", "0:v:0", "-map", "0:a?", "-vf", vf]
            elif layout == "blurred_bars_20_60_20":
                center_height = int(height * 0.6) // 2 * 2
                bar_offset = (height - center_height) // 2
                graph = (
                    f"[0:v]split=2[bgsrc][fgsrc];"
                    f"[bgsrc]scale={width}:{height}:force_original_aspect_ratio=increase,"
                    f"crop={width}:{height},boxblur=20:10[bg];"
                    f"[fgsrc]scale={width}:{center_height}:force_original_aspect_ratio=increase,"
                    f"crop={width}:{center_height}[fg];"
                    f"[bg][fg]overlay=0:{bar_offset},setsar=1,fps={fps},format=yuv420p[vbase]"
                )
                if subtitle_filter:
                    graph += f";[vbase]{subtitle_filter}[vout]"
                else:
                    graph += ";[vbase]null[vout]"
                cmd += ["-filter_complex", graph, "-map", "[vout]", "-map", "0:a?"]
            elif layout == "split_vertical":
                panel_height = height // 2
                graph = (
                    f"[1:v]scale={width}:{panel_height}:force_original_aspect_ratio=increase,"
                    f"crop={width}:{panel_height},setsar=1[top];"
                    f"[2:v]scale={width}:{panel_height}:force_original_aspect_ratio=increase,"
                    f"crop={width}:{panel_height},setsar=1[bottom];"
                    f"[top][bottom]vstack=inputs=2,setsar=1,fps={fps},format=yuv420p[vbase]"
                )
                if subtitle_filter:
                    graph += f";[vbase]{subtitle_filter}[vout]"
                else:
                    graph += ";[vbase]null[vout]"
                cmd += ["-filter_complex", graph, "-map", "[vout]", "-map", "0:a?"]
            else:
                raise PipelineError(f"Unsupported layout: {layout}")

            cmd += [
                "-c:v", "libx264", "-preset", args.preset, "-crf", str(args.crf),
                "-pix_fmt", "yuv420p", "-r", fps, "-fps_mode", "cfr",
                "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
                "-movflags", "+faststart", str(part)
            ]
            run_checked(cmd)
            parts.append(part)

        concat_file = tmpdir / "concat.txt"
        concat_file.write_text("".join(f"file '{p.as_posix()}'\\n" for p in parts), encoding="utf-8")
        assembled = tmpdir / "assembled.mp4"
        run_checked([
            ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
            "-f", "concat", "-safe", "0", "-i", str(concat_file),
            "-c", "copy", "-movflags", "+faststart", str(assembled)
        ])
        run_checked([ffmpeg, "-hide_banner", "-v", "error", "-i", str(assembled), "-f", "null", "-"])
        staged_output = None
        try:
            with tempfile.NamedTemporaryFile(prefix=".shortform-", suffix=output.suffix, dir=output.parent, delete=False) as handle:
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
        "layouts": sorted({segment["layout"] for segment in edl["segments"]}),
        "captions": sum(len(segment.get("captions", [])) for segment in edl["segments"]),
        "status": "rendered_and_decode_checked",
        "limitations": [
            "Split layout uses explicit top and bottom secondary video sources; primary source audio is retained.",
            "Blurred-bars layout uses a blurred full-frame background and sharp 60% center panel.",
            "Kino captions use ASS/libass; word karaoke requires word timings in the EDL.",
            "CPU libx264 is used; CUDA/NVENC encoding is not implemented.",
            "60 fps CFR conversion does not create native 60 fps motion from lower-frame-rate footage.",
            "Decode success is not a substitute for human visual and audio review."
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


def command_analyze_pacing(args: argparse.Namespace) -> int:
    from .pacing import analyze_pacing_files

    result = analyze_pacing_files(
        Path(args.analysis).expanduser().resolve(strict=True),
        Path(args.candidates).expanduser().resolve(strict=True),
        Path(args.output).expanduser().resolve(),
        long_pause_seconds=args.long_pause
    )
    print(json.dumps({
        "output": str(Path(args.output).expanduser().resolve()),
        "candidate_count": result["candidate_count"],
        "method": result["method"],
        "automatic_edits": False
    }, indent=2))
    return 0


def command_analyze_visuals(args: argparse.Namespace) -> int:
    from .visual import analyze_visuals

    source = Path(args.source).expanduser().resolve(strict=True)
    report = analyze_visuals(
        source,
        sample_rate=args.sample_rate,
        max_frames=args.max_frames,
        detect_faces=not args.no_face_detection
    )
    output = json.dumps(report, indent=2, ensure_ascii=False) + "\\n"
    if args.output:
        destination = Path(args.output).expanduser().resolve()
        if destination == source:
            raise PipelineError("Visual report cannot overwrite the source media")
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(output, encoding="utf-8")
    else:
        print(output, end="")
    return 0


def command_generate_captions(args: argparse.Namespace) -> int:
    from .caption_generation import generate_captions_file

    result = generate_captions_file(
        Path(args.analysis).expanduser().resolve(strict=True),
        Path(args.candidates).expanduser().resolve(strict=True),
        Path(args.output).expanduser().resolve(),
        candidate_id=args.candidate_id,
        layout=args.layout
    )
    print(json.dumps({
        "output": str(Path(args.output).expanduser().resolve()),
        "candidate_id": result["candidate_id"],
        "caption_count": len(result["captions"]),
        "layout": result["layout"]
    }, indent=2))
    return 0


def command_qc(args: argparse.Namespace) -> int:
    from .qc import run_qc

    report = run_qc(
        Path(args.source).expanduser().resolve(strict=True),
        expected_width=args.width,
        expected_height=args.height,
        expected_fps=args.fps
    )
    output = json.dumps(report, indent=2, ensure_ascii=False) + "\\n"
    if args.output:
        destination = Path(args.output).expanduser().resolve()
        if destination == Path(args.source).expanduser().resolve():
            raise PipelineError("QC report cannot overwrite the media file")
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(output, encoding="utf-8")
    else:
        print(output, end="")
    return 0 if report["status"] == "passed" else 1


def command_record_feedback(args: argparse.Namespace) -> int:
    from .feedback import DEFAULT_FEEDBACK_PATH, record_feedback

    candidates = json.loads(Path(args.candidates).expanduser().resolve(strict=True).read_text(encoding="utf-8"))
    feedback_path = Path(args.feedback_file).expanduser().resolve() if args.feedback_file else DEFAULT_FEEDBACK_PATH
    record = record_feedback(candidates, args.candidate_id, args.decision, feedback_path, args.reason)
    print(json.dumps({
        "feedback_file": str(feedback_path),
        "candidate_id": record["candidate_id"],
        "decision": record["decision"],
        "stored": True
    }, indent=2))
    return 0


def command_apply_feedback(args: argparse.Namespace) -> int:
    from .feedback import DEFAULT_FEEDBACK_PATH, apply_feedback_file

    feedback_path = Path(args.feedback_file).expanduser().resolve() if args.feedback_file else DEFAULT_FEEDBACK_PATH
    result = apply_feedback_file(
        Path(args.candidates).expanduser().resolve(strict=True),
        feedback_path,
        Path(args.output).expanduser().resolve(),
        min_observations=args.min_observations
    )
    print(json.dumps({
        "output": str(Path(args.output).expanduser().resolve()),
        "records_used": result.get("feedback_learning", {}).get("records_used", 0),
        "status": result.get("feedback_learning", {}).get("status")
    }, indent=2))
    return 0


def command_repair(args: argparse.Namespace) -> int:
    from .repair import repair_technical_export

    result = repair_technical_export(
        Path(args.source).expanduser().resolve(strict=True),
        Path(args.output).expanduser().resolve(),
        width=args.width,
        height=args.height,
        fps=args.fps,
        crf=args.crf,
        preset=args.preset,
        overwrite=args.overwrite
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result["qc_after_repair"]["status"] == "passed" else 1


def command_analyze_project(args: argparse.Namespace) -> int:
    from .pipeline import analyze_project

    manifest = analyze_project(
        Path(args.source).expanduser().resolve(strict=True),
        Path(args.output_dir).expanduser().resolve(),
        model=args.model,
        device=args.device,
        top_candidates=args.top,
        layout=args.layout,
        include_visuals=args.visuals
    )
    print(json.dumps(manifest, indent=2, ensure_ascii=False))
    return 0 if manifest["status"] != "cancelled" else 130


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
    pacing = sub.add_parser("analyze-pacing", help="propose context-safe pacing decisions for ranked candidates")
    pacing.add_argument("analysis", help="audio-analysis JSON")
    pacing.add_argument("candidates", help="candidate JSON from find-moments")
    pacing.add_argument("-o", "--output", required=True)
    pacing.add_argument("--long-pause", type=float, default=1.8)
    pacing.set_defaults(func=command_analyze_pacing)
    visuals = sub.add_parser("analyze-visuals", help="sample scenes and propose conservative face-guided 9:16 crop keyframes")
    visuals.add_argument("source")
    visuals.add_argument("-o", "--output")
    visuals.add_argument("--sample-rate", type=float, default=1.0)
    visuals.add_argument("--max-frames", type=int, default=120)
    visuals.add_argument("--no-face-detection", action="store_true")
    visuals.set_defaults(func=command_analyze_visuals)
    captions = sub.add_parser("generate-captions", help="group ASR word timings into Kino caption events")
    captions.add_argument("analysis", help="audio-analysis JSON")
    captions.add_argument("candidates", help="candidate JSON from find-moments")
    captions.add_argument("-o", "--output", required=True)
    captions.add_argument("--candidate-id")
    captions.add_argument("--layout", default="fullscreen", choices=["fullscreen", "split_vertical", "blurred_bars_20_60_20"])
    captions.set_defaults(func=command_generate_captions)
    qc = sub.add_parser("qc", help="run technical black/freeze/codec/frame-rate/audio-peak checks")
    qc.add_argument("source")
    qc.add_argument("-o", "--output")
    qc.add_argument("--width", type=int, default=1080)
    qc.add_argument("--height", type=int, default=1920)
    qc.add_argument("--fps", default="60/1")
    qc.set_defaults(func=command_qc)
    feedback = sub.add_parser("record-feedback", help="store a local human editorial decision for a candidate")
    feedback.add_argument("candidates")
    feedback.add_argument("--candidate-id", required=True)
    feedback.add_argument("--decision", required=True, choices=["approve", "edited", "reject"])
    feedback.add_argument("--reason", default="")
    feedback.add_argument("--feedback-file")
    feedback.set_defaults(func=command_record_feedback)
    learn = sub.add_parser("apply-feedback", help="apply learned local category preferences to candidate ranking")
    learn.add_argument("candidates")
    learn.add_argument("-o", "--output", required=True)
    learn.add_argument("--feedback-file")
    learn.add_argument("--min-observations", type=int, default=3)
    learn.set_defaults(func=command_apply_feedback)
    repair = sub.add_parser("repair", help="write a separate normalized H.264/AAC export and rerun technical QC")
    repair.add_argument("source")
    repair.add_argument("output")
    repair.add_argument("--width", type=int, default=1080)
    repair.add_argument("--height", type=int, default=1920)
    repair.add_argument("--fps", default="60/1")
    repair.add_argument("--crf", type=int, default=18)
    repair.add_argument("--preset", default="medium", choices=["ultrafast", "fast", "medium", "slow", "veryslow"])
    repair.add_argument("--overwrite", action="store_true")
    repair.set_defaults(func=command_repair)
    analyze = sub.add_parser("analyze-project", help="run source-to-candidate analysis and create draft EDLs")
    analyze.add_argument("source")
    analyze.add_argument("-o", "--output-dir", required=True)
    analyze.add_argument("--model", default="small", choices=["tiny", "base", "small", "medium", "large-v3"])
    analyze.add_argument("--device", default="auto", choices=["auto", "cpu", "cuda"])
    analyze.add_argument("--top", type=int, default=5)
    analyze.add_argument("--layout", default="fullscreen", choices=["fullscreen", "blurred_bars_20_60_20"])
    analyze.add_argument("--visuals", action="store_true", help="run optional OpenCV visual sampling")
    analyze.set_defaults(func=command_analyze_project)
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
