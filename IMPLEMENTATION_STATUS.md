# Implementation and Verification Status

Last updated: 2026-11-14

This file records repository evidence, not design intent. A feature is not verified merely because code or a prompt exists.

## Feature status

| Feature | Status | What exists / what remains |
|---|---|---|
| Media ingestion | Partial, unverified | FFprobe metadata and SHA-256 source fingerprint. No staged immutable source copy, proxy workflow, robust VFR/timecode mapping or media corruption test matrix. |
| Audio intelligence | Partial implementation; unit components added, CI pending | Temporary mono 16 kHz extraction, RMS/peak windows, silence candidates, optional faster-whisper ASR with word timestamps and VAD filtering. CUDA preflight with CPU int8 fallback and resource report. No diarization, overlap/laughter/emotion classification, multi-mic separation or calibrated ASR confidence. |
| Viral moment detection | Partial heuristic implementation; CI pending | Transcript-aligned candidates with explainable 100-point score (hook/payoff cues, speech density, lexical variety, audio energy and boundaries). Fixed low confidence, English-biased cues; no semantic model, labeled evaluation set or virality prediction. |
| Retention & pacing | Partial implementation; CI pending | Utterance keeps, long-silence trim suggestions, meaningful-pause preservation cues and repeated-word flags. Advisory only; no automatic trim is rendered. ASR boundaries and silence meaning remain uncertain. |
| Visual storytelling | Partial implementation; CI pending | CPU OpenCV sampling, frame-difference scene candidates, frontal-face Haar detections, smoothed 9:16 crop keyframes. Optional project orchestration attaches face detections to fullscreen EDLs; FFmpeg interpolates crop movement. No object/action/HUD/OCR tracking, semantic scene understanding or GPU vision. |
| EDL | Partial implementation; CI pending | Schema and semantic validation for source fingerprint, ordered source ranges, split source specs, captions/word timing and crop keyframes. No transition, motion, overlay, audio-mix or general keyframe contract. |
| Rendering & layouts | Partial implementation; FFmpeg integration pending | Fullscreen, blurred 20/60/20 bars, and top/bottom split using two fingerprint-verified secondary sources. Per-segment ASS captions and word karaoke. H.264/AAC CPU encode with 60 fps CFR target. No NVENC, transition system, audio mixing or user-footage verification. |
| Kino captions | Partial implementation; CI pending | ASR word grouping, ASS/libass burn-in, karaoke timing, centered single-line split styling and bottom styling for fullscreen/blurred bars. No custom font packaging, animated word motion, face/HUD-safe placement or typography preview. |
| Automatic QC & repair | Partial technical implementation; CI pending | Full decode check; QC for stream presence, dimensions, average FPS, H.264, black/freeze intervals, audio sample peak and stream start/duration metadata alignment (not perceptual sync). Separate non-destructive H.264/AAC normalization repair reruns QC. No true-peak/loudness, listening-based sync, OCR/caption QA, story/visual QC or content repair. |
| Human approval | Partial | Final renderer requires explicit EDL approval. No preview UI or in-app approval workflow. |
| Resource management | Partial implementation; CI pending | psutil RAM and nvidia-smi VRAM preflight, model-specific reserves, CUDA/CPU choice and actual backend reporting. No job queue, concurrency manager, disk reservation, live peak sampling or OOM retry. |
| Performance feedback & learning | Partial implementation; CI pending | Local approve/edited/reject labels and smoothed category preference adjustments bounded to +/-5 points after three observations. No model training, audience metrics or YouTube Analytics (intentionally excluded). |
| Job orchestration | Partial implementation; CI pending | `analyze-project` runs probe → audio/ASR → candidate ranking → pacing → optional visuals → captions → per-candidate draft EDLs. Atomic artifacts, per-stage progress/failure/cancel manifest, child-process termination on Ctrl+C and non-empty output-folder protection. No resume, bounded queue or subprocess progress streaming. |
| Installers | Implemented and CI-tested | Linux and PowerShell installers stage skills, include referenced support files and preserve prior installations with backups. Earlier Linux/Windows CI runs passed. |

## Automated tests and verification

Tests have been added for EDL validation, subprocess cancellation, audio metrics, moment ranking, pacing, crop geometry/keyframe expressions, captions, resource selection, QC, local feedback, pipeline orchestration and FFmpeg render/repair integration.

**Important:** The last confirmed Linux/Windows CI run passed before most of these new modules and integration tests were added. The latest branch revision has not yet reported a CI run. Do not treat the new tests as passing until Actions runs them. The FFmpeg integration test generates synthetic videos and exercises all three layouts, ASS captions, dynamic crop keyframes and technical repair; it is not a substitute for testing the user's real footage.

## Hardware and model policy

- Default ASR model: faster-whisper `small`; model weights download on first use and are not bundled.
- Auto device selection checks available RAM and NVIDIA VRAM. It attempts CUDA int8_float16 when the model reserve is available, otherwise CPU int8; the actual backend is recorded.
- On the Ryzen 5 5500 / RTX 3060 12 GB / 16 GB RAM desktop, `small` is the safe starting point. Do not run multiple ASR/vision models concurrently.
- Current rendering uses CPU libx264. The RTX 3060 is not used for encoding; no NVENC path or real target-machine benchmark exists.
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
6. Complete visual/caption/audio QC and safe repair. Keep YouTube Analytics excluded unless the owner explicitly changes scope.
