---
name: visual-storytelling
description: Analyze subjects, actions, scenes, framing, and visual continuity to keep important content visible in short-form edits.
---

# Visual Storytelling

Use computer vision to support editorial decisions, not to replace understanding.

## Executable baseline

Install the optional visual dependency with `python -m pip install -e ".[visual]"`, then run `shortform-editor analyze-visuals SOURCE -o visual-analysis.json`. The current module samples frames (the orchestrator prioritizes selected candidate windows and respects a frame budget), estimates scene-change candidates from frame differences, detects frontal faces with OpenCV's bundled Haar cascade, and optionally uses the OpenCV-contrib CSRT tracker to bridge missed detections between samples. It smooths the tracked face center and emits conservative 9:16 crop keyframes. It uses CPU OpenCV; no CUDA model is loaded.

This is limited face tracking, not general subject tracking or scene understanding. It cannot detect gameplay HUDs, sports objects, hands, arbitrary products or actions. CSRT may lose a face during occlusion, fast motion, large scale changes or scene cuts; failed tracking falls back to center framing. When a face is not detected it falls back to center framing. When `analyze-project --visuals` is enabled, detected face keyframes are attached to fullscreen draft EDLs and interpolated by FFmpeg during render. Keyframes are still low-confidence and must be reviewed; no face detection means center crop. Blurred-bars and split layouts do not yet consume these crop keyframes. Treat all crop plans as review-required.

## Evidence sources

- Scene detection for structural changes.
- Object/person detection and tracking for subject location and continuity.
- OCR for meaningful on-screen text, gameplay HUD, labels, and existing subtitles.
- Motion/optical-flow evidence for camera movement and action.
- Selective segmentation/masking only when a specific edit requires it.
- Audio diarization, transcript context, mouth movement, and visual evidence may jointly support active-speaker estimates. Never infer identity from voice alone.

OpenCV's software package is Apache-2.0 licensed. Review the exact bundled Haar cascade asset and third-party dependency notices before redistribution; optional model weights must be checked individually. Do not add AGPL-licensed detector frameworks or model weights without explicit project-owner approval.

## Framing

- Track primary and secondary subjects, faces/bodies, hands, important objects, and action regions.
- Respect edges, headroom, gaze direction, gameplay HUD, subtitles, and caption-safe areas.
- Prefer stable, smooth, predictive crops over jittery frame-by-frame chasing.
- Widen or fall back to a safe composition when tracking confidence drops.
- Never crop away the action or a reaction necessary to understand the moment.
- Do not use identity recognition. Track anonymous visual subjects within the clip only.

## Layout selection

Choose only among:
- `fullscreen`
- `split_vertical` (top/bottom stacked only)
- `blurred_bars_20_60_20` (20% blurred top / 60% sharp center / 20% blurred bottom)

Choose based on source geometry and storytelling. Do not switch layouts for arbitrary variety.

## Testing

Test single speaker, two similar-looking speakers, subject leaving/re-entering frame, moving camera, gameplay HUD, sports action, hands/objects, edge composition, low-resolution footage, occlusion, and low-confidence tracking. Record crop stability, subject visibility, tracking confidence, and failure cases.


## Manual subject tracking

When automatic face detection misses a non-face subject (for example a game character, car, ball or product), a human may seed a normalized region-of-interest box for CSRT tracking:

```bash
shortform-editor analyze-visuals gameplay.mp4 -o visual-analysis.json --no-face-detection --track-roi 0.32 0.18 0.24 0.42 --sample-rate 3 --max-frames 240
```

The four values are normalized `x y width height` fractions of the frame (0 to 1). The seed is applied at the first sampled frame of each analyzed region; CSRT follows the visible texture between samples. If tracking is unavailable or lost, the report marks the fallback and uses center framing. This is user-initialized tracking, not automatic object detection or semantic gameplay understanding. Review all crop keyframes.
