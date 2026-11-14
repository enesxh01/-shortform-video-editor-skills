# Implementation Status

Last updated: 2026-11-14
Runtime version: 0.2.0

## Implemented and CI-verified

The GitHub Actions runtime workflow has successfully compiled the Python runtime, passed unit tests, and rendered synthetic media through all three layouts on Ubuntu with FFmpeg. The integration test checks output dimensions, 60 fps, audio, subtitle rendering, manifest creation, and full decode.

- Source inspection with ffprobe metadata and SHA-256 fingerprinting.
- EDL validation for source identity, timestamps, segment bounds, layout requirements, captions, FPS, and approval state.
- FFmpeg rendering for fullscreen center-crop, vertical split (two supplied video sources), and blurred 20/60/20 layout.
- ASS captions, caption positioning, optional timed word/karaoke highlighting.
- H.264/libx264 and AAC export, CFR target rate, temporary render, output validation, full decode, and JSON manifest.
- Optional local faster-whisper word-timestamp ASR adapter (the adapter is implemented; actual model execution is not yet CI-tested).
- OpenCode installer for Windows PowerShell and Bash, including runtime, EDL examples, shared references, schemas, config, and docs.
- CI checks for compilation, unit tests, FFmpeg integration renders, and Bash installer smoke test.

## Partial or not yet verified

- Semantic viral-moment discovery is an editorial workflow for the orchestrating AI using transcript/visual evidence and the scoring rubric. It is not a standalone deterministic detector that can promise viral clips.
- ASR requires the optional faster-whisper package and a user-approved model download. Model accuracy, GPU acceleration, non-English names/slang, and long-video performance must be tested on real footage.
- Fullscreen currently uses a centered crop. Subject/face/object tracking and dynamic crop-keyframe rendering are not implemented; the renderer rejects EDLs that request unsupported crop_keyframes.
- Renderer supports CFR only. 60 fps output is a delivery frame rate, not a claim that lower-frame-rate footage contains 60 unique captured frames per second.
- GPU encoding is not enabled; libx264 is the reproducible baseline.
- Visual/storytelling QC still requires a person to review the exported clip. Automated decode and metadata checks cannot judge whether a crop, caption, hook, or edit is creatively correct.
- Windows installation and rendering have not been tested on the user's PC. Real long-form source footage, mixed codecs, VFR edge cases, audio offsets, and low-resource failure recovery remain to be tested.

## Release decision

The repository is ready for a first controlled local installation and synthetic-media smoke test. It is **not** yet honestly classifiable as a fully autonomous, production-proven, professional clipper until the partial items above are implemented or explicitly accepted and real footage has been tested.
