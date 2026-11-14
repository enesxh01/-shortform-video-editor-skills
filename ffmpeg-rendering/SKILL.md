---
name: ffmpeg-rendering
description: Render deterministic vertical short-form videos from a versioned EDL using FFmpeg with quality-focused 60 FPS export handling and verified outputs.
---

# FFmpeg Rendering

## Source of truth

Render only from a validated, versioned EDL. Probe inputs and verify stream mapping before rendering. Preserve source media and record exact FFmpeg version/command, filters, codecs, encoder settings, and source hashes.

## Default export profile

- Container: MP4.
- Video: H.264; `--encoder auto` prefers NVIDIA `h264_nvenc` when listed by FFmpeg and retries with CPU `libx264` if NVENC fails. Use `--encoder libx264` to force software encoding or `--encoder h264_nvenc` to require NVENC. NVENC defaults to preset p5 and VBR CQ 19; equal numeric quality settings are not equivalent across encoders.
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

The current split layout requires two explicit secondary videos; it does not silently duplicate one source or guess the second panel. Each segment may optionally specify `fade_in_seconds` and `fade_out_seconds` from 0 to 2 seconds; these fade video and available source audio to/from black. They default to zero. Optional `color_grade` values control brightness, contrast, saturation and gamma, while `sharpen` applies bounded FFmpeg unsharp masking. All look controls default to neutral/off and are validated before rendering; aggressive values can amplify noise or clip tones.

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


Multi-segment EDLs are concatenated in array order. Per-segment fade-to/from-black transitions are supported, but cross-dissolves, transition overlaps, motion transitions and timeline gaps/overlaps are not. Semantic validation rejects a non-sequential `timeline_start` rather than rendering a misleading timeline.


## Resumable segment rendering

For long jobs, pass `--resume` on the first `shortform-editor render` invocation and on every retry. The renderer stores a hidden per-output work directory beside the final MP4. Its state is bound to the primary source SHA-256, exact EDL SHA-256, secondary split-source fingerprints, output path, preview mode and encoder/quality settings. A cached segment is reused only if its recorded SHA-256 matches, FFprobe confirms H.264 with the expected dimensions and frame rate, and FFmpeg can fully decode it. Invalid or incomplete parts are discarded and re-encoded. Final concatenation and publication are always repeated; the final MP4 is staged and atomically published only after decode validation. A successful technical QC pass removes the work directory. Keep the work directory intact between retries. Changing the EDL, source or encoding settings intentionally rejects the old cache.
