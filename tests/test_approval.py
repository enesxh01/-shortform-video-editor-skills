import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from shortform_editor.approval import approve_edl_file
from shortform_editor.cli import PipelineError


def make_edl(fingerprint):
    return {
        "schema_version": "1.0",
        "project_id": "approval-test",
        "source": {"fingerprint": fingerprint, "time_base": "1/90000", "frame_rate": "30/1"},
        "render": {
            "width": 1080, "height": 1920, "fps_target": "60/1",
            "fps_mode": "cfr", "fps_conversion": "duplicate_drop", "container": "mp4",
            "video_codec": "h264", "audio_codec": "aac"
        },
        "segments": [{
            "id": "candidate-1", "source_in": "00:00:01.000",
            "source_out": "00:00:10.000", "layout": "fullscreen"
        }],
        "approval": {"status": "draft", "approved_by_user": False}
    }


class ApprovalTests(unittest.TestCase):
    def test_requires_explicit_confirmation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.mp4"
            edl_path = root / "edit.json"
            source.write_bytes(b"source")
            edl_path.write_text(json.dumps(make_edl("sha256:" + "a" * 64)), encoding="utf-8")
            with self.assertRaises(PipelineError):
                approve_edl_file(edl_path, source, confirm=False)

    def test_approves_only_valid_matching_source_edl(self):
        fingerprint = "sha256:" + "a" * 64
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.mp4"
            edl_path = root / "edit.json"
            source.write_bytes(b"source")
            edl_path.write_text(json.dumps(make_edl(fingerprint)), encoding="utf-8")
            with patch("shortform_editor.approval.probe_media", return_value={
                "source": {"fingerprint": fingerprint},
                "format": {"duration": "30.0"}
            }):
                result = approve_edl_file(edl_path, source, confirm=True)
            saved = json.loads(edl_path.read_text(encoding="utf-8"))
            self.assertEqual(result["status"], "approved")
            self.assertEqual(saved["approval"], {"status": "approved", "approved_by_user": True})

    def test_rejects_wrong_source_fingerprint(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.mp4"
            edl_path = root / "edit.json"
            source.write_bytes(b"source")
            edl_path.write_text(json.dumps(make_edl("sha256:" + "b" * 64)), encoding="utf-8")
            with patch("shortform_editor.approval.probe_media", return_value={
                "source": {"fingerprint": "sha256:" + "a" * 64},
                "format": {"duration": "30.0"}
            }):
                with self.assertRaises(PipelineError):
                    approve_edl_file(edl_path, source, confirm=True)


if __name__ == "__main__":
    unittest.main()
