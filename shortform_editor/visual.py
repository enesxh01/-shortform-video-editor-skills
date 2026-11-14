from __future__ import annotations

from pathlib import Path
from typing import Any

from .cli import PipelineError, file_stat_signature, probe_media


def get_face_tracker_factory(cv2: Any):
    """Return the CSRT factory when the OpenCV contrib build exposes it."""
    factory = getattr(cv2, "TrackerCSRT_create", None)
    if factory is None:
        legacy = getattr(cv2, "legacy", None)
        factory = getattr(legacy, "TrackerCSRT_create", None) if legacy is not None else None
    return factory if callable(factory) else None



def validate_normalized_roi(roi: tuple[float, float, float, float] | list[float]) -> tuple[float, float, float, float]:
    """Validate an initial tracking box expressed as normalized x, y, width, height."""
    import math
    if len(roi) != 4:
        raise ValueError("Tracking ROI must contain normalized x, y, width and height")
    x, y, width, height = (float(value) for value in roi)
    if not all(math.isfinite(value) for value in (x, y, width, height)):
        raise ValueError("Tracking ROI values must be finite")
    if x < 0 or y < 0 or width <= 0 or height <= 0 or x + width > 1 or y + height > 1:
        raise ValueError("Tracking ROI must be a positive normalized box fully inside the frame")
    return x, y, width, height


def normalized_roi_to_pixels(roi: tuple[float, float, float, float],
                             frame_width: int, frame_height: int) -> tuple[float, float, float, float]:
    if frame_width <= 0 or frame_height <= 0:
        raise ValueError("Frame dimensions must be positive")
    x, y, width, height = validate_normalized_roi(roi)
    return (x * frame_width, y * frame_height, width * frame_width, height * frame_height)


def compute_crop_box(width: int, height: int, center_x: float, center_y: float,
                     target_aspect: float = 9 / 16) -> dict[str, float]:
    if width <= 0 or height <= 0 or target_aspect <= 0:
        raise ValueError("Frame dimensions and target aspect must be positive")
    source_aspect = width / height
    if source_aspect > target_aspect:
        crop_h = float(height)
        crop_w = crop_h * target_aspect
    else:
        crop_w = float(width)
        crop_h = crop_w / target_aspect
    x = min(max(center_x - crop_w / 2, 0.0), width - crop_w)
    y = min(max(center_y - crop_h / 2, 0.0), height - crop_h)
    return {
        "x": round(x, 2),
        "y": round(y, 2),
        "width": round(crop_w, 2),
        "height": round(crop_h, 2)
    }



def build_ffmpeg_crop_filter(keyframes: list[dict[str, Any]], clip_start: float,
                             fps: str, source_width: int, source_height: int) -> str | None:
    if not keyframes:
        return None
    from fractions import Fraction

    frame_rate = float(Fraction(fps))
    if frame_rate <= 0:
        raise ValueError("Frame rate must be positive")
    points = []
    crop_width = crop_height = None
    for item in sorted(keyframes, key=lambda entry: float(entry["time_seconds"])):
        crop = item["crop_9_16"]
        width = int(crop["width"]) // 2 * 2
        height = int(crop["height"]) // 2 * 2
        if width <= 0 or height <= 0 or width > source_width or height > source_height:
            continue
        if crop_width is None:
            crop_width, crop_height = width, height
        if width != crop_width or height != crop_height:
            continue
        x = min(max(float(crop["x"]), 0.0), source_width - crop_width)
        y = min(max(float(crop["y"]), 0.0), source_height - crop_height)
        frame_number = max(0, round((float(item["time_seconds"]) - clip_start) * frame_rate))
        if points and frame_number <= points[-1][0]:
            points[-1] = (frame_number, x, y, bool(item.get("scene_cut", False)))
        else:
            points.append((frame_number, x, y, bool(item.get("scene_cut", False))))
    if not points or crop_width is None or crop_height is None:
        return None

    def expression(axis: int) -> str:
        values = [(point[0], point[axis], point[3]) for point in points]
        expr = f"{values[-1][1]:.2f}"
        for index in range(len(values) - 2, -1, -1):
            n1, v1, _ = values[index]
            n2, v2, next_is_cut = values[index + 1]
            span = max(1, n2 - n1)
            interp = f"{v1:.2f}" if next_is_cut else f"({v1:.2f}+({v2-v1:.2f})*(n-{n1})/{span})"
            expr = f"if(lt(n,{n2}),{interp},{expr})"
        first_n, first_value, _ = values[0]
        return f"if(lt(n,{first_n}),{first_value:.2f},{expr})"

    return (
        f"crop={crop_width}:{crop_height}:x='{expression(1)}':"
        f"y='{expression(2)}'"
    )


