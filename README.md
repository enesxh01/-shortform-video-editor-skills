# Shortform Video Editor Skills

A local-first OpenCode skill suite and early executable foundation for building a quality-focused short-form video clipping and editing pipeline.

## Project goals

- Analyze long-form source videos and identify self-contained, compelling short-form moments.
- Preserve context, truthful hooks, complete payoffs, and meaningful reactions.
- Produce polished vertical edits for Shorts, Reels, and TikTok.
- Use local, free/open-source tooling wherever practical.
- Prioritize creative quality, source integrity, and verifiable quality control over speed.
- Keep the workflow human-reviewable, recoverable, and resource-aware.

## Non-goals

- No YouTube Analytics, channel-performance ingestion, OAuth, views/retention dashboards, or analytics-driven optimization. Candidate ranking can learn only from explicit local human editorial feedback.
- No automatic background music.
- No automatic B-roll or sound effects unless explicitly requested for a particular edit.
- No promise or guarantee of virality.

## Visual layouts

The design supports exactly three primary layouts: fullscreen, top/bottom vertical split, and blurred bars with a 20/60/20 top/main/bottom composition. **The current renderer implements all three layouts.** Split-screen requires explicit top and bottom secondary source files; blurred bars use a sharp 60% center panel; captions are ASS-based with optional word karaoke.

## Skill suite

- `shortform-video-editor` — end-to-end orchestrator
- `video-editor-architecture` — module boundaries and contracts
- `media-ingestion` — safe source inspection and staging
- `audio-intelligence` — FFmpeg audio extraction, energy/silence evidence, optional faster-whisper ASR with word timestamps (partial implementation)
- `viral-moment-detection` — transcript-aligned candidate discovery and explainable heuristic ranking (baseline implementation; low confidence)
- `visual-storytelling` — sampled scene-change evidence and conservative face-guided 9:16 crop plans (partial implementation)
- `retention-pacing` — transcript-bound pacing proposals and review-only silence trimming (baseline implementation)
- `editing-director` — conflict resolution and EDL authoring
- `edit-decision-list` — versioned timeline contract
- `kino-editing` — word-timed caption grouping, ASS/Kino rendering and layout-specific placement (partial implementation; advanced motion presets remain design-only)
- `ffmpeg-rendering` — deterministic rendering and 60 FPS policy
- `resource-management` — RAM/VRAM preflight and ASR backend selection (partial implementation; job scheduling remains design-only)
- `job-orchestration` — one-command analysis pipeline, staged artifacts and cancellation manifest (partial implementation; resume/queue not yet built)
- `quality-assurance` — technical codec/dimension/FPS/black/freeze/audio-peak QC (partial; visual/story/caption review still human)
- `preview-approval` — human review gates (design-only)
- `video-editor-testing` — unit, integration, benchmark, and footage matrix
- `security-provenance` — safe handling and license/provenance checks
- `observability` — structured logs and diagnostics
- `performance-feedback` — local human approval/rejection feedback and bounded category preference learning (no analytics)\n- `project-memory` — explicit preferences only

## Executable foundation (early MVP)

Requirements: Python 3.10+, FFmpeg/ffprobe on PATH.

```bash
python -m pip install -e .
shortform-editor analyze-project input.mp4 -o job-output/ --model small --device auto
shortform-editor probe input.mp4 -o probe.json
shortform-editor analyze-audio input.mp4 -o audio-analysis.json
shortform-editor find-moments audio-analysis.json -o candidates.json
shortform-editor analyze-pacing audio-analysis.json candidates.json -o pacing.json
# Optional extras: python -m pip install -e '.[audio,visual]' (or install only what you need)
shortform-editor analyze-visuals input.mp4 -o visual-analysis.json
shortform-editor generate-captions audio-analysis.json candidates.json -o captions.json --layout fullscreen
# Optional ASR: python -m pip install -e '.[audio]'
shortform-editor validate-edl edit.json --probe probe.json
shortform-editor render input.mp4 edit.json output.mp4
shortform-editor qc output.mp4 -o qc-report.json
shortform-editor repair input.mp4 repaired.mp4
shortform-editor record-feedback candidates.json --candidate-id moment-... --decision approve
shortform-editor apply-feedback candidates.json -o ranked.json
python -m unittest discover -s tests -v
```

The `analyze-project` command orchestrates source probing, audio/ASR, candidate ranking, pacing, optional visual analysis, caption generation and per-candidate draft EDLs. Drafts are never auto-approved or rendered. The current CLI provides source probing and SHA-256 fingerprinting, EDL schema/semantic validation, an approved-EDL FFmpeg renderer, and an initial audio analysis command. Audio analysis extracts mono 16 kHz WAV in a temporary directory, measures half-second RMS/peak windows and sustained silence candidates, and optionally runs faster-whisper with word timestamps and VAD. Default ASR model is `small`; CUDA is attempted with int8_float16 and falls back to CPU int8. Install ASR with `python -m pip install -e '.[audio]'`; model weights download on first use. The renderer supports fullscreen center-crop, blurred 20/60/20 bars, and top/bottom split using two fingerprint-verified secondary sources; per-segment ASS captions support word-level karaoke when timings are supplied; `generate-captions` groups ASR word timestamps into caption events for manual insertion into the selected EDL segment. Moment discovery currently uses a transparent English-biased cue heuristic, speech density, lexical variety, audio energy and boundary evidence; it assigns low confidence and requires human review. It is not a trained semantic model or a virality predictor. The pipeline does not yet perform diarization, speaker attribution, laughter/emotion classification, general subject tracking, content repair, or complete visual/story/caption QC. A separate technical repair command can normalize codec, dimensions and FPS without overwriting the source. Technical QC checks codecs, dimensions, frame rate, black/frozen intervals and sample peak. The 60 fps output policy is not a claim of native 60 fps motion from lower-frame-rate footage.

## Install OpenCode skills

Windows PowerShell:

```powershell
.\\scripts\\install.ps1
```

Linux/macOS:

```bash
bash scripts/install.sh
```

Both installers stage skills before replacing existing installations, preserve prior skill directories in timestamped backups, and package each skill's referenced support files inside that skill directory.

## Quality policy

A feature is not considered verified merely because code or documentation exists. Verification status must distinguish implemented-and-tested behavior from unverified implementation, partial work, design-only work, and blocked work. Technical QC does not replace human review of the actual exported video.
