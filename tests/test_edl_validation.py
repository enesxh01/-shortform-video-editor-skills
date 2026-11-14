import json
import unittest
from pathlib import Path

from shortform_editor.cli import SCHEMA_PATH, load_schema, validate_edl


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
        self.assertTrue(validate_edl(edl))

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


if __name__ == "__main__":
    unittest.main()
