import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

from shortform_editor.ingest import download_source
from shortform_editor.cli import PipelineError


class URLIngestionTests(unittest.TestCase):
    def test_rejects_non_http_protocols(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(PipelineError):
                download_source("file:///etc/passwd", Path(directory) / "out")

    def test_rejects_missing_host(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(PipelineError):
                download_source("https:///video", Path(directory) / "out")

    def test_rejects_nonempty_output_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "out"
            output.mkdir()
            (output / "keep.txt").write_text("keep")
            with self.assertRaises(PipelineError):
                download_source("https://example.com/video", output)

    def test_enforces_download_size_bounds(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(PipelineError):
                download_source("https://example.com/video", Path(directory) / "out", 0)


    def test_downloads_single_url_and_probes_merged_media(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "out"
            output.mkdir()
            state = {}

            class FakeYoutubeDL:
                def __init__(self, options):
                    state["options"] = options
                def __enter__(self):
                    return self
                def __exit__(self, *args):
                    return False
                def extract_info(self, url, download):
                    state["url"] = url
                    state["download"] = download
                    (output / "source.mp4").write_bytes(b"video")
                    return {"title": "Test clip", "extractor_key": "Example"}
                def prepare_filename(self, info):
                    return str(output / "source.webm")

            fake = types.ModuleType("yt_dlp")
            fake.YoutubeDL = FakeYoutubeDL
            probe = {"source": {"fingerprint": "sha256:test"}, "format": {"duration": "10"}}
            with patch.dict(sys.modules, {"yt_dlp": fake}), \\
                 patch("shortform_editor.ingest.probe_media", return_value=probe):
                result = download_source("https://example.com/watch?v=123", output)

            self.assertEqual(result["source_path"], str(output / "source.mp4"))
            self.assertEqual(result["source_fingerprint"], "sha256:test")
            self.assertTrue(state["options"]["noplaylist"])
            self.assertEqual(state["options"]["max_filesize"], 2048 * 1024 * 1024)
            self.assertTrue(state["download"])


if __name__ == "__main__":
    unittest.main()
