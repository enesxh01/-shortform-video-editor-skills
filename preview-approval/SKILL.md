---
name: preview-approval
description: Present clip candidates and edit previews for human review, collect explicit approvals, and preserve rejected alternatives.
---

# Preview and Human Approval

Human review is a required quality gate for creative decisions.

## Preview stages

1. Candidate review: show title/summary, source timestamps, score breakdown, hook, payoff, and context risks.
2. Boundary review: show alternate in/out points when the boundary is uncertain.
3. Edit review: preview crop/layout, captions, motion, pacing, and audio.
4. Export review: show final file, export metadata, QC summary, and known limitations.

## Executable approval workflow

- Create a fast 30 fps preview without changing the EDL approval state: `shortform-editor render-preview INPUT.mp4 DRAFT_EDL.json preview.mp4`.
- The preview is for review only. It is not the final 60 fps export and does not approve the EDL.
- Only after the user explicitly says to approve that exact EDL, run `shortform-editor approve-edl DRAFT_EDL.json --source INPUT.mp4 --confirm`. This re-probes the source, verifies the fingerprint/duration and EDL schema, then atomically marks the EDL approved.
- Render the final output only after approval: `shortform-editor render INPUT.mp4 APPROVED_EDL.json final.mp4`.
- Never add `--confirm` or run `approve-edl` merely because the user asked for a preview or analysis.

## Rules

- Never imply the user has approved an edit by merely viewing a preview.
- Preserve rejected candidates and feedback as project artifacts; do not silently delete them.
- Make it easy to compare alternatives at the same timestamp.
- Clearly distinguish proxy previews from final-resolution renders.
- Do not ask the user to approve every tiny deterministic technical detail. Escalate meaningful creative ambiguity.
- A user may approve one clip while rejecting another; approvals are per artifact/version.

## Output

Record reviewer decision, EDL version, preview/final artifact hash, timestamp, and explicit feedback. Only an explicit approval changes the approval state to approved.
