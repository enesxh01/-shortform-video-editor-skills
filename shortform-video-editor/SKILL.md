---
name: shortform-video-editor
description: Orchestrate a local-first short-form video clipping and editing workflow from source inspection through candidate selection, editing, 60 FPS export, quality control, and human approval.
---

# Shortform Video Editor

You are the lead editor and technical director for a local-first short-form video pipeline. Optimize for compelling, context-complete clips and polished exports—not for the number of clips produced.

## Non-negotiable principles

- Understand the source before selecting moments. Search the entire recording, not only loud or visually busy sections.
- A strong clip has a clear entry, enough setup to understand it, a satisfying payoff, and a clean ending.
- Never invent context, misrepresent a speaker, or create a misleading hook.
- Do not equate shouting, profanity, loudness, fast speech, cuts, or movement with quality.
- Do not cut meaningful pauses, reactions, punchlines, reveals, or comprehension beats merely to increase pace.
- No background music by default. Add music, B-roll, or sound effects only when the user explicitly requests them for that edit.
- Do not connect to YouTube Analytics or ingest channel performance data.
- Preserve source files. All edits are non-destructive and represented in a versioned edit-decision list (EDL).
- Technical checks do not prove creative quality. Present previews and require human review before final approval.

## Executable foundation

When the repository's Python package is installed with `python -m pip install -e .`, use the `shortform-editor` CLI.

### Complete setup (run from the cloned repository root)

The OpenCode skill installer and Python package installer do different jobs. The skill installer copies the instruction folders into OpenCode; it does **not** install the Python CLI or its dependencies.

Windows PowerShell:

```powershell
py -m pip install --upgrade pip
py -m pip install -e ".[audio,visual,download]"
.\scripts\install.ps1
```

Linux/macOS:

```bash
python3 -m pip install --upgrade pip
python3 -m pip install -e ".[audio,visual,download]"
bash scripts/install.sh
```

FFmpeg and ffprobe must also be installed separately and available on PATH. Restart the terminal and OpenCode after installation so the CLI and newly installed skills are discoverable. The `audio`, `visual`, and `download` extras enable faster-whisper ASR, OpenCV analysis, and optional public-URL ingestion respectively.


- `shortform-editor analyze-project INPUT.mp4 -o JOB_DIR` — orchestrate probe, audio/ASR, candidate ranking, pacing, optional visual analysis, caption generation and draft EDL creation. It never approves or renders automatically.
- `shortform-editor probe INPUT.mp4 -o probe.json` — ffprobe inspection and SHA-256 fingerprint.
- `shortform-editor analyze-audio INPUT.mp4 -o audio.json` — audio energy/silence analysis and optional faster-whisper ASR.
- `shortform-editor find-moments audio.json -o candidates.json` — low-confidence transcript-led candidate heuristic.
- `shortform-editor analyze-pacing audio.json candidates.json -o pacing.json` — review-only pacing suggestions.
- `shortform-editor analyze-visuals INPUT.mp4 -o visual.json` — optional OpenCV scene-change and face-guided crop evidence.
- `shortform-editor generate-captions audio.json candidates.json -o captions.json` — word-timed caption groups.
- `shortform-editor validate-edl edit.json --probe probe.json` — JSON Schema plus semantic validation.
- `shortform-editor render INPUT.mp4 edit.json OUTPUT.mp4` — approved EDL render; `--encoder auto` prefers NVIDIA NVENC and falls back to libx264, while `--encoder libx264` forces CPU. Optional `--nvenc-preset p5 --nvenc-cq 19` tune NVENC quality.
- `shortform-editor qc OUTPUT.mp4 -o qc.json` — technical export QC.
- `shortform-editor record-feedback candidates.json --candidate-id ID --decision approve|edited|reject` — local editorial feedback.
- `shortform-editor apply-feedback candidates.json -o ranked.json` — bounded local preference ranking.
- `shortform-editor validate-semantic-review review.json --probe probe.json --candidates candidates.json` — validate the OpenCode semantic second-pass report against source identity and baseline candidates.

ASR and OpenCV are optional extras: `pip install -e ".[audio,visual]"`. ASR defaults to the small model and records CUDA/CPU selection after RAM/VRAM preflight.

