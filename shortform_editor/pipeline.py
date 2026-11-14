from __future__ import annotations

import json
import hashlib
import os
import re
import tempfile
import time
from pathlib import Path
from typing import Any

from .audio import analyze_audio
from .caption_generation import generate_captions
from .feedback import apply_feedback, load_feedback
from .cli import PipelineError, file_stat_signature, probe_media, timestamp_seconds
from .moments import detect_moments
from .pacing import analyze_pacing
from .visual import analyze_visuals
from .captions import apply_face_aware_caption_positions


def _timecode(seconds: float) -> str:
    millis = max(0, round(seconds * 1000))
    hours, rest = divmod(millis, 3_600_000)
    minutes, rest = divmod(rest, 60_000)
    secs, ms = divmod(rest, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{ms:03d}"


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    staged = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", prefix=".shortform-json-",
                                         suffix=".tmp", dir=path.parent, delete=False) as handle:
            staged = Path(handle.name)
            handle.write(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(staged, path)
    finally:
        if staged is not None:
            staged.unlink(missing_ok=True)



def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _record_checkpoint(path: Path, state: dict[str, Any], state_path: Path) -> None:
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    state.setdefault("artifact_sha256", {})[path.name] = digest
    _write_json(state_path, state)


def _cached_artifact(output_dir: Path, filename: str, source_fingerprint: str,
                     fingerprint_path: tuple[str, ...], state: dict[str, Any]) -> dict[str, Any] | None:
    path = output_dir / filename
    expected_digest = state.get("artifact_sha256", {}).get(filename)
    if not expected_digest or not path.is_file():
        return None
    if hashlib.sha256(path.read_bytes()).hexdigest() != expected_digest:
        return None
    value = _read_json(path)
    if value is None:
        return None
    current: Any = value
    for key in fingerprint_path:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    if current != source_fingerprint:
        return None
    return value


def analyze_project(source: Path, output_dir: Path, model: str = "small",
                    device: str = "auto", top_candidates: int = 5,
                    layout: str = "fullscreen", include_visuals: bool = False,
                    split_top_source: Path | None = None, split_bottom_source: Path | None = None,
                    split_top_in: str = "00:00:00.000",
                    split_bottom_in: str = "00:00:00.000", resume: bool = False) -> dict[str, Any]:
    source = source.expanduser().resolve(strict=True)
    output_dir = output_dir.expanduser().resolve()
    if output_dir == source or source.is_relative_to(output_dir):
        raise PipelineError("Output directory must not be the source file or a parent containing the source")
    if not 1 <= top_candidates <= 20:
        raise PipelineError("Top candidate count must be between 1 and 20")
    if layout not in {"fullscreen", "blurred_bars_20_60_20", "split_vertical"}:
        raise PipelineError(f"Unsupported project layout: {layout}")
    if layout == "split_vertical" and (split_top_source is None or split_bottom_source is None):
        raise PipelineError("split_vertical requires --split-top-source and --split-bottom-source")
    if layout != "split_vertical" and (split_top_source is not None or split_bottom_source is not None):
        raise PipelineError("Split secondary sources can only be supplied with layout=split_vertical")
    if layout == "split_vertical":
        timestamp_seconds(split_top_in)
        timestamp_seconds(split_bottom_in)

    job_settings = {
        "source": str(source), "model": model, "device": device,
        "top_candidates": top_candidates, "layout": layout,
        "include_visuals": include_visuals,
        "split_top_source": str(split_top_source.expanduser().resolve()) if split_top_source else None,
        "split_bottom_source": str(split_bottom_source.expanduser().resolve()) if split_bottom_source else None,
        "split_top_in": split_top_in, "split_bottom_in": split_bottom_in
    }
    config_sha256 = hashlib.sha256(
        json.dumps(job_settings, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    state_path = output_dir / "job-state.json"
    if output_dir.exists() and any(output_dir.iterdir()):
        if not resume:
            raise PipelineError("Output directory is not empty; use --resume with the original settings or choose a new job directory")
        state = _read_json(state_path)
        if not state or state.get("config_sha256") != config_sha256:
            raise PipelineError("Cannot resume: job state is missing, invalid, or its source/options do not match this run")
    else:
        if resume:
            raise PipelineError("Cannot resume: output directory has no existing job state")
        output_dir.mkdir(parents=True, exist_ok=True)
        state = {"schema_version": "1.0", "config_sha256": config_sha256,
                 "settings": job_settings, "source_fingerprint": None}
        _write_json(state_path, state)

    stages = []
    warnings = []

    def save_progress(status: str, error: str | None = None) -> None:
        _write_json(output_dir / "manifest.json", {
            "schema_version": "1.0", "status": status, "source": str(source),
            "config_sha256": config_sha256, "completed_stages": stages,
            "warnings": warnings, "error": error
        })

    save_progress("running")

    def stage(name: str, function, cached: dict[str, Any] | None = None):
        if cached is not None:
            stages.append({"stage": name, "status": "reused_checkpoint", "duration_seconds": 0.0})
            save_progress("running")
            return cached
        started = time.perf_counter()
        result = function()
        stages.append({
            "stage": name, "status": "completed",
            "duration_seconds": round(time.perf_counter() - started, 3)
        })
        save_progress("running")
        return result

    try:
        # Always re-probe and re-hash the source before trusting cached artifacts.
        probe = stage("probe", lambda: probe_media(source))
        source_signature = file_stat_signature(source)
        source_fingerprint = probe["source"]["fingerprint"]
        saved_fingerprint = state.get("source_fingerprint")
        if saved_fingerprint and saved_fingerprint != source_fingerprint:
            raise PipelineError("Cannot resume: source fingerprint changed since the original job")
        state["source_fingerprint"] = source_fingerprint
        _write_json(state_path, state)
        _write_json(output_dir / "probe.json", probe)

        split_probes = {}
        split_paths = {}
        split_signatures = {}
        if layout == "split_vertical":
            for key, raw_path in (("split_top", split_top_source), ("split_bottom", split_bottom_source)):
                path = raw_path.expanduser().resolve(strict=True)
                if path == source:
                    raise PipelineError(f"{key} must be a separate source file, not the primary input")
                split_paths[key] = path
                split_probes[key] = probe_media(path)
                split_signatures[key] = file_stat_signature(path)

        cached_audio = _cached_artifact(output_dir, "audio-analysis.json", source_fingerprint, ("source", "fingerprint"), state) if resume else None
        audio = stage("audio", lambda: analyze_audio(source, model_size=model, device=device, probe_report=probe), cached_audio)
        if audio.get("source", {}).get("fingerprint") != source_fingerprint:
            raise PipelineError("Source media changed between initial probe and audio analysis; restart the project")
        if file_stat_signature(source) != source_signature:
            raise PipelineError("Source media changed during audio analysis; restart the project")
        _write_json(output_dir / "audio-analysis.json", audio)
        _record_checkpoint(output_dir / "audio-analysis.json", state, state_path)

        cached_candidates = _cached_artifact(output_dir, "candidates.json", source_fingerprint, ("source_fingerprint",), state) if resume else None
        if cached_candidates is not None:
            candidates = stage("moment_detection", lambda: None, cached_candidates)
            candidates = stage("performance_feedback", lambda: candidates, candidates)
        else:
            candidates = stage("moment_detection", lambda: detect_moments(audio, limit=top_candidates))

        def apply_local_feedback():
            try:
                return apply_feedback(candidates, load_feedback())
            except PipelineError as exc:
                warnings.append(f"Local feedback was ignored: {exc}")
                result = dict(candidates)
                result["feedback_learning"] = {
                    "status": "ignored_invalid_feedback",
                    "records_used": 0,
                    "reason": str(exc)
                }
                return result

        if cached_candidates is None:
            candidates = stage("performance_feedback", apply_local_feedback)
        candidates["source_fingerprint"] = source_fingerprint
        _write_json(output_dir / "candidates.json", candidates)
        _record_checkpoint(output_dir / "candidates.json", state, state_path)

        cached_pacing = _cached_artifact(output_dir, "pacing.json", source_fingerprint, ("source_fingerprint",), state) if resume else None
        pacing = stage("retention_pacing", lambda: analyze_pacing(audio, candidates), cached_pacing)
        pacing["source_fingerprint"] = source_fingerprint
        _write_json(output_dir / "pacing.json", pacing)
        _record_checkpoint(output_dir / "pacing.json", state, state_path)
        pacing_by_id = {item.get("candidate_id"): item for item in pacing.get("candidates", [])}

        visuals = None
        if include_visuals:
            try:
                candidate_regions = [
                    (item["source_in_seconds"], item["source_out_seconds"])
                    for item in candidates["candidates"]
                ]
                cached_visuals = _cached_artifact(output_dir, "visual-analysis.json", source_fingerprint, ("source", "fingerprint"), state) if resume else None
                visuals = stage(
                    "visual_analysis",
                    lambda: analyze_visuals(source, regions=candidate_regions, probe_report=probe),
                    cached_visuals
                )
                if visuals.get("source", {}).get("fingerprint") != probe["source"]["fingerprint"]:
                    raise PipelineError("Source media changed between initial probe and visual analysis; restart the project")
                if file_stat_signature(source) != source_signature:
                    raise PipelineError("Source media changed during visual analysis; restart the project")
                _write_json(output_dir / "visual-analysis.json", visuals)
                _record_checkpoint(output_dir / "visual-analysis.json", state, state_path)
            except PipelineError as exc:
                warnings.append(f"Visual analysis unavailable: {exc}")

        final_source_signature = stage("source_integrity_check", lambda: file_stat_signature(source))
        if final_source_signature != source_signature:
            raise PipelineError("Source media changed during project analysis; discard this job and restart from the new source version")
        for key, path in split_paths.items():
            if file_stat_signature(path) != split_signatures[key]:
                raise PipelineError(f"{key} media changed during project analysis; restart with stable split sources")

        video_stream = next(s for s in probe["streams"] if s.get("codec_type") == "video")
        time_base = video_stream.get("time_base") or "1/90000"
        source_fps = video_stream.get("avg_frame_rate") or "30/1"
        try:
            from fractions import Fraction
            if Fraction(source_fps) <= 0:
                source_fps = "30/1"
        except (ValueError, ZeroDivisionError):
            source_fps = "30/1"

        drafts = []
        for candidate in candidates["candidates"]:
            try:
                caption_report = generate_captions(audio, candidate, layout=layout)
                captions = caption_report["captions"]
            except PipelineError as exc:
                captions = []
                warnings.append(f"No captions for {candidate['candidate_id']}: {exc}")

            safe_id = re.sub(r"[^a-zA-Z0-9_-]", "_", candidate["candidate_id"])
            segment_edl = {
                "id": candidate["candidate_id"],
                "source_in": _timecode(candidate["source_in_seconds"]),
                "source_out": _timecode(candidate["source_out_seconds"]),
                "timeline_start": "00:00:00.000",
                "layout": layout,
                "reason": f"{candidate['family']}: {candidate['transcript_excerpt'][:180]}",
                "confidence": candidate["confidence"],
                "captions": captions
            }
            if layout == "split_vertical":
                clip_duration = candidate["source_out_seconds"] - candidate["source_in_seconds"]
                split_specs = {}
                split_valid = True
                for key, start_text in (("split_top", split_top_in), ("split_bottom", split_bottom_in)):
                    split_start = timestamp_seconds(start_text)
                    split_end = split_start + clip_duration
                    split_duration = float(split_probes[key].get("format", {}).get("duration") or 0)
                    if split_end > split_duration + 0.05:
                        warnings.append(f"Skipped {candidate['candidate_id']}: {key} source is too short for {clip_duration:.2f}s")
                        split_valid = False
                        break
                    split_specs[key] = {
                        "path": str(split_paths[key]),
                        "fingerprint": split_probes[key]["source"]["fingerprint"],
                        "source_in": _timecode(split_start),
                        "source_out": _timecode(split_end)
                    }
                if not split_valid:
                    continue
                segment_edl.update(split_specs)

            pacing_item = pacing_by_id.get(candidate["candidate_id"])
            if pacing_item:
                segment_edl["pacing_review"] = {
                    "decisions": pacing_item.get("decisions", []),
                    "repeated_word_flags": pacing_item.get("repeated_word_flags", []),
                    "note": pacing_item.get("note", "Pacing proposals are advisory; no cuts are applied automatically.")
                }
            if visuals and layout == "fullscreen":
                crop_frames = [
                    item for item in visuals["analysis"]["crop_keyframes"]
                    if candidate["source_in_seconds"] <= item["time_seconds"] <= candidate["source_out_seconds"]
                ]
                if any(item["subject_evidence"] in {"face_detection", "face_tracking"} for item in crop_frames):
                    segment_edl["crop_keyframes"] = [
                        {"time_seconds": item["time_seconds"], "crop_9_16": item["crop_9_16"], "scene_cut": item.get("scene_cut", False)}
                        for item in crop_frames
                    ]
                    segment_edl["captions"] = apply_face_aware_caption_positions(
                        captions,
                        crop_frames,
                        int(visuals["source"]["width"]),
                        int(visuals["source"]["height"])
                    )

            edl = {
                "schema_version": "1.0",
                "project_id": probe["source"]["sha256"][:12],
                "source": {
                    "fingerprint": probe["source"]["fingerprint"],
                    "time_base": time_base,
                    "frame_rate": source_fps,
                    "variable_frame_rate": probe.get("frame_timing", {}).get("variable_frame_rate")
                },
                "render": {
                    "width": 1080,
                    "height": 1920,
                    "fps_target": "60/1",
                    "fps_mode": "cfr",
                    "fps_conversion": "duplicate_drop",
                    "container": "mp4",
                    "video_codec": "h264",
                    "audio_codec": "aac"
                },
                "segments": [segment_edl],
                "approval": {"status": "draft", "approved_by_user": False}
            }
            edl_path = output_dir / "edl" / f"{safe_id}.json"
            _write_json(edl_path, edl)
            drafts.append({
                "candidate_id": candidate["candidate_id"],
                "edl": str(edl_path),
                "caption_count": len(captions),
                "approval_required": True
            })

        status = "partial" if warnings or not candidates["candidates"] else "analysis_complete_drafts_pending_review"
        manifest = {
            "schema_version": "1.0",
            "status": status,
            "source": {
                "path": str(source),
                "fingerprint": probe["source"]["fingerprint"],
                "duration_seconds": probe.get("format", {}).get("duration")
            },
            "stages": stages,
            "artifacts": {
                "probe": "probe.json",
                "audio": "audio-analysis.json",
                "candidates": "candidates.json",
                "pacing": "pacing.json",
                "visuals": "visual-analysis.json" if visuals else None
            },
            "draft_edls": drafts,
            "feedback_learning": candidates.get("feedback_learning", {"status": "not_available"}),
            "warnings": warnings,
            "next_step": "Review candidate boundaries and EDL drafts, add/adjust layouts and captions, then explicitly set approval.status=approved and approved_by_user=true before rendering."
        }
        _write_json(output_dir / "manifest.json", manifest)
        return manifest
    except KeyboardInterrupt:
        save_progress("cancelled", "Interrupted by user. Completed stage artifacts are preserved; rerun into a new empty job directory.")
        raise
    except Exception as exc:
        save_progress("failed", f"{type(exc).__name__}: {exc}")
        raise
