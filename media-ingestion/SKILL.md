---
name: media-ingestion
description: Safely inspect, validate, fingerprint, and stage local or linked video sources while preserving originals and accurate media timing.
---

# Media Ingestion

- Accept user-provided local files or explicitly supported links. Do not bypass access controls or download private content without authorization.
- Validate file type by probing content, not trusting extension alone.
- Inspect duration, dimensions, codec, pixel format, frame rate, time base, VFR/CFR, rotation metadata, color metadata, audio streams, channels, sample rate, start timestamps, and corruption.
- Record source checksum, file size, probe JSON, tool version, and ingestion time.
- Preserve original file unchanged. Use a project-local staging reference; copy only when needed.
- Generate proxies only for analysis/preview and maintain exact source-to-proxy timestamp mapping.
- Detect unsupported codecs, malformed streams, unusual timestamps, missing audio, and suspicious duration discrepancies.
- Sanitize filenames and paths. Prevent path traversal and command injection.
- Keep downloads and temporary files in isolated directories with size limits and cleanup rules.
- Never silently discard streams or metadata needed for editing.
- Return a clear ingestion report with warnings and whether the source is safe to process.
