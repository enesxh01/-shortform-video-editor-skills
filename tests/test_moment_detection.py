import unittest

from shortform_editor.moments import _has_cue, detect_moments, select_diverse_candidates
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

    def test_candidate_shortlist_limits_family_dominance_before_filling(self):
        candidates = [
            {"candidate_id": f"comedy-{index}", "family": "comedy_or_reaction", "score": 100 - index, "confidence": 0.35}
            for index in range(5)
        ] + [
            {"candidate_id": "knowledge-1", "family": "useful_explanation", "score": 80, "confidence": 0.35},
            {"candidate_id": "story-1", "family": "story_or_commentary", "score": 70, "confidence": 0.35}
        ]
        selected = select_diverse_candidates(candidates, limit=4, max_per_family=2)
        families = [item["family"] for item in selected]
        self.assertEqual(families.count("comedy_or_reaction"), 2)
        self.assertIn("useful_explanation", families)
        self.assertIn("story_or_commentary", families)
        self.assertEqual(len(selected), 4)

    def test_candidate_shortlist_preserves_score_order_within_family(self):
        candidates = [
            {"candidate_id": "low", "family": "story", "score": 30, "confidence": 0.3},
            {"candidate_id": "high", "family": "story", "score": 90, "confidence": 0.3},
            {"candidate_id": "mid", "family": "story", "score": 60, "confidence": 0.3}
        ]
        selected = select_diverse_candidates(candidates, limit=3, max_per_family=2)
        self.assertEqual([item["candidate_id"] for item in selected], ["high", "mid", "low"])

    def test_cue_matching_uses_word_boundaries(self):
        self.assertTrue(_has_cue("But then it happened", "but"))
        self.assertFalse(_has_cue("The button was broken", "but"))
        self.assertTrue(_has_cue("Mirëpo kjo ishte e vërteta", "mirëpo"))
        self.assertTrue(_has_cue("Në fund kjo funksionoi", "në fund"))

    def test_flags_weak_asr_evidence_without_changing_heuristic_score(self):
        report = analysis_report()
        for segment in report["analysis"]["transcription"]["segments"]:
            segment["avg_logprob"] = -1.0
            segment["no_speech_prob"] = 0.5
            for word in segment["words"]:
                word["probability"] = 0.4
        result = detect_moments(report, min_duration=12, max_duration=35, limit=5)
        candidate = result["candidates"][0]
        self.assertEqual(candidate["transcript_diagnostics"]["quality_flag"], "review_transcript")
        self.assertLess(candidate["transcript_diagnostics"]["mean_word_probability"], 0.55)
        self.assertTrue(any("ASR confidence indicators are weak" in risk for risk in candidate["risks"]))
        self.assertEqual(sum(candidate["score_breakdown"].values()), candidate["score"])

    def test_reports_low_confidence_word_spans_and_confidence_coverage(self):
        report = analysis_report()
        for segment_index, segment in enumerate(report["analysis"]["transcription"]["segments"]):
            for word in segment["words"]:
                word["probability"] = 0.35 if segment_index < 2 else 0.95
        candidate = detect_moments(report, min_duration=12, max_duration=35, limit=5)["candidates"][0]
        diagnostics = candidate["transcript_diagnostics"]
        self.assertGreater(diagnostics["word_confidence_coverage"], 0.99)
        self.assertGreaterEqual(diagnostics["low_confidence_word_count"], 3)
        self.assertGreater(diagnostics["low_confidence_word_ratio"], 0.25)
        self.assertTrue(diagnostics["low_confidence_spans"])
        self.assertEqual(diagnostics["quality_flag"], "review_transcript")
        self.assertTrue(any("timestamp ranges" in risk for risk in candidate["risks"]))

    def test_marks_missing_asr_confidence_as_unassessed(self):
        candidate = detect_moments(analysis_report(), min_duration=12, max_duration=35, limit=5)["candidates"][0]
        self.assertEqual(candidate["transcript_diagnostics"]["quality_flag"], "insufficient_asr_evidence")
        self.assertTrue(any("metadata is unavailable" in risk for risk in candidate["risks"]))

    def test_ignores_malformed_asr_confidence_metadata(self):
        report = analysis_report()
        for segment in report["analysis"]["transcription"]["segments"]:
            segment["avg_logprob"] = "not-a-number"
            segment["no_speech_prob"] = float("nan")
            for word in segment["words"]:
                word["probability"] = 2.0
        candidate = detect_moments(report, min_duration=12, max_duration=35, limit=5)["candidates"][0]
        self.assertEqual(candidate["transcript_diagnostics"]["quality_flag"], "insufficient_asr_evidence")
        self.assertIsNone(candidate["transcript_diagnostics"]["mean_segment_logprob"])
        self.assertIsNone(candidate["transcript_diagnostics"]["mean_word_probability"])

    def test_adds_kosovar_albanian_hook_and_payoff_cues(self):
        self.assertTrue(_has_cue("Ja pse kjo ndodhi papritur", "ja pse"))
        self.assertTrue(_has_cue("Kështu që gjithçka funksionoi", "kështu që"))
        self.assertTrue(_has_cue("A e din çfarë ndodhi", "a e din"))

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
