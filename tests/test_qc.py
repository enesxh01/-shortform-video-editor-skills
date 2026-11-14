import tempfile
import unittest
from pathlib import Path
from argparse import Namespace
from unittest.mock import patch

from shortform_editor.qc import add_expected_duration_check, assess_probe
from shortform_editor.cli import PipelineError, command_qc, command_repair
from shortform_editor.repair import repair_technical_export


def probe():
    return {
        "streams": [
            {"codec_type": "video", "width": 1080, "height": 1920, "avg_frame_rate": "60/1", "codec_name": "h264", "pix_fmt": "yuv420p", "start_time": "0.0", "duration": "10.0"},
            {"codec_type": "audio", "codec_name": "aac", "channels": 2, "sample_rate": "48000", "start_time": "0.0", "duration": "10.0"}
        ]
    }


class QCTests(unittest.TestCase):
    def test_passes_expected_stream_metadata_and_clean_logs(self):
        result = assess_probe(probe(), "mean_volume: -18.0 dB\nmax_volume: -2.0 dB\nI: -14.0 LUFS\nLRA: 4.0 LU\nPeak: -2.0 dBFS")
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

    def test_handles_missing_or_malformed_frame_rate_metadata(self):
        report = probe()
        report["streams"][0]["avg_frame_rate"] = None
        result = assess_probe(report, "")
        self.assertEqual(result["status"], "fail")
        self.assertIn("Unexpected average frame rate", result["failures"])

    def test_handles_malformed_expected_frame_rate(self):
        result = assess_probe(probe(), "", expected_fps="not-a-frame-rate")
        self.assertEqual(result["status"], "fail")
        self.assertIn("Unexpected average frame rate", result["failures"])

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
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.mp4"
            source.write_bytes(b"placeholder")
            with patch("shortform_editor.qc.run_qc", return_value=report):
                result = command_qc(Namespace(source=str(source), width=1080, height=1920, fps="60/1", output=None))
        self.assertEqual(result, 0)

    def test_repair_rejects_ffmpeg_filter_expression_in_fps(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.mp4"
            source.write_bytes(b"placeholder")
            with self.assertRaisesRegex(PipelineError, "positive rational number"):
                repair_technical_export(
                    source, Path(directory) / "out.mp4",
                    fps="60/1,drawtext=text=unexpected"
                )

    def test_repair_normalizes_rational_fps_before_ffmpeg(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.mp4"
            source.write_bytes(b"placeholder")
            with patch("shortform_editor.repair.probe_media", side_effect=[
                     {"format": {"duration": "1.0"}, "source": {"fingerprint": "sha256:source"}},
                     {"format": {"duration": "1.0"}, "source": {"fingerprint": "sha256:output"}}
                 ]), patch("shortform_editor.repair.file_stat_signature", return_value=(1, 1, 1, 1)), \
                 patch("shortform_editor.repair.require_tool", return_value="ffmpeg"), \
                 patch("shortform_editor.repair.run_checked") as run, \
                 patch("shortform_editor.repair.os.replace"), \
                 patch("shortform_editor.repair.run_qc", return_value={"status": "passed", "checks": [], "failures": []}):
                result = repair_technical_export(
                    source, Path(directory) / "out.mp4", fps="120/2"
                )
            self.assertEqual(result["qc_after_repair"]["status"], "passed")
            self.assertTrue(any("fps=60/1" in arg for arg in run.call_args_list[0].args[0]))

    def test_repair_warning_is_nonfatal(self):
        report = {"qc_after_repair": {"status": "warning"}}
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.mp4"
            source.write_bytes(b"placeholder")
            with patch("shortform_editor.repair.repair_technical_export", return_value=report):
                result = command_repair(Namespace(
                    source=str(source), output=str(Path(directory) / "unused-out.mp4"), width=1080, height=1920,
                    fps="60/1", crf=18, preset="medium", overwrite=False
                ))
        self.assertEqual(result, 0)


    def test_flags_freeze_that_continues_to_end_of_file(self):
        report = probe()
        report["format"] = {"duration": "10.0"}
        result = assess_probe(report, "freeze_start:8.0\nfreeze_duration:2.0")
        self.assertEqual(result["freeze_regions"], [{"start": 8.0, "end": 10.0}])
        self.assertEqual(result["status"], "fail")


    def test_checks_rendered_duration_against_edl(self):
        passed = add_expected_duration_check({"status": "passed", "checks": [], "failures": []}, 15.02, 15.0)
        self.assertEqual(passed["status"], "passed")
        failed = add_expected_duration_check({"status": "passed", "checks": [], "failures": []}, 14.5, 15.0)
        self.assertEqual(failed["status"], "fail")
        self.assertIn("Rendered duration does not match the EDL timeline", failed["failures"])


    def test_parses_ebu_r128_loudness_and_true_peak(self):
        logs = (
            "mean_volume: -18.0 dB\nmax_volume: -2.0 dB\n"
            "Integrated loudness:\n    I: -14.0 LUFS\n"
            "Loudness range:\n    LRA: 4.2 LU\n"
            "True peak:\n    Peak: -0.8 dBFS\n"
        )
        result = assess_probe(probe(), logs)
        self.assertEqual(result["audio_loudness"]["integrated_lufs"], -14.0)
        self.assertEqual(result["audio_loudness"]["range_lu"], 4.2)
        self.assertEqual(result["audio_loudness"]["true_peak_dbfs"], -0.8)
        checks = {item["name"]: item for item in result["checks"]}
        self.assertEqual(checks["integrated_loudness"]["status"], "passed")
        self.assertEqual(checks["true_peak"]["status"], "warning")
        self.assertEqual(result["status"], "warning")

    def test_reports_loudness_outside_guidance_as_advisory(self):
        logs = (
            "max_volume: -4.0 dB\n"
            "Integrated loudness:\n    I: -22.0 LUFS\n"
            "Loudness range:\n    LRA: 8.0 LU\n"
            "True peak:\n    Peak: -3.0 dBFS\n"
        )
        result = assess_probe(probe(), logs)
        self.assertEqual(result["status"], "warning")
        self.assertIn("Integrated loudness is outside the general short-form guidance band; listen before changing gain", result["warnings"])
        self.assertEqual(result["audio_loudness"]["integrated_lufs"], -22.0)


    def test_editorial_quality_reports_fast_and_overlong_single_line_captions_without_blocking(self):
        from shortform_editor.qc import assess_edit_quality
        edl = {"segments": [{
            "source_in": "00:00:00.000", "source_out": "00:00:10.000",
            "layout": "split_vertical",
            "captions": [{
                "start": "00:00:01.000", "end": "00:00:02.000",
                "text": "This caption is intentionally much too long for the single line"
            }]
        }]}
        report = assess_edit_quality(edl)
        self.assertEqual(report["status"], "review_needed")
        self.assertTrue(any("characters/second" in warning for warning in report["warnings"]))
        self.assertTrue(any("horizontal scaling" in warning for warning in report["warnings"]))
        self.assertTrue(any(check["name"] == "caption_readability" and check["status"] == "review"
                            for check in report["checks"]))

    def test_editorial_quality_flags_short_segments_missing_captions_and_flash_captions(self):
        from shortform_editor.qc import assess_edit_quality
        edl = {"segments": [
            {"source_in": "00:00:00.000", "source_out": "00:00:04.000",
             "layout": "fullscreen", "captions": []},
            {"source_in": "00:00:04.000", "source_out": "00:00:08.000",
             "layout": "fullscreen", "captions": [{
                 "start": "00:00:04.000", "end": "00:00:04.200", "text": "Flash"
             }]}
        ]}
        report = assess_edit_quality(edl)
        self.assertEqual(report["status"], "review_needed")
        self.assertTrue(any("very short" in warning for warning in report["warnings"]))
        self.assertTrue(any("no captions" in warning for warning in report["warnings"]))
        self.assertTrue(any("less than 0.35s" in warning for warning in report["warnings"]))

    def test_editorial_quality_clean_edl_has_no_obvious_flags(self):
        from shortform_editor.qc import assess_edit_quality
        edl = {"segments": [{
            "source_in": "00:00:00.000", "source_out": "00:00:20.000",
            "layout": "fullscreen", "captions": [{
                "start": "00:00:01.000", "end": "00:00:03.000", "text": "A readable caption"
            }]
        }]}
        report = assess_edit_quality(edl)
        self.assertEqual(report["status"], "no_obvious_flags")
        self.assertFalse(report["warnings"])



if __name__ == "__main__":
    unittest.main()
