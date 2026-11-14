import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from shortform_editor.pipeline import analyze_project
from shortform_editor.cli import PipelineError, validate_edl


class PipelineOrchestrationTests(unittest.TestCase):
    def test_creates_analysis_artifacts_and_unapproved_edl_draft(self):
        fingerprint = "sha256:" + ("9" * 64)
        candidate = {
            "candidate_id": "moment-123456789abc",
            "source_fingerprint": fingerprint,
            "source_in_seconds": 2.0,
            "source_out_seconds": 18.0,
            "family": "story_or_commentary",
            "transcript_excerpt": "A complete test moment",
            "confidence": 0.35
        }
        probe = {
            "source": {"path": "source.mp4", "sha256": "9" * 64, "fingerprint": fingerprint},
            "format": {"duration": "30.0"},
            "streams": [{
                "codec_type": "video", "time_base": "1/90000",
                "avg_frame_rate": "30/1"
            }]
        }
        audio = {
            "source": {"fingerprint": fingerprint},
            "analysis": {"transcription": {"status": "completed"}}
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.mp4"
            source.write_bytes(b"test input placeholder")
            output = root / "job"
            with patch("shortform_editor.pipeline.probe_media", return_value=probe), \
                 patch("shortform_editor.pipeline.analyze_audio", return_value=audio), \
                 patch("shortform_editor.pipeline.detect_moments", return_value={"candidates": [candidate]}), \
                 patch("shortform_editor.pipeline.analyze_pacing", return_value={"candidates": []}), \
                 patch("shortform_editor.pipeline.generate_captions", return_value={"captions": [
                     {"start": "00:00:03.000", "end": "00:00:04.000", "text": "Test caption"}
                 ]}), \
                 patch("shortform_editor.pipeline.analyze_visuals", return_value={"analysis": {"crop_keyframes": [
                     {"time_seconds": 2.0, "subject_evidence": "face_detection", "confidence": 0.45,
                      "crop_9_16": {"x": 10, "y": 0, "width": 200, "height": 360}, "center": {"x": 110, "y": 180}},
                     {"time_seconds": 5.0, "subject_evidence": "center_fallback", "confidence": 0.1,
                      "crop_9_16": {"x": 20, "y": 0, "width": 200, "height": 360}, "center": {"x": 120, "y": 180}}
                 ]}}):
                manifest = analyze_project(source, output, top_candidates=1, include_visuals=True)

            self.assertEqual(manifest["status"], "analysis_complete_drafts_pending_review")
            self.assertTrue((output / "audio-analysis.json").exists())
            self.assertTrue((output / "candidates.json").exists())
            self.assertTrue((output / "pacing.json").exists())
            edl_path = Path(manifest["draft_edls"][0]["edl"])
            edl = json.loads(edl_path.read_text(encoding="utf-8"))
            self.assertEqual(edl["approval"], {"status": "draft", "approved_by_user": False})
            self.assertEqual(edl["segments"][0]["layout"], "fullscreen")
            self.assertEqual(len(edl["segments"][0]["captions"]), 1)
            self.assertEqual(set(edl["segments"][0]["crop_keyframes"][0]), {"time_seconds", "crop_9_16"})
            self.assertEqual(validate_edl(edl), [])

    def test_refuses_output_directory_containing_source(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.mp4"
            source.write_bytes(b"source")
            with self.assertRaises(PipelineError):
                analyze_project(source, root)

    def test_refuses_nonempty_job_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.mp4"
            source.write_bytes(b"source")
            output = root / "job"
            output.mkdir()
            (output / "old.json").write_text("{}", encoding="utf-8")
            with self.assertRaises(PipelineError):
                analyze_project(source, output)


if __name__ == "__main__":
    unittest.main()
