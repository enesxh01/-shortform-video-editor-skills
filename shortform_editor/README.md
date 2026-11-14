# Shortform Editor Runtime

This folder contains the executable local rendering/inspection runtime. The skill suite is the editorial brain; this Python CLI performs deterministic media operations.

## Requirements

- Python 3.10+
- FFmpeg and ffprobe installed and available on PATH
- No Python third-party packages required for core commands

## Optional local transcription

Install faster-whisper only if you want local ASR: `python -m pip install faster-whisper`. Then run `python shortform_editor/cli.py transcribe SOURCE -o project/transcript.json --model small --device auto --compute-type auto`. The first run downloads the selected model; no model is downloaded by the installer or other commands. Choose `--model medium` for potentially better accuracy if VRAM/RAM and speed permit. Word-level timestamps, language confidence, segment log probabilities, and VAD-filtered segments are saved as JSON. Review names, numbers, slang, and non-English transcription manually.

## Commands

```powershell
python .\shortform_editor\cli.py inspect "D:\media\source.mp4" --output project\source-report.json
python .\shortform_editor\cli.py validate project\edit.json --source "D:\media\source.mp4"
python .\shortform_editor\cli.py render project\edit.json --output exports\clip-01.mp4
python .\shortform_editor\cli.py qc exports\clip-01.mp4
```

inspect records source SHA-256, duration, stream metadata, dimensions, frame rates, time bases, and audio streams.

validate checks required EDL fields, timestamps, segment bounds, layouts, split-screen sources, export dimensions, FPS syntax, approval state, and (when --source is supplied) source fingerprint identity.

render accepts only an explicitly user-approved EDL. It creates a vertical MP4, burns supplied captions, preserves source audio, uses libx264/AAC, targets the EDL's rational CFR frame rate, validates dimensions/FPS, and fully decodes the temporary output before moving it into place. It writes a JSON render manifest next to the output.

qc probes and fully decodes an existing export.

## EDL conventions

- source.path is the absolute path to the original source file.
- source.fingerprint must be the sha256 value from inspect.
- source.time_base and source.frame_rate are rational strings (for example 1/90000, 30000/1001).
- Segment source_in and source_out are source timestamps.
- Caption start and end are relative to the beginning of their segment.
- split_vertical requires split_top and split_bottom objects, each with path, source_in, and source_out.
- approval.status must be approved and approved_by_user must be true before rendering.

## Important limitations

The runtime does not itself perform semantic ASR, diarization, object tracking, face tracking, or viral judgment. Those are analysis/editorial tasks performed by the orchestrating AI and optional local model adapters. It does not claim that 60 fps output contains 60 unique captured frames per second. Visual inspection remains mandatory: technical QC cannot detect every crop, subtitle, interpolation, or storytelling defect.

GPU encoding is intentionally not enabled by default; software x264 is the reproducible quality baseline. Optional acceleration should be added only after hardware-specific quality and compatibility tests.
