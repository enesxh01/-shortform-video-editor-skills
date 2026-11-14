import tempfile
import unittest
from pathlib import Path

from shortform_editor.captions import _ass_time, ffmpeg_subtitles_filter, write_ass_subtitles
from shortform_editor.cli import PipelineError


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
            self.assertIn(r"{\an5\q2\fscx", content)
            self.assertIn("One line", content)

    def test_caption_safe_area_and_pop_fade_animation(self):
        segment = {"captions": [{
            "start": "00:00:01.000", "end": "00:00:02.000", "text": "Safe caption",
            "font_size": 60, "margin_v": 320, "animation": "pop_fade"
        }]}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "animated.ass"
            write_ass_subtitles(segment, "fullscreen", 0.0, path)
            content = path.read_text(encoding="utf-8")
        self.assertIn(r"\fs60", content)
        self.assertIn(r"\t(0,140,", content)
        self.assertIn(r"\fad(90,80)", content)
        self.assertIn("Default,,0,0,320,,", content)

    def test_rejects_out_of_range_caption_safe_area(self):
        segment = {"captions": [{
            "start": "00:00:01.000", "end": "00:00:02.000", "text": "Unsafe",
            "margin_v": 900
        }]}
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(PipelineError):
                write_ass_subtitles(segment, "fullscreen", 0.0, Path(directory) / "bad.ass")

    def test_filter_path_escapes_windows_drive_colon(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "subtitles.ass"
            path.write_text("", encoding="utf-8")
            self.assertIn("subtitles=filename=", ffmpeg_subtitles_filter(path))


    def test_karaoke_punctuation_has_no_leading_space(self):
        segment = {"captions": [{
            "start": "00:00:01.000", "end": "00:00:02.000",
            "text": "Hello, world!",
            "words": [
                {"text": "Hello", "start": "00:00:01.000", "end": "00:00:01.300"},
                {"text": ",", "start": "00:00:01.300", "end": "00:00:01.350"},
                {"text": "world", "start": "00:00:01.400", "end": "00:00:01.800"},
                {"text": "!", "start": "00:00:01.800", "end": "00:00:01.850"}
            ]
        }]}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "captions.ass"
            write_ass_subtitles(segment, "fullscreen", 1.0, path)
            content = path.read_text(encoding="utf-8")
        self.assertNotIn("Hello ,", content)
        self.assertNotIn("world !", content)

    def test_newlines_are_converted_to_ass_line_breaks(self):
        segment = {"captions": [{
            "start": "00:00:01.000", "end": "00:00:02.000",
            "text": "First line\\nSecond line"
        }]}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "captions.ass"
            write_ass_subtitles(segment, "fullscreen", 1.0, path)
            content = path.read_text(encoding="utf-8")
        self.assertIn(r"First line\NSecond line", content)


if __name__ == "__main__":
    unittest.main()
