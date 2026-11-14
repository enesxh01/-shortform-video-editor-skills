# Implementation and Verification Status

Last updated: 2026-11-14

This file records repository evidence, not design intent. A feature is not verified merely because code or a prompt exists.

## Feature status

| Feature | Status | What exists / what remains |
|---|---|---|
| Media ingestion | Partial implementation; URL safety unit tests added, CI pending | Optional yt-dlp single-URL HTTP(S) ingestion with playlists disabled, empty-output-folder guard, configured size limit and FFprobe/SHA-256 validation; local-file ingestion remains available. File-stat snapshots detect ordinary source mutation during probing and later analysis/render/repair stages without repeatedly hashing large media. No authenticated/private/DRM source support, staged immutable copy, proxy workflow, robust VFR/timecode mapping or media corruption test matrix. |
| Audio intelligence | Partial implementation; unit components added, CI pending | Temporary mono 16 kHz extraction, RMS/peak windows, silence candidates, optional faster-whisper ASR with word timestamps and VAD filtering. Model-specific host RAM and NVIDIA VRAM preflight, CUDA int8_float16 selection, CPU int8 fallback, and a full CPU retry if CUDA fails during lazy inference; actual backend and resource report are recorded. No diarization, overlap/laughter/emotion classification, multi-mic separation or calibrated ASR confidence. |
| Viral moment detection | Partial heuristic implementation; CI pending | Transcript-aligned candidates with explainable 100-point score (hook/payoff cues, speech density, lexical variety, audio energy and boundaries). Fixed low confidence, English-biased cues. The OpenCode skill now instructs a separate full-transcript LLM semantic review pass with timestamp-evidence rules; this is prompt-level agent behavior, not a tested Python model integration. No labeled evaluation set or virality prediction. |
| Retention & pacing | Partial implementation; CI pending | Utterance keeps, long-silence trim suggestions, meaningful-pause preservation cues and repeated-word flags. Advisory only; candidate-specific pacing decisions and repeated-word flags are attached to EDL drafts, but no automatic trim is rendered. ASR boundaries and silence meaning remain uncertain. |
| Visual storytelling | Partial implementation; CI pending | CPU OpenCV-contrib sampling, frame-difference scene candidates, frontal-face Haar detections, optional CSRT face tracking between samples, and smoothed 9:16 crop keyframes. Optional project orchestration attaches detected/tracked face keyframes to fullscreen EDLs; FFmpeg interpolates crop movement and holds framing across detected scene cuts. No general object/action/HUD/OCR tracking, semantic scene understanding or GPU vision. |
| EDL | Partial implementation; CI pending | Schema and semantic validation for source fingerprint, ordered source ranges, split source specs, captions/word timing, crop keyframes, optional 0–2 second per-segment fade-in/fade-out and source-bounded advisory pacing metadata. The EDL schema is packaged for wheel installs and kept in sync with the repository copy. The renderer concatenates segments sequentially and rejects unsupported timeline gaps/overlaps. No cross-dissolve, motion, overlay, audio-mix or general keyframe contract. |
| Rendering & layouts | Partial implementation; FFmpeg integration pending | Fullscreen, blurred 20/60/20 bars, and top/bottom split using two fingerprint-verified secondary sources. Per-segment ASS captions and word karaoke. Optional per-segment FFmpeg color correction (brightness/contrast/saturation/gamma) and luma sharpening are schema-bounded and disabled by default. H.264/AAC with 60 fps CFR target; auto mode prefers NVENC and retries CPU libx264 if NVENC initialization/rendering fails. Optional synchronized per-clip video and audio fade-in/fade-out effects are supported. Final render automatically runs technical QC and checks duration against the EDL. No cross-dissolve, full audio mixing or user-footage verification. |
| Kino captions | Partial implementation; CI pending | ASR word grouping, ASS/libass burn-in, karaoke timing, centered single-line split styling and bottom styling for fullscreen/blurred bars. No custom font packaging, animated word motion, face/HUD-safe placement or typography preview. |
| Automatic QC & repair | Partial technical implementation; CI pending | Full decode check; QC for stream presence, dimensions, average FPS, H.264/yuv420p, AAC/48 kHz, black/freeze intervals, audio sample peak, stream start/duration metadata alignment and rendered duration versus EDL (not perceptual sync). Separate non-destructive H.264/AAC normalization repair reruns QC. No true-peak/loudness, listening-based sync, OCR/caption QA, story/visual QC or content repair. |
| Human approval | Partial implementation; unit tests added, CI pending | Fast 30 fps preview renders without changing approval state; explicit `approve-edl --confirm` re-probes and validates the exact source/EDL, stores a canonical content hash/timestamp, and final render rejects any post-approval EDL edit. No graphical preview UI. |
| Resource management | Partial implementation; CI pending | psutil RAM and nvidia-smi VRAM preflight, model-specific reserves, CUDA/CPU choice and actual backend reporting. No job queue, concurrency manager, disk reservation, live peak sampling or general multi-job OOM recovery; only the ASR CUDA-to-CPU fallback is implemented. |
| Performance feedback & learning | Partial implementation; CI pending | Local approve/edited/reject labels and smoothed category preference adjustments bounded to +/-5 points after three unique candidate observations; repeated reviews of the same source/candidate count once and the latest label wins. The project orchestrator automatically applies saved local preferences before candidate ranking. No model training, audience metrics or YouTube Analytics (intentionally excluded). |
| Job orchestration | Partial implementation; CI pending | `download-source` can optionally fetch one authorized public HTTP(S) URL; `analyze-project` runs probe → audio/ASR → candidate ranking → pacing → optional visuals → captions → per-candidate draft EDLs. Atomic artifacts, per-stage progress/failure/cancel manifest, child-process termination on Ctrl+C and non-empty output-folder protection. No resume, bounded queue or subprocess progress streaming. |
| Installers | Implemented and CI-tested | Linux and PowerShell installers stage skills, include referenced support files and preserve prior installations with backups. Earlier Linux/Windows CI runs passed. |

