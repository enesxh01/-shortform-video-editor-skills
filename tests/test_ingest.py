import tempfile
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


if __name__ == "__main__":
    unittest.main()
