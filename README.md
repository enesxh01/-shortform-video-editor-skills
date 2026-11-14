# Shortform Video Editor Skills

A local-first OpenCode skill suite with an early executable Python/FFmpeg foundation for short-form video analysis and editing.

> **Important:** The current implementation is on branch `implementation/foundation-and-install-fixes`. Until that branch is merged into `main`, clone that branch explicitly rather than the default branch.

```bash
git clone --branch implementation/foundation-and-install-fixes https://github.com/enesxh01/-shortform-video-editor-skills.git
```



For a non-face subject such as a gameplay character, car or ball, you can manually seed a normalized tracking box (x, y, width, height from 0 to 1):

```bash
shortform-editor analyze-visuals gameplay.mp4 -o visual-analysis.json --no-face-detection --track-roi 0.32 0.18 0.24 0.42 --sample-rate 3 --max-frames 240
```

This prefers CSRT when the installed OpenCV-contrib build exposes it and falls back to built-in KLT optical flow otherwise. It is user-seeded tracking, not automatic object detection; if tracking is lost, the report marks the fallback. Review the resulting crop keyframes.

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



For a full analysis job with the same human-selected subject box applied to each candidate window, use:

```bash
shortform-editor analyze-project input.mp4 -o job-output/ --visuals --visual-roi 0.32 0.18 0.24 0.42
```

The ROI is included in the analysis-job settings fingerprint, so a resume must use the same coordinates.

## Layout selection defaults

For native 9:16 source footage, the editing skills prefer the blurred 20/60/20 composition: blurred full-frame background, sharp slightly enlarged center 60%, and no black bars. Landscape footage normally uses a 9:16 fullscreen crop when it preserves the important content. Split vertical is reserved for an explicit request or supplied top/bottom panel sources.

## Visual layouts

The renderer has initial code for exactly three layouts:
- `fullscreen`: 9:16 center crop with optional face-guided crop keyframes.
- `split_vertical`: top/bottom panels from two explicit secondary sources, with centered captions.
- `blurred_bars_20_60_20`: blurred top 20%, sharp center 60%, blurred bottom 20%.