## Automated tests and verification

Tests have been added for optional fade schema/semantic validation and synthetic rendering across all three layouts with video/audio fades, semantic-review baseline identity/score validation, preview/approval safety and post-approval edit rejection, EDL validation including sequential timeline constraints and packaged schema parity, subprocess cancellation, source-mutation detection, audio metrics, CUDA-to-CPU fallback, moment ranking, pacing, crop geometry/keyframe expressions and optional CSRT tracker-factory compatibility, caption grouping/ASS punctuation, resource selection, QC including duration and terminal-freeze checks, deduplicated local feedback, pipeline orchestration and synthetic FFmpeg render/repair integration.

**Important:** The last confirmed Linux/Windows CI run passed before most of these new modules and integration tests were added. The branch now has a Linux/Windows, Python 3.10/3.12 CI matrix configured with optional audio/visual extras and synthetic FFmpeg integration tests. The latest branch workflow run is queued across Linux/Windows and Python 3.10/3.12; no passing result is claimed. Do not treat the new tests as passing until Actions completes successfully. The FFmpeg integration test generates synthetic videos and exercises all three layouts, ASS captions, dynamic crop keyframes, draft preview, explicit approval and technical repair; it is not a substitute for testing the user's real footage.

## Hardware and model policy

- Default ASR model: faster-whisper `small`; model weights download on first use and are not bundled.
- Auto device selection checks model-specific available RAM and NVIDIA VRAM. It attempts CUDA int8_float16 when reserves are met, then retries the complete transcription on CPU int8 if CUDA fails during inference; actual backend and fallback notes are recorded.
- On the Ryzen 5 5500 / RTX 3060 12 GB / 16 GB RAM desktop, `small` is the safe starting point. Do not run multiple ASR/vision models concurrently.
- Rendering auto mode prefers H.264 NVENC when listed by FFmpeg and falls back to CPU libx264 if the NVENC attempt fails. The user can force either encoder. The RTX 3060 path is implemented but not yet verified on the target desktop; no target-machine benchmark exists.
- 60 fps CFR output can duplicate/drop frames; it does not create native 60 fps motion from 30 fps footage.

## Licensing

- faster-whisper and CTranslate2 are MIT-licensed; OpenCV 4.5+ is Apache-2.0. The bundled OpenCV Haar cascade has a separate Intel BSD-style license notice.
- FFmpeg licensing depends on the exact build and enabled components (LGPL/GPL). The project does not bundle FFmpeg.
- Exact transitive dependency and model-weight terms must be checked before redistribution. See `THIRD_PARTY_NOTICES.md`.
- The repository has no root `LICENSE`; the owner must explicitly choose one before reuse/redistribution rights can be assumed.

## Next implementation gates

1. Get the latest Linux and Windows CI green; fix syntax, unit, installer and FFmpeg integration failures.
2. Run `analyze-project` on a short user-owned sample and inspect candidate quality, captions, crop behavior, every layout, audio sync and QC output.
3. Benchmark small-model ASR on the target desktop, recording runtime, RAM, VRAM, CUDA/cuDNN compatibility and transcript/timestamp quality.
4. Build a labeled human-reviewed candidate set; improve semantic moment scoring and non-English behavior before raising confidence.
5. Implement audio diarization/events, more general visual subject/action detection, transitions/motion, preview/approval UI, robust VFR handling and resumable jobs.
6. Complete visual/caption/audio QC and safe repair, including caption OCR/readability, safe-area and perceptual checks. Keep YouTube Analytics excluded unless the owner explicitly changes scope.
