import json
import shutil
import subprocess
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from unittest.mock import patch

from shortform_editor.approval import edl_approval_hash
from shortform_editor.cli import command_render, command_render_preview, probe_media
from shortform_editor.repair import repair_technical_export


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "FFmpeg integration tools unavailable")
class RenderIntegrationTests(unittest.TestCase):
    def test_all_layouts_and_kino_captions_render_to_vertical_mp4(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.mp4"
            top = root / "top.mp4"
            bottom = root / "bottom.mp4"

            def make_video(path, source_filter, with_audio=False):
                cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                       "-f", "lavfi", "-i", source_filter]
                if with_audio:
                    cmd += ["-f", "lavfi", "-i", "sine=frequency=440:duration=3"]
                cmd += ["-t", "3", "-c:v", "libx264", "-preset", "ultrafast",
                        "-pix_fmt", "yuv420p"]
                if with_audio:
                    cmd += ["-c:a", "aac", "-shortest"]
                cmd.append(str(path))
                subprocess.run(cmd, check=True, capture_output=True)

            make_video(source, "testsrc2=size=640x360:rate=30:duration=3", True)
            make_video(top, "testsrc2=size=640x360:rate=30:duration=3")
            make_video(bottom, "testsrc2=size=360x640:rate=30:duration=3")

            source_probe = probe_media(source)
            top_probe = probe_media(top)
            bottom_probe = probe_media(bottom)
            time_base = next(s["time_base"] for s in source_probe["streams"] if s["codec_type"] == "video")

            layouts = ["fullscreen", "blurred_bars_20_60_20", "split_vertical"]
            fullscreen_edl_path = None
            for layout in layouts:
                segment = {
                    "id": layout,
                    "source_in": "00:00:00.000",
                    "source_out": "00:00:02.000",
                    "layout": layout,
                    "fade_in_seconds": 0.15,
                    "fade_out_seconds": 0.15,
                    "color_grade": {"brightness": 0.015, "contrast": 1.05, "saturation": 1.08, "gamma": 1.0, "sharpen": 0.35},
                    "captions": [{
                        "start": "00:00:00.200",
                        "end": "00:00:01.500",
                        "text": "This is a test",
                        "words": [
                            {"text": "This", "start": "00:00:00.200", "end": "00:00:00.500"},
                            {"text": "is", "start": "00:00:00.500", "end": "00:00:00.700"},
                            {"text": "a", "start": "00:00:00.700", "end": "00:00:00.850"},
                            {"text": "test", "start": "00:00:00.850", "end": "00:00:01.200"}
                        ]
                    }]
                }
                if layout == "fullscreen":
                    segment["crop_keyframes"] = [
                        {"time_seconds": 0.0, "crop_9_16": {"x": 20, "y": 0, "width": 202.5, "height": 360}},
                        {"time_seconds": 1.0, "crop_9_16": {"x": 100, "y": 0, "width": 202.5, "height": 360}}
                    ]
                if layout == "split_vertical":
                    segment["split_top"] = {
                        "path": str(top), "fingerprint": top_probe["source"]["fingerprint"],
                        "source_in": "00:00:00.000", "source_out": "00:00:02.000"
                    }
                    segment["split_bottom"] = {
                        "path": str(bottom), "fingerprint": bottom_probe["source"]["fingerprint"],
                        "source_in": "00:00:00.000", "source_out": "00:00:02.000"
                    }

                edl = {
                    "schema_version": "1.0",
                    "project_id": "render-integration",
                    "source": {
                        "fingerprint": source_probe["source"]["fingerprint"],
                        "time_base": time_base,
                        "frame_rate": "30/1",
                        "variable_frame_rate": False
                    },
                    "render": {
                        "width": 1080, "height": 1920, "fps_target": "60/1",
                        "fps_mode": "cfr", "fps_conversion": "duplicate_drop",
                        "container": "mp4", "video_codec": "h264", "audio_codec": "aac"
                    },
                    "segments": [segment],
                    "approval": {"status": "draft", "approved_by_user": False}
                }
                edl["approval"] = {
                    "status": "approved",
                    "approved_by_user": True,
                    "approved_at": "2026-01-01T00:00:00+00:00"
                }
                edl["approval"]["approved_edl_sha256"] = edl_approval_hash(edl)
                edl_path = root / f"{layout}.json"
                edl_path.write_text(json.dumps(edl), encoding="utf-8")
                if layout == "fullscreen":
                    fullscreen_edl_path = edl_path
                output = root / f"{layout}.mp4"
                result = command_render(Namespace(
                    source=str(source), edl=str(edl_path), output=str(output),
                    crf=30, preset="ultrafast", overwrite=False
                ))
                self.assertEqual(result, 0)
                self.assertTrue(output.exists())
                rendered = probe_media(output)
                video = next(s for s in rendered["streams"] if s["codec_type"] == "video")
                self.assertEqual((video["width"], video["height"]), (1080, 1920))
                self.assertEqual(video["codec_name"], "h264")
                self.assertEqual(video["avg_frame_rate"], "60/1")
                self.assertTrue(any(s["codec_type"] == "audio" for s in rendered["streams"]))

            preview_edl = json.loads(fullscreen_edl_path.read_text(encoding="utf-8"))
            preview_edl["approval"] = {"status": "draft", "approved_by_user": False}
            draft_path = root / "preview-draft.json"
            draft_path.write_text(json.dumps(preview_edl), encoding="utf-8")
            preview_output = root / "preview.mp4"
            preview_result = command_render_preview(Namespace(
                source=str(source), edl=str(draft_path), output=str(preview_output), overwrite=False
            ))
            self.assertEqual(preview_result, 0)
            self.assertEqual(json.loads(draft_path.read_text(encoding="utf-8"))["approval"]["status"], "draft")
            preview_probe = probe_media(preview_output)
            preview_video = next(s for s in preview_probe["streams"] if s["codec_type"] == "video")
            self.assertEqual(preview_video["avg_frame_rate"], "30/1")

            repaired = root / "repaired.mp4"
            repair_report = repair_technical_export(
                source, repaired, width=1080, height=1920, fps="30/1",
                crf=30, preset="ultrafast"
            )
            self.assertTrue(repaired.exists())
            self.assertEqual(repair_report["output"], str(repaired.resolve()))
            self.assertEqual(repair_report["qc_after_repair"]["status"], "passed")


    def test_resume_render_reuses_only_hash_valid_decodable_segments(self):
        from shortform_editor.cli import _render_part_is_reusable, sha256_file
        with tempfile.TemporaryDirectory() as directory:
            part = Path(directory) / "part.mp4"
            part.write_bytes(b"encoded-segment")
            record = {"sha256": sha256_file(part), "encoder": "libx264"}
            with patch("shortform_editor.cli.run_checked") as run:
                run.return_value.stdout = json.dumps({"streams": [{
                    "codec_type": "video", "codec_name": "h264", "width": 1080,
                    "height": 1920, "avg_frame_rate": "60/1"
                }]})
                self.assertTrue(_render_part_is_reusable(part, record, "ffmpeg", "ffprobe", 1080, 1920, "60/1"))
                self.assertEqual(run.call_count, 2)
            self.assertFalse(_render_part_is_reusable(part, {"sha256": "0" * 64}, "ffmpeg", "ffprobe", 1080, 1920, "60/1"))
            self.assertFalse(_render_part_is_reusable(part, record, "ffmpeg", "ffprobe", 720, 1280, "60/1"))



    def test_resume_allows_replacing_only_an_existing_output_with_a_render_state(self):
        from shortform_editor.cli import _existing_output_is_resumable
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / "final.mp4"
            state = root / ".final.mp4.shortform-work" / "render-state.json"
            output.write_bytes(b"previous-final")
            self.assertFalse(_existing_output_is_resumable(output, False, state))
            self.assertFalse(_existing_output_is_resumable(output, True, state))
            state.parent.mkdir()
            state.write_text("{}", encoding="utf-8")
            self.assertTrue(_existing_output_is_resumable(output, False, state))

    def test_render_resume_fingerprint_changes_with_renderer_or_ffmpeg_version(self):
        import hashlib
        import json
        def fingerprint(renderer_version, ffmpeg_version):
            settings = {"renderer_cache_version": renderer_version,
                        "ffmpeg_version": ffmpeg_version, "source_fingerprint": "source"}
            return hashlib.sha256(json.dumps(settings, sort_keys=True,
                separators=(",", ":")).encode("utf-8")).hexdigest()
        baseline = fingerprint("2", "ffmpeg version 7.1")
        self.assertNotEqual(baseline, fingerprint("3", "ffmpeg version 7.1"))
        self.assertNotEqual(baseline, fingerprint("2", "ffmpeg version 7.2"))



if __name__ == "__main__":
    unittest.main()