def sample_timestamps(duration: float, sample_rate: float = 1.0,
                     max_frames: int = 120) -> list[float]:
    if duration <= 0 or sample_rate <= 0 or max_frames < 2:
        raise ValueError("Duration, sample rate and frame cap must be positive")
    count = min(max_frames, max(2, int(duration * sample_rate)))
    step = duration / count
    return [round(index * step, 3) for index in range(count)]



def sample_region_timestamps(regions: list[tuple[float, float]], duration: float,
                            source_offset: float, sample_rate: float = 1.0,
                            max_frames: int = 120) -> list[tuple[float, int]]:
    if duration <= 0 or sample_rate <= 0 or max_frames < 2:
        raise ValueError("Duration, sample rate and frame cap must be positive")
    intervals = []
    for index, (source_start, source_end) in enumerate(regions):
        local_start = max(0.0, float(source_start) - source_offset)
        local_end = min(duration, float(source_end) - source_offset)
        if local_end > local_start:
            intervals.append((local_start, local_end, index))
    if not intervals:
        return []
    intervals.sort(key=lambda item: item[0])
    total = sum(end - start for start, end, _ in intervals)
    count = min(max_frames, max(len(intervals), int(total * sample_rate)))
    step = total / count
    sampled = []
    cumulative = 0.0
    interval_index = 0
    for sample_index in range(count):
        virtual_time = sample_index * step
        while interval_index < len(intervals) - 1 and virtual_time >= cumulative + (intervals[interval_index][1] - intervals[interval_index][0]):
            cumulative += intervals[interval_index][1] - intervals[interval_index][0]
            interval_index += 1
        start, end, region_id = intervals[interval_index]
        local_time = min(end - 0.001, start + virtual_time - cumulative)
        sampled.append((round(max(0.0, local_time), 3), region_id))
    return sampled


