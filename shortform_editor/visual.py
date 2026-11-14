from __future__ import annotations

from pathlib import Path
from typing import Any

from .cli import PipelineError, probe_media


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
                    regions: list[tuple[float, float]] | None = None) -> dict[str, Any]:
    source = source.expanduser().resolve(strict=True)
    report = probe_media(source)
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

    capture = cv2.VideoCapture(str(source))
    if not capture.isOpened():
        raise PipelineError("OpenCV could not open the source video")
    fps = float(video_stream.get("avg_frame_rate", "0/1").split("/")[0]) / max(
        1.0, float(video_stream.get("avg_frame_rate", "0/1").split("/")[1])
    ) if "/" in str(video_stream.get("avg_frame_rate", "")) else 0.0

    samples = []
    previous_gray = None
    previous_center = (width / 2.0, height / 2.0)
    smoothed_center = previous_center
    scene_changes = []
    timestamp_items = (
        sample_region_timestamps(regions, duration, video_time_offset, sample_rate, max_frames)
        if regions is not None else [(item, 0) for item in sample_timestamps(duration, sample_rate, max_frames)]
    )
    previous_region = None
    for frame_index, (timestamp, region_id) in enumerate(timestamp_items):
        if region_id != previous_region:
            previous_gray = None
            previous_center = (width / 2.0, height / 2.0)
            smoothed_center = previous_center
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
        if selected_face is not None:
            cx_small = float(selected_face[0] + selected_face[2] / 2)
            cy_small = float(selected_face[1] + selected_face[3] / 2)
            center_x = cx_small / frame.shape[1] * width
            center_y = cy_small / frame.shape[0] * height
            confidence = 0.45
            subject = "face_detection"
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
            "confidence": confidence,
            "center": {"x": round(smoothed_center[0], 2), "y": round(smoothed_center[1], 2)},
            "crop_9_16": crop,
            "motion_score": round(motion_score, 4)
        })
        previous_center = smoothed_center

    capture.release()
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
            "sampling_regions": regions if regions is not None else [[0.0, duration]],
            "scene_change_candidates": scene_changes,
            "crop_keyframes": samples
        },
        "limitations": [
            "This baseline detects scene-change candidates and frontal faces only; it does not understand objects, actions, gameplay HUDs, hands or sports context.",
            "Haar face detections are not identity recognition and are not reliable for every angle, lighting condition or demographic.",
            "No face detection means a safe center crop, not inferred subject tracking.",
            "Sampling timestamps can drift on variable-frame-rate media; verify crop keyframes against the actual export.",
            "Crop plans are suggestions; no video is modified by this analysis."
        ]
    }
