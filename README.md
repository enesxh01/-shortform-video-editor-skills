# Shortform Video Editor Skills

A local-first OpenCode skill suite with an early executable Python/FFmpeg foundation for short-form video analysis and editing.

## Goals

- Find self-contained, compelling moments in long-form video.
- Preserve context, truthful hooks, complete payoffs and meaningful reactions.
- Produce polished vertical edits for Shorts, Reels and TikTok.
- Prefer local/free tooling, source integrity, human review and measurable quality checks.

## Scope boundaries

- No YouTube Analytics, channel-performance ingestion, OAuth, views/retention dashboards or analytics-driven optimization. Ranking can learn only from explicit local human editorial feedback.
- No automatic background music.
- No automatic B-roll or sound effects unless requested for a specific edit.
- No virality guarantees.

## Visual layouts

The renderer has initial code for exactly three layouts:
- `fullscreen`: 9:16 center crop with optional face-guided crop keyframes.
- `split_vertical`: top/bottom panels from two explicit secondary sources, with centered captions.
- `blurred_bars_20_60_20`: blurred top 20%, sharp center 60%, blurred bottom 20%.

All three layouts and ASS captions have synthetic FFmpeg integration coverage configured, but the latest branch's CI result is still pending. Split mode requires fingerprinted `split_top` and `split_bottom` source specs in the EDL.

## Skill suite

- `shortform-video-editor` — end-to-end orchestrator
- `video-editor-architecture` — module boundaries and contracts
- `media-ingestion` — source inspection and staging policy
- `audio-intelligence` — FFmpeg extraction, energy/silence evidence, optional faster-whisper ASR
- `viral-moment-detection` — transcript-led candidate ranking (low-confidence heuristic)
- `retention-pacing` — review-only silence trimming and repetition flags
- `visual-storytelling` — scene-change evidence and frontal-face crop suggestions
- `editing-director` — conflict resolution and EDL authoring
- `edit-decision-list` — versioned timeline contract
- `kino-editing` — word-timed ASS captions and layout placement
- `ffmpeg-rendering` — three layouts and 60 FPS policy
- `resource-management` — RAM/VRAM preflight for ASR
- `job-orchestration` — analysis pipeline and draft EDL generation
- `quality-assurance` — technical QC and bounded technical repair
- `preview-approval` — human review gates (design-only)
- `video-editor-testing` — unit, integration, benchmark and footage matrix
- `security-provenance` — safe handling and license/provenance checks
- `observability` — diagnostics and logging policy
- `performance-feedback` — local human editorial feedback, no audience analytics
- `project-memory` — explicit preferences only

## Executable workflow

Requirements: Python 3.10+, FFmpeg and ffprobe on PATH.

Install the mandatory CLI dependencies and optional analysis packages:

```bash
python -m pip install -e ".[audio,visual]"
```

Then run:

```bash
shortform-editor analyze-project input.mp4 -o job-output/ --model small --device auto --visuals
```

This orchestrates:
1. Source probe and SHA-256 fingerprint.
2. Audio extraction, optional faster-whisper ASR and word timestamps.
3. Transcript-led moment candidate ranking.
4. Review-only retention/pacing analysis.
5. Optional visual scene sampling and frontal-face crop keyframes.
6. Kino caption generation.
7. One unapproved EDL draft per candidate.

The pipeline does **not** approve or render automatically. Review the candidate boundaries, captions, crop plans and EDL. Only after explicit human approval should the EDL be set to `approval.status="approved"` and `approval.approved_by_user=true`.

Useful follow-up commands:

```bash
shortform-editor validate-edl job-output/edl/moment-....json --probe job-output/probe.json
shortform-editor render input.mp4 approved-edl.json output.mp4
shortform-editor qc output.mp4 -o qc-report.json
shortform-editor repair input.mp4 repaired.mp4
shortform-editor record-feedback job-output/candidates.json --candidate-id moment-... --decision approve
shortform-editor apply-feedback job-output/candidates.json -o ranked.json
```

### Implementation limits

- Moment detection is an English-biased heuristic, not semantic AI or a virality predictor; it deliberately reports low confidence.
- Audio has ASR and energy/silence analysis, but no diarization, overlap, laughter/emotion classification or multi-mic separation.
- Visual analysis detects scene-change candidates and frontal faces only; it does not understand arbitrary objects, actions, sports or gameplay HUDs.
- Pacing trims are advisory and never automatically remove content.
- Captions use ASS/libass and word karaoke; advanced motion presets, custom font packaging and safe-area preview are not implemented.
- QC checks stream metadata, codec, dimensions, FPS, black/frozen intervals, sample peak and stream timing metadata. It is not full creative QC or listening-based lip-sync analysis.
- Technical repair writes a new normalized H.264/AAC file; it cannot repair missing/black/frozen content or clipping.
- Rendering currently uses CPU libx264; the RTX 3060 is used only when faster-whisper successfully selects CUDA. No target-machine benchmark or NVENC path has been completed.
- 60 fps CFR output may duplicate/drop frames; it does not create native 60 fps motion from lower-frame-rate footage.

See `IMPLEMENTATION_STATUS.md` for feature-by-feature evidence and `THIRD_PARTY_NOTICES.md` for licensing. The repository has no root `LICENSE`; the owner must choose one before redistribution rights can be assumed.

## Install OpenCode skills

Windows PowerShell:

```powershell
.\scripts\install.ps1
```

Linux/macOS:

```bash
bash scripts/install.sh
```

Both installers stage skills before replacing existing installations, preserve prior skill directories in timestamped backups and package each skill's referenced support files.

## Quality policy

A feature is not verified merely because code or documentation exists. Verification must distinguish implemented-and-tested behavior from unverified implementation, partial work, design-only work and blocked work. Technical QC never replaces human review of the exported video.
