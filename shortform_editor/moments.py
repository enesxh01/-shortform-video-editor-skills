from __future__ import annotations

import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any

from .cli import PipelineError


HOOK_CUES = (
    "but", "however", "until", "suddenly", "turns out", "the truth", "the reason",
    "what happened", "i realized", "you need to", "here is why", "here's why",
    "watch what happens", "here is what", "here's what", "the moment when",
    "the problem", "the secret", "nobody", "never", "always",
    # Common Albanian, Spanish, French and German narrative turns.
    "mirëpo", "derisa", "papritur", "doli që", "e vërteta", "arsyeja",
    "çfarë ndodhi", "problemi", "sekreti", "askush", "kurrë",
    "ja pse", "në fakt", "a e din", "nuk e priste", "kush e mendonte",
    "në atë moment", "dhe pastaj", "nuk do ta besosh", "u zbulua",
    "sin embargo", "de repente", "resulta que", "la verdad", "el problema", "nadie", "nunca",
    "pourtant", "soudain", "la vérité", "le problème", "personne", "jamais",
    "allerdings", "plötzlich", "die wahrheit", "der grund", "das problem", "niemand", "nie"
)
PAYOFF_CUES = (
    "because", "that's why", "so that's", "in the end", "finally", "which means",
    "the answer", "it worked", "it failed", "that was", "therefore", "as a result",
    "sepse", "kjo është arsyeja", "në fund", "më në fund", "që do të thotë", "përgjigjja", "funksionoi", "dështoi", "prandaj",
    "kështu që", "për këtë arsye", "dhe ja", "në fund fare", "doli e vërtetë",
    "porque", "por eso", "al final", "la respuesta", "funcionó", "falló", "por lo tanto",
    "parce que", "c'est pourquoi", "à la fin", "la réponse", "ça a marché",
    "weil", "deshalb", "am ende", "die antwort", "es hat funktioniert"
)
COMEDY_CUES = ("laugh", "laughter", "funny", "joke", "kidding", "haha", "lol", "shaka", "qesh", "hahaha", "chiste", "broma", "rire", "blague", "witz", "lustig")
KNOWLEDGE_CUES = ("how to", "the reason", "for example", "means that", "you can", "the difference", "si të", "për shembull", "do të thotë", "mund të", "cómo", "por ejemplo", "significa", "comment", "par exemple", "bedeutet", "zum beispiel")
CONFLICT_CUES = ("wrong", "disagree", "no way", "you're wrong", "you are wrong", "argue", "fight", "gabim", "nuk pajtohem", "s'ke të drejtë", "no tienes razón", "equivocado", "pas d'accord", "falsch", "ich stimme nicht zu")


def _text(segments: list[dict[str, Any]]) -> str:
    return " ".join(str(item.get("text", "")).strip() for item in segments).strip()


def _has_cue(text: str, cue: str) -> bool:
    return re.search(r"(?<!\w)" + re.escape(cue.lower()) + r"(?!\w)", text.lower()) is not None


def _has_any_cue(text: str, cues: tuple[str, ...]) -> bool:
    return any(_has_cue(text, cue) for cue in cues)


def _cue_score(text: str, cues: tuple[str, ...], cap: int) -> int:
    hits = sum(1 for cue in cues if _has_cue(text, cue))
    return min(cap, hits * 5)


