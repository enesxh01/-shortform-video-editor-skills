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
- Keep previous versions; never overwrite approved EDL history.
- Validate schema and semantic constraints before rendering.
- Record why an edit was made and which evidence supports it.

The current EDL is intentionally a minimal first contract. Captions, crop keyframes, tracking, transitions, overlays, per-segment audio processing and provenance expansion remain future schema work; do not add undocumented properties because strict validation rejects them.
