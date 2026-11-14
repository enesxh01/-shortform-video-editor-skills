import unittest

from shortform_editor.resources import choose_inference_device


class ResourceSelectionTests(unittest.TestCase):
    def test_selects_cuda_when_vram_budget_is_met(self):
        snapshot = {
            "ram_available_gb": 8.0,
            "gpu": {"available": True, "memory_free_mb": 9000}
        }
        self.assertEqual(
            choose_inference_device("small", "auto", snapshot)[:2],
            ("cuda", "int8_float16")
        )

    def test_falls_back_to_cpu_when_vram_is_too_low(self):
        snapshot = {
            "ram_available_gb": 8.0,
            "gpu": {"available": True, "memory_free_mb": 1200}
        }
        device, compute, notes = choose_inference_device("small", "auto", snapshot)
        self.assertEqual((device, compute), ("cpu", "int8"))
        self.assertTrue(notes)

    def test_rejects_low_available_ram(self):
        snapshot = {"ram_available_gb": 1.0, "gpu": {"available": False}}
        with self.assertRaises(RuntimeError):
            choose_inference_device("small", "auto", snapshot)

    def test_explicit_cuda_refuses_insufficient_vram(self):
        snapshot = {
            "ram_available_gb": 8.0,
            "gpu": {"available": True, "memory_free_mb": 1500}
        }
        with self.assertRaises(RuntimeError):
            choose_inference_device("small", "cuda", snapshot)

    def test_medium_cpu_requires_larger_ram_reserve(self):
        snapshot = {
            "ram_available_gb": 4.0,
            "gpu": {"available": False}
        }
        with self.assertRaises(RuntimeError):
            choose_inference_device("medium", "auto", snapshot)


    def test_cuda_still_requires_model_specific_host_ram_reserve(self):
        snapshot = {
            "ram_available_gb": 4.0,
            "gpu": {"available": True, "memory_free_mb": 9000}
        }
        with self.assertRaises(RuntimeError):
            choose_inference_device("medium", "cuda", snapshot)

    def test_rejects_unknown_device(self):
        with self.assertRaises(ValueError):
            choose_inference_device("small", "tpu", {"ram_available_gb": 8.0, "gpu": {}})


if __name__ == "__main__":
    unittest.main()
