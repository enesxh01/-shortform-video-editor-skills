import unittest

from shortform_editor.qc import assess_probe


def probe():
    return {
        "streams": [
            {"codec_type": "video", "width": 1080, "height": 1920, "avg_frame_rate": "60/1", "codec_name": "h264"},
            {"codec_type": "audio", "codec_name": "aac", "channels": 2}
        ]
    }


class QCTests(unittest.TestCase):
    def test_passes_expected_stream_metadata_and_clean_logs(self):
        result = assess_probe(probe(), "mean_volume: -18.0 dB\nmax_volume: -2.0 dB")
        self.assertEqual(result["status"], "passed")
        self.assertFalse(result["failures"])

    def test_flags_black_freeze_and_clipping(self):
        logs = (
            "black_start:1.0 black_end:2.0 black_duration:1.0\n"
            "freeze_start:3.0\nfreeze_end:5.0 freeze_duration:2.0\n"
            "mean_volume: -5.0 dB\nmax_volume: -0.0 dB"
        )
        result = assess_probe(probe(), logs)
        self.assertEqual(result["status"], "fail")
        self.assertEqual(len(result["black_regions"]), 1)
        self.assertEqual(len(result["freeze_regions"]), 1)
        self.assertIn("Audio sample peak is at or near digital clipping", result["failures"])

    def test_flags_wrong_frame_rate(self):
        report = probe()
        report["streams"][0]["avg_frame_rate"] = "30/1"
        result = assess_probe(report, "")
        self.assertEqual(result["status"], "fail")
        self.assertIn("Unexpected average frame rate", result["failures"])

    def test_reports_missing_audio_as_warning(self):
        report = probe()
        report["streams"] = report["streams"][:1]
        result = assess_probe(report, "")
        self.assertEqual(result["status"], "warning")


if __name__ == "__main__":
    unittest.main()
