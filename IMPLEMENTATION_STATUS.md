# Implementation and Verification Status

Last updated: 2026-11-14

This file records repository evidence, not design intent. A feature is not verified merely because code or a prompt exists.

## Feature status

| Feature | Status | What exists / what remains |
|---|---|---|
| Media ingestion | Partial implementation; URL safety unit tests added, CI matrix passing (Ubuntu/Windows, Python 3.10/3.12) | Optional yt-dlp single-URL HTTP(S) ingestion with playlists disabled, empty-output-folder guard, configured size limit enforced by yt-dlp plus a cumulative observed-byte progress hook across separate audio/video downloads and a final on-disk size check; embedded URL credentials are rejected, destination paths are validated, and the resulting file receives FFprobe/SHA-256 validation; local-file ingestion remains available. File-stat snapshots detect ordinary source mutation during probing and later analysis/render/repair stages without repeatedly hashing large media. No authenticated/private/DRM source support, staged immutable copy, proxy workflow, full VFR/timecode normalization or media corruption test matrix. FFprobe now samples up to 240 decoded video-frame timestamps across up to eight evenly spaced windows throughout the source and reports likely CFR/VFR/insufficient-sample diagnostics; this is a bounded stratified heuristic, not exhaustive full-file VFR detection or timestamp normalization. |
| Audio intelligence | Partial implementation; unit components added, CI matrix passing (Ubuntu/Windows, Python 3.10/3.12) | Temporary mono 16 kHz extraction, RMS/peak windows, silence candidates, optional faster-whisper ASR with word timestamps and VAD filtering. Model-specific host RAM and NVIDIA VRAM preflight, CUDA int8_float16 selection, CPU int8 fallback, and a full CPU retry if CUDA fails during lazy inference; actual backend and resource report are recorded. No diarization, overlapping-speech separation, laughter/emotion classification, multi-mic separation or calibrated ASR confidence. |
| Viral moment detection | Partial heuristic implementation; CI matrix passing (Ubuntu/Windows, Python 3.10/3.12) | Transcript-aligned candidates with explainable 100-point score (hook/payoff cues, speech density, lexical variety, audio energy and boundaries). Fixed low confidence; common English, Albanian (including additional colloquial/Kosovar phrases), Spanish, French and German cue phrases are supported. Candidate records surface Whisper segment log-probability, no-speech probability, word-confidence coverage, low-confidence word count/ratio and up to eight contiguous low-confidence timestamp spans as transcript-review warnings without treating them as calibrated confidence or silently changing the moment score. The returned shortlist applies a maximum of three candidates per content family before filling remaining slots by score, reducing repetitive shortlist composition without changing candidate scores. Full multilingual/code-switched understanding remains incomplete. The OpenCode skill now instructs a separate full-transcript LLM semantic review pass with timestamp-evidence rules; this is prompt-level agent behavior, not a tested Python model integration. No labeled evaluation set or virality prediction. |
| Retention & pacing | Partial implementation; CI matrix passing (Ubuntu/Windows, Python 3.10/3.12) | Utterance keeps, long-silence trim suggestions, meaningful-pause preservation cues and repeated-word flags. Advisory only; candidate-specific pacing decisions and repeated-word flags are attached to EDL drafts, but no automatic trim is rendered. ASR boundaries and silence meaning remain uncertain. |
| Visual storytelling | Partial implementation; CI matrix passing (Ubuntu/Windows, Python 3.10/3.12) | CPU OpenCV-contrib sampling, frame-difference scene candidates, frontal-face Haar detections, optional CSRT face tracking between samples, normalized face bounding boxes, and smoothed 9:16 crop keyframes. Optional project orchestration attaches detected/tracked face keyframes to fullscreen EDLs; FFmpeg interpolates crop movement and holds framing across detected scene cuts. No automatic general object/action/HUD/OCR detection, semantic scene understanding or GPU vision. Manual ROI tracking is available in both `analyze-visuals --track-roi` and `analyze-project --visual-roi`; it requires a user-selected initial box and can lose the subject. |
| EDL | Partial implementation; CI matrix passing (Ubuntu/Windows, Python 3.10/3.12) | Schema and semantic validation for source fingerprint, ordered source ranges, split source specs, captions/word timing, crop keyframes, optional 0–2 second per-segment fade-in/fade-out and source-bounded advisory pacing metadata. The EDL schema is packaged for wheel installs and kept in sync with the repository copy. The renderer concatenates segments sequentially and rejects unsupported timeline gaps/overlaps. No cross-dissolve, motion, overlay, audio-mix or general keyframe contract. |
| Rendering & layouts | Partial implementation; FFmpeg integration tests passing (Ubuntu/Windows, Python 3.10/3.12) | Fullscreen, blurred 20/60/20 bars, and top/bottom split using two fingerprint-verified secondary sources. Per-segment ASS captions and word karaoke. Optional per-segment FFmpeg color correction (brightness/contrast/saturation/gamma) and luma sharpening are schema-bounded and disabled by default. H.264/AAC with 60 fps CFR target; auto mode prefers NVENC and retries CPU libx264 if NVENC initialization/rendering fails. Optional `render --resume` persists per-segment encodes under a config fingerprint and reuses only hash-matching, FFprobe-validated, fully decoded parts; final assembly and publication are repeated on each retry. Optional synchronized per-clip video and audio fade-in/fade-out effects are supported. Final render automatically runs technical QC and checks duration against the EDL. No cross-dissolve, full audio mixing or user-footage verification. |
| Kino captions | Partial implementation; CI matrix passing (Ubuntu/Windows, Python 3.10/3.12) | ASR word grouping, ASS/libass burn-in, karaoke timing, centered single-line split styling and bottom styling for fullscreen/blurred bars. Per-caption selection of a safe font family already installed on the rendering system and optional validated per-word `#RRGGBB` highlight colors are supported; no custom font file packaging, font discovery/fallback report, HUD-aware placement or typography preview. Optional caption-level font sizing, vertical safe-area margin and restrained pop/fade entrances are supported. Fullscreen drafts with visual face evidence now move captions to the top when detected faces overlap the lower caption safe area, or keep captions at the bottom when faces overlap the upper area; ambiguous evidence leaves placement unchanged. This is face-box heuristic placement, not general collision detection. EDL validation also enforces one-line captions for split/blurred layouts, up to three lines for fullscreen, chronological non-overlapping caption events, and layout-specific caption positioning. |
| Automatic QC & repair | Partial technical + editorial implementation; CI matrix passing (Ubuntu/Windows, Python 3.10/3.12) | Full decode check; QC for stream presence, dimensions, average FPS, H.264/yuv420p, AAC/48 kHz, black/freeze intervals, audio sample peak, stream start/duration metadata alignment and rendered duration versus EDL (not perceptual sync). Separate non-destructive H.264/AAC normalization repair validates and canonicalizes bounded rational FPS input before building FFmpeg filters, then reruns QC. EBU R128 integrated loudness, loudness range and true-peak measurements are now reported as advisory checks (general -16 to -12 LUFS guidance band and -1 dBTP ceiling; not platform guarantees). No listening-based sync, OCR/caption QA, story/visual QC or content repair. |
| Human approval | Partial implementation; unit tests added, CI matrix passing (Ubuntu/Windows, Python 3.10/3.12) | Fast 30 fps preview renders without changing approval state; explicit `approve-edl --confirm` re-probes and validates the exact source/EDL, stores a canonical content hash/timestamp, and final render rejects any post-approval EDL edit. No graphical preview UI. |
| Resource management | Partial implementation; CI matrix passing (Ubuntu/Windows, Python 3.10/3.12) | psutil RAM and nvidia-smi VRAM preflight, model-specific reserves, CUDA/CPU choice and actual backend reporting. No job queue, concurrency manager, disk reservation, live peak sampling or general multi-job OOM recovery; only the ASR CUDA-to-CPU fallback is implemented. |
| Performance feedback & learning | Partial implementation; CI matrix passing (Ubuntu/Windows, Python 3.10/3.12) | Local approve/edited/reject labels and smoothed category preference adjustments bounded to +/-5 points after three unique candidate observations; repeated reviews of the same source/candidate count once and the latest label wins. The project orchestrator automatically applies saved local preferences before candidate ranking. No model training, audience metrics or YouTube Analytics (intentionally excluded). |
| Job orchestration | Partial implementation; CI matrix passing (Ubuntu/Windows, Python 3.10/3.12) | `download-source` can optionally fetch one authorized public HTTP(S) URL; `analyze-project` runs probe → audio/ASR → candidate ranking → pacing → optional visuals → captions → per-candidate draft EDLs. Atomic artifacts, per-stage progress/failure/cancel manifest, child-process termination on Ctrl+C, non-empty output-folder protection and `--resume` support for matching jobs. Resume always re-probes/re-hashes the primary source, verifies the original option fingerprint, validates cached artifact source fingerprints and SHA-256 digests, and reuses intact audio/candidate/pacing/visual analysis checkpoints; altered or missing checkpoints are recomputed. No bounded queue or subprocess progress streaming. |
| Installers | Implemented and CI-tested | Linux and PowerShell installers stage skills, include referenced support files and preserve prior installations with backups. Earlier Linux/Windows CI runs passed. |

