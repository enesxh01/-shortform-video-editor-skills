from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .cli import PipelineError


DEFAULT_FEEDBACK_PATH = Path.home() / ".shortform-editor" / "feedback.jsonl"
LABEL_VALUE = {"approve": 1.0, "edited": 0.5, "reject": 0.0}


def _read_feedback(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError as exc:
            raise PipelineError(f"Invalid feedback JSONL at line {line_number}: {exc}") from exc
        if not isinstance(item, dict):
            raise PipelineError(f"Feedback record at line {line_number} must be a JSON object")
        if item.get("decision") not in LABEL_VALUE:
            raise PipelineError(f"Unknown feedback decision at line {line_number}")
        if not isinstance(item.get("family"), str) or not item["family"].strip():
            raise PipelineError(f"Feedback record at line {line_number} has no valid family")
        records.append(item)
    return records


def record_feedback(candidates: dict[str, Any], candidate_id: str, decision: str,
                    path: Path = DEFAULT_FEEDBACK_PATH, reason: str = "") -> dict[str, Any]:
    if decision not in LABEL_VALUE:
        raise PipelineError("Feedback decision must be approve, edited or reject")
    candidate = next(
        (item for item in candidates.get("candidates", []) if item.get("candidate_id") == candidate_id),
        None
    )
    if candidate is None:
        raise PipelineError(f"Candidate ID not found: {candidate_id}")
    if len(reason) > 500:
        raise PipelineError("Feedback reason must be 500 characters or fewer")
    record = {
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "source_fingerprint": candidate.get("source_fingerprint"),
        "candidate_id": candidate_id,
        "family": candidate.get("family", "unknown"),
        "decision": decision,
        "reason": reason.strip() or None
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")
        handle.flush()
    return record


def apply_feedback(candidates: dict[str, Any], records: list[dict[str, Any]],
                   min_observations: int = 3) -> dict[str, Any]:
    if min_observations < 1:
        raise PipelineError("Minimum feedback observations must be positive")
    # A candidate may be reviewed more than once; only its latest decision counts.
    # This prevents repeated clicks on one clip from masquerading as independent examples.
    latest_by_candidate: dict[tuple[str, str], dict[str, Any]] = {}
    anonymous_records = []
    for index, item in enumerate(records):
        if not isinstance(item, dict) or item.get("decision") not in LABEL_VALUE:
            continue
        family = item.get("family")
        if not isinstance(family, str) or not family.strip():
            continue
        candidate_id = item.get("candidate_id")
        fingerprint = item.get("source_fingerprint") or ""
        if candidate_id:
            latest_by_candidate[(str(fingerprint), str(candidate_id))] = item
        else:
            anonymous_records.append((index, item))
    valid_records = list(latest_by_candidate.values()) + [item for _, item in anonymous_records]
    if not valid_records:
        result = dict(candidates)
        result["feedback_learning"] = {"status": "no_feedback", "records_used": 0}
        return result

    values = [LABEL_VALUE[item["decision"]] for item in valid_records]
    global_rate = (sum(values) + 1.0) / (len(values) + 2.0)
    family_records: dict[str, list[float]] = {}
    for item in valid_records:
        family_records.setdefault(item["family"], []).append(LABEL_VALUE[item["decision"]])

    family_stats = {}
    adjustments = {}
    for family, family_values in family_records.items():
        rate = (sum(family_values) + 1.0) / (len(family_values) + 2.0)
        adjustment = max(-5.0, min(5.0, (rate - global_rate) * 10.0)) if len(family_values) >= min_observations else 0.0
        family_stats[family] = {
            "observations": len(family_values),
            "smoothed_approval_rate": round(rate, 3),
            "score_adjustment": round(adjustment, 2)
        }
        adjustments[family] = adjustment

    ranked = []
    for candidate in candidates.get("candidates", []):
        item = dict(candidate)
        adjustment = adjustments.get(item.get("family"), 0.0)
        item["feedback_adjustment"] = round(adjustment, 2)
        item["score_after_feedback"] = round(float(item.get("score", 0)) + adjustment, 2)
        ranked.append(item)
    ranked.sort(key=lambda item: item["score_after_feedback"], reverse=True)
    result = dict(candidates)
    result["candidates"] = ranked
    result["feedback_learning"] = {
        "status": "applied",
        "records_used": len(valid_records),
        "global_smoothed_approval_rate": round(global_rate, 3),
        "family_statistics": family_stats,
        "method": "smoothed category-level human editorial preference; no channel analytics or view data"
    }
    return result


def apply_feedback_file(candidates_path: Path, feedback_path: Path, output_path: Path,
                        min_observations: int = 3) -> dict[str, Any]:
    try:
        candidates = json.loads(candidates_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PipelineError(f"Could not read candidate report: {exc}") from exc
    records = _read_feedback(feedback_path)
    result = apply_feedback(candidates, records, min_observations)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return result
