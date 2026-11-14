from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from .cli import PipelineError, timestamp_seconds


HOOK_CUES = (
    "but", "however", "until", "suddenly", "turns out", "the truth", "the reason",
    "what happened", "i realized", "you need to", "here is why", "here's why",
    "the problem", "the secret", "nobody", "never", "always"
)
PAYOFF_CUES = (
    "because", "that's why", "so that's", "in the end", "finally", "which means",
    "the answer", "it worked", "it failed", "that was", "therefore", "as a result"
)
COMEDY_CUES = ("laugh", "laughter", "funny", "joke", "kidding", "haha", "lol")
KNOWLEDGE_CUES = ("how to", "the reason", "for example", "means that", "you can", "the difference")
CONFLICT_CUES = ("wrong", "disagree", "no way", "you're wrong", "you are wrong", "argue", "fight")


def _text(segments: list[dict[str, Any]]) -> str:
    return " ".join(str(item.get("text", "")).strip() for item in segments).strip()


def _cue_score(text: str, cues: tuple[str, ...], cap: int) -> int:
    lowered = text.lower()
    hits = sum(1 for cue in cues if cue in lowered)
    return min(cap, hits * 5)


def _candidate_family(text: str) -> str:
    lowered = text.lower()
    if any(cue in lowered for cue in COMEDY_CUES):
        return "comedy_or_reaction"
    if any(cue in lowered for cue in CONFLICT_CUES):
        return "conflict_or_debate"
    if any(cue in lowered for cue in KNOWLEDGE_CUES):
        return "useful_explanation"
    if "?" in text:
        return "curiosity_or_question"
    return "story_or_commentary"


def _audio_energy(audio_windows: list[dict[str, Any]], start: float, end: float) -> float:
    selected = [
        float(window["rms_dbfs"])
        for window in audio_windows
        if float(window.get("end", 0)) > start and float(window.get("start", 0)) < end
        and not window.get("silence", False)
    ]
    if not selected:
        return 0.0
    # Map ordinary speech energy (-42 to -10 dBFS) to a bounded support score.
    mean_dbfs = sum(selected) / len(selected)
    return max(0.0, min(1.0, (mean_dbfs + 42.0) / 32.0))


def _segments_for_window(segments: list[dict[str, Any]], start: float, end: float) -> list[dict[str, Any]]:
    return [item for item in segments if float(item["end"]) > start and float(item["start"]) < end]


