import unittest

from shortform_editor.moments import _has_cue, detect_moments
from shortform_editor.cli import PipelineError


def analysis_report():
    texts = [
        "We thought the machine was completely broken.",
        "But then we discovered the real problem.",
        "The reason was a tiny loose cable.",
        "So we connected it properly and it started working.",
        "That was the answer and nobody expected it."
    ]
    segments = []
    for index, text in enumerate(texts):
        start = index * 5.0
        segments.append({
            "id": index,
            "start": start,
            "end": start + 4.5,
            "text": text,
            "words": [{"text": word, "start": start, "end": start + 0.2} for word in text.split()]
        })
    return {
        "source": {"fingerprint": "sha256:" + ("a" * 64)},
        "analysis": {
            "transcription": {"status": "completed", "segments": segments},
            "audio_metrics": {"windows": [
                {"start": i * 0.5, "end": (i + 1) * 0.5, "rms_dbfs": -20.0, "silence": False}
                for i in range(50)
            ]}
        }
    }


class MomentDetectionTests(unittest.TestCase):
    def test_returns_ranked_candidates_with_explainable_scores(self):
        result = detect_moments(analysis_report(), min_duration=12, max_duration=35, limit=5)
        self.assertGreaterEqual(result["candidate_count"], 1)
        candidate = result["candidates"][0]
        self.assertEqual(candidate["source_fingerprint"], "sha256:" + ("a" * 64))
        self.assertEqual(sum(candidate["score_breakdown"].values()), candidate["score"])
        self.assertTrue(candidate["human_review_required"])
        self.assertEqual(candidate["confidence"], 0.35)

    def test_cue_matching_uses_word_boundaries(self):
        self.assertTrue(_has_cue("But then it happened", "but"))
        self.assertFalse(_has_cue("The button was broken", "but"))

    def test_requires_completed_transcript(self):
        report = analysis_report()
        report["analysis"]["transcription"]["status"] = "skipped"
        with self.assertRaises(PipelineError):
            detect_moments(report)

    def test_rejects_invalid_duration_bounds(self):
        with self.assertRaises(PipelineError):
            detect_moments(analysis_report(), min_duration=60, max_duration=20)


if __name__ == "__main__":
    unittest.main()
