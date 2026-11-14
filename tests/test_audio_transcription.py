import sys
import types
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from shortform_editor.audio import _transcribe


class FakeWord:
    def __init__(self, word, start, end):
        self.word = word
        self.start = start
        self.end = end
        self.probability = 0.99


class FakeSegment:
    text = "hello"
    start = 0.0
    end = 0.5
    avg_logprob = -0.1
    no_speech_prob = 0.01
    words = [FakeWord(" hello", 0.0, 0.5)]


class TranscriptionFallbackTests(unittest.TestCase):
    def test_cuda_lazy_inference_failure_restarts_on_cpu(self):
        attempts = []

        class FakeWhisperModel:
            def __init__(self, model_size, device, compute_type):
                self.device = device
                attempts.append((device, compute_type))

            def transcribe(self, *args, **kwargs):
                if self.device == "cuda":
                    def broken_generator():
                        raise RuntimeError("CUDA out of memory during first inference")
                        yield None
                    return broken_generator(), SimpleNamespace(language="en", language_probability=0.9)
                return iter([FakeSegment()]), SimpleNamespace(language="en", language_probability=0.9)

        fake_module = types.ModuleType("faster_whisper")
        fake_module.WhisperModel = FakeWhisperModel
        snapshot = {"ram_available_gb": 8.0, "gpu": {"available": True, "memory_free_mb": 9000}}
        with patch.dict(sys.modules, {"faster_whisper": fake_module}), \
             patch("shortform_editor.resources.resource_snapshot", return_value=snapshot), \
             patch("shortform_editor.resources.choose_inference_device", side_effect=[
                 ("cuda", "int8_float16", []),
                 ("cpu", "int8", [])
             ]):
            result = _transcribe(Path("unused.wav"), "small", "auto", None)

        self.assertEqual(attempts, [("cuda", "int8_float16"), ("cpu", "int8")])
        self.assertEqual(result["device"], "cpu")
        self.assertEqual(result["words"][0]["text"], " hello")
        self.assertTrue(any("CUDA inference failed" in note for note in result["device_selection_notes"]))

    def test_explicit_cuda_failure_does_not_silently_switch_backend(self):
        class FakeWhisperModel:
            def __init__(self, model_size, device, compute_type):
                self.device = device

            def transcribe(self, *args, **kwargs):
                raise RuntimeError("CUDA unavailable")

        fake_module = types.ModuleType("faster_whisper")
        fake_module.WhisperModel = FakeWhisperModel
        snapshot = {"ram_available_gb": 8.0, "gpu": {"available": True, "memory_free_mb": 9000}}
        with patch.dict(sys.modules, {"faster_whisper": fake_module}), \
             patch("shortform_editor.resources.resource_snapshot", return_value=snapshot), \
             patch("shortform_editor.resources.choose_inference_device", return_value=("cuda", "int8_float16", [])):
            with self.assertRaises(Exception):
                _transcribe(Path("unused.wav"), "small", "cuda", None)


if __name__ == "__main__":
    unittest.main()
