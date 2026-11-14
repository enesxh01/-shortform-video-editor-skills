import unittest

from shortform_editor.caption_generation import generate_captions
from shortform_editor.cli import PipelineError


def fixtures():
    fingerprint = "sha256:" + ("e" * 64)
    analysis = {
        "source": {"fingerprint": fingerprint},
        "analysis": {"transcription": {
            "status": "completed",
            "words": [
                {"text": "We", "start": 1.0, "end": 1.2},
                {"text": "found", "start": 1.2, "end": 1.5},
                {"text": "the", "start": 1.5, "end": 1.6},
                {"text": "answer", "start": 1.6, "end": 2.0},
                {"text": ".", "start": 2.0, "end": 2.05},
                {"text": "It", "start": 2.6, "end": 2.8},
                {"text": "worked", "start": 2.8, "end": 3.2}
            ]
        }}
    }
    candidate = {
        "source_fingerprint": fingerprint,
        "candidate_id": "moment-test",
        "source_in_seconds": 1.0,
        "source_out_seconds": 4.0
    }
    return analysis, candidate


class CaptionGenerationTests(unittest.TestCase):
    def test_groups_word_timestamps_and_attaches_punctuation(self):
        analysis, candidate = fixtures()
        result = generate_captions(analysis, candidate)
        self.assertGreaterEqual(len(result["captions"]), 2)
        self.assertEqual(result["captions"][0]["text"], "We found the answer.")
        self.assertTrue(result["captions"][0]["words"])

    def test_split_captions_are_center_positioned(self):
        analysis, candidate = fixtures()
        result = generate_captions(analysis, candidate, layout="split_vertical")
        self.assertTrue(all(item["position"] == "center" for item in result["captions"]))

    def test_rejects_wrong_source(self):
        analysis, candidate = fixtures()
        candidate["source_fingerprint"] = "sha256:" + ("f" * 64)
        with self.assertRaises(PipelineError):
            generate_captions(analysis, candidate)


if __name__ == "__main__":
    unittest.main()
