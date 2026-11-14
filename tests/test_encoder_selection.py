import subprocess
import unittest
from unittest.mock import patch

from shortform_editor.cli import PipelineError, choose_video_encoder


class EncoderSelectionTests(unittest.TestCase):
    @patch("shortform_editor.cli.run_checked")
    def test_auto_prefers_nvenc_when_ffmpeg_lists_it(self, run_checked):
        run_checked.return_value = subprocess.CompletedProcess(
            ["ffmpeg", "-encoders"], 0, stdout=" V....D h264_nvenc NVIDIA NVENC H.264 encoder\n", stderr=""
        )
        self.assertEqual(choose_video_encoder("ffmpeg", "auto"), "h264_nvenc")

    @patch("shortform_editor.cli.run_checked")
    def test_auto_uses_cpu_when_nvenc_is_unavailable(self, run_checked):
        run_checked.return_value = subprocess.CompletedProcess(
            ["ffmpeg", "-encoders"], 0, stdout=" V....D libx264 H.264 encoder\n", stderr=""
        )
        self.assertEqual(choose_video_encoder("ffmpeg", "auto"), "libx264")

    @patch("shortform_editor.cli.run_checked")
    def test_explicit_nvenc_fails_clearly_when_not_listed(self, run_checked):
        run_checked.return_value = subprocess.CompletedProcess(
            ["ffmpeg", "-encoders"], 0, stdout=" V....D libx264 H.264 encoder\n", stderr=""
        )
        with self.assertRaisesRegex(PipelineError, "does not list the encoder"):
            choose_video_encoder("ffmpeg", "h264_nvenc")

    @patch("shortform_editor.cli.run_checked")
    def test_forced_cpu_does_not_probe_nvenc(self, run_checked):
        self.assertEqual(choose_video_encoder("ffmpeg", "libx264"), "libx264")
        run_checked.assert_not_called()


if __name__ == "__main__":
    unittest.main()
