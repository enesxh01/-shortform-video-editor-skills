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


    def test_face_aware_caption_position_moves_caption_above_lower_face(self):
        from shortform_editor.captions import apply_face_aware_caption_positions
        captions = [{"start": "00:00:01.000", "end": "00:00:03.000", "text": "Hello"}]
        samples = [{
            "time_seconds": 1.5,
            "subject_bbox_normalized": {"x": 0.45, "y": 0.74, "width": 0.10, "height": 0.20},
            "crop_9_16": {"x": 656.0, "y": 0.0, "width": 608.0, "height": 1080.0}
        }]
        result = apply_face_aware_caption_positions(captions, samples, 1920, 1080)
        self.assertEqual(result[0]["position"], "top")
        self.assertEqual(result[0]["position_reason"], "face_overlap_with_lower_caption_safe_area")

    def test_face_aware_caption_position_keeps_caption_below_upper_face(self):
        from shortform_editor.captions import apply_face_aware_caption_positions
        captions = [{"start": "00:00:01.000", "end": "00:00:03.000", "text": "Hello"}]
        samples = [{
            "time_seconds": 1.5,
            "subject_bbox_normalized": {"x": 0.45, "y": 0.08, "width": 0.10, "height": 0.18},
            "crop_9_16": {"x": 656.0, "y": 0.0, "width": 608.0, "height": 1080.0}
        }]
        result = apply_face_aware_caption_positions(captions, samples, 1920, 1080)
        self.assertEqual(result[0]["position"], "bottom")

    def test_supports_optional_per_word_kino_highlight_color(self):
        segment = {"captions": [{
            "start": "00:00:01.000", "end": "00:00:02.000",
            "text": "Important detail",
            "words": [
                {"text": "Important", "start": "00:00:01.000", "end": "00:00:01.500", "highlight_color": "#FF0000"},
                {"text": "detail", "start": "00:00:01.500", "end": "00:00:02.000"}
            ]
        }]}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "highlight.ass"
            write_ass_subtitles(segment, "fullscreen", 0.0, path)
            content = path.read_text(encoding="utf-8")
        self.assertIn(r"{\c&H000000FF&}", content)
        self.assertIn(r"{\c}", content)

    def test_rejects_invalid_per_word_highlight_color(self):
        segment = {"captions": [{
            "start": "00:00:01.000", "end": "00:00:02.000", "text": "Bad color",
            "words": [{
                "text": "Bad", "start": "00:00:01.000", "end": "00:00:02.000",
                "highlight_color": "red"
            }]
        }]}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "invalid-highlight.ass"
            with self.assertRaises(PipelineError):
                write_ass_subtitles(segment, "fullscreen", 0.0, path)

    def test_supports_safe_installed_font_name(self):
        segment = {"captions": [{
            "start": "00:00:01.000", "end": "00:00:02.000",
            "text": "Kino caption", "font_name": "Montserrat SemiBold"
        }]}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "font.ass"
            write_ass_subtitles(segment, "fullscreen", 0.0, path)
            content = path.read_text(encoding="utf-8")
        self.assertIn(r"\fnMontserrat SemiBold", content)

    def test_rejects_unsafe_font_name(self):
        segment = {"captions": [{
            "start": "00:00:01.000", "end": "00:00:02.000",
            "text": "Kino caption", "font_name": "Arial}\\NDialogue: injected"
        }]}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "unsafe.ass"
            with self.assertRaises(PipelineError):
                write_ass_subtitles(segment, "fullscreen", 0.0, path)

    def test_top_caption_position_uses_top_alignment(self):
        segment = {"captions": [{
            "start": "00:00:01.000", "end": "00:00:02.000", "text": "Top caption",
            "position": "top"
        }]}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "top.ass"
            write_ass_subtitles(segment, "fullscreen", 0.0, path)
            content = path.read_text(encoding="utf-8")
        self.assertIn(r"{\an8}", content)


if __name__ == "__main__":
    unittest.main()