def _candidate_family(text: str) -> str:
    lowered = text.lower()
    if _has_any_cue(lowered, COMEDY_CUES):
        return "comedy_or_reaction"
    if _has_any_cue(lowered, CONFLICT_CUES):
        return "conflict_or_debate"
    if _has_any_cue(lowered, KNOWLEDGE_CUES):
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
    def finite_values(values: list[Any], minimum: float, maximum: float) -> list[float]:
        accepted = []
        for value in values:
            try:
                number = float(value)
            except (TypeError, ValueError):
                continue
            if math.isfinite(number) and minimum <= number <= maximum:
                accepted.append(number)
        return accepted

    segment_logprobs = finite_values(
        [item.get("avg_logprob") for item in chosen], -20.0, 0.0
    )
    segment_no_speech = finite_values(
        [item.get("no_speech_prob") for item in chosen], 0.0, 1.0
    )
    word_probabilities = finite_values(
        [word.get("probability") for item in chosen for word in item.get("words", [])],
        0.0, 1.0
    )
    transcript_diagnostics = {
        "mean_segment_logprob": round(sum(segment_logprobs) / len(segment_logprobs), 4) if segment_logprobs else None,
        "mean_no_speech_probability": round(sum(segment_no_speech) / len(segment_no_speech), 4) if segment_no_speech else None,
        "mean_word_probability": round(sum(word_probabilities) / len(word_probabilities), 4) if word_probabilities else None,
        "quality_flag": "insufficient_asr_evidence"
    }
    if segment_logprobs or word_probabilities:
        weak_logprob = bool(segment_logprobs and transcript_diagnostics["mean_segment_logprob"] < -0.8)
        weak_words = bool(word_probabilities and transcript_diagnostics["mean_word_probability"] < 0.55)
        high_no_speech = bool(segment_no_speech and transcript_diagnostics["mean_no_speech_probability"] > 0.35)
        transcript_diagnostics["quality_flag"] = (
            "review_transcript" if weak_logprob or weak_words or high_no_speech else "no_obvious_asr_warning"
        )
    risks = []
    if transcript_diagnostics["quality_flag"] == "review_transcript":
        risks.append("ASR confidence indicators are weak; verify the transcript against the source audio before editing.")
    if transcript_diagnostics["quality_flag"] == "insufficient_asr_evidence":
        risks.append("ASR confidence metadata is unavailable; transcript accuracy has not been assessed.")
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
        "transcript_diagnostics": transcript_diagnostics,
        "confidence": 0.35,
        "confidence_note": "Low-confidence heuristic ranking; no semantic model or labeled training set is used.",
        "risks": risks,
        "human_review_required": True
    }


def select_diverse_candidates(candidates: list[dict[str, Any]], limit: int,
                             max_per_family: int = 3) -> list[dict[str, Any]]:
    """Keep strong candidates while avoiding a shortlist dominated by one content family."""
    if limit < 1 or max_per_family < 1:
        raise ValueError("Candidate limit and family cap must be positive")
    ranked = sorted(
        candidates,
        key=lambda item: (float(item.get("score", 0)), float(item.get("confidence", 0))),
        reverse=True
    )
    selected: list[dict[str, Any]] = []
    deferred: list[dict[str, Any]] = []
    family_counts: dict[str, int] = {}
    for candidate in ranked:
        family = str(candidate.get("family") or "unclassified")
        if family_counts.get(family, 0) < max_per_family and len(selected) < limit:
            selected.append(candidate)
            family_counts[family] = family_counts.get(family, 0) + 1
        else:
            deferred.append(candidate)
    if len(selected) < limit:
        selected.extend(deferred[:limit - len(selected)])
    return selected


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

    source_id = analysis.get("source", {}).get("fingerprint")
    if not isinstance(source_id, str) or not re.fullmatch(r"sha256:[a-f0-9]{64}", source_id):
        raise PipelineError("Audio analysis is missing a valid SHA-256 source fingerprint")
    audio_windows = analysis.get("analysis", {}).get("audio_metrics", {}).get("windows", [])
    anchors = []
    for index, segment in enumerate(segments):
        text = str(segment.get("text", "")).lower()
        if "?" in text or _has_any_cue(text, HOOK_CUES + PAYOFF_CUES):
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

    ranked_candidates = sorted(candidates, key=lambda item: (item["score"], item["confidence"]), reverse=True)
    selected_candidates = select_diverse_candidates(ranked_candidates, limit, max_per_family=3)
    return {
        "schema_version": "1.0",
        "source_fingerprint": source_id,
        "method": "transparent_rules_and_audio_energy",
        "candidate_count": len(selected_candidates),
        "selection_policy": {
            "primary_order": "heuristic_score_then_confidence",
            "family_diversity_cap": 3,
            "note": "Up to three candidates per content family are selected before filling remaining slots by score; scores are unchanged."
        },
        "candidates": selected_candidates,
        "limitations": [
            "This is a transparent baseline, not a trained viral-moment model and not a probability of virality.",
            "Text cues include common English, Albanian, Spanish, French and German expressions; other languages and code-switching still need human review.",
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