## Frame-timing diagnostics (implemented; heuristic)

- FFprobe samples up to 240 decoded video-frame timestamps across up to eight evenly spaced windows throughout the source when duration is known (one initial window otherwise).
- The analyzer compares adjacent timestamp intervals against a median-based tolerance and reports `likely_cfr`, `likely_vfr`, or `insufficient_samples` with sample counts and irregular-interval ratio.
- The diagnostic is carried into generated EDL source metadata when available. If the sample cannot be read, the report remains unknown rather than silently assuming CFR.
- This is not complete VFR detection: a bounded multi-window sample can miss cadence changes between sampled windows. It does not rewrite timestamps, normalize audio/video PTS, or guarantee A/V sync for arbitrary VFR media. Those remain explicit implementation and real-footage validation gates.

## Automated tests and verification

Tests have been added and passed for normalized manual ROI tracking, analyze-project CLI parsing, ROI validation and resume-fingerprint mismatch, resumable render-part hash/decode validation, resumable analysis checkpoint reuse, option/source mismatch rejection and tampered-artifact detection; sampled frame-timestamp cadence classification (regular, irregular, insufficient and malformed timestamps, plus sampling-gap exclusion and multi-window FFprobe interval construction), layout-specific caption line counts, non-overlapping caption timing, safe layout positioning and caption control-character rejection; ASR reliability warnings, missing/malformed confidence metadata and additional Albanian/Kosovar cues; EBU R128 integrated loudness, loudness range and true-peak parsing/advisories, bounded/canonical repair FPS input and malformed QC frame-rate metadata, FFmpeg concat-manifest quoting of apostrophes/backslashes and rejection of control characters in paths, cleanup of partial URL downloads after downloader validation failures and protection against a report path overwriting downloaded media, optional fade schema/semantic validation, bounded color-grade/sharpen EDL validation and synthetic rendering across all three layouts with video/audio fades plus color correction/sharpening, caption safe-area/font-size/pop-fade output validation, safe installed-font and per-word highlight schema validation, safe installed-font selection, ASS-injection rejection, per-word highlight color output and invalid-color rejection, face-aware top/bottom placement and ASS alignment, semantic-review baseline identity/score validation, preview/approval safety and post-approval edit rejection, EDL validation including sequential timeline constraints and packaged schema parity, subprocess cancellation, source-mutation detection, audio metrics, CUDA-to-CPU fallback, moment ranking, pacing, crop geometry/keyframe expressions and optional CSRT tracker-factory compatibility, caption grouping/ASS punctuation, resource selection, QC including duration and terminal-freeze checks, deduplicated local feedback, pipeline orchestration and synthetic FFmpeg render/repair integration.

