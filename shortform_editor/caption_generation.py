from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .cli import PipelineError


def _timecode(seconds: float) -> str:
    millis = max(0, round(seconds * 1000))
    hours, rest = divmod(millis, 3_600_000)
    minutes, rest = divmod(rest, 60_000)
    secs, ms = divmod(rest, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{ms:03d}"


def generate_captions(analysis: dict[str, Any], candidate: dict[str, Any],
                      layout: str = "fullscreen", max_words: int = 5,
                      max_chars: int = 28, max_duration: float = 2.2) -> dict[str, Any]:
    if layout not in {"fullscreen", "split_vertical", "blurred_bars_20_60_20"}:
        raise PipelineError(f"Unsupported caption layout: {layout}")
    if not 2 <= max_words <= 10 or not 12 <= max_chars <= 60 or not 0.8 <= max_duration <= 5:
        raise PipelineError("Caption grouping bounds are outside safe limits")
    source_fingerprint = analysis.get("source", {}).get("fingerprint")
    if candidate.get("source_fingerprint") != source_fingerprint:
        raise PipelineError("Candidate and audio-analysis source fingerprints do not match")
    transcription = analysis.get("analysis", {}).get("transcription", {})
    if transcription.get("status") != "completed":
        raise PipelineError("Caption generation requires completed transcription")
    start_bound = float(candidate["source_in_seconds"])
    end_bound = float(candidate["source_out_seconds"])
    words = [
        word for word in transcription.get("words", [])
        if float(word["start"]) >= start_bound and float(word["end"]) <= end_bound
        and str(word.get("text", "")).strip()
    ]
    if not words:
        raise PipelineError("No word-level timestamps exist inside this candidate; rerun ASR with word timestamps enabled")

    captions = []
    group = []

    def flush() -> None:
        nonlocal group
        if not group:
            return
        text = "".join(str(word["text"]) for word in group).strip()
        if not text:
            group = []
            return
        start = float(group[0]["start"])
        end = float(group[-1]["end"])
        captions.append({
            "start": _timecode(start),
            "end": _timecode(end),
            "text": text,
            "words": [
                {"text": str(word["text"]).strip(), "start": _timecode(float(word["start"])), "end": _timecode(float(word["end"]))}
                for word in group
            ],
            "style": "kino",
            "position": "center" if layout == "split_vertical" else "auto"
        })
        group = []

    for word in words:
        token = str(word["text"]).strip()
        start = float(word["start"])
        end = float(word["end"])
        if end <= start:
            continue
        if group:
            group_text = "".join(str(item["text"]) for item in group).strip()
            gap = start - float(group[-1]["end"])
            proposed_text = group_text + " " + token
            elapsed = end - float(group[0]["start"])
            sentence_end = group_text.endswith((".", "?", "!", "…", ":"))
            if (
                gap > 0.45 or len(group) >= max_words or len(proposed_text) > max_chars
                or elapsed > max_duration or sentence_end
            ):
                flush()
        group.append(word)
    flush()

    return {
        "schema_version": "1.0",
        "source_fingerprint": source_fingerprint,
        "candidate_id": candidate.get("candidate_id"),
        "layout": layout,
        "captions": captions,
        "limitations": [
            "Word timestamps and punctuation come from ASR and require spelling/timing review.",
            "Karaoke is a word-level highlight, not phoneme-level synchronization.",
            "The renderer uses a system Arial-compatible font fallback; exact typography can vary by machine."
        ]
    }


def generate_captions_file(analysis_path: Path, candidates_path: Path, output_path: Path,
                           candidate_id: str | None = None, layout: str = "fullscreen") -> dict[str, Any]:
    try:
        analysis = json.loads(analysis_path.read_text(encoding="utf-8"))
        candidate_report = json.loads(candidates_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PipelineError(f"Could not read caption inputs: {exc}") from exc
    candidates = candidate_report.get("candidates", [])
    if candidate_id:
        candidate = next((item for item in candidates if item.get("candidate_id") == candidate_id), None)
        if candidate is None:
            raise PipelineError(f"Candidate ID not found: {candidate_id}")
    elif candidates:
        candidate = candidates[0]
    else:
        raise PipelineError("Candidate report contains no candidates")
    result = generate_captions(analysis, candidate, layout)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return result
