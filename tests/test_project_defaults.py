import json
import unittest
from pathlib import Path


class ProjectDefaultsTests(unittest.TestCase):
    def test_native_vertical_layout_policy_preserves_preferred_composition(self):
        path = Path(__file__).resolve().parents[1] / "config" / "project-defaults.json"
        config = json.loads(path.read_text(encoding="utf-8"))
        policy = config["editing"]["layout_selection_policy"]
        self.assertEqual(policy["native_9_16_source"], "blurred_bars_20_60_20")
        self.assertEqual(policy["landscape_source"], "fullscreen")
        self.assertTrue(policy["allow_editorial_override"])
        self.assertFalse(config["editing"]["background_music"])
        self.assertFalse(config["editing"]["sound_effects"])


if __name__ == "__main__":
    unittest.main()
