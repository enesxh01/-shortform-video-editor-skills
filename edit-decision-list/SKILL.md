---
name: edit-decision-list
description: Define and validate a frame-accurate, versioned edit decision list as the single source of truth for all clip edits and renders.
---

# Edit Decision List

The EDL is the canonical, versioned representation of every edit. Modules propose changes; the editing director approves and writes the final EDL.

## Required concepts

- schema version and project ID;
- source fingerprint and stream identifiers;
- explicit time base and frame-rate metadata;
- ordered timeline segments with source in/out and timeline positions;
- speed changes only when explicitly intended;
- layout, crop keyframes, tracking references;
- caption text, word timing, style, safe-area position;
- audio gain/filter decisions;
- transitions and overlays;
- requested optional B-roll/SFX/music state;
- render profile, target FPS, and FPS conversion method;
- provenance, confidence, warnings, and approval state.

## Rules

- Use integer frame indices or rational timestamps; avoid floating-point drift.
- Source in/out must be valid and ordered.
- Never silently shift audio or video offsets.
- Every transform must be deterministic and reproducible.
- Keep previous versions; never overwrite approved EDL history.
- Validate schema and semantic constraints before rendering.
- Record why an edit was made and which evidence supports it.
