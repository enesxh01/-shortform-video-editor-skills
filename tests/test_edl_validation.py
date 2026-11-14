import json
import unittest
from pathlib import Path

from shortform_editor.cli import PipelineError, SCHEMA_PATH, _segment_look_filters, load_schema, validate_edl


def valid_edl():
    return {
        "schema_version": "1.0",
        "project_id": "test-project",
        "source": {
            "fingerprint": "sha256:" + ("a" * 64),
            "time_base": "1/90000",
            "frame_rate": "30/1",
            "variable_frame_rate": False
        },
        "render": {
            "width": 1080,
            "height": 1920,
            "fps_target": "60/1",
            "fps_mode": "cfr",
            "fps_conversion": "duplicate_drop",
            "container": "mp4",
            "video_codec": "h264",
            "audio_codec": "aac"
        },
        "segments": [{
            "id": "clip-1",
            "source_in": "00:00:02.000",
            "source_out": "00:00:08.500",
            "timeline_start": "00:00:00.000",
            "layout": "fullscreen",
            "reason": "test",
            "confidence": 0.8
        }],
        "approval": {"status": "draft", "approved_by_user": False}
    }


class EDLValidationTests(unittest.TestCase):
    def test_packaged_schema_matches_repository_schema(self):
        repository_schema = Path(__file__).resolve().parents[1] / "schemas" / "edit-decision-list.schema.json"
        packaged_schema = Path(__file__).resolve().parents[1] / "shortform_editor" / "schemas" / "edl.schema.json"
        self.assertEqual(repository_schema.read_bytes(), packaged_schema.read_bytes())
        semantic_repository = repository_schema.with_name("semantic-review.schema.json")
        semantic_packaged = packaged_schema.with_name("semantic-review.schema.json")
        self.assertEqual(semantic_repository.read_bytes(), semantic_packaged.read_bytes())

    def test_accepts_valid_draft(self):
        self.assertEqual(validate_edl(valid_edl()), [])

    def test_accepts_optional_fades(self):
        edl = valid_edl()
        edl["segments"][0]["fade_in_seconds"] = 0.25
        edl["segments"][0]["fade_out_seconds"] = 0.25
        self.assertEqual(validate_edl(edl), [])

    def test_accepts_color_grade_and_sharpening_controls(self):
        edl = valid_edl()
        edl["segments"][0]["color_grade"] = {
            "brightness": 0.02, "contrast": 1.08, "saturation": 1.12,
            "gamma": 0.98, "sharpen": 0.45
        }
        self.assertEqual(validate_edl(edl), [])

    def test_builds_professional_grade_and_sharpen_filters(self):
        filters = _segment_look_filters({"color_grade": {
            "brightness": 0.02, "contrast": 1.1, "saturation": 1.15,
            "gamma": 0.95, "sharpen": 0.4
        }})
        self.assertEqual(len(filters), 2)
        self.assertTrue(filters[0].startswith("eq="))
        self.assertTrue(filters[1].startswith("unsharp="))

    def test_neutral_look_does_not_add_filters(self):
        self.assertEqual(_segment_look_filters({}), [])

    def test_rejects_non_finite_or_excessive_sharpening(self):
        with self.assertRaises(PipelineError):
            _segment_look_filters({"color_grade": {"sharpen": 2.0}})

    def test_rejects_out_of_range_color_grade(self):
        edl = valid_edl()
        edl["segments"][0]["color_grade"] = {"sharpen": 1.8}
        self.assertTrue(validate_edl(edl))

    def test_rejects_fades_longer_than_segment(self):
        edl = valid_edl()
        edl["segments"][0]["source_out"] = "00:00:04.500"
        edl["segments"][0]["fade_in_seconds"] = 1.5
        edl["segments"][0]["fade_out_seconds"] = 1.0
        self.assertTrue(any("fade durations" in error for error in validate_edl(edl)))

    def test_rejects_out_before_in(self):
        edl = valid_edl()
        edl["segments"][0]["source_out"] = "00:00:01.000"
        self.assertTrue(any("source_out must be greater" in e for e in validate_edl(edl)))

    def test_rejects_empty_segments(self):
        edl = valid_edl()
        edl["segments"] = []
        self.assertTrue(validate_edl(edl))

    def test_rejects_non_timestamp(self):
        edl = valid_edl()
        edl["segments"][0]["source_in"] = "banana"
        self.assertTrue(validate_edl(edl))

    def test_rejects_landscape_or_wrong_ratio(self):
        edl = valid_edl()
        edl["render"]["width"] = 7
        edl["render"]["height"] = 3
        self.assertTrue(validate_edl(edl))

    def test_rejects_approval_without_user_confirmation(self):
        edl = valid_edl()
        edl["approval"] = {"status": "approved", "approved_by_user": False}
        self.assertTrue(validate_edl(edl))

    def test_rejects_duplicate_segment_ids(self):
        edl = valid_edl()
        edl["segments"].append(dict(edl["segments"][0]))
        self.assertTrue(any("duplicates" in e for e in validate_edl(edl)))

    def test_rejects_segment_beyond_source_duration(self):
        self.assertTrue(validate_edl(valid_edl(), source_duration=5.0))

    def test_rejects_wrong_source_fingerprint(self):
        self.assertTrue(any("fingerprint does not match" in e for e in validate_edl(
            valid_edl(), source_fingerprint="sha256:" + ("b" * 64)
        )))

    def test_split_layout_requires_two_source_specs(self):
        edl = valid_edl()
        edl["segments"][0]["layout"] = "split_vertical"
        edl["segments"][0]["split_top"] = {
            "path": "top.mp4", "fingerprint": "sha256:" + ("b" * 64),
            "source_in": "00:00:02.000", "source_out": "00:00:08.500"
        }
        edl["segments"][0]["split_bottom"] = {
            "path": "bottom.mp4", "fingerprint": "sha256:" + ("c" * 64),
            "source_in": "00:00:02.000", "source_out": "00:00:08.500"
        }
        self.assertEqual(validate_edl(edl), [])
        del edl["segments"][0]["split_bottom"]
        self.assertTrue(any("split_bottom" in error for error in validate_edl(edl)))


    def test_split_layout_reports_each_missing_source_once(self):
        edl = valid_edl()
        edl["segments"][0]["layout"] = "split_vertical"
        errors = validate_edl(edl)
        self.assertEqual(sum("split_top" in error and "required property" in error for error in errors), 1)
        self.assertEqual(sum("split_bottom" in error and "required property" in error for error in errors), 1)
        self.assertFalse(any("requires both" in error for error in errors))

    def test_rejects_caption_outside_segment(self):
        edl = valid_edl()
        edl["segments"][0]["captions"] = [{
            "start": "00:00:01.000",
            "end": "00:00:03.000",
            "text": "Caption outside segment"
        }]
        self.assertTrue(any("must fit inside" in e for e in validate_edl(edl)))


    def test_rejects_pacing_decision_outside_segment(self):
        edl = valid_edl()
        edl["segments"][0]["pacing_review"] = {
            "decisions": [{
                "decision": "trim", "source_in": "00:00:01.000",
                "source_out": "00:00:02.000", "rationale": "Outside",
                "confidence": 0.5, "context_risk": "medium"
            }],
            "repeated_word_flags": [],
            "note": "Advisory only"
        }
        self.assertTrue(any("fit inside the segment source range" in e for e in validate_edl(edl)))



    def test_rejects_timeline_gap_unsupported_by_sequential_renderer(self):
        edl = valid_edl()
        second = dict(edl["segments"][0])
        second["id"] = "clip-2"
        second["source_in"] = "00:00:10.000"
        second["source_out"] = "00:00:16.000"
        second["timeline_start"] = "00:00:10.000"
        edl["segments"].append(second)
        self.assertTrue(any("sequential render position" in error for error in validate_edl(edl)))


    def test_rejects_approved_edl_without_content_hash(self):
        edl = valid_edl()
        edl["approval"] = {"status": "approved", "approved_by_user": True}
        self.assertTrue(any("approved_edl_sha256" in error for error in validate_edl(edl)))


    def test_installed_schema_path_resolves_packaged_edl_schema(self):
        self.assertEqual(SCHEMA_PATH.name, "edl.schema.json")
        self.assertTrue(SCHEMA_PATH.is_file())
        self.assertIn("properties", load_schema())


    def test_accepts_safe_font_and_word_highlight_edl_fields(self):
        edl = valid_edl()
        edl["segments"][0]["captions"] = [{
            "start": "00:00:02.500", "end": "00:00:04.000",
            "text": "Important detail", "font_name": "Montserrat SemiBold",
            "words": [
                {"text": "Important", "start": "00:00:02.500", "end": "00:00:03.200", "highlight_color": "#FFCC00"},
                {"text": "detail", "start": "00:00:03.200", "end": "00:00:04.000"}
            ]
        }]
        self.assertEqual(validate_edl(edl), [])

    def test_rejects_invalid_word_highlight_color_in_edl(self):
        edl = valid_edl()
        edl["segments"][0]["captions"] = [{
            "start": "00:00:02.500", "end": "00:00:04.000",
            "text": "Important", "words": [{
                "text": "Important", "start": "00:00:02.500", "end": "00:00:04.000",
                "highlight_color": "yellow"
            }]
        }]
        self.assertTrue(any("highlight_color" in error for error in validate_edl(edl)))

    def test_rejects_control_characters_in_caption_text(self):
        edl = valid_edl()
        edl["segments"][0]["captions"] = [{
            "start": "00:00:02.500", "end": "00:00:04.000",
            "text": "Unsafe\x00caption"
        }]
        self.assertTrue(any("unsupported control characters" in error for error in validate_edl(edl)))

    def test_rejects_control_characters_in_caption_word_text(self):
        edl = valid_edl()
        edl["segments"][0]["captions"] = [{
            "start": "00:00:02.500", "end": "00:00:04.000",
            "text": "Unsafe caption",
            "words": [{
                "text": "Unsafe\x01", "start": "00:00:02.500", "end": "00:00:04.000"
            }]
        }]
        self.assertTrue(any("words[0].text contains unsupported control characters" in error for error in validate_edl(edl)))

    def test_split_captions_must_be_one_line(self):
        edl = valid_edl()
        edl["segments"][0]["layout"] = "split_vertical"
        edl["segments"][0]["split_top"] = {
            "path": "top.mp4", "fingerprint": "sha256:" + ("b" * 64),
            "source_in": "00:00:02.000", "source_out": "00:00:08.500"
        }
        edl["segments"][0]["split_bottom"] = {
            "path": "bottom.mp4", "fingerprint": "sha256:" + ("c" * 64),
            "source_in": "00:00:02.000", "source_out": "00:00:08.500"
        }
        edl["segments"][0]["captions"] = [{
            "start": "00:00:02.500", "end": "00:00:04.000",
            "text": "First line\nSecond line"
        }]
        self.assertTrue(any("must be exactly one line" in error for error in validate_edl(edl)))

    def test_blurred_bars_captions_must_be_one_line(self):
        edl = valid_edl()
        edl["segments"][0]["layout"] = "blurred_bars_20_60_20"
        edl["segments"][0]["captions"] = [{
            "start": "00:00:02.500", "end": "00:00:04.000",
            "text": "First line\nSecond line"
        }]
        self.assertTrue(any("must be exactly one line" in error for error in validate_edl(edl)))

    def test_fullscreen_captions_are_limited_to_three_lines(self):
        edl = valid_edl()
        edl["segments"][0]["captions"] = [{
            "start": "00:00:02.500", "end": "00:00:04.000",
            "text": "One\nTwo\nThree\nFour"
        }]
        self.assertTrue(any("at most three lines" in error for error in validate_edl(edl)))

    def test_caption_events_must_not_overlap(self):
        edl = valid_edl()
        edl["segments"][0]["captions"] = [
            {"start": "00:00:02.500", "end": "00:00:04.000", "text": "First"},
            {"start": "00:00:03.500", "end": "00:00:05.000", "text": "Second"}
        ]
        self.assertTrue(any("overlaps or is out of chronological order" in error for error in validate_edl(edl)))

    def test_split_captions_cannot_be_moved_out_of_divider(self):
        edl = valid_edl()
        edl["segments"][0]["layout"] = "split_vertical"
        edl["segments"][0]["split_top"] = {
            "path": "top.mp4", "fingerprint": "sha256:" + ("b" * 64),
            "source_in": "00:00:02.000", "source_out": "00:00:08.500"
        }
        edl["segments"][0]["split_bottom"] = {
            "path": "bottom.mp4", "fingerprint": "sha256:" + ("c" * 64),
            "source_in": "00:00:02.000", "source_out": "00:00:08.500"
        }
        edl["segments"][0]["captions"] = [{
            "start": "00:00:02.500", "end": "00:00:04.000",
            "text": "Centered", "position": "top"
        }]
        self.assertTrue(any("must remain centered" in error for error in validate_edl(edl)))

    def test_blurred_bars_captions_cannot_be_moved_into_blurred_bars(self):
        edl = valid_edl()
        edl["segments"][0]["layout"] = "blurred_bars_20_60_20"
        edl["segments"][0]["captions"] = [{
            "start": "00:00:02.500", "end": "00:00:04.000",
            "text": "Safe", "position": "top"
        }]
        self.assertTrue(any("must remain in the main composition" in error for error in validate_edl(edl)))


if __name__ == "__main__":
    unittest.main()
