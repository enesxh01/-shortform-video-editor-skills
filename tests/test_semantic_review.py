import unittest
from pathlib import Path

from shortform_editor.semantic_review import validate_semantic_review


def review_fixture():
    fingerprint = "sha256:" + ("c" * 64)
    candidate = {
        "candidate_id": "semantic-moment-1",
        "source_in_seconds": 2.0,
        "source_out_seconds": 12.0,
        "family": "comedy",
        "transcript_excerpt": "A joke setup and complete punchline.",
        "hook": "The unexpected question.",
        "setup": "The speaker explains the situation.",
        "progression": "The story escalates.",
        "payoff": "The punchline lands.",
        "ending": "The reaction completes the beat.",
        "score": 90,
        "score_breakdown": {
            "hook": 15, "context": 15, "payoff": 20,
            "clarity": 20, "emotional_or_utility_value": 20
        },
        "confidence": "medium",
        "risks": [],
        "evidence": [
            {"start_seconds": 2.0, "end_seconds": 5.0, "text": "The setup."},
            {"start_seconds": 5.0, "end_seconds": 12.0, "text": "The punchline."}
        ]
    }
    return {
        "schema_version": "1.0",
        "source_fingerprint": fingerprint,
        "baseline_candidate_ids": ["moment-baseline-1"],
        "semantic_candidates": [candidate],
        "rejected_candidates": [],
        "final_ranked_candidates": [{
            "candidate_id": "semantic-moment-1",
            "score": 90,
            "confidence": "medium",
            "rationale": "Complete setup and payoff."
        }]
    }


class SemanticReviewTests(unittest.TestCase):
    def test_validates_source_bound_semantic_review(self):
        review = review_fixture()
        fingerprint = review["source_fingerprint"]
        probe = {"source": {"fingerprint": fingerprint}, "format": {"duration": "30.0"}}
        candidates = {"source_fingerprint": fingerprint, "candidates": [{"candidate_id": "moment-baseline-1"}]}
        self.assertEqual(validate_semantic_review(review, probe, candidates), [])

    def test_rejects_fingerprint_mismatch_and_score_mismatch(self):
        review = review_fixture()
        review["semantic_candidates"][0]["score"] = 50
        probe = {"source": {"fingerprint": "sha256:" + ("d" * 64)}, "format": {"duration": "30.0"}}
        errors = validate_semantic_review(review, probe)
        self.assertTrue(any("fingerprint does not match" in error for error in errors))
        self.assertTrue(any("score must equal" in error for error in errors))

    def test_rejects_final_ranking_of_rejected_candidate(self):
        review = review_fixture()
        review["rejected_candidates"] = [{
            "candidate_id": "moment-baseline-1",
            "source_in_seconds": 0.0,
            "source_out_seconds": 3.0,
            "reason": "Missing context"
        }]
        review["final_ranked_candidates"].append({
            "candidate_id": "moment-baseline-1",
            "score": 50,
            "confidence": "low",
            "rationale": "Not recommended"
        })
        errors = validate_semantic_review(review)
        self.assertTrue(any("cannot appear in final ranking" in error for error in errors))

    def test_requires_descending_final_rank_order(self):
        review = review_fixture()
        review["final_ranked_candidates"].append({
            "candidate_id": "moment-baseline-1",
            "score": 95,
            "confidence": "high",
            "rationale": "Higher score should rank first."
        })
        errors = validate_semantic_review(review)
        self.assertTrue(any("not ordered by descending score" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
