# Test Plan

This repository currently defines the skill and validation requirements; it does not claim that a complete editor implementation or automated test suite exists yet.

## Required automated tests

- JSON Schema validation for EDL.
- YAML frontmatter validation and folder/name matching for every skill.
- Relative-link validation for Markdown references.
- Unit tests for timestamp/time-base conversions, VFR mapping, crop transforms, caption safe areas, scoring aggregation, and FFmpeg argument construction.
- Integration tests for ingestion → analysis → candidate → EDL → render → QC.
- Failure tests for corrupt media, missing streams, GPU OOM, disk full, cancellation, interrupted render, and retry recovery.
- Security tests for path traversal, shell injection, untrusted metadata, and unsafe archive inputs.

## Real-footage validation matrix

| Category | Cases |
|---|---|
| Conversation | solo speaker, interview, overlap, interruptions |
| Entertainment | comedy setup/payoff, reaction, storytime |
| Gaming/live | fast gameplay, HUD, streamer facecam, long quiet sections |
| Education | tutorial, demonstration, on-screen text |
| Sports/action | fast motion, camera pans, subject occlusion |
| Source quality | 4K, 1080p, 720p, low resolution, noisy audio |
| Timing | 23.976, 24, 25, 29.97, 30, 50, 59.94, 60, 120 fps, VFR |
| Failures | corrupt file, missing audio, offset timestamps, low disk, OOM |

## Honest reporting

For each test, report fixture, environment, expected result, actual result, pass/fail, logs, and known limitations. Never mark a test as passed because it was not run.
