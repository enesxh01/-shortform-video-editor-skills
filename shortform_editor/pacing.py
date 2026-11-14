from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .cli import PipelineError


MEANINGFUL_PAUSE_CUES = (
    "wait", "wow", "oh", "uh", "um", "well", "so", "listen", "look",
    "laugh", "laughter", "hmm", "you know"
)


def _overlap_ratio(start: float, end: float, regions: list[dict[str, Any]]) -> float:
    duration = max(0.001, end - start)
    overlap = 0.0
    for region in regions:
        left = max(start, float(region["start"]))
        right = min(end, float(region["end"]))
        if right > left:
            overlap += right - left
    return min(1.0, overlap / duration)


def _timecode(seconds: float) -> str:
    total_ms = max(0, round(seconds * 1000))
    hours, remainder = divmod(total_ms, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    secs, millis = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"


def analyze_pacing(analysis: dict[str, Any], candidates: dict[str, Any],
                   long_pause_seconds: float = 1.8) -> dict[str, Any]:
    transcript = analysis.get("analysis", {}).get("transcription", {})
    if transcript.get("status") != "completed":
        raise PipelineError("Pacing analysis requires a completed transcript")
    if long_pause_seconds < 0.5 or long_pause_seconds > 8:
        raise PipelineError("Long-pause threshold must be between 0.5 and 8 seconds")
    if candidates.get("source_fingerprint") != analysis.get("source", {}).get("fingerprint"):
        raise PipelineError("Candidate and audio-analysis source fingerprints do not match")
    segments = transcript.get("segments", [])
    silence_regions = analysis.get("analysis", {}).get("audio_metrics", {}).get("silence_regions", [])
    output_candidates = []

    for candidate in candidates.get("candidates", []):
        start = float(candidate["source_in_seconds"])
        end = float(candidate["source_out_seconds"])
        selected = [
            item for item in segments
            if float(item["end"]) > start and float(item["start"]) < end
        ]
        decisions = []
        for index, segment in enumerate(selected):
            seg_start = max(start, float(segment["start"]))
            seg_end = min(end, float(segment["end"]))
            if seg_end <= seg_start:
                continue
            decisions.append({
                "decision": "keep",
                "source_in": _timecode(seg_start),
                "source_out": _timecode(seg_end),
                "rationale": "Preserve the complete ASR utterance boundary; no automatic word-level cut is proposed.",
                "confidence": 0.9,
                "context_risk": "low"
            })
            if index + 1 >= len(selected):
                continue
            next_segment = selected[index + 1]
            gap_start = float(segment["end"])
            gap_end = float(next_segment["start"])
            gap = gap_end - gap_start
            if gap <= 0.25:
                continue
            left_text = str(segment.get("text", "")).lower()
            right_text = str(next_segment.get("text", "")).lower()
            context_text = left_text[-40:]
            meaningful = any(
                re.search(rf"(?<!\\w){re.escape(cue)}(?!\\w)", context_text)
                for cue in MEANINGFUL_PAUSE_CUES
            )
            silence_ratio = _overlap_ratio(gap_start, gap_end, silence_regions)
            if gap >= long_pause_seconds and silence_ratio >= 0.75 and not meaningful:
                decisions.append({
                    "decision": "trim",
                    "source_in": _timecode(gap_start),
                    "source_out": _timecode(gap_end),
                    "rationale": f"{gap:.2f}s gap is mostly energy-detected silence; proposed for human review only.",
                    "confidence": 0.45,
                    "context_risk": "medium"
                })
            else:
                decisions.append({
                    "decision": "preserve_pause",
                    "source_in": _timecode(gap_start),
                    "source_out": _timecode(gap_end),
                    "rationale": "Pause may carry delivery, reaction, turn-taking or context; preserve unless reviewed.",
                    "confidence": 0.75 if meaningful else 0.55,
                    "context_risk": "high" if meaningful else "medium"
                })

        # Flag adjacent repeated words for review; never remove them automatically.
        all_words = [
            str(word.get("text", "")).strip().lower()
            for item in selected for word in item.get("words", [])
        ]
        repetitions = []
        for index in range(1, len(all_words)):
            if all_words[index] and all_words[index] == all_words[index - 1]:
                repetitions.append(all_words[index])
        output_candidates.append({
            "candidate_id": candidate.get("candidate_id"),
            "source_in": _timecode(start),
            "source_out": _timecode(end),
            "decisions": decisions,
            "repeated_word_flags": sorted(set(repetitions)),
            "note": "Trim proposals are advisory only. No source ranges are changed or rendered."
        })

    return {
        "schema_version": "1.0",
        "method": "transcript_boundaries_and_silence_evidence",
        "candidate_count": len(output_candidates),
        "candidates": output_candidates,
        "limitations": [
            "ASR segment boundaries are not guaranteed sentence boundaries.",
            "Energy silence is not proof of dead air; silence may be meaningful.",
            "No automatic edit or render occurs; every trim suggestion requires human approval."
        ]
    }


def analyze_pacing_files(analysis_path: Path, candidates_path: Path, output_path: Path,
                         long_pause_seconds: float = 1.8) -> dict[str, Any]:
    try:
        analysis = json.loads(analysis_path.read_text(encoding="utf-8"))
        candidates = json.loads(candidates_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PipelineError(f"Could not read pacing inputs: {exc}") from exc
    result = analyze_pacing(analysis, candidates, long_pause_seconds)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return result
