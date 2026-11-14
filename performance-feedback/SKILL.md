---
name: performance-feedback
description: Learn from explicit local editorial approvals, rejections and edits to improve future candidate ranking without importing channel analytics.
---

# Performance Feedback and Learning

## Scope

This module learns only from explicit human editorial decisions stored locally. It does not fetch YouTube Analytics, views, watch time, retention curves, OAuth data or channel credentials. Those integrations are intentionally excluded.

## Workflow

1. After reviewing a candidate, record `approve`, `edited` or `reject` with an optional short reason:
   `shortform-editor record-feedback candidates.json --candidate-id moment-... --decision approve`.
2. Apply learned category preferences to a future candidate report:
   `shortform-editor apply-feedback candidates.json -o ranked.json`.
3. Inspect the adjustment and the original score before selecting a clip.

## Learning behavior

- Feedback is stored as JSONL under `~/.shortform-editor/feedback.jsonl` by default; a custom path can be supplied.
- Category-level adjustments use smoothed approval rates and require at least three observations per family.
- Adjustments are bounded to +/-5 points and never replace the underlying evidence score.
- `edited` is treated as a partial positive preference signal, not as a full approval.
- The system does not train model weights or infer the reason for a decision beyond the optional human note.

## Privacy and controls

- Feedback remains local unless the user explicitly shares it.
- Reasons should not contain personal data or private information about people in source videos.
- The user may back up or delete the local feedback file at any time.
- Do not describe this as audience-performance learning; it learns editorial preferences from human labels only.
