---
name: visual-storytelling
description: Analyze subjects, actions, scenes, framing, and visual continuity to keep important content visible in short-form edits.
---

# Visual Storytelling

Use computer vision to support editorial decisions, not to replace understanding.

## Evidence sources

- Scene detection for structural changes.
- Object/person detection and tracking for subject location and continuity.
- OCR for meaningful on-screen text, gameplay HUD, labels, and existing subtitles.
- Motion/optical-flow evidence for camera movement and action.
- Selective segmentation/masking only when a specific edit requires it.
- Audio diarization, transcript context, mouth movement, and visual evidence may jointly support active-speaker estimates. Never infer identity from voice alone.

Check current licenses and terms before selecting model families or distributing dependencies. In particular, review licenses for detector frameworks and segmentation models rather than assuming they are permissive.

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
