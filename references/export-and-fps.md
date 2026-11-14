# Export and 60 FPS Policy

## Default profile

Unless the user or delivery platform specifies otherwise:
- 1080 × 1920, 9:16;
- MP4 container;
- H.264 video, yuv420p;
- AAC audio where source audio exists;
- 60 fps constant-frame-rate target;
- high-quality encode settings validated for the selected encoder;
- no background music by default.

## Frame-rate decision table

| Source | Default handling | Required disclosure/check |
|---|---|---|
| 59.94/60 fps CFR | Preserve motion; normalize to requested 60 CFR only as needed | Verify frame count and pacing |
| 120 fps or higher | Use intended playback speed; downsample carefully to 60 unless slow motion is explicitly planned | Avoid unintended speed changes |
| 50 fps | Convert to 60 only with a documented cadence strategy | Inspect judder/duplicates |
| 25/30 fps | Convert output timeline to 60 using frame duplication or tested interpolation only if appropriate | Explain that output container rate is not native captured motion |
| 24/23.976 fps | Preserve cinematic cadence where possible; if 60 CFR is mandatory, choose and inspect conversion strategy | Watch for uneven cadence |
| VFR | Normalize timestamps carefully before CFR render | Verify audio sync and frame pacing |
| Very low FPS | Prefer honest cadence preservation over visibly destructive interpolation | Disclose limitation |

## Interpolation caution

Optical-flow interpolation can create warped edges, ghosting, doubled hands/faces, and invented intermediate motion. Use it only after a source-specific test and visual review. Frame blending can create trails. Duplication can create judder. There is no universal best conversion.

## Verification checklist

Use ffprobe on the finished output and record:
- codec, width, height, pixel format;
- average and nominal frame rate;
- frame count and duration;
- audio codec, channels, sample rate;
- start timestamps and stream offsets.

Decode the entire file and inspect representative frames plus motion segments. A successful FFmpeg exit code alone is not sufficient.
