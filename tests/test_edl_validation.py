import unittest

from shortform_editor.cli import validate_edl


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
    def test_accepts_valid_draft(self):
        self.assertEqual(validate_edl(valid_edl()), [])

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


if __name__ == "__main__":
    unittest.main()
