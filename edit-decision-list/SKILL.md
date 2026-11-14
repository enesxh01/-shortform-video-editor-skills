---
name: edit-decision-list
description: Define and validate a frame-accurate, versioned edit decision list as the single source of truth for all clip edits and renders.
---

# Edit Decision List

The EDL is the canonical, versioned representation of every edit. Modules propose changes; the editing director approves and writes the final EDL.

## Schema and validation

The installed schema is at `schemas/edit-decision-list.schema.json` inside this skill. The repository CLI additionally applies semantic checks with `shortform-editor validate-edl`.

- Use integer frame indices or rational timestamps; avoid floating-point drift.
- Source in/out must be valid and ordered.
- Segments must be non-empty and IDs unique.
- Output must be valid portrait 9:16 with even dimensions.
- Timeline starts must be nondecreasing when supplied.
- An approved EDL must explicitly set `approved_by_user: true`.
- If a probe report is supplied, segment out-points must not exceed source duration.
- Never silently shift audio or video offsets.
- Every transform must be deterministic and reproducible.
- Optional `fade_in_seconds` and `fade_out_seconds` may be set per segment (0–2 seconds each); their sum must be shorter than the segment duration. They fade video and available source audio to/from black.
- Keep previous versions; never overwrite approved EDL history.
- Validate schema and semantic constraints before rendering.
- Record why an edit was made and which evidence supports it.

The current EDL is intentionally a minimal first contract. Captions, crop keyframes and per-segment fade-to/from-black transitions are represented in the schema. General subject tracking, cross-dissolves, overlays, independent audio mixing and broader provenance expansion remain future schema work; do not add undocumented properties because strict validation rejects them.


The optional `pacing_review` segment field stores ordered, source-bounded `keep`, `trim`, and `preserve_pause` evidence plus repeated-word flags. It is review metadata only and must not be interpreted as an instruction to cut automatically.


The current FFmpeg renderer concatenates EDL segments sequentially. When `timeline_start` is supplied, it must equal the cumulative duration of prior segments. Fade-to/from-black is supported inside each segment; cross-dissolves, transition overlaps, timeline gaps, overlaps and layered composition are not supported and are rejected rather than silently ignored.
