import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

from shortform_editor.ingest import download_source, _download_size_guard
from shortform_editor.cli import PipelineError, command_download_source


class URLIngestionTests(unittest.TestCase):
    def test_download_report_cannot_overwrite_downloaded_media(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.mp4"
            source.write_bytes(b"keep media bytes")
            args = types.SimpleNamespace(
                url="https://example.com/video",
                output_dir=str(Path(directory) / "out"),
                max_filesize_mb=2048,
                report=str(source)
            )
            report = {"source_path": str(source), "probe": {}}
            with patch("shortform_editor.cli.download_source", return_value=report):
                with self.assertRaisesRegex(PipelineError, "must not overwrite"):
                    command_download_source(args)
            self.assertEqual(source.read_bytes(), b"keep media bytes")

    def test_rejects_non_http_protocols(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(PipelineError):
                download_source("file:///etc/passwd", Path(directory) / "out")

    def test_rejects_embedded_url_credentials(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(PipelineError, "embedded credentials"):
                download_source("https://user:secret@example.com/video", Path(directory) / "out")

    def test_download_size_guard_aborts_as_soon_as_observed_bytes_exceed_cap(self):
        guard = _download_size_guard(100)
        guard({"filename": "video.mp4", "downloaded_bytes": 100})
        with self.assertRaisesRegex(PipelineError, "exceeded"):
            guard({"filename": "video.mp4", "downloaded_bytes": 101})

    def test_download_size_guard_counts_video_and_audio_streams_together(self):
        guard = _download_size_guard(100)
        guard({"filename": "video.mp4", "downloaded_bytes": 60})
        guard({"filename": "video.mp4", "downloaded_bytes": 60})
        with self.assertRaisesRegex(PipelineError, "exceeded"):
            guard({"filename": "audio.m4a", "downloaded_bytes": 41})

    def test_rejects_missing_host(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(PipelineError):
                download_source("https:///video", Path(directory) / "out")

    def test_rejects_output_path_that_is_a_file(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "not-a-directory"
            output.write_text("keep")
            with self.assertRaisesRegex(PipelineError, "not a directory"):
                download_source("https://example.com/video", output)
            self.assertEqual(output.read_text(), "keep")

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


    def test_cleans_partial_files_after_downloader_validation_error(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "out"
            output.mkdir()

            class AmbiguousYoutubeDL:
                def __init__(self, options): pass
                def __enter__(self): return self
                def __exit__(self, *args): return False
                def extract_info(self, url, download):
                    (output / "first.mp4").write_bytes(b"one")
                    (output / "second.mp4").write_bytes(b"two")
                    return {"title": "ambiguous"}
                def prepare_filename(self, info):
                    return str(output / "missing.webm")

            fake = types.ModuleType("yt_dlp")
            fake.YoutubeDL = AmbiguousYoutubeDL
            with patch.dict(sys.modules, {"yt_dlp": fake}):
                with self.assertRaisesRegex(PipelineError, "one unambiguous media file"):
                    download_source("https://example.com/video", output)
            self.assertEqual(list(output.iterdir()), [])

    def test_live_size_guard_aborts_and_cleans_partial_download(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "out"
            output.mkdir()

            class OversizeYoutubeDL:
                def __init__(self, options):
                    self.options = options
                def __enter__(self): return self
                def __exit__(self, *args): return False
                def extract_info(self, url, download):
                    (output / "source.mp4.part").write_bytes(b"partial")
                    self.options["progress_hooks"][0]({
                        "downloaded_bytes": 2048 * 1024 * 1024 + 1
                    })
                def prepare_filename(self, info):
                    return str(output / "source.mp4")

            fake = types.ModuleType("yt_dlp")
            fake.YoutubeDL = OversizeYoutubeDL
            with patch.dict(sys.modules, {"yt_dlp": fake}):
                with self.assertRaisesRegex(PipelineError, "exceeded"):
                    download_source("https://example.com/video", output)
            self.assertEqual(list(output.iterdir()), [])

    def test_cleans_partial_files_after_downloader_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "out"
            output.mkdir()
            class FailingYoutubeDL:
                def __init__(self, options): pass
                def __enter__(self): return self
                def __exit__(self, *args): return False
                def extract_info(self, url, download):
                    (output / "source.mp4.part").write_bytes(b"partial")
                    raise RuntimeError("network interrupted")
            fake = types.ModuleType("yt_dlp")
            fake.YoutubeDL = FailingYoutubeDL
            with patch.dict(sys.modules, {"yt_dlp": fake}):
                with self.assertRaises(PipelineError):
                    download_source("https://example.com/video", output)
            self.assertEqual(list(output.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
