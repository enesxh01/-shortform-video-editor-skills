import unittest

from shortform_editor.visual import compute_crop_box


class CropGeometryTests(unittest.TestCase):
    def test_landscape_center_crop_is_9_16_and_within_source(self):
        crop = compute_crop_box(1920, 1080, 960, 540)
        self.assertAlmostEqual(crop["width"] / crop["height"], 9 / 16, places=3)
        self.assertAlmostEqual(crop["x"], (1920 - crop["width"]) / 2, places=2)
        self.assertGreaterEqual(crop["x"], 0)
        self.assertLessEqual(crop["x"] + crop["width"], 1920)

    def test_portrait_source_uses_vertical_center_crop_when_too_tall(self):
        crop = compute_crop_box(1080, 2340, 540, 1170)
        self.assertEqual(crop["width"], 1080)
        self.assertAlmostEqual(crop["height"], 1920, places=2)
        self.assertAlmostEqual(crop["y"], 210, places=2)

    def test_rejects_invalid_geometry(self):
        with self.assertRaises(ValueError):
            compute_crop_box(0, 1080, 540, 540)


if __name__ == "__main__":
    unittest.main()
