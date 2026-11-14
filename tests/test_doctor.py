import json
import subprocess
import unittest
from argparse import Namespace
from contextlib import redirect_stdout
from io import StringIO
from unittest.mock import patch

from shortform_editor.cli import command_doctor


FILTERS = "\n".join([
    " T.. subtitles", " T.. fps", " T.. scale", " T.. crop", " T.. setpts",
    " T.. setsar", " T.. format", " T.. aresample", " T.. blackdetect",
    " T.. freezedetect", " T.. volumedetect", " T.. ebur128", " T.. split",
    " T.. overlay", " T.. vstack", " T.. boxblur", " T.. fade", " T.. eq",
    " T.. unsharp", " T.. null"
])


class DoctorTests(unittest.TestCase):
    def _mock_environment(self, filters=FILTERS):
        def which(name):
            return {"ffmpeg": "/fake/ffmpeg", "ffprobe": "/fake/ffprobe"}.get(name)

        def run(args):
            if args[-1] == "-encoders":
                stdout = "Encoders: h264_nvenc libx264 aac"
            elif args[-1] == "-filters":
                stdout = filters
            else:
                stdout = "tool version fake"
            return subprocess.CompletedProcess(args, 0, stdout, "")

        def find_spec(name):
            return object() if name in {"jsonschema", "psutil"} else None

        return which, run, find_spec

    def test_reports_missing_required_tools_and_optional_extras(self):
        output = StringIO()
        with patch("shortform_editor.cli.shutil.which", return_value=None), patch("importlib.util.find_spec", return_value=None), redirect_stdout(output):
            result = command_doctor(Namespace())
        report = json.loads(output.getvalue())
        self.assertEqual(result, 2)
        self.assertEqual(report["status"], "needs_attention")
        self.assertIn("ffmpeg", report["missing_required"])
        self.assertIn("faster_whisper", report["missing_optional"])

    def test_reports_ready_core_with_missing_optional_extras_and_nvenc(self):
        output = StringIO()
        which, run, find_spec = self._mock_environment()
        with patch("shortform_editor.cli.shutil.which", side_effect=which), patch("shortform_editor.cli.run_checked", side_effect=run), patch("importlib.util.find_spec", side_effect=find_spec), redirect_stdout(output):
            result = command_doctor(Namespace())
        report = json.loads(output.getvalue())
        self.assertEqual(result, 0)
        self.assertEqual(report["status"], "ready_with_optional_extras_missing")
        self.assertTrue(report["accelerators"]["h264_nvenc"]["available"])
        self.assertTrue(report["accelerators"]["libx264"]["available"])
        self.assertTrue(report["accelerators"]["aac"]["available"])
        self.assertTrue(report["accelerators"]["subtitles_filter"]["available"])
        self.assertTrue(report["accelerators"]["filters"]["ebur128"]["available"])
        self.assertEqual(set(report["missing_optional"]), {"faster_whisper", "cv2", "yt_dlp"})

    def test_reports_missing_required_aac_encoder(self):
        output = StringIO()
        which, run, find_spec = self._mock_environment()
        def without_aac(args):
            result = run(args)
            if args[-1] == "-encoders":
                result.stdout = "Encoders: h264_nvenc libx264"
            return result
        with patch("shortform_editor.cli.shutil.which", side_effect=which), patch("shortform_editor.cli.run_checked", side_effect=without_aac), patch("importlib.util.find_spec", side_effect=find_spec), redirect_stdout(output):
            result = command_doctor(Namespace())
        report = json.loads(output.getvalue())
        self.assertEqual(result, 2)
        self.assertIn("ffmpeg_aac_encoder", report["missing_required"])
        self.assertFalse(report["accelerators"]["aac"]["available"])

    def test_reports_missing_required_filter_instead_of_false_ready(self):
        output = StringIO()
        filters = "\n".join(line for line in FILTERS.splitlines() if "ebur128" not in line)
        which, run, find_spec = self._mock_environment(filters)
        with patch("shortform_editor.cli.shutil.which", side_effect=which), patch("shortform_editor.cli.run_checked", side_effect=run), patch("importlib.util.find_spec", side_effect=find_spec), redirect_stdout(output):
            result = command_doctor(Namespace())
        report = json.loads(output.getvalue())
        self.assertEqual(result, 2)
        self.assertIn("ffmpeg_filter:ebur128", report["missing_required"])
        self.assertFalse(report["accelerators"]["filters"]["ebur128"]["available"])


if __name__ == "__main__":
    unittest.main()
