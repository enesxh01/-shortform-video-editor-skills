import tempfile
import unittest
from pathlib import Path

from shortform_editor.feedback import apply_feedback, record_feedback
from shortform_editor.cli import PipelineError


class FeedbackTests(unittest.TestCase):
    def test_category_preferences_adjust_ranking_with_bounded_scores(self):
        candidates = {
            "candidates": [
                {"candidate_id": "a", "family": "comedy_or_reaction", "score": 60},
                {"candidate_id": "b", "family": "conflict_or_debate", "score": 61}
            ]
        }
        records = (
            [{"candidate_id": f"comedy-{i}", "source_fingerprint": "source-a", "family": "comedy_or_reaction", "decision": "approve"} for i in range(3)] +
            [{"candidate_id": f"conflict-{i}", "source_fingerprint": "source-a", "family": "conflict_or_debate", "decision": "reject"} for i in range(3)]
        )
        result = apply_feedback(candidates, records)
        self.assertEqual(result["candidates"][0]["candidate_id"], "a")
        self.assertEqual(result["candidates"][0]["feedback_adjustment"], 3.0)
        self.assertEqual(result["candidates"][1]["feedback_adjustment"], -3.0)

    def test_requires_minimum_observations_before_adjusting(self):
        candidates = {"candidates": [{"candidate_id": "a", "family": "story", "score": 50}]}
        result = apply_feedback(candidates, [
            {"candidate_id": "story-1", "family": "story", "decision": "approve"},
            {"candidate_id": "story-2", "family": "story", "decision": "approve"}
        ])
        self.assertEqual(result["candidates"][0]["feedback_adjustment"], 0.0)

    def test_records_feedback_only_for_existing_candidate(self):
        candidates = {"candidates": [{
            "candidate_id": "moment-1",
            "source_fingerprint": "sha256:" + ("a" * 64),
            "family": "story_or_commentary"
        }]}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "feedback.jsonl"
            record = record_feedback(candidates, "moment-1", "approve", path, "Good payoff")
            self.assertEqual(record["decision"], "approve")
            self.assertTrue(path.exists())
            with self.assertRaises(PipelineError):
                record_feedback(candidates, "missing", "approve", path)


    def test_repeated_reviews_of_same_candidate_count_only_once(self):
        candidates = {"candidates": [{"candidate_id": "next", "family": "comedy_or_reaction", "score": 50}]}
        records = [
            {"candidate_id": "same", "source_fingerprint": "source-a", "family": "comedy_or_reaction", "decision": "reject"},
            {"candidate_id": "same", "source_fingerprint": "source-a", "family": "comedy_or_reaction", "decision": "approve"},
            {"candidate_id": "other", "source_fingerprint": "source-a", "family": "comedy_or_reaction", "decision": "approve"},
        ]
        result = apply_feedback(candidates, records, min_observations=3)
        self.assertEqual(result["feedback_learning"]["records_used"], 2)
        self.assertEqual(result["candidates"][0]["feedback_adjustment"], 0.0)


if __name__ == "__main__":
    unittest.main()
