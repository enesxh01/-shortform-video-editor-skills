---
name: retention-pacing
description: Tighten selected clips by improving pacing while preserving comprehension, meaningful pauses, jokes, reactions, and story beats.
---

# Retention and Pacing

This module edits the pacing of already-selected candidates. It does not decide whether a moment is intrinsically compelling; that belongs to viral-moment detection.

## Understand before tightening

Use transcript, audio, visual events, speaker turns, joke/story structure, and action continuity. Identify:
- meaningful pauses;
- setup and payoff;
- repetitions and tangents;
- breaths and natural phrasing;
- reaction time;
- demonstrations and visual proof;
- transitions needed for comprehension.

## Decision types

Each proposed timeline decision must be structured as:
- `keep`
- `trim`
- `tighten`
- `preserve_pause`
- `hold`
- `visual_change`

Include source in/out, proposed duration, rationale, confidence, and context risk.

## Rules

- Never cut across a word, sentence meaning, joke timing, reaction, reveal, or action result.
- Remove dead air only when it contributes nothing.
- Do not use silence detection as an automatic edit decision.
- Preserve natural cadence; avoid robotic jump-cut pacing.
- Avoid repetitive zooms and gratuitous transitions.
- If a cut could alter meaning or comprehension, preserve the original or request review.

## Validation

Measure false cuts, missed dead air, damaged sentences, lost punchlines, timing changes, and runtime. Review the actual output, not only the decision log.
