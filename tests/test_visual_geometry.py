import unittest

from types import SimpleNamespace
from unittest.mock import patch

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



    def test_manual_roi_seeds_and_updates_generic_csrt_tracker(self):
        import sys
        import tempfile
        from pathlib import Path
        from shortform_editor.visual import analyze_visuals

        class Frame:
            shape = (180, 320, 3)

        class Gray:
            shape = (180, 320)

        class Capture:
            def __init__(self):
                self.frames = [Frame(), Frame()]
            def isOpened(self):
                return True
            def set(self, *_args):
                return True
            def read(self):
                return (True, self.frames.pop(0)) if self.frames else (False, None)
            def release(self):
                pass

        class Tracker:
            def __init__(self):
                self.initial_box = None
            def init(self, _frame, box):
                self.initial_box = box
                return True
            def update(self, _frame):
                return True, (150.0, 60.0, 20.0, 20.0)

        tracker = Tracker()
        capture = Capture()
        cv2_stub = SimpleNamespace(
            VideoCapture=lambda _path: capture,
            CAP_PROP_POS_MSEC=0,
            COLOR_BGR2GRAY=1,
            cvtColor=lambda _frame, _code: Gray(),
            absdiff=lambda _left, _right: SimpleNamespace(mean=lambda: 0.0),
            TrackerCSRT_create=lambda: tracker
        )
        probe = {
            "source": {"path": "", "fingerprint": "sha256:" + "a" * 64},
            "streams": [{
                "codec_type": "video", "width": 320, "height": 180,
                "avg_frame_rate": "30/1", "start_time": "0.0"
            }],
            "format": {"duration": "2.0"}
        }
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.mp4"
            source.write_bytes(b"synthetic")
            probe["source"]["path"] = str(source)
            with patch.dict(sys.modules, {"cv2": cv2_stub}):
                report = analyze_visuals(
                    source, sample_rate=1.0, max_frames=2, detect_faces=False,
                    probe_report=probe, initial_roi=(0.25, 0.25, 0.25, 0.25)
                )
        samples = report["analysis"]["crop_keyframes"]
        self.assertEqual(tracker.initial_box, (80.0, 45.0, 80.0, 45.0))
        self.assertEqual(samples[0]["subject_evidence"], "manual_roi_tracking_seed")
        self.assertEqual(samples[1]["subject_evidence"], "manual_roi_tracking")
        self.assertEqual(samples[1]["subject_bbox_normalized"]["x"], 150.0 / 320.0)
        self.assertEqual(report["analysis"]["manual_tracking_roi_normalized"], [0.25, 0.25, 0.25, 0.25])



    def test_manual_roi_optical_flow_tracks_translation_without_contrib_tracker(self):
        import cv2
        import numpy as np
        from shortform_editor.visual import _advance_optical_flow, _optical_flow_features

        rng = np.random.default_rng(7)
        first = np.zeros((140, 180), dtype=np.uint8)
        first[30:90, 40:100] = rng.integers(0, 256, size=(60, 60), dtype=np.uint8)
        transform = np.float32([[1, 0, 7], [0, 1, 4]])
        second = cv2.warpAffine(first, transform, (180, 140))
        initial_box = (40.0, 30.0, 60.0, 60.0)
        points = _optical_flow_features(cv2, first, initial_box)
        self.assertIsNotNone(points)
        self.assertGreaterEqual(len(points), 4)
        tracked = _advance_optical_flow(cv2, first, second, points, initial_box)
        self.assertIsNotNone(tracked)
        updated_box, next_points, inliers = tracked
        self.assertGreaterEqual(inliers, 4)
        self.assertGreaterEqual(len(next_points), 4)
        self.assertAlmostEqual(updated_box[0], 47.0, delta=2.0)
        self.assertAlmostEqual(updated_box[1], 34.0, delta=2.0)

    def test_analyze_project_cli_accepts_manual_visual_roi(self):
        from shortform_editor.cli import build_parser
        args = build_parser().parse_args([
            "analyze-project", "input.mp4", "-o", "job",
            "--visuals", "--visual-roi", "0.2", "0.1", "0.3", "0.4"
        ])
        self.assertTrue(args.visuals)
        self.assertEqual(args.visual_roi, [0.2, 0.1, 0.3, 0.4])



if __name__ == "__main__":
    unittest.main()
