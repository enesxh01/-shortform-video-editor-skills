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

## Rules

- Never imply the user has approved an edit by merely viewing a preview.
- Preserve rejected candidates and feedback as project artifacts; do not silently delete them.
- Make it easy to compare alternatives at the same timestamp.
- Clearly distinguish proxy previews from final-resolution renders.
- Do not ask the user to approve every tiny deterministic technical detail. Escalate meaningful creative ambiguity.
- A user may approve one clip while rejecting another; approvals are per artifact/version.

## Output

Record reviewer decision, EDL version, preview/final artifact hash, timestamp, and explicit feedback. Only an explicit approval changes the approval state to approved.