All three layouts and ASS captions have synthetic FFmpeg integration coverage. The latest full GitHub Actions matrix passed on Ubuntu and Windows with Python 3.10 and 3.12 ([run #43622463389](https://github.com/enesxh01/-shortform-video-editor-skills/actions/runs/43622463389)). The run passed 187 tests, synthetic FFmpeg integration, all four isolated skill installers and one-command setup checks. Split mode requires two secondary video files; provide them with `--split-top-source` and `--split-bottom-source`, plus optional source offsets.

## Skill suite

- `shortform-video-editor` — end-to-end orchestrator
- `video-editor-architecture` — module boundaries and contracts
- `media-ingestion` — source inspection and staging policy
- `audio-intelligence` — FFmpeg extraction, energy/silence and generic transient/rise evidence, optional faster-whisper ASR
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
- `preview-approval` — 30 fps preview rendering and explicit fingerprint-checked approval (partial; no graphical preview UI)
- `video-editor-testing` — unit, integration, benchmark and footage matrix
- `security-provenance` — safe handling and license/provenance checks
- `observability` — diagnostics and logging policy
- `performance-feedback` — local human editorial feedback, no audience analytics
- `project-memory` — explicit preferences only

## Executable workflow

Requirements: Python 3.10+, FFmpeg and ffprobe on PATH.

**One-command setup from the cloned repository root:**

Windows PowerShell:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\setup.ps1
```

Linux/macOS:

```bash
bash scripts/setup.sh
```

These setup scripts install the editable CLI package plus the audio, visual and download extras, install the OpenCode skills with backups, and run `shortform-editor doctor`, which checks the FFmpeg H.264/AAC encoders and required render/QC filters. They do not silently install system packages or change your OS PATH. If FFmpeg is missing, install an FFmpeg build that includes ffprobe, libx264 (or NVENC) and the subtitles filter, then rerun setup. The scripts print an OS-appropriate installation hint where possible.

For a skills-only update after the CLI is already installed, use `bash scripts/install.sh` or `powershell -ExecutionPolicy Bypass -File scripts/install.ps1`.

To ingest a single URL into a new, empty folder (playlists are disabled):

```bash
shortform-editor download-source 'https://example.com/video' --output-dir downloaded-source/ --max-filesize-mb 2048 --report download-report.json
```

The downloader rejects embedded URL credentials and enforces its configured size cap using yt-dlp's file-size limit, cumulative observed transfer progress across separate audio/video streams, and a final on-disk check. Its destination must be a new or empty directory. Download only media you own or are authorized to use; this is not a DRM, private-content, or access-control bypass.

Then run:

```bash
shortform-editor analyze-project input.mp4 -o job-output/ --model small --device auto --visuals
# If interrupted, resume the same job with identical options:
shortform-editor analyze-project input.mp4 -o job-output/ --model small --device auto --visuals --resume
# For top/bottom split: add --layout split_vertical --split-top-source top.mp4 --split-bottom-source bottom.mp4
```

This orchestrates:
1. Source probe and SHA-256 fingerprint, plus an advisory 240-frame timestamp-cadence sample across up to eight evenly spaced windows (`likely_cfr`, `likely_vfr`, or unknown). This is not full-file VFR proof. The renderer rebases each segment's video PTS, converts to CFR, and resamples audio timestamps to compensate for ordinary clock drift; arbitrary damaged timestamps still need human sync review.
2. Audio extraction, optional faster-whisper ASR and word timestamps.
3. Transcript-led moment candidate ranking.
4. Review-only retention/pacing analysis.
5. Optional visual scene sampling and frontal-face crop keyframes.
6. Kino caption generation.
7. One unapproved EDL draft per candidate.

The pipeline does **not** approve or render automatically. Once you explicitly approve an EDL, the render command exports it and automatically runs technical QC. `render --resume` keeps verified segment encodes in a hidden work directory beside the output and reuses only parts whose source/EDL/encoder settings, SHA-256 digest, H.264 dimensions/FPS and full decode check still match; pass `--resume` on the first run and every retry. Review the candidate boundaries, captions, crop plans and EDL. Render a 30 fps preview first; only after you explicitly approve that exact edit should you run `approve-edl --confirm`, followed by the final render.

Useful follow-up commands:

```bash
shortform-editor validate-edl job-output/edl/moment-....json --probe job-output/probe.json
shortform-editor validate-semantic-review review.json --probe job-output/probe.json --candidates job-output/candidates.json
shortform-editor render-preview input.mp4 draft-edl.json preview.mp4
# Only after explicit human approval of this exact edit:
shortform-editor approve-edl draft-edl.json --source input.mp4 --confirm
shortform-editor render input.mp4 approved-edl.json output.mp4

# Make long renders resumable (include --resume on the first run and retries):
shortform-editor render input.mp4 approved-edl.json output.mp4 --resume
shortform-editor qc output.mp4 -o qc-report.json
shortform-editor repair input.mp4 repaired.mp4
shortform-editor record-feedback job-output/candidates.json --candidate-id moment-... --decision approve
shortform-editor apply-feedback job-output/candidates.json -o ranked.json
```

### Implementation limits

- The Python moment detector is an English-biased heuristic and deliberately reports low confidence. The OpenCode skill adds a separate LLM semantic review pass over the full timestamped transcript, but that prompt-driven review has not been benchmarked or evaluated on a labeled set; neither stage predicts virality.
- Audio has ASR and energy/silence analysis, but no diarization, overlap, laughter/emotion classification or multi-mic separation.
- Visual analysis detects scene changes and frontal faces, then uses optional OpenCV-contrib CSRT to track a detected face between sampled frames when possible. A manually selected non-face ROI uses CSRT when available and built-in KLT optical flow otherwise. It still does not automatically understand arbitrary objects, actions, sports or gameplay HUDs.
- Pacing trims are advisory and never automatically remove content.
- Captions use ASS/libass and word karaoke; advanced motion presets, custom font packaging and safe-area preview are not implemented. Optional per-clip fade-in/fade-out transitions now support synchronized video and source-audio fades (0–2 seconds each). These fade to/from black; cross-dissolves and motion transitions remain unimplemented.
- QC checks stream metadata, codec, dimensions, FPS, black/frozen intervals, sample peak and stream timing metadata. A separate non-blocking `creative_quality` advisory flags potentially fast or overlong captions, flash-duration events, missing captions and unusually short/long segments. Neither report replaces human review or listening-based lip-sync analysis.
- Technical repair writes a new normalized H.264/AAC file; it cannot repair missing/black/frozen content or clipping.
- Rendering now prefers NVIDIA H.264 NVENC automatically when the FFmpeg build exposes it, with a CPU libx264 fallback if NVENC fails to initialize. `--encoder libx264` forces CPU; `--encoder h264_nvenc` requires NVENC. The RTX 3060 can accelerate encoding, but no target-machine benchmark has been completed.
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

Both installers stage and copy the OpenCode skill folders and their referenced support files before replacing existing installations, preserving prior skill directories in timestamped backups. They do not install the Python package or FFmpeg; complete both setup steps above before asking OpenCode to run the CLI.

## Quality policy

A feature is not verified merely because code or documentation exists. Verification must distinguish implemented-and-tested behavior from unverified implementation, partial work, design-only work and blocked work. Technical QC never replaces human review of the exported video.
