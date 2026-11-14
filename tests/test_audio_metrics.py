import tempfile
import unittest
import wave
from array import array
from pathlib import Path

from shortform_editor.audio import _window_metrics


class AudioMetricTests(unittest.TestCase):
    def test_detects_sustained_silence_and_active_audio(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "tone.wav"
            samples = array("h", [0] * 16000 + [12000] * 16000)
            with wave.open(str(path), "wb") as wav:
                wav.setnchannels(1)
                wav.setsampwidth(2)
                wav.setframerate(16000)
                wav.writeframes(samples.tobytes())

            result = _window_metrics(path, window_seconds=0.5, silence_dbfs=-38.0)
            self.assertEqual(result["duration_seconds"], 2.0)
            self.assertEqual(len(result["silence_regions"]), 1)
            self.assertAlmostEqual(result["silence_regions"][0]["start"], 0.0)
            self.assertAlmostEqual(result["silence_regions"][0]["end"], 1.0)
            self.assertGreater(result["peak_dbfs"], -10.0)
            self.assertTrue(result["windows"][0]["silence"])
            self.assertFalse(result["windows"][-1]["silence"])

    def test_reports_no_silence_for_audible_signal(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "tone.wav"
            samples = array("h", [8000] * 16000)
            with wave.open(str(path), "wb") as wav:
                wav.setnchannels(1)
                wav.setsampwidth(2)
                wav.setframerate(16000)
                wav.writeframes(samples.tobytes())
            result = _window_metrics(path)
            self.assertEqual(result["silence_regions"], [])


if __name__ == "__main__":
    unittest.main()
