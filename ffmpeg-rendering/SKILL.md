---
name: ffmpeg-rendering
description: Render deterministic vertical short-form videos from a versioned EDL using FFmpeg with quality-focused 60 FPS export handling and verified outputs.
---

# FFmpeg Rendering

## Source of truth

Render only from a validated, versioned EDL. Probe inputs and verify stream mapping before rendering. Preserve source media and record exact FFmpeg version/command, filters, codecs, encoder settings, and source hashes.

## Default export profile

- Container: MP4.
- Video: H.264 (libx264 baseline fallback; hardware encoders only after quality/compatibility validation).
- Frame size: 1080x1920 (9:16).
- Frame rate target: 60 fps CFR by default.
- Pixel format: yuv420p for broad compatibility.
- Audio: AAC, preserve source dynamics; no music unless explicitly requested.
- Quality: CRF-based software encoding or a measured equivalent for hardware encoding; do not claim identical quality from equal numeric settings across encoders.
- Faststart enabled where appropriate.
- Verify actual output dimensions, frame rate, frame count, duration, codec, audio streams, and decode integrity after render.

## 60 FPS policy

- 60 fps is the default output target, not permission to fabricate motion or destroy source cadence.
- Inspect source nominal/average frame rate, time base, VFR/CFR status, duplicate/drop patterns, and frame pacing.
- Native 60 fps or higher: preserve motion and convert to stable 60 fps CFR when requested.
- Native 50/30/25/24 fps: choose a documented conversion strategy. Frame duplication/blending may create cadence artifacts; optical-flow interpolation may create warping/ghosting. Do not enable interpolation blindly.
- For low-frame-rate footage, prefer clean frame-rate conversion or preserve native cadence when interpolation visibly harms quality. Clearly disclose that a 60 fps container/output does not mean true 60 fps captured motion.
- Never speed up, slow down, or alter clip duration just to reach 60 fps.
- If the source is VFR, normalize timestamps carefully and validate audio sync and frame pacing.
- Use the original source for final render; proxies are analysis/preview only.
- Confirm every output's real frame rate with ffprobe and inspect motion for judder, duplicates, or interpolation defects.

## Rendering safety

- Build FFmpeg arguments as argument arrays, never shell-concatenate untrusted paths or metadata.
- Escape filtergraph values safely.
- Use temporary output then atomic rename after successful validation.
- Handle cancellation without corrupting previous approved exports.
- Keep logs and render manifest.
- Do not delete source or project assets during cleanup.

## Verification

A successful process exit is insufficient. Probe and decode the output, verify expected duration/frame count/streams, inspect representative frames and motion, and run the QC skill.
