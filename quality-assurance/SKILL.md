---
name: quality-assurance
description: Run technical and visual quality checks on rendered clips, classify defects, repair only safe issues, and verify every rerender.
---

# Quality Assurance

## QC departments

1. Visual integrity: black/frozen/corrupt/missing frames, aspect ratio, dimensions, FPS, flicker, crop, tracking, layout, transitions.
2. Captions/typography: spelling, transcript match, timing, overlap, safe areas, readability, clipping, line count and layout-specific placement.
3. Audio integrity: clipping, loudness, missing/muted stream, sync, abrupt cuts, unwanted noise, silence, channel issues.
4. Editing integrity: hook clarity, complete context/payoff, no accidental jump, no lost reaction, no misleading crop or caption.
5. Export integrity: codec/container, resolution, frame rate, frame count, duration, pixel format, stream mapping, successful full decode.

## Severity

- critical: output unusable, meaning altered, key content missing, severe corruption, major sync failure;
- major: visible/audible defect that materially harms viewing;
- minor: polish issue;
- warning: known limitation or uncertain measurement;
- passed: check completed and met criteria.

A critical failure cannot be hidden by an average score. Report failures by department.

## Audio levels

Do not blindly force short-form content to broadcast loudness targets. EBU R128 -23 LUFS is a broadcast reference, not a universal social-video target. Measure integrated loudness, true peak, clipping, and dynamics; choose a platform/profile target only when verified. Preserve dynamics and avoid pumping. A true-peak ceiling around -1 dBTP may be used as a conservative engineering target where appropriate, not as a substitute for listening.

## Repair loop

Render → technical QC → visual QC → classify → safe repair → rerender → full recheck → approval.

- Repair only understood, reversible defects.
- Never replace source black frames automatically.
- Do not rewrite uncertain captions without checking source audio.
- Bound repair attempts and report unresolved issues.
- Keep before/after artifacts and reasons.

## Human review

Technical QC cannot assess humor, authenticity, emotional timing, or whether a crop feels right. Provide a preview and require human approval for final delivery.