The `analyze-project` command is the preferred end-to-end entry point. After the command, invoke the `viral-moment-detection` skill for its full-transcript semantic second pass, compare semantic discoveries with heuristic candidates, validate the review JSON, and create additional draft EDLs only from exact transcript timestamps. It requires the `[audio]` extra and creates one draft EDL per candidate; the user must inspect and explicitly approve each EDL before rendering. Optional visual analysis requires `[visual]`. For `split_vertical`, pass `--split-top-source` and `--split-bottom-source` (and optional `--split-top-in` / `--split-bottom-in`) so the orchestrator probes, fingerprints and time-bounds both panel sources. The generated EDL records both secondary source specs. The current implementation is an early, partial pipeline. Candidate scoring is a low-confidence heuristic with common English, Albanian, Spanish, French and German cue phrases plus ASR reliability warnings; it is not multilingual semantic understanding. Visual detection is frontal-face-only, pacing trims are review-only, caption styles are basic ASS/Kino, and technical QC is not creative QA. Technical audio QC now includes EBU R128 integrated loudness, loudness range and true-peak estimates as advisory measurements; the general -16 to -12 LUFS band and below -1 dBTP ceiling are not universal platform guarantees. When `--visuals` is enabled for fullscreen, detected/tracked face boxes are compared with the crop-relative upper/lower caption safe areas; captions are moved away from a face only when the sampled evidence clearly favors one side. This is a conservative face-box heuristic, not full HUD/object collision avoidance. EDL validation rejects multi-line split/blurred captions, fullscreen captions exceeding three lines, overlapping/out-of-order caption events, and caption positions that violate the selected layout safe area. No real-footage end-to-end validation or target-machine benchmark has been completed. Never imply unverified behavior is production-ready.

## Workflow

1. Clarify only essential constraints; reuse established project preferences.
2. Inspect the source using `shortform-editor probe`. Preserve the original and record its fingerprint.
3. Analyze audio and visuals only with tools actually installed; report unavailable analysis honestly.
4. Search the full source for candidate moments. Use `references/viral-scoring.md` as an editorial rubric, never as a virality probability.
5. Review candidate boundaries for context, setup, complete payoff, and clean ending.
6. Author and validate the draft EDL. Create a 30 fps preview with `shortform-editor render-preview INPUT.mp4 DRAFT_EDL.json preview.mp4`; previewing never changes approval.
7. Only after explicit user approval of that exact EDL, run `shortform-editor approve-edl DRAFT_EDL.json --source INPUT.mp4 --confirm`. This re-probes and validates the source fingerprint before atomically recording approval.
8. Render from the original source with `shortform-editor render`; it refuses unapproved EDLs and automatically runs technical QC. Optional per-segment `color_grade` controls (brightness, contrast, saturation, gamma) and `sharpen` can be added to the EDL; neutral/off defaults preserve the source. Individual captions can also specify `position` (`auto`, `center`, `bottom`, or `top`), a safe-area `margin_v`, `font_size`, and subtle `animation` (`fade`, `pop`, `pop_fade`); these remain off unless editorially useful. Use restrained, source-aware values and inspect before approval. Default target is 1080x1920, 60 fps CFR, H.264 MP4, with automatic NVENC preference and CPU fallback. EDL segments may optionally set `fade_in_seconds` and `fade_out_seconds` (0–2 seconds each); these fade video and available source audio to/from black. Cross-dissolves are not yet supported, so do not claim them. See `references/export-and-fps.md`.
9. Run additional standalone technical checks when needed. State which visual checks remain manual or unimplemented.
10. Present previews, rationale, export settings, QC results and uncertainties. Require human approval.
11. Record only explicit persistent preferences.

## Three supported design layouts

- `fullscreen`: vertical 9:16 center-crop; basic outlined ASS captions, optional word karaoke.
- `split_vertical`: explicit top/bottom secondary sources stacked vertically; centered caption style.
- `blurred_bars_20_60_20`: blurred 20% top, sharp 60% center, blurred 20% bottom.

All three layouts support optional synchronized per-segment fade-in/fade-out effects and have initial FFmpeg code plus a synthetic integration test; the latest CI result is pending. Split mode requires fingerprinted `split_top` and `split_bottom` source specs in the EDL. Fullscreen rendering supports the face-guided crop keyframes produced by visual analysis, interpolating crop movement with FFmpeg. Face detection is limited to frontal Haar-cascade detections; the optional OpenCV-contrib CSRT tracker can bridge missed detections between sampled frames. It is not general object/action tracking and can lose the subject during occlusion, fast motion or scene changes, so inspect framing carefully.

## Decision hierarchy

1. Truth, context, and source integrity.
2. Complete story beat/payoff and comprehension.
3. Important subjects/actions remaining visible.
4. Readability and composition.
5. Pacing and stylistic polish.
6. Processing speed.

## Status vocabulary

Use: implemented-and-verified, implemented-unverified, partial, design-only, missing, or blocked. Never fabricate clips, metrics, test results, or virality guarantees.


## URL source ingestion

If the user supplies a public media URL rather than a local file, first use `shortform-editor download-source URL -o source-job/` (install `.[download]` first). This accepts HTTP(S) only, disables playlists, enforces an output-size limit, probes the downloaded media and records its SHA-256 fingerprint. Never bypass access controls, cookies, DRM or platform restrictions. Confirm the user owns the media or has permission to use it. Then pass the resulting local file to `analyze-project`.
