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


def analyze_visuals(source: Path, sample_rate: float = 1.0, max_frames: int = 120,
                    detect_faces: bool = True) -> dict[str, Any]:
    source = source.expanduser().resolve(strict=True)
    report = probe_media(source)
    video_stream = next((s for s in report.get("streams", []) if s.get("codec_type") == "video"), None)
    if not video_stream:
        raise PipelineError("Input contains no video stream")
    width, height = int(video_stream["width"]), int(video_stream["height"])
    duration = float(report.get("format", {}).get("duration") or 0)
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
    frame_index = 0
    timestamp = 0.0
    step = 1.0 / sample_rate
    while timestamp < duration and frame_index < max_frames:
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
                    "time_seconds": round(timestamp, 3),
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
            "time_seconds": round(timestamp, 3),
            "subject_evidence": subject,
            "confidence": confidence,
            "center": {"x": round(smoothed_center[0], 2), "y": round(smoothed_center[1], 2)},
            "crop_9_16": crop,
            "motion_score": round(motion_score, 4)
        })
        previous_center = smoothed_center
        frame_index += 1
        timestamp += step

    capture.release()
    return {
        "schema_version": "1.0",
        "source": {
            "path": str(source),
            "fingerprint": report["source"]["fingerprint"],
            "width": width,
            "height": height,
            "duration_seconds": duration,
            "reported_fps": fps
        },
        "analysis": {
            "sample_rate_fps": sample_rate,
            "sampled_frames": len(samples),
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
