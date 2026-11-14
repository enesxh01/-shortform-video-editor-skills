import json
import subprocess
import unittest
from argparse import Namespace
from contextlib import redirect_stdout
from io import StringIO
from unittest.mock import patch

from shortform_editor.cli import command_doctor


class DoctorTests(unittest.TestCase):
    def test_reports_missing_required_tools_and_optional_extras(self):
        output = StringIO()
        with patch("shortform_editor.cli.shutil.which", return_value=None), \
             patch("importlib.util.find_spec", return_value=None), redirect_stdout(output):
            result = command_doctor(Namespace())
        report = json.loads(output.getvalue())
        self.assertEqual(result, 2)
        self.assertEqual(report["status"], "needs_attention")
        self.assertIn("ffmpeg", report["missing_required"])
        self.assertIn("faster_whisper", report["missing_optional"])

    def test_reports_ready_core_with_missing_optional_extras_and_nvenc(self):
        output = StringIO()
        def which(name):
            return {"ffmpeg": "/fake/ffmpeg", "ffprobe": "/fake/ffprobe"}.get(name)
        def run(args):
            stdout = ("Encoders: h264_nvenc libx264" if args[-1] == "-encoders" else
                      ("Filters: subtitles" if args[-1] == "-filters" else "tool version fake"))
            return subprocess.CompletedProcess(args, 0, stdout, "")
        def find_spec(name):
            return object() if name in {"jsonschema", "psutil"} else None
        with patch("shortform_editor.cli.shutil.which", side_effect=which), \
             patch("shortform_editor.cli.run_checked", side_effect=run), \
             patch("importlib.util.find_spec", side_effect=find_spec), redirect_stdout(output):
            result = command_doctor(Namespace())
        report = json.loads(output.getvalue())
        self.assertEqual(result, 0)
        self.assertEqual(report["status"], "ready_with_optional_extras_missing")
        self.assertTrue(report["accelerators"]["h264_nvenc"]["available"])
        self.assertTrue(report["accelerators"]["libx264"]["available"])
        self.assertTrue(report["accelerators"]["subtitles_filter"]["available"])
        self.assertEqual(set(report["missing_optional"]), {"faster_whisper", "cv2", "yt_dlp"})


if __name__ == "__main__":
    unittest.main()
