---
name: video-editor-testing
description: Validate the video editor through unit, integration, benchmark, regression, and real-footage tests with honest verification reporting.
---

# Video Editor Testing

## Test layers

- Unit: schemas, timestamp math, scoring, crop transforms, caption layout, EDL validation, command construction.
- Integration: ingestion → analysis → candidate → EDL → render → QC.
- Regression: previously approved clips and known failure fixtures.
- Benchmarks: runtime, RAM/VRAM, model load/unload, throughput, frame pacing, render quality.
- Human review: actual clips across genres and source conditions.

## Required footage matrix

Test podcasts, interviews, gaming, livestreams, education/tutorials, comedy, storytelling, multi-speaker dialogue, noisy audio, non-English/code-switching, landscape and vertical footage, VFR, low resolution, long recordings, occlusion, and resource exhaustion.

## Failure tests

Invalid/corrupt input, unsupported codec, missing model, GPU unavailable, out-of-memory, disk full, cancellation, interrupted render, missing audio, timestamp offsets, duplicate frames, and QC failure.

## Acceptance criteria

- No source file mutation.
- No unsafe shell interpolation.
- Time mapping and audio sync within explicitly defined tolerances.
- No accidental cut across words or required story beats in reviewed samples.
- 60 fps output is verified from the rendered file; cadence/interpolation defects are separately inspected.
- Critical QC failures block approval.
- Cancellation/retry does not corrupt approved outputs.
- All tests report actual results, not assumed results.

## Status labels

Use only: implemented-and-verified, implemented-unverified, partial, design-only, missing, blocked. Include test evidence and known limitations.
