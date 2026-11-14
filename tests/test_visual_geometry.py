import unittest

from types import SimpleNamespace

from shortform_editor.visual import build_ffmpeg_crop_filter, compute_crop_box, get_face_tracker_factory, sample_region_timestamps, sample_timestamps


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

    def test_face_tracker_factory_supports_modern_opencv_api(self):
        factory = lambda: "tracker"
        cv2 = SimpleNamespace(TrackerCSRT_create=factory)
        self.assertIs(get_face_tracker_factory(cv2), factory)

    def test_face_tracker_factory_supports_legacy_opencv_api(self):
        factory = lambda: "tracker"
        cv2 = SimpleNamespace(legacy=SimpleNamespace(TrackerCSRT_create=factory))
        self.assertIs(get_face_tracker_factory(cv2), factory)

    def test_face_tracker_factory_is_optional(self):
        self.assertIsNone(get_face_tracker_factory(SimpleNamespace()))

    def test_rejects_invalid_geometry(self):
        with self.assertRaises(ValueError):
            compute_crop_box(0, 1080, 540, 540)

    def test_samples_across_entire_long_source_with_frame_cap(self):
        times = sample_timestamps(3600.0, sample_rate=1.0, max_frames=120)
        self.assertEqual(len(times), 120)
        self.assertEqual(times[0], 0.0)
        self.assertGreater(times[-1], 3500.0)

    def test_samples_candidate_regions_in_source_order(self):
        sampled = sample_region_timestamps([(100.0, 110.0), (0.0, 10.0)], 120.0, 0.0, 1.0, 30)
        self.assertEqual(len(sampled), 20)
        self.assertEqual(sampled[0][1], 1)
        self.assertEqual(sampled[-1][1], 0)
        self.assertLess(sampled[0][0], sampled[-1][0])

    def test_scene_cut_holds_old_crop_then_jumps_to_new_scene(self):
        keyframes = [
            {"time_seconds": 0.0, "scene_cut": False, "crop_9_16": {"x": 20, "y": 0, "width": 202.5, "height": 360}},
            {"time_seconds": 1.0, "scene_cut": True, "crop_9_16": {"x": 100, "y": 0, "width": 202.5, "height": 360}}
        ]
        expression = build_ffmpeg_crop_filter(keyframes, 0.0, "60/1", 640, 360)
        self.assertIn("if(lt(n,60),20.00,100.00)", expression)

    def test_builds_interpolated_crop_expression(self):
        keyframes = [
            {"time_seconds": 0.0, "crop_9_16": {"x": 20, "y": 0, "width": 202.5, "height": 360}},
            {"time_seconds": 1.0, "crop_9_16": {"x": 100, "y": 0, "width": 202.5, "height": 360}}
        ]
        expression = build_ffmpeg_crop_filter(keyframes, 0.0, "60/1", 640, 360)
        self.assertIn("crop=202:360", expression)
        self.assertIn("n-0", expression)
        self.assertIn("lt(n,60)", expression)


    def test_validates_normalized_manual_tracking_roi(self):
        from shortform_editor.visual import validate_normalized_roi, normalized_roi_to_pixels
        roi = validate_normalized_roi((0.2, 0.1, 0.3, 0.4))
        self.assertEqual(roi, (0.2, 0.1, 0.3, 0.4))
        self.assertEqual(normalized_roi_to_pixels(roi, 640, 360), (128.0, 36.0, 192.0, 144.0))

    def test_rejects_invalid_manual_tracking_roi(self):
        from shortform_editor.visual import validate_normalized_roi
        for roi in ((-0.1, 0.1, 0.2, 0.2), (0.8, 0.8, 0.3, 0.3),
                    (0.1, 0.1, 0, 0.2), (0.1, float("nan"), 0.2, 0.2),
                    (0.1, 0.2, 0.3)):
            with self.subTest(roi=roi):
                with self.assertRaises(ValueError):
                    validate_normalized_roi(roi)



    def test_analyze_visuals_cli_accepts_normalized_manual_roi(self):
        from shortform_editor.cli import build_parser
        args = build_parser().parse_args([
            "analyze-visuals", "gameplay.mp4", "--no-face-detection",
            "--track-roi", "0.32", "0.18", "0.24", "0.42",
            "--sample-rate", "3"
        ])
        self.assertEqual(args.track_roi, [0.32, 0.18, 0.24, 0.42])
        self.assertTrue(args.no_face_detection)
        self.assertEqual(args.sample_rate, 3.0)



if __name__ == "__main__":
    unittest.main()
