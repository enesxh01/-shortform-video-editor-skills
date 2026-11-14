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
            [{"family": "comedy_or_reaction", "decision": "approve"} for _ in range(3)] +
            [{"family": "conflict_or_debate", "decision": "reject"} for _ in range(3)]
        )
        result = apply_feedback(candidates, records)
        self.assertEqual(result["candidates"][0]["candidate_id"], "a")
        self.assertEqual(result["candidates"][0]["feedback_adjustment"], 3.0)
        self.assertEqual(result["candidates"][1]["feedback_adjustment"], -3.0)

    def test_requires_minimum_observations_before_adjusting(self):
        candidates = {"candidates": [{"candidate_id": "a", "family": "story", "score": 50}]}
        result = apply_feedback(candidates, [
            {"family": "story", "decision": "approve"},
            {"family": "story", "decision": "approve"}
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


if __name__ == "__main__":
    unittest.main()
