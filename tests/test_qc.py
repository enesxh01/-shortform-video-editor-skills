import unittest
from argparse import Namespace
from unittest.mock import patch

from shortform_editor.qc import assess_probe
from shortform_editor.cli import command_qc, command_repair


def probe():
    return {
        "streams": [
            {"codec_type": "video", "width": 1080, "height": 1920, "avg_frame_rate": "60/1", "codec_name": "h264", "start_time": "0.0", "duration": "10.0"},
            {"codec_type": "audio", "codec_name": "aac", "channels": 2, "start_time": "0.0", "duration": "10.0"}
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

    def test_flags_stream_timing_metadata_mismatch(self):
        report = probe()
        report["streams"][0]["start_time"] = "0.0"
        report["streams"][0]["duration"] = "10.0"
        report["streams"][1]["start_time"] = "0.3"
        report["streams"][1]["duration"] = "9.0"
        result = assess_probe(report, "")
        self.assertEqual(result["status"], "fail")
        self.assertIn("Audio/video stream start or duration metadata differs beyond tolerance", result["failures"])


    def test_qc_warning_is_nonfatal_for_optional_missing_audio(self):
        report = {"status": "warning", "checks": [], "failures": [], "warnings": ["No audio stream"]}
        with patch("shortform_editor.qc.run_qc", return_value=report):
            result = command_qc(Namespace(source="unused.mp4", width=1080, height=1920, fps="60/1", output=None))
        self.assertEqual(result, 0)

    def test_repair_warning_is_nonfatal(self):
        report = {"qc_after_repair": {"status": "warning"}}
        with patch("shortform_editor.repair.repair_technical_export", return_value=report):
            result = command_repair(Namespace(
                source="unused.mp4", output="unused-out.mp4", width=1080, height=1920,
                fps="60/1", crf=18, preset="medium", overwrite=False
            ))
        self.assertEqual(result, 0)


if __name__ == "__main__":
    unittest.main()
