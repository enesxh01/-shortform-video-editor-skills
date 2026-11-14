# Quality Gates

A clip advances only when it passes the gate for its stage. Do not collapse all quality into one score.

## Gate 1 — Source integrity
- Source can be probed and decoded.
- Streams, offsets, frame rate, time base, and duration are understood.
- Original is unchanged and fingerprinted.
- Any unsupported or suspicious properties are reported.

## Gate 2 — Editorial candidate
- Hook is understandable and truthful.
- Setup is sufficient for a new viewer.
- Payoff is complete.
- No essential context, reaction, or action is missing.
- Candidate score and uncertainty are documented.
- Near-duplicates are identified.

## Gate 3 — Edit plan
- EDL validates against schema and source bounds.
- Timeline timing is frame-accurate or rational.
- Layout choice has a content-based reason.
- Captions match the source audio and respect safe areas.
- Optional music/B-roll/SFX are off unless explicitly requested.

## Gate 4 — Render
- Original source is used for final render.
- Export profile is recorded.
- 60 FPS target handling is explicit and source-aware.
- Render completes to a temporary output and is atomically promoted only after validation.

## Gate 5 — Technical QC
- Full decode succeeds.
- Dimensions, codec, pixel format, frame rate, frame count, duration, and streams match expectations.
- Audio/video sync and levels are checked.
- No unexplained black/frozen/corrupt frames or severe artifacts.

## Gate 6 — Visual/creative QC
- Watch the complete clip.
- Inspect opening, payoff, transitions, crop edges, captions, and motion.
- Check interpolation/cadence for judder, duplicates, warping, or ghosting.
- Confirm the edit still represents the source honestly.

## Gate 7 — Approval
- Show preview and QC report.
- Human explicitly approves the final artifact.
- Store artifact checksum and EDL revision.
- A failed or rejected version is never labeled approved.
