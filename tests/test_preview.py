import json
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from unittest.mock import patch

from shortform_editor.cli import command_render_preview


class PreviewTests(unittest.TestCase):
    def test_preview_uses_temporary_30fps_edl_without_approving_original(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.mp4"
            edl_path = root / "draft.json"
            output = root / "preview.mp4"
            source.write_bytes(b"source")
            edl = {
                "render": {"fps_target": "60/1", "fps_mode": "cfr", "fps_conversion": "duplicate_drop"},
                "approval": {"status": "draft", "approved_by_user": False}
            }
            edl_path.write_text(json.dumps(edl), encoding="utf-8")
            captured = {}

            def fake_render(args):
                captured["args"] = args
                captured["edl"] = json.loads(Path(args.edl).read_text(encoding="utf-8"))
                return 0

            with patch("shortform_editor.cli.command_render", side_effect=fake_render):
                result = command_render_preview(Namespace(
                    source=str(source), edl=str(edl_path), output=str(output), overwrite=False
                ))

            self.assertEqual(result, 0)
            self.assertEqual(captured["edl"]["render"]["fps_target"], "30/1")
            self.assertTrue(captured["args"].preview)
            self.assertEqual(json.loads(edl_path.read_text(encoding="utf-8")), edl)


if __name__ == "__main__":
    unittest.main()
