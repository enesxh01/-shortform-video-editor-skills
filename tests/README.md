# Test Plan

## Automated coverage

Run all unit tests from the repository root:

```bash
python -m unittest discover -s tests -p "test_*.py" -v
python -m py_compile shortform_editor/cli.py
```

The current unit suite covers timestamp parsing, malformed timestamps, EDL structural validation, invalid layouts, split-layout requirements, approval enforcement, and source fingerprint mismatch. GitHub Actions runs compilation and unit tests on pushes and pull requests.

## Required media integration tests (must run on a machine with FFmpeg)

- Generate short synthetic CFR videos with and without audio and render approved EDLs.
- Verify fullscreen and blurred-bars layouts; verify split_vertical with two independent sources.
- Verify caption timing, Unicode text, safe margins, and no-caption output.
- Verify output metadata, frame count, CFR rate, stream mapping, audio sync, and complete decode.
- Exercise VFR, 23.976/24/25/29.97/30/50/59.94/60/120 fps inputs.
- Exercise corrupt media, missing streams, missing FFmpeg, insufficient disk, cancellation, and interrupted render.
- Confirm source files remain unchanged and previous approved exports survive failed rerenders.

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

A test is passed only after it actually runs. Unit tests do not establish successful rendering on the user's machine or prove visual storytelling quality. Report environment, fixture, expected result, actual result, pass/fail, logs, and known limitations.
