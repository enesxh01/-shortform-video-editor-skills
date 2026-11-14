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

## Implemented layouts and captions

The current renderer supports:
- `fullscreen`: center-crop to the configured 9:16 frame.
- `blurred_bars_20_60_20`: full-frame blurred background with a sharp center panel occupying 60% of output height and blurred 20% top/bottom bands.
- `split_vertical`: top and bottom panels sourced from explicit `split_top` and `split_bottom` EDL source specs; both secondary source fingerprints and durations are verified. Primary source audio is retained.

Per-segment captions use ASS/libass. Word-level karaoke highlighting is available when caption word timestamps are supplied. Fullscreen captions use a bold outlined bottom style; split-layout captions are centered and use a smaller single-line style. Fonts depend on the host's font availability. A build without FFmpeg libass support cannot render captions and must fail clearly.

The current split layout requires two explicit secondary videos; it does not silently duplicate one source or guess the second panel.

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


After assembling and decode-checking the final MP4, the `render` command automatically runs the independent technical QC pass and includes its report in the JSON result. A failed QC result returns a non-zero exit code while preserving the rendered file for inspection. Warnings (for example, a source with no audio stream) remain non-fatal.


Multi-segment EDLs are concatenated in array order. Timeline gaps/overlaps and transitions are intentionally unsupported; semantic validation rejects a non-sequential `timeline_start` rather than rendering a misleading timeline.