def _make_candidate(source_id: str, segments: list[dict[str, Any]], audio_windows: list[dict[str, Any]],
                    start_index: int, end_index: int) -> dict[str, Any] | None:
    chosen = segments[start_index:end_index + 1]
    if not chosen:
        return None
    start = float(chosen[0]["start"])
    end = float(chosen[-1]["end"])
    duration = end - start
    if duration <= 0:
        return None
    text = _text(chosen)
    words = re.findall(r"\b[\w']+\b", text.lower())
    if len(words) < 8:
        return None

    hook = min(20, _cue_score(text[: max(1, len(text) // 2)], HOOK_CUES, 15) + (5 if "?" in text[:len(text)//2] else 0))
    payoff = min(20, _cue_score(text[len(text)//2:], PAYOFF_CUES, 15) + (5 if text.rstrip().endswith((".", "!", "?")) else 0))
    density = len(words) / duration
    pacing = 20 if 1.8 <= density <= 4.5 else max(0, 20 - int(abs(density - 3.0) * 5))
    lexical_variety = len(set(words)) / max(1, len(words))
    variety = min(15, int(lexical_variety * 20))
    energy = int(_audio_energy(audio_windows, start, end) * 15)
    boundary = 10 if chosen[0].get("words") and chosen[-1].get("words") else 6
    scores = {
        "hook_signal": hook,
        "payoff_signal": payoff,
        "speech_pacing": pacing,
        "lexical_variety": variety,
        "audio_energy_support": energy,
        "boundary_evidence": boundary
    }
    total = sum(scores.values())
    identity = hashlib.sha1(f"{source_id}:{start:.3f}:{end:.3f}".encode()).hexdigest()[:12]
    family = _candidate_family(text)
    risks = []
    if hook < 5:
        risks.append("No strong textual hook cue detected; manual opening review required.")
    if payoff < 5:
        risks.append("Payoff may be incomplete or is not signaled by the heuristic.")
    if density < 1.2:
        risks.append("Low speech density; check whether pauses are meaningful or dead air.")
    if duration > 55:
        risks.append("Long candidate; confirm that the full context justifies the duration.")
    return {
        "candidate_id": f"moment-{identity}",
        "source_fingerprint": source_id,
        "source_in_seconds": round(start, 3),
        "source_out_seconds": round(end, 3),
        "duration_seconds": round(duration, 3),
        "family": family,
        "transcript_excerpt": text,
        "score": total,
        "score_breakdown": scores,
        "confidence": 0.35,
        "confidence_note": "Low-confidence heuristic ranking; no semantic model or labeled training set is used.",
        "risks": risks,
        "human_review_required": True
    }


def detect_moments(analysis: dict[str, Any], min_duration: float = 12.0,
                   max_duration: float = 55.0, limit: int = 10) -> dict[str, Any]:
    transcription = analysis.get("analysis", {}).get("transcription", {})
    if transcription.get("status") != "completed":
        raise PipelineError("Viral candidate discovery requires a completed transcript; run analyze-audio with ASR enabled")
    segments = transcription.get("segments", [])
    if not segments:
        raise PipelineError("Transcript contains no speech segments")
    if min_duration < 5 or max_duration <= min_duration or max_duration > 180:
        raise PipelineError("Duration bounds must satisfy 5 <= min < max <= 180 seconds")
    if limit < 1 or limit > 100:
        raise PipelineError("Candidate limit must be between 1 and 100")

    source_id = analysis.get("source", {}).get("fingerprint", "unknown")
    audio_windows = analysis.get("analysis", {}).get("audio_metrics", {}).get("windows", [])
    anchors = []
    for index, segment in enumerate(segments):
        text = str(segment.get("text", "")).lower()
        if "?" in text or any(cue in text for cue in HOOK_CUES + PAYOFF_CUES):
            anchors.append(index)
    if not anchors:
        anchors = list(range(0, len(segments), max(1, len(segments) // 8)))

    candidates = []
    seen_ranges: list[tuple[float, float]] = []
    for anchor in anchors:
        anchor_start = float(segments[anchor]["start"])
        anchor_end = float(segments[anchor]["end"])
        target_start = max(float(segments[0]["start"]), anchor_start - min(8.0, max_duration * 0.2))
        target_end = min(float(segments[-1]["end"]), max(anchor_end + 12.0, anchor_start + min_duration))
        target_end = min(target_end, target_start + max_duration)
        start_index = min(range(len(segments)), key=lambda i: abs(float(segments[i]["start"]) - target_start))
        end_index = min(range(start_index, len(segments)), key=lambda i: abs(float(segments[i]["end"]) - target_end))
        while end_index > start_index and float(segments[end_index]["end"]) - float(segments[start_index]["start"]) < min_duration:
            if end_index + 1 < len(segments):
                end_index += 1
            else:
                break
        candidate = _make_candidate(source_id, segments, audio_windows, start_index, end_index)
        if candidate is None:
            continue
        start, end = candidate["source_in_seconds"], candidate["source_out_seconds"]
        if end - start < min_duration - 0.1 or end - start > max_duration + 0.1:
            continue
        overlap = any(
            max(0.0, min(end, old_end) - max(start, old_start)) / max(0.001, min(end-start, old_end-old_start)) > 0.65
            for old_start, old_end in seen_ranges
        )
        if overlap:
            continue
        seen_ranges.append((start, end))
        candidates.append(candidate)

    candidates.sort(key=lambda item: (item["score"], item["confidence"]), reverse=True)
    return {
        "schema_version": "1.0",
        "source_fingerprint": source_id,
        "method": "transparent_rules_and_audio_energy",
        "candidate_count": min(limit, len(candidates)),
        "candidates": candidates[:limit],
        "limitations": [
            "This is a transparent baseline, not a trained viral-moment model and not a probability of virality.",
            "Text cue rules are English-biased; multilingual/code-switched transcripts need human review.",
            "Audio energy is supporting evidence only and does not equal excitement or quality.",
            "No candidate is approved automatically; check context, opening, payoff, rights and privacy."
        ]
    }


def detect_moments_file(path: Path, output: Path, min_duration: float = 12.0,
                        max_duration: float = 55.0, limit: int = 10) -> dict[str, Any]:
    try:
        analysis = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PipelineError(f"Could not read audio analysis JSON: {exc}") from exc
    result = detect_moments(analysis, min_duration, max_duration, limit)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return result
