# Shortform Video Editor Skills

A local-first OpenCode skill suite for building and operating a quality-focused short-form video clipping and editing pipeline.

## Project goals

- Analyze long-form source videos and identify self-contained, compelling short-form moments.
- Preserve context, truthful hooks, complete payoffs, and meaningful reactions.
- Produce polished vertical edits for Shorts, Reels, and TikTok.
- Use local, free/open-source tooling wherever practical.
- Prioritize creative quality, source integrity, and verifiable quality control over speed.
- Keep the workflow human-reviewable, recoverable, and resource-aware.

## Non-goals

- No YouTube Analytics, channel-performance ingestion, OAuth, views/retention dashboards, or analytics-driven optimization.
- No automatic background music.
- No automatic B-roll or sound effects unless explicitly requested for a particular edit.
- No promise or guarantee of virality.

## Visual layouts

The editing system supports exactly three primary layouts:

1. **Fullscreen** — vertical 9:16 composition with careful subject-aware reframing and editorial captions.
2. **Vertical split** — two panels stacked top/bottom, never side-by-side; one caption line centered in the divider.
3. **Blurred bars (20/60/20)** — vertical 9:16 composition with a blurred 20% top region, 60% sharp main footage, and blurred 20% bottom region, derived from relevant footage.

Layout changes must be motivated by the content, not used as arbitrary visual variety.

## Skill suite

- `shortform-video-editor` — end-to-end orchestrator
- `video-editor-architecture` — module boundaries and contracts
- `media-ingestion` — safe source inspection and staging
- `audio-intelligence` — ASR, word timing, VAD, speaker-turn evidence
- `viral-moment-detection` — full-source candidate discovery and scoring
- `visual-storytelling` — subject/action analysis and framing
- `retention-pacing` — context-safe tightening
- `editing-director` — conflict resolution and EDL authoring
- `edit-decision-list` — versioned timeline contract
- `kino-editing` — captions, motion, and the three approved layouts
- `ffmpeg-rendering` — deterministic rendering and 60 FPS policy
- `resource-management` — CPU/GPU/RAM/VRAM/disk scheduling
- `job-orchestration` — progress, cancellation, and recovery
- `quality-assurance` — technical and visual QC
- `preview-approval` — human review gates
- `video-editor-testing` — unit, integration, benchmark, and footage matrix
- `security-provenance` — safe handling and license/provenance checks
- `observability` — structured logs and diagnostics
- `project-memory` — explicit preferences only

Detailed references live in `references/`; the EDL contract is in `schemas/`; installation scripts are in `scripts/`.

## Executable runtime

The repository now includes a Python/FFmpeg runtime in `shortform_editor/` for source inspection, EDL validation, approved EDL rendering, and full-decode export QC. See [runtime documentation](shortform_editor/README.md). Core commands require Python 3.10+ and FFmpeg/ffprobe; no third-party Python package is needed.

```powershell
python .\shortform_editor\cli.py inspect "D:\media\source.mp4" --output project\source-report.json
python .\shortform_editor\cli.py validate project\edit.json --source "D:\media\source.mp4"
python .\shortform_editor\cli.py render project\edit.json --output exports\clip-01.mp4
python .\shortform_editor\cli.py qc exports\clip-01.mp4
```

The AI skill suite still performs semantic interpretation and authors the EDL; the runtime does not pretend deterministic heuristics can replace ASR, diarization, tracking, or human editorial judgment.

## Install

Windows PowerShell:

```powershell
.\\scripts\\install.ps1
```

Linux/macOS:

```bash
bash scripts/install.sh
```

Both scripts install skill folders containing `SKILL.md` into OpenCode's global skills directory by default. Pass a destination path to override it.

## Quality policy

A feature is not considered verified merely because code or documentation exists. Verification status must distinguish implemented-and-tested behavior from unverified implementation, partial work, design-only work, and blocked work. Technical QC does not replace human review of the actual exported video.

## Repository status

This repository is being built in stages. See the skill directories and project documentation for current implementation guidance and validation status.
