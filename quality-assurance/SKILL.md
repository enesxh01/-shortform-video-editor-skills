---
name: quality-assurance
description: Run technical and visual quality checks on rendered clips, classify defects, repair only safe issues, and verify every rerender.
---

# Quality Assurance

## Executable technical QC baseline

The `shortform-editor render` command automatically runs technical QC after rendering and includes the report in its JSON output. Run `shortform-editor qc OUTPUT.mp4 -o qc-report.json` separately when you need a standalone recheck. The current command checks stream presence, configured dimensions, average frame rate, H.264 codec, yuv420p pixel format, AAC codec and 48 kHz audio, black intervals, frozen-frame intervals, audio sample peak, EBU R128 integrated loudness/loudness range/true peak when audio is present, and audio/video stream start/duration metadata alignment. A missing audio stream is a warning; major technical defects return a failing exit code.

Stream timing is metadata-only and cannot prove lip-sync or perceptual synchronization. This is not complete QC. EBU R128 loudness and true-peak readings are advisory: a general -16 to -12 LUFS band and a true-peak ceiling below -1 dBTP are guidance, not universal platform rules. The report does not validate caption spelling/timing, crop quality, HUD/object caption collisions, audio/video sync by listening, story comprehension or visual appeal. Fullscreen drafts may use sampled face boxes to choose top or bottom captions, but this is not a substitute for visual review. Black/freeze detections can flag intentional creative choices and require review.

## Bounded technical repair

Run `shortform-editor repair INPUT.mp4 OUTPUT.mp4` to create a separate normalized H.264/AAC 1080x1920 60 fps CFR export and run technical QC again. The original is never overwritten. This repairs container/codec/frame-size/frame-rate compatibility only. It does not synthesize missing content, remove black/frozen frames, de-clip audio, correct captions or guarantee visual quality. Inspect the repair report's unresolved list and review the output.

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