def analyze_visuals(source: Path, sample_rate: float = 1.0, max_frames: int = 120,
                    detect_faces: bool = True,
                    regions: list[tuple[float, float]] | None = None,
                    probe_report: dict[str, Any] | None = None,
                    initial_roi: tuple[float, float, float, float] | None = None) -> dict[str, Any]:
    source = source.expanduser().resolve(strict=True)
    report = probe_report if probe_report is not None else probe_media(source)
    reported_path = Path(report.get("source", {}).get("path", source)).expanduser().resolve()
    if reported_path != source:
        raise PipelineError("Supplied probe report belongs to a different source path")
    source_signature = file_stat_signature(source)
    video_stream = next((s for s in report.get("streams", []) if s.get("codec_type") == "video"), None)
    if not video_stream:
        raise PipelineError("Input contains no video stream")
    width, height = int(video_stream["width"]), int(video_stream["height"])
    duration = float(report.get("format", {}).get("duration") or 0)
    try:
        video_time_offset = float(video_stream.get("start_time") or 0.0)
    except (TypeError, ValueError):
        video_time_offset = 0.0
    if duration <= 0:
        raise PipelineError("Source duration is unavailable or invalid")
    if sample_rate < 0.2 or sample_rate > 5:
        raise PipelineError("Visual sample rate must be between 0.2 and 5 frames per second")
    if max_frames < 2 or max_frames > 600:
        raise PipelineError("Maximum sampled frames must be between 2 and 600")

    try:
        import cv2
    except ImportError as exc:
        raise PipelineError("Visual analysis requires the optional visual extra: pip install -e '.[visual]'") from exc

    detector = None
    if detect_faces:
        cascade_path = Path(cv2.data.haarcascades) / "haarcascade_frontalface_default.xml"
        detector = cv2.CascadeClassifier(str(cascade_path))
        if detector.empty():
            raise PipelineError("OpenCV face cascade could not be loaded")
    try:
        tracking_roi = validate_normalized_roi(initial_roi) if initial_roi is not None else None
    except (TypeError, ValueError) as exc:
        raise PipelineError(f"Invalid manual tracking ROI: {exc}") from exc

    capture = cv2.VideoCapture(str(source))
    if not capture.isOpened():
        raise PipelineError("OpenCV could not open the source video")
    fps = float(video_stream.get("avg_frame_rate", "0/1").split("/")[0]) / max(
        1.0, float(video_stream.get("avg_frame_rate", "0/1").split("/")[1])
    ) if "/" in str(video_stream.get("avg_frame_rate", "")) else 0.0

    samples = []
    face_tracker = None
    tracker_factory = get_face_tracker_factory(cv2) if (detect_faces or tracking_roi is not None) else None
    previous_gray = None
    previous_center = (width / 2.0, height / 2.0)
    smoothed_center = previous_center
    scene_changes = []
    timestamp_items = (
        sample_region_timestamps(regions, duration, video_time_offset, sample_rate, max_frames)
        if regions is not None else [(item, 0) for item in sample_timestamps(duration, sample_rate, max_frames)]
    )
    previous_region = None
    roi_seeded = False
    for frame_index, (timestamp, region_id) in enumerate(timestamp_items):
        if region_id != previous_region:
            previous_gray = None
            previous_center = (width / 2.0, height / 2.0)
            smoothed_center = previous_center
            face_tracker = None
            roi_seeded = False
            previous_region = region_id
        capture.set(cv2.CAP_PROP_POS_MSEC, timestamp * 1000.0)
        ok, frame = capture.read()
        if not ok:
            break
        frame_h, frame_w = frame.shape[:2]
        scale = min(1.0, 640.0 / max(frame_w, frame_h))
        if scale < 1.0:
            frame = cv2.resize(frame, (max(1, int(frame_w * scale)), max(1, int(frame_h * scale))))
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        motion_score = 0.0
        if previous_gray is not None and previous_gray.shape == gray.shape:
            diff = cv2.absdiff(previous_gray, gray)
            motion_score = float(diff.mean()) / 255.0
            if motion_score >= 0.22:
                face_tracker = None
                scene_changes.append({
                    "time_seconds": round(timestamp + video_time_offset, 3),
                    "change_score": round(motion_score, 4)
                })
        previous_gray = gray

        selected_face = None
        if detector is not None:
            faces = detector.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(24, 24))
            if len(faces):
                selected_face = max(
                    faces,
                    key=lambda box: (box[2] * box[3]) / (
                        1.0 + abs((box[0] + box[2] / 2) - previous_center[0] * frame.shape[1] / width) / max(1, frame.shape[1])
                    )
                )
        subject_bbox_normalized = None
        if tracking_roi is not None and not roi_seeded:
            roi_box = normalized_roi_to_pixels(tracking_roi, frame.shape[1], frame.shape[0])
            if callable(tracker_factory):
                try:
                    candidate_tracker = tracker_factory()
                    initialized = candidate_tracker.init(frame, roi_box)
                    face_tracker = candidate_tracker if initialized is not False else None
                except Exception:
                    face_tracker = None
            x, y, box_w, box_h = roi_box
            subject_bbox_normalized = {"x": tracking_roi[0], "y": tracking_roi[1],
                                       "width": tracking_roi[2], "height": tracking_roi[3]}
            center_x = (x + box_w / 2) / frame.shape[1] * width
            center_y = (y + box_h / 2) / frame.shape[0] * height
            confidence = 0.55 if face_tracker is not None else 0.25
            subject = "manual_roi_tracking_seed" if face_tracker is not None else "manual_roi_seed_only"
            roi_seeded = True
        elif tracking_roi is not None and face_tracker is not None:
            try:
                tracking_ok, tracked_box = face_tracker.update(frame)
            except Exception:
                tracking_ok, tracked_box = False, None
            if tracking_ok and tracked_box is not None:
                x, y, box_w, box_h = (float(value) for value in tracked_box)
                subject_bbox_normalized = {
                    "x": max(0.0, x / frame.shape[1]),
                    "y": max(0.0, y / frame.shape[0]),
                    "width": min(1.0, box_w / frame.shape[1]),
                    "height": min(1.0, box_h / frame.shape[0])
                }
                center_x = (x + box_w / 2) / frame.shape[1] * width
                center_y = (y + box_h / 2) / frame.shape[0] * height
                confidence = 0.4
                subject = "manual_roi_tracking"
            else:
                face_tracker = None
                center_x, center_y = width / 2.0, height / 2.0
                confidence = 0.05
                subject = "manual_roi_tracking_lost"
        elif tracking_roi is not None:
            center_x, center_y = width / 2.0, height / 2.0
            confidence = 0.05
            subject = "manual_roi_tracking_lost"
        elif selected_face is not None:
            tracker_box = tuple(float(value) for value in selected_face)
            if callable(tracker_factory):
                try:
                    candidate_tracker = tracker_factory()
                    initialized = candidate_tracker.init(frame, tracker_box)
                    face_tracker = candidate_tracker if initialized is not False else None
                except Exception:
                    face_tracker = None
            face_x, face_y, face_w, face_h = (float(value) for value in selected_face)
            subject_bbox_normalized = {
                "x": max(0.0, face_x / frame.shape[1]),
                "y": max(0.0, face_y / frame.shape[0]),
                "width": min(1.0, face_w / frame.shape[1]),
                "height": min(1.0, face_h / frame.shape[0])
            }
            cx_small = face_x + face_w / 2
            cy_small = face_y + face_h / 2
            center_x = cx_small / frame.shape[1] * width
            center_y = cy_small / frame.shape[0] * height
            confidence = 0.45
            subject = "face_detection"
        elif face_tracker is not None:
            try:
                tracking_ok, tracked_box = face_tracker.update(frame)
            except Exception:
                tracking_ok, tracked_box = False, None
            if tracking_ok and tracked_box is not None:
                x, y, box_w, box_h = tracked_box
                subject_bbox_normalized = {
                    "x": max(0.0, float(x) / frame.shape[1]),
                    "y": max(0.0, float(y) / frame.shape[0]),
                    "width": min(1.0, float(box_w) / frame.shape[1]),
                    "height": min(1.0, float(box_h) / frame.shape[0])
                }
                center_x = (float(x) + float(box_w) / 2) / frame.shape[1] * width
                center_y = (float(y) + float(box_h) / 2) / frame.shape[0] * height
                confidence = 0.32
                subject = "face_tracking"
            else:
                face_tracker = None
                center_x, center_y = width / 2.0, height / 2.0
                confidence = 0.1
                subject = "center_fallback"
        else:
            center_x, center_y = width / 2.0, height / 2.0
            confidence = 0.1
            subject = "center_fallback"

        alpha = 0.35
        smoothed_center = (
            alpha * center_x + (1 - alpha) * smoothed_center[0],
            alpha * center_y + (1 - alpha) * smoothed_center[1]
        )
        crop = compute_crop_box(width, height, smoothed_center[0], smoothed_center[1])
        samples.append({
            "time_seconds": round(timestamp + video_time_offset, 3),
            "region_index": region_id,
            "scene_cut": motion_score >= 0.22,
            "subject_evidence": subject,
            "subject_bbox_normalized": subject_bbox_normalized,
            "confidence": confidence,
            "center": {"x": round(smoothed_center[0], 2), "y": round(smoothed_center[1], 2)},
            "crop_9_16": crop,
            "motion_score": round(motion_score, 4)
        })
        previous_center = smoothed_center

    capture.release()
    if file_stat_signature(source) != source_signature:
        raise PipelineError("Source media changed during visual analysis; discard crop suggestions and restart from the new source version")
    return {
        "schema_version": "1.0",
        "source": {
            "path": str(source),
            "fingerprint": report["source"]["fingerprint"],
            "width": width,
            "height": height,
            "duration_seconds": duration,
            "reported_fps": fps,
            "source_time_offset_seconds": video_time_offset
        },
        "analysis": {
            "requested_sample_rate_fps": sample_rate,
            "effective_sample_rate_fps": round(len(samples) / duration, 4),
            "sampled_frames": len(samples),
            "manual_tracking_roi_normalized": list(tracking_roi) if tracking_roi is not None else None,
            "sampling_regions": regions if regions is not None else [[0.0, duration]],
            "scene_change_candidates": scene_changes,
            "crop_keyframes": samples
        },
        "limitations": [
            "This baseline detects scene-change candidates and frontal faces. An optional user-supplied normalized ROI can seed CSRT tracking for a visible object, character or gameplay subject, but it does not automatically detect arbitrary objects, actions, HUDs, hands or sports context.",
            "Haar face detections are not identity recognition and are not reliable for every angle, lighting condition or demographic.",
            "CSRT tracking can bridge missed frontal-face detections or follow a user-seeded ROI when the opencv-contrib build exposes the tracker; it may fail during fast motion, occlusion, large appearance changes or scene cuts. A lost manual ROI falls back to center framing.",
            "No face detection and no valid active tracker means a safe center crop.",
            "Sampling timestamps can drift on variable-frame-rate media; verify crop keyframes against the actual export.",
            "Face boxes can guide fullscreen caption placement away from upper/lower caption safe areas, but this is a sparse face-only heuristic, not general object/HUD collision detection.",
            "Crop plans are suggestions; no video is modified by this analysis."
        ]
    }