**CI verification:** GitHub Actions run [#43617695392](https://github.com/enesxh01/-shortform-video-editor-skills/actions/runs/43617695392) passed all four matrix jobs: Ubuntu and Windows on Python 3.10 and 3.12. Each job passed the full unit/FFmpeg integration suite, CLI entry-point check, wheel/schema packaging, and the platform-specific isolated skill installer. Synthetic FFmpeg tests cover all three layouts, ASS captions, dynamic crop keyframes, draft preview, explicit approval and technical repair. This confirms the automated suite and clean installer paths; it does not validate the user's real footage, RTX 3060 NVENC initialization, visual quality or performance on the target PC.

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
\n\n## Disk-space preflight (implemented)\n\n- Added `check_disk_space` with an explicit safety reserve and actionable insufficient-space error.\n- Render preflight checks both output and system temporary volumes before expensive encoding.\n- Uses a conservative duration-based working-set estimate; it is not an exact output-size prediction.\n- Unit tests cover adequate and inadequate free-space cases.\n

## Editorial quality advisory (implemented; heuristic)

- Final render output now includes a `creative_quality` report based on EDL timings and caption text. It flags potentially unreadable caption speed (>20/>25 characters per second), overlong one-line captions in split/blurred layouts, flash-duration events, missing captions, and unusually short/long segments.
- These checks are non-blocking and do not change technical QC exit status. Thresholds are guidance, not universal rules; the user must watch the edit for actual readability, context and pacing.


## Resumable rendering (implemented; CI matrix passing)

- `render --resume` can be used on the initial render and subsequent retries. It persists per-segment MP4s in a hidden work directory beside the output.
- Cache identity includes the primary source fingerprint, exact EDL hash, secondary split-source fingerprints, output path, render profile, preview mode and encoder-quality options. Reusing a segment additionally requires a matching SHA-256 digest, FFprobe-confirmed H.264/dimensions/FPS and a successful full FFmpeg decode.
- Incomplete or altered parts are discarded and re-encoded. Final concat, full decode, staged publication and QC are repeated. A successful QC pass removes the work directory; failed/interrupted jobs preserve it for retry.
- The synthetic interruption/recovery integration test now passes in the completed four-platform CI matrix. Real-footage interruption behavior and target-desktop NVENC performance remain unverified. Keep the hidden work directory between retries; changing inputs or encoder settings invalidates the cache.


## VFR and audio timestamp handling (partial)

- Every rendered video segment resets its video PTS origin with `setpts=PTS-STARTPTS`, passes through an explicit CFR `fps` filter and `-fps_mode cfr` conversion. Split-layout inputs are normalized independently before stacking. When source audio exists, the audio path now uses `aresample=48000:async=1:first_pts=0` before AAC encoding, with any requested fades appended to that filter chain. This compensates for ordinary timestamp gaps/clock drift while preserving the timeline.
- This is not a guarantee for arbitrary corrupt/non-monotonic PTS, unusual edit lists, damaged timestamps or perceptual lip-sync. Keep VFR source diagnostics advisory and inspect real footage.


## Manual ROI tracking (implemented; heuristic)

- `analyze-visuals --track-roi X Y WIDTH HEIGHT` accepts a normalized 0..1 bounding box and seeds the optional OpenCV-contrib CSRT tracker. This can follow a user-selected non-face subject without a dedicated detector or model weights.
- The initial ROI is applied at the first sample of each analyzed region. Tracking loss is explicitly labeled and falls back to center framing; it never invents a subject location. Increase `--sample-rate` for faster movement, subject to the frame cap.
- This is not automatic object detection, gameplay HUD recognition, semantic action understanding or a guarantee of continuous tracking. Manual selection and human review remain required.


## Per-segment resume integration test

- The FFmpeg integration suite now simulates interruption after the first of two segment encodes, verifies the completed segment checkpoint is persisted, restarts the same render, confirms the first segment is reused and the final output is decoded/probed at 60 fps CFR.
- This exercises the recovery path on synthetic media in CI; real-footage interruption behavior and target-desktop NVENC performance remain unverified.


## Synthetic VFR normalization test

- The FFmpeg integration suite now creates a deliberately irregular-frame-cadence H.264 source with continuous AAC audio, verifies the bounded probe identifies likely VFR, renders it through the timestamp-rebase/CFR/audio-resample path, then verifies a 60/1 CFR output and video/audio stream durations aligned within 100 ms.
- This is a synthetic regression test for ordinary VFR cadence gaps; it does not establish perceptual lip-sync for arbitrary damaged timestamps or prove all real-world VFR files are safe.


## Transcript confidence localization (implemented; advisory)

- Candidate reports now expose word-confidence coverage, low-confidence word count/ratio and up to eight contiguous low-confidence timestamp spans.
- A candidate is flagged for transcript review when average ASR confidence is weak or at least three words and 25% of confidence-scored words are below the advisory 0.55 threshold.
- The heuristic does not change the candidate's ranking score; it surfaces where a human should verify spelling/names against the original audio. ASR probabilities are model estimates, not calibrated truth.


## One-command setup (implemented; CI pending)

- `scripts/setup.sh` and `scripts/setup.ps1` install the editable CLI package with audio, visual and download extras, install the OpenCode skills with timestamped backups, and run the environment doctor.
- They intentionally do not silently install system FFmpeg packages or alter PATH. If FFmpeg/ffprobe are missing, setup leaves the Python package and skills installed, prints OS-specific guidance and exits non-zero until the required FFmpeg build is available.
