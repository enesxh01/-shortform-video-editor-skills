# Test Plan and Current Automated Coverage

The automated suite is intentionally small and must grow with each implementation stage.

## Run

```bash
python -m pip install -e .
python -m unittest discover -s tests -v
```

## Implemented automated tests

- EDL JSON Schema validation and semantic checks: ordered source in/out timestamps, non-empty segment list, timestamp format, 9:16 output dimensions, user-confirmed approval state, unique segment IDs, and optional source-duration bounds.

## Not yet implemented / not yet tested

- Installer behavior on Linux and Windows (CI/manual verification required).
- ffprobe integration tests against real and corrupt media.
- Frame-rate and VFR normalization tests.
- FFmpeg render integration and audio-sync tests.
- Captions, tracking, split-screen, blurred-bars and visual QC.
- Viral candidate discovery, transcription, speaker diarization and retention analysis.
- GPU/VRAM/RAM benchmarks and recovery/failure injection.

Never mark a test passed unless it was run. Real-footage validation is required before claiming production readiness.
