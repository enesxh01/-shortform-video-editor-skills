# Implementation and Verification Status

Last updated: 2026-11-14

This file describes repository evidence, not intended behavior. A documented design is not an implementation. A test is not passed unless it has actually run.

## Feature status

| Feature | Status | Evidence / boundary |
|---|---|---|
| Media ingestion | Partial, unverified | Python CLI invokes ffprobe, checks for a video stream, records metadata and SHA-256. No safe staging, proxy mapping, full corruption diagnosis or source-specific time-base normalization yet. |
| Audio intelligence | Partial implementation, unit-tested components; real-media/model run pending | FFmpeg extraction to temporary mono 16 kHz PCM, RMS/peak windows, sustained silence candidates, optional faster-whisper transcription with word timestamps and built-in VAD; CUDA int8_float16 attempted then CPU int8 fallback, actual backend recorded. No diarization, overlap/laughter/emotion classifier or multi-mic separation. |
| Viral moment detection | Partial heuristic implementation, unit tests pending CI | Transcript-aligned candidate windows and explainable 100-point heuristic rank hook/payoff cues, speech density, lexical variety, audio energy and boundary evidence. Fixed low confidence (0.35), English-biased cues, no semantic model or virality prediction; human review required. |
| Retention and pacing | Partial implementation, unit tests pending CI | Transcript-bound utterance keeps, silence-overlap proposals, meaningful-pause preservation cues and repeated-word flags. Trims are advisory only, source-fingerprint bound and never auto-rendered. ASR sentence boundaries and pause meaning remain uncertain. |
| Visual storytelling | Partial implementation, geometry unit tests pending CI | Optional OpenCV CPU sampling, frame-difference scene-change candidates, frontal-face Haar detection, smoothed face-center keyframes and bounded 9:16 crop geometry; `analyze-project --visuals` can attach these to fullscreen EDLs and FFmpeg interpolates crop motion. Center fallback when no face; no object/action/HUD tracking, OCR, GPU vision or general semantic scene understanding. |
| EDL | Partial implementation, unit tests pending CI | JSON Schema and semantic validation now cover primary source fingerprint, segment timing, split-source specs/duration matching, caption timing and word order. No transition/motion/overlay/keyframe animation schema yet. |
| Rendering | Partial implementation; real FFmpeg integration pending | FFmpeg renderer now supports fullscreen center-crop, 20/60/20 blurred bars, top/bottom split from two fingerprint-verified secondary sources, per-segment ASS captions and optional word karaoke. H.264/AAC CPU encode at configured CFR target. No NVENC, transitions, motion keyframes or real-footage integration test yet. |
| Automatic QC and repair | Partial technical QC implementation; tests pending CI | Added post-render technical QC for stream presence, dimensions, average FPS, H.264 codec, black/freeze intervals and audio sample peak. Renderer also performs full decode check. Bounded repair command writes a separate H.264/AAC normalized export and reruns technical QC; it does not repair black/frozen content, clipping, captions or story. True-peak/loudness, A/V sync listening, caption OCR and visual/story QC remain missing. |
| Kino captions | Partial implementation, unit tests pending CI | ASR word timestamps can be grouped into caption events and rendered with ASS/libass; split captions centered, fullscreen/blurred bars bottom by default. Advanced per-word motion, custom font packaging and safe-area detection remain unimplemented. |\n| Human approval | Partial | EDL approval flag gates final rendering. No preview UI or interactive approval tool. |
| Resource management | Partial implementation, unit tests pending CI | psutil RAM and nvidia-smi VRAM preflight chooses CUDA only above per-model reserve, otherwise CPU int8; refuses inference below 2.5 GB available RAM. No queue, concurrency manager, disk reservation, live peak sampling or OOM retry. |
| Performance feedback and learning | Partial implementation, unit tests pending CI | Records explicit local approve/edited/reject labels and uses smoothed family-level preferences to adjust candidate rankings by at most +/-5 points after three observations. No model training, audience metrics or YouTube Analytics. |
| Job orchestration | Partial implementation, orchestration tests pending CI | `analyze-project` runs probe → audio/ASR → moment candidates → pacing → optional visual analysis → caption generation → one unapproved EDL draft per candidate. Preserves completed stage artifacts on Ctrl+C and writes a cancelled manifest; no resume, bounded job queue or subprocess progress streaming yet. |\n| Installers | Implemented, CI-tested | Linux and PowerShell installers stage skill folders, package referenced docs and preserve prior versions in backups. A full Linux/Windows CI run passed; the latest rerun has passed Linux and is still completing Windows. |

## Automated coverage added

- EDL schema validation and semantic unit tests.
- Cross-platform CI workflow intended to run unit tests, CLI startup and isolated installer checks.

Current verified test result: **8 EDL unit tests passed on Linux and Windows in CI run 16; Linux tests and installer smoke check also passed in CI run 21. The Windows job for run 21 is still in progress.** No real-footage render test has run.

## Known limitations and risks

- The Python package requires Python 3.10+, FFmpeg and ffprobe on PATH.
- jsonschema is the only declared Python runtime dependency.
- The current renderer is CPU libx264; it does not use the RTX 3060 for encoding or AI inference.
- The 60 fps CFR target can duplicate/drop frames; it does not create authentic 60 fps motion from 30 fps footage.
- The renderer is a simple first implementation, not an Opus/Crayo-equivalent editor.
- An FFmpeg integration test now generates synthetic video/audio and exercises all three layouts, ASS captions and technical repair on CI runners; the latest branch version of that test has not yet reported a CI result. No user-footage, GPU/VRAM/RAM or performance benchmark has been run. Caption burn-in depends on an FFmpeg build with libass.
- No root project license has been selected. Do not assume the repository is permissively licensed or redistribute it as an open-source product until the owner chooses a license and model/dependency terms are reviewed.

## Next implementation gates

1. Get CI green on Linux and Windows; fix any failures.
2. Run probe, EDL validation and render on a short user-owned sample video; verify output with ffprobe and visual/audio playback.
3. Add integration tests for VFR, non-zero stream start times, audio offsets, missing audio, corrupt input, cancellation and disk exhaustion.
4. Implement audio transcription/VAD behind an optional adapter and benchmark models on the target desktop before selecting defaults.
5. Build candidate generation and scoring from transcript + audio/visual evidence, with human-reviewed labeled examples.
6. Add visual analysis, caption generation, the two remaining layouts, QC and safe repair only after the EDL contract is expanded and tested.
