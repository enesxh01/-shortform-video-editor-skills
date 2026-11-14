import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from shortform_editor.cli import analyze_frame_timestamps, probe_frame_timing


class FrameTimingDiagnosticsTests(unittest.TestCase):
    def test_classifies_regular_frame_cadence_as_likely_cfr(self):
        timestamps = [index / 30 for index in range(120)]
        report = analyze_frame_timestamps(timestamps)
        self.assertEqual(report["status"], "likely_cfr")
        self.assertIs(report["variable_frame_rate"], False)
        self.assertEqual(report["sampled_frames"], 120)

    def test_flags_materially_irregular_frame_cadence(self):
        timestamps = [0.0]
        for index in range(1, 120):
            timestamps.append(timestamps[-1] + (1 / 30 if index % 3 else 1 / 24))
        report = analyze_frame_timestamps(timestamps)
        self.assertEqual(report["status"], "likely_vfr")
        self.assertIs(report["variable_frame_rate"], True)
        self.assertGreater(report["irregular_interval_ratio"], 0.05)

    def test_insufficient_timestamps_remain_unknown(self):
        report = analyze_frame_timestamps([0.0, 1 / 30, 2 / 30])
        self.assertEqual(report["status"], "insufficient_samples")
        self.assertIsNone(report["variable_frame_rate"])

    def test_invalid_and_duplicate_timestamps_are_ignored(self):
        report = analyze_frame_timestamps(
            [index / 25 for index in range(30)] + ["bad", None, 0.0]
        )
        self.assertEqual(report["status"], "likely_cfr")
        self.assertEqual(report["sampled_frames"], 30)

    def test_report_discloses_sample_scope_and_no_normalization(self):
        report = analyze_frame_timestamps([index / 30 for index in range(30)])
        self.assertEqual(report["scope"], "stratified_frame_samples")
        self.assertIn("does not normalize timestamps", report["limitation"])

    def test_probe_samples_multiple_windows_across_video(self):
        timestamps = [{"best_effort_timestamp_time": str(index / 30)} for index in range(40)]
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.mp4"
            source.write_bytes(b"synthetic")
            with patch("shortform_editor.cli.run_checked", return_value=SimpleNamespace(
                stdout=json.dumps({"frames": timestamps})
            )) as runner:
                report = probe_frame_timing(source, "ffprobe", duration_seconds=100.0, sample_frames=40, sample_windows=4)
        self.assertEqual(report["status"], "likely_cfr")
        self.assertEqual(report["sample_windows"], 4)
        args = runner.call_args.args[0]
        self.assertIn("0.0%+#10,33.222%+#10,66.444%+#10,99.667%+#10", args)
        self.assertTrue(any("best_effort_timestamp_time" in item for item in args))
        self.assertEqual(args[-1], str(source))

    def test_probe_malformed_json_returns_unknown_instead_of_failing(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.mp4"
            source.write_bytes(b"synthetic")
            with patch("shortform_editor.cli.run_checked", return_value=SimpleNamespace(stdout="{")):
                report = probe_frame_timing(source, "ffprobe")
        self.assertEqual(report["status"], "insufficient_samples")
        self.assertIsNone(report["variable_frame_rate"])

    def test_non_monotonic_presentation_timestamps_are_not_hidden(self):
        timestamps = [index / 30 for index in range(30)]
        timestamps[15] = timestamps[14] - 0.1
        report = analyze_frame_timestamps(timestamps)
        self.assertEqual(report["status"], "likely_vfr")
        self.assertGreater(report["non_monotonic_intervals"], 0)

    def test_sampling_gaps_are_not_counted_as_frame_intervals(self):
        timestamps = [index / 30 for index in range(20)]
        timestamps += [10 + index / 30 for index in range(20)]
        report = analyze_frame_timestamps(timestamps, sample_window_starts=[0, 10])
        self.assertEqual(report["status"], "likely_cfr")
        self.assertEqual(report["sampled_intervals"], 38)


if __name__ == "__main__":
    unittest.main()
