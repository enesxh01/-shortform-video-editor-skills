import unittest

from shortform_editor.pacing import analyze_pacing
from shortform_editor.cli import PipelineError


def report():
    fingerprint = "sha256:" + ("c" * 64)
    analysis = {
        "source": {"fingerprint": fingerprint},
        "analysis": {
            "transcription": {"status": "completed", "segments": [
                {"start": 0.0, "end": 3.0, "text": "This is the setup", "words": [{"text": "This"}, {"text": "is"}]},
                {"start": 6.0, "end": 8.0, "text": "Wait, wait, that changed everything", "words": [{"text": "wait"}, {"text": "wait"}]},
                {"start": 10.0, "end": 14.0, "text": "And here is the final answer", "words": [{"text": "answer"}]}
            ]},
            "audio_metrics": {"silence_regions": [
                {"start": 3.0, "end": 6.0},
                {"start": 8.0, "end": 10.0}
            ]}
        }
    }
    candidates = {
        "source_fingerprint": fingerprint,
        "candidates": [{
            "candidate_id": "moment-1",
            "source_in_seconds": 0.0,
            "source_out_seconds": 14.0
        }]
    }
    return analysis, candidates


class PacingTests(unittest.TestCase):
    def test_proposes_long_silence_trim_but_preserves_meaningful_pause(self):
        analysis, candidates = report()
        result = analyze_pacing(analysis, candidates)
        decisions = result["candidates"][0]["decisions"]
        trims = [item for item in decisions if item["decision"] == "trim"]
        preserved = [item for item in decisions if item["decision"] == "preserve_pause"]
        self.assertEqual(len(trims), 1)
        self.assertEqual(len(preserved), 1)
        self.assertIn("human review", trims[0]["rationale"])

    def test_flags_repeated_words_without_removing_them(self):
        analysis, candidates = report()
        result = analyze_pacing(analysis, candidates)
        self.assertEqual(result["candidates"][0]["repeated_word_flags"], ["wait"])

    def test_rejects_mismatched_source(self):
        analysis, candidates = report()
        candidates["source_fingerprint"] = "sha256:" + ("d" * 64)
        with self.assertRaises(PipelineError):
            analyze_pacing(analysis, candidates)


if __name__ == "__main__":
    unittest.main()
