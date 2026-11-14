import os
import os
import tempfile
import unittest
from pathlib import Path

from shortform_editor.cli import PipelineError, _concat_demuxer_entry


class ConcatManifestTests(unittest.TestCase):
    def test_escapes_apostrophes_and_backslashes_for_ffmpeg_token_parser(self):
        with tempfile.TemporaryDirectory() as directory:
            media = Path(directory) / ("creator's cut" + chr(92) + "final.mp4")
            entry = _concat_demuxer_entry(media)
        self.assertIn("creator" + chr(92) + "'s cut", entry)
        if os.name == "nt":
            # Windows path separators are normalized to forward slashes before FFmpeg parsing.
            self.assertIn("/final.mp4", entry)
        else:
            if os.name == "nt":
            # Windows cannot represent a literal backslash in a filename; Path.as_posix() normalizes separators.
            self.assertIn("/final.mp4", entry)
        else:
            self.assertIn(chr(92) + chr(92) + "final.mp4", entry)
        self.assertTrue(entry.startswith("file '"))
        self.assertTrue(entry.endswith("'" + chr(10)))

    def test_rejects_control_characters_in_concat_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            media = Path(directory) / ("bad" + chr(10) + "name.mp4")
            with self.assertRaises(PipelineError):
                _concat_demuxer_entry(media)


if __name__ == "__main__":
    unittest.main()
