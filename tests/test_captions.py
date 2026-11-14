import tempfile
import unittest
from pathlib import Path

from shortform_editor.captions import _ass_time, ffmpeg_subtitles_filter, write_ass_subtitles


class CaptionTests(unittest.TestCase):
    def test_ass_time_formats_centiseconds(self):
        self.assertEqual(_ass_time(61.239), "0:01:01.24")

    def test_writes_karaoke_timed_kino_caption(self):
        segment = {
            "captions": [{
                "start": "00:00:01.000",
                "end": "00:00:03.000",
                "text": "Hello there",
                "words": [
                    {"text": "Hello", "start": "00:00:01.000", "end": "00:00:01.500"},
                    {"text": "there", "start": "00:00:01.500", "end": "00:00:02.000"}
                ]
            }]
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "captions.ass"
            self.assertEqual(write_ass_subtitles(segment, "fullscreen", 0.0, path), path)
            content = path.read_text(encoding="utf-8")
            self.assertIn(r"{\kf50}Hello {\kf50}there", content)
            self.assertIn("Style: Default,Arial,68", content)

    def test_split_layout_uses_centered_single_line_style(self):
        segment = {"captions": [{
            "start": "00:00:01.000", "end": "00:00:02.000", "text": "One line"
        }]}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "split.ass"
            write_ass_subtitles(segment, "split_vertical", 0.0, path)
            content = path.read_text(encoding="utf-8")
            self.assertIn("Style: Default,Arial,48", content)
            self.assertIn(r"{\an5}One line", content)

    def test_filter_path_escapes_windows_drive_colon(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "subtitles.ass"
            path.write_text("", encoding="utf-8")
            self.assertIn("subtitles=filename=", ffmpeg_subtitles_filter(path))


if __name__ == "__main__":
    unittest.main()
