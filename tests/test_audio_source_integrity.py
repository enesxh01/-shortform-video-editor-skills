import tempfile
import unittest
import wave
from pathlib import Path
from unittest.mock import patch

from shortform_editor.audio import analyze_audio
from shortform_editor.cli import PipelineError


class AudioSourceIntegrityTests(unittest.TestCase):
    def test_rejects_source_changed_during_audio_analysis(self):
        first = {
            "source": {"fingerprint": "sha256:" + "a" * 64},
            "streams": [{"codec_type": "audio", "index": 1, "start_time": "0.0"}]
        }
        second = {
            "source": {"fingerprint": "sha256:" + "b" * 64},
            "streams": [{"codec_type": "audio", "index": 1, "start_time": "0.0"}]
        }

        def write_wav(source, destination, stream_index):
            with wave.open(str(destination), "wb") as wav:
                wav.setnchannels(1)
                wav.setsampwidth(2)
                wav.setframerate(16000)
                wav.writeframes(b"\x00\x00" * 16000)

        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.mp4"
            source.write_bytes(b"placeholder")
            with patch("shortform_editor.audio.probe_media", side_effect=[first, second]), \
                 patch("shortform_editor.audio._extract_mono_wav", side_effect=write_wav):
                with self.assertRaisesRegex(PipelineError, "changed during audio analysis"):
                    analyze_audio(source, transcribe=False)


if __name__ == "__main__":
    unittest.main()
