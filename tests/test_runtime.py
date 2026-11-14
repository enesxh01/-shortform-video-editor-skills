import importlib.util
import unittest
from pathlib import Path

MODULE = Path(__file__).resolve().parents[1] / "shortform_editor" / "cli.py"
spec = importlib.util.spec_from_file_location("shortform_cli", MODULE)
cli = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cli)

class TimestampTests(unittest.TestCase):
    def test_timestamp_formats(self):
        self.assertAlmostEqual(cli.seconds("01:02.500"), 62.5)
        self.assertAlmostEqual(cli.seconds("1:02:03.25"), 3723.25)
        self.assertAlmostEqual(cli.seconds(12.75), 12.75)

    def test_invalid_timestamp(self):
        with self.assertRaises(cli.EditorError):
            cli.seconds("00:75")

class EDLTests(unittest.TestCase):
    def valid_edl(self):
        return {
            "schema_version":"1.0","project_id":"test",
            "source":{"path":"source.mp4","fingerprint":"sha256:"+"a"*64,"time_base":"1/90000"},
            "render":{"width":1080,"height":1920,"fps_target":"60/1","fps_mode":"cfr","container":"mp4"},
            "segments":[{"id":"clip-1","source_in":"00:00:01","source_out":"00:00:08","layout":"fullscreen"}],
            "approval":{"status":"needs_review","approved_by_user":False}
        }

    def test_valid_draft(self):
        self.assertEqual(cli.validate(self.valid_edl()), [])

    def test_reversed_segment_rejected(self):
        edl=self.valid_edl()
        edl["segments"][0]["source_out"]="00:00:00"
        self.assertTrue(any("source_out must be after" in x for x in cli.validate(edl)))

    def test_invalid_layout_rejected(self):
        edl=self.valid_edl()
        edl["segments"][0]["layout"]="side_by_side"
        self.assertTrue(any("unsupported layout" in x for x in cli.validate(edl)))

    def test_split_requires_both_sources(self):
        edl=self.valid_edl()
        edl["segments"][0]["layout"]="split_vertical"
        self.assertTrue(any("split_top" in x for x in cli.validate(edl)))
        self.assertTrue(any("split_bottom" in x for x in cli.validate(edl)))

    def test_unapproved_draft_is_not_marked_approved(self):
        edl=self.valid_edl()
        edl["approval"]={"status":"approved","approved_by_user":False}
        self.assertTrue(any("approved_by_user=true" in x for x in cli.validate(edl)))

    def test_source_fingerprint_mismatch(self):
        edl=self.valid_edl()
        info={"duration":20,"fingerprint":"sha256:"+"b"*64}
        self.assertTrue(any("fingerprint mismatch" in x for x in cli.validate(edl,info)))

if __name__ == "__main__":
    unittest.main()
