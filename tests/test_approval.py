import json
from argparse import Namespace
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from shortform_editor.approval import approve_edl_file, edl_approval_hash
from shortform_editor.cli import PipelineError, command_render


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
            self.assertEqual(saved["approval"]["status"], "approved")
            self.assertTrue(saved["approval"]["approved_by_user"])
            self.assertEqual(saved["approval"]["approved_edl_sha256"], edl_approval_hash(saved))
            self.assertTrue(saved["approval"]["approved_at"])

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


    def test_edl_content_edit_invalidates_approval_hash(self):
        edl = make_edl("sha256:" + "a" * 64)
        edl["approval"] = {
            "status": "approved", "approved_by_user": True,
            "approved_at": "2026-01-01T00:00:00+00:00"
        }
        edl["approval"]["approved_edl_sha256"] = edl_approval_hash(edl)
        approved_hash = edl["approval"]["approved_edl_sha256"]
        edl["segments"][0]["reason"] = "Changed after approval"
        self.assertNotEqual(approved_hash, edl_approval_hash(edl))


    def test_final_render_rejects_edl_modified_after_approval(self):
        fingerprint = "sha256:" + "a" * 64
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.mp4"
            edl_path = root / "edit.json"
            source.write_bytes(b"source")
            edl = make_edl(fingerprint)
            edl["approval"] = {
                "status": "approved",
                "approved_by_user": True,
                "approved_at": "2026-01-01T00:00:00+00:00"
            }
            edl["approval"]["approved_edl_sha256"] = edl_approval_hash(edl)
            edl["segments"][0]["reason"] = "Edited after approval"
            edl_path.write_text(json.dumps(edl), encoding="utf-8")
            with patch("shortform_editor.cli.probe_media", return_value={
                "source": {"fingerprint": fingerprint},
                "format": {"duration": "30.0"}
            }):
                with self.assertRaisesRegex(PipelineError, "content changed after approval"):
                    command_render(Namespace(
                        source=str(source), edl=str(edl_path), output=str(root / "final.mp4"),
                        crf=18, preset="medium", overwrite=False
                    ))


if __name__ == "__main__":
    unittest.main()
