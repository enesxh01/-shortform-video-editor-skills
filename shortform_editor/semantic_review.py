from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .cli import PipelineError


SCHEMA_PATH = Path(__file__).resolve().parent / "schemas" / "semantic-review.schema.json"


def validate_semantic_review(review: dict[str, Any], probe: dict[str, Any] | None = None,
                             candidates: dict[str, Any] | None = None) -> list[str]:
    try:
        from jsonschema import Draft202012Validator
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    except (ImportError, OSError, json.JSONDecodeError) as exc:
        raise PipelineError(f"Cannot load semantic review validator: {exc}") from exc

    errors = sorted(Draft202012Validator(schema).iter_errors(review), key=lambda error: list(error.absolute_path))
    messages = [
        f"{'.'.join(map(str, error.absolute_path)) or '<root>'}: {error.message}"
        for error in errors
    ]
    if messages:
        return messages

    fingerprint = review["source_fingerprint"]
    baseline_ids = set(review["baseline_candidate_ids"])
    if candidates is not None:
        candidate_fingerprint = candidates.get("source_fingerprint")
        if candidate_fingerprint != fingerprint:
            messages.append("Semantic review source fingerprint does not match baseline candidate report")
        actual_baseline_ids = {item.get("candidate_id") for item in candidates.get("candidates", [])}
        unknown_baseline_ids = baseline_ids - actual_baseline_ids
        if unknown_baseline_ids:
            messages.append("baseline_candidate_ids contains IDs absent from the supplied candidate report")
    if probe is not None:
        probe_fingerprint = probe.get("source", {}).get("fingerprint")
        if probe_fingerprint != fingerprint:
            messages.append("Semantic review source fingerprint does not match probe report")
        raw_duration = probe.get("format", {}).get("duration")
        duration = float(raw_duration) if raw_duration is not None else None
    else:
        duration = None

    semantic_ids = set()
    semantic_scores = {}
    for index, candidate in enumerate(review["semantic_candidates"]):
        candidate_id = candidate["candidate_id"]
        if candidate_id in semantic_ids:
            messages.append(f"semantic_candidates[{index}].candidate_id is duplicated")
        semantic_ids.add(candidate_id)
        start = float(candidate["source_in_seconds"])
        end = float(candidate["source_out_seconds"])
        if end <= start:
            messages.append(f"semantic_candidates[{index}] source_out_seconds must be greater than source_in_seconds")
        if duration is not None and end > duration + 0.05:
            messages.append(f"semantic_candidates[{index}] exceeds source duration")
        if sum(candidate["score_breakdown"].values()) != candidate["score"]:
            messages.append(f"semantic_candidates[{index}] score must equal the sum of score_breakdown")
        semantic_scores[candidate_id] = candidate["score"]
        previous_evidence_end = start
        for evidence_index, evidence in enumerate(candidate["evidence"]):
            evidence_start = float(evidence["start_seconds"])
            evidence_end = float(evidence["end_seconds"])
            if evidence_end <= evidence_start or evidence_start < start or evidence_end > end or evidence_start < previous_evidence_end:
                messages.append(f"semantic_candidates[{index}].evidence[{evidence_index}] has invalid or unordered bounds")
            previous_evidence_end = evidence_end
        for alternative_index, alternative in enumerate(candidate.get("alternatives", [])):
            alternative_start = float(alternative["source_in_seconds"])
            alternative_end = float(alternative["source_out_seconds"])
            if alternative_end <= alternative_start or alternative_start < start - 10 or alternative_end > end + 10:
                messages.append(f"semantic_candidates[{index}].alternatives[{alternative_index}] has invalid bounds")
            if duration is not None and alternative_end > duration + 0.05:
                messages.append(f"semantic_candidates[{index}].alternatives[{alternative_index}] exceeds source duration")

    rejected_ids = set()
    for index, candidate in enumerate(review["rejected_candidates"]):
        candidate_id = candidate["candidate_id"]
        if candidate_id in rejected_ids:
            messages.append(f"rejected_candidates[{index}].candidate_id is duplicated")
        rejected_ids.add(candidate_id)
        if candidate_id not in baseline_ids and candidate_id not in semantic_ids:
            messages.append(f"rejected_candidates[{index}] references an unknown candidate ID")
        if candidate_id in semantic_ids:
            messages.append(f"Candidate {candidate_id!r} cannot be both semantically selected and rejected")
        start, end = float(candidate["source_in_seconds"]), float(candidate["source_out_seconds"])
        if end <= start:
            messages.append(f"rejected_candidates[{index}] has invalid source bounds")
        if duration is not None and end > duration + 0.05:
            messages.append(f"rejected_candidates[{index}] exceeds source duration")

    known_ids = baseline_ids | semantic_ids
    ranked_ids = set()
    previous_rank_score = 101
    for index, candidate in enumerate(review["final_ranked_candidates"]):
        candidate_id = candidate["candidate_id"]
        if candidate_id in ranked_ids:
            messages.append(f"final_ranked_candidates[{index}].candidate_id is duplicated")
        ranked_ids.add(candidate_id)
        if candidate_id not in known_ids:
            messages.append(f"final_ranked_candidates[{index}] references an unknown candidate ID")
        if candidate_id in semantic_scores and candidate["score"] != semantic_scores[candidate_id]:
            messages.append(f"final_ranked_candidates[{index}] score differs from semantic candidate score")
        if candidate_id in rejected_ids:
            messages.append(f"Rejected candidate {candidate_id!r} cannot appear in final ranking")
        if candidate["score"] > previous_rank_score:
            messages.append(f"final_ranked_candidates[{index}] is not ordered by descending score")
        previous_rank_score = candidate["score"]
    return messages


def validate_semantic_review_file(review_path: Path, probe_path: Path | None = None,
                                  candidates_path: Path | None = None) -> dict[str, Any]:
    try:
        review = json.loads(review_path.read_text(encoding="utf-8"))
        probe = json.loads(probe_path.read_text(encoding="utf-8")) if probe_path else None
        candidates = json.loads(candidates_path.read_text(encoding="utf-8")) if candidates_path else None
    except (OSError, json.JSONDecodeError) as exc:
        raise PipelineError(f"Could not read semantic review input: {exc}") from exc
    errors = validate_semantic_review(review, probe, candidates)
    return {
        "status": "invalid" if errors else "valid",
        "source_fingerprint": review.get("source_fingerprint"),
        "semantic_candidates": len(review.get("semantic_candidates", [])),
        "final_ranked_candidates": len(review.get("final_ranked_candidates", [])),
        "errors": errors
    }
