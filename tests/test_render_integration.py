import json
import shutil
import subprocess
import tempfile
import unittest
from fractions import Fraction
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "shortform_editor" / "cli.py"
import importlib.util
spec = importlib.util.spec_from_file_location("shortform_cli_integration", MODULE_PATH)
cli = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cli)

@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "FFmpeg is not installed")
class RenderIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.source = self.root / "source.mp4"
        subprocess.run([
            "ffmpeg","-hide_banner","-loglevel","error","-y",
            "-f","lavfi","-i","testsrc2=size=320x180:rate=30:duration=2",
            "-f","lavfi","-i","sine=frequency=440:sample_rate=48000:duration=2",
            "-shortest","-c:v","libx264","-pix_fmt","yuv420p","-c:a","aac",str(self.source)
        ],check=True)
        self.info=cli.probe(self.source)

    def tearDown(self):
        self.tmp.cleanup()

    def edl(self, layout):
        seg={"id":"one","source_in":"00:00:00","source_out":"00:00:01.2","layout":layout,
             "captions":[{"start":"00:00:00.2","end":"00:00:00.9","text":"Integration test","position":"bottom"}]}
        if layout=="split_vertical":
            top=self.root/"top.mp4"; bottom=self.root/"bottom.mp4"
            shutil.copy2(self.source,top); shutil.copy2(self.source,bottom)
            seg["split_top"]={"path":str(top),"fingerprint":cli.sha256(top),"source_in":"00:00:00","source_out":"00:00:01.2"}
            seg["split_bottom"]={"path":str(bottom),"fingerprint":cli.sha256(bottom),"source_in":"00:00:00","source_out":"00:00:01.2"}
        return {"schema_version":"1.0","project_id":"integration",
          "source":{"path":str(self.source),"fingerprint":self.info["fingerprint"],"time_base":self.info["video"]["time_base"] or "1/30",
                    "frame_rate":self.info["video"]["frame_rate"],"variable_frame_rate":False},
          "render":{"width":360,"height":640,"fps_target":"60/1","fps_mode":"cfr","fps_conversion":"duplicate_drop",
                    "container":"mp4","video_codec":"h264","audio_codec":"aac"},
          "segments":[seg],"approval":{"status":"approved","approved_by_user":True}}

    def test_all_supported_layouts_render_and_decode(self):
        for layout in ("fullscreen","blurred_bars_20_60_20","split_vertical"):
            with self.subTest(layout=layout):
                edl_path=self.root/f"{layout}.json"
                edl_path.write_text(json.dumps(self.edl(layout)),encoding="utf-8")
                output=self.root/f"{layout}.mp4"
                manifest=cli.render(edl_path,output)
                self.assertTrue(output.is_file())
                self.assertEqual(manifest["status"],"technical_qc_passed_human_visual_review_required")
                self.assertEqual(manifest["output_probe"]["video"]["width"],360)
                self.assertEqual(manifest["output_probe"]["video"]["height"],640)
                self.assertEqual(Fraction(manifest["output_probe"]["video"]["frame_rate"]),Fraction(60,1))
                self.assertTrue(output.with_suffix(".mp4.manifest.json").is_file())

if __name__ == "__main__":
    unittest.main()
