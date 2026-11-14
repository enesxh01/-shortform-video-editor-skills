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
                 patch("shortform_editor.pipeline.analyze_pacing", return_value={"candidates": [{
                     "candidate_id": candidate["candidate_id"],
                     "decisions": [{
                         "decision": "keep", "source_in": "00:00:02.000",
                         "source_out": "00:00:18.000", "rationale": "Keep utterance",
                         "confidence": 0.9, "context_risk": "low"
                     }],
                     "repeated_word_flags": ["the"],
                     "note": "Advisory only"
                 }]}), \
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
            self.assertEqual(edl["segments"][0]["pacing_review"]["repeated_word_flags"], ["the"])
            self.assertEqual(set(edl["segments"][0]["crop_keyframes"][0]), {"time_seconds", "crop_9_16", "scene_cut"})
            self.assertEqual(validate_edl(edl), [])


    def test_split_project_creates_fingerprinted_top_and_bottom_specs(self):
        primary_fp = "sha256:" + ("1" * 64)
        top_fp = "sha256:" + ("2" * 64)
        bottom_fp = "sha256:" + ("3" * 64)
        candidate = {
            "candidate_id": "moment-split",
            "source_fingerprint": primary_fp,
            "source_in_seconds": 2.0,
            "source_out_seconds": 18.0,
            "family": "story_or_commentary",
            "transcript_excerpt": "Split test",
            "confidence": 0.35
        }
        def fake_probe(path):
            path = Path(path)
            fingerprint = primary_fp if path.name == "source.mp4" else (top_fp if path.name == "top.mp4" else bottom_fp)
            return {
                "source": {"path": str(path), "sha256": fingerprint.split(":")[1], "fingerprint": fingerprint},
                "format": {"duration": "30.0"},
                "streams": [{"codec_type": "video", "time_base": "1/90000", "avg_frame_rate": "30/1"}]
            }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, top, bottom = root / "source.mp4", root / "top.mp4", root / "bottom.mp4"
            for path in (source, top, bottom):
                path.write_bytes(b"placeholder")
            output = root / "split-job"
            audio = {"source": {"fingerprint": primary_fp}, "analysis": {"transcription": {"status": "completed"}}}
            with patch("shortform_editor.pipeline.probe_media", side_effect=fake_probe), \
                 patch("shortform_editor.pipeline.analyze_audio", return_value=audio), \
                 patch("shortform_editor.pipeline.detect_moments", return_value={"candidates": [candidate]}), \
                 patch("shortform_editor.pipeline.analyze_pacing", return_value={"candidates": []}), \
                 patch("shortform_editor.pipeline.generate_captions", return_value={"captions": []}):
                manifest = analyze_project(
                    source, output, top_candidates=1, layout="split_vertical",
                    split_top_source=top, split_bottom_source=bottom,
                    split_top_in="00:00:02.000", split_bottom_in="00:00:00.000"
                )
            edl = json.loads(Path(manifest["draft_edls"][0]["edl"]).read_text(encoding="utf-8"))
            segment = edl["segments"][0]
            self.assertEqual(segment["split_top"]["fingerprint"], top_fp)
            self.assertEqual(segment["split_top"]["source_in"], "00:00:02.000")
            self.assertEqual(segment["split_top"]["source_out"], "00:00:18.000")
            self.assertEqual(segment["split_bottom"]["fingerprint"], bottom_fp)
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


    def test_pipeline_applies_saved_feedback_before_ranking_candidates(self):
        fingerprint = "sha256:" + ("8" * 64)
        candidates = [
            {"candidate_id": "story", "source_fingerprint": fingerprint, "source_in_seconds": 2.0,
             "source_out_seconds": 18.0, "family": "story_or_commentary", "transcript_excerpt": "Story",
             "confidence": 0.35, "score": 54},
            {"candidate_id": "comedy", "source_fingerprint": fingerprint, "source_in_seconds": 20.0,
             "source_out_seconds": 36.0, "family": "comedy_or_reaction", "transcript_excerpt": "Comedy",
             "confidence": 0.35, "score": 50}
        ]
        records = (
            [{"candidate_id": f"comedy-{i}", "source_fingerprint": "past", "family": "comedy_or_reaction", "decision": "approve"} for i in range(3)] +
            [{"candidate_id": f"story-{i}", "source_fingerprint": "past", "family": "story_or_commentary", "decision": "reject"} for i in range(3)]
        )
        probe = {
            "source": {"path": "source.mp4", "sha256": "8" * 64, "fingerprint": fingerprint},
            "format": {"duration": "40.0"},
            "streams": [{"codec_type": "video", "time_base": "1/90000", "avg_frame_rate": "30/1"}]
        }
        audio = {"source": {"fingerprint": fingerprint}, "analysis": {"transcription": {"status": "completed"}}}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.mp4"
            source.write_bytes(b"placeholder")
            with patch("shortform_editor.pipeline.probe_media", return_value=probe), \
                 patch("shortform_editor.pipeline.analyze_audio", return_value=audio), \
                 patch("shortform_editor.pipeline.detect_moments", return_value={"source_fingerprint": fingerprint, "candidates": candidates}), \
                 patch("shortform_editor.pipeline.load_feedback", return_value=records), \
                 patch("shortform_editor.pipeline.analyze_pacing", return_value={"candidates": []}), \
                 patch("shortform_editor.pipeline.generate_captions", return_value={"captions": []}):
                manifest = analyze_project(source, root / "job", top_candidates=2)
            ranked = json.loads((root / "job" / "candidates.json").read_text(encoding="utf-8"))
            self.assertEqual(ranked["candidates"][0]["candidate_id"], "comedy")
            self.assertEqual(manifest["feedback_learning"]["records_used"], 6)


if __name__ == "__main__":
    unittest.main()
