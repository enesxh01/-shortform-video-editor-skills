---
name: security-provenance
description: Protect local media projects through safe file handling, command construction, dependency license review, and provenance records.
---

# Security, Licensing, and Provenance

## Input and process safety

- Treat filenames, metadata, subtitles, URLs, and archive contents as untrusted.
- Validate file types by probing content, enforce configurable size/duration limits, and isolate temporary files.
- Prevent path traversal, symlink escapes, archive bombs, and unbounded downloads.
- Invoke FFmpeg and other tools with argument arrays, not shell-interpolated command strings.
- Escape filtergraph values and validate user-supplied expressions.
- Do not execute scripts or code embedded in source media.
- Do not bypass access controls or fetch private content without authorization.

## Privacy

- Local-first by default. No cloud upload or external API call without explicit user approval.
- Never store account passwords, tokens, or unrelated sensitive information in project memory or logs.
- Redact secrets and private local paths from shareable reports where appropriate.

## Licensing

Before adding a model, library, codec, font, or effect, record name, version, license, source, redistribution limits, commercial-use limits, model terms, and required attribution. The current runtime inventory is in `THIRD_PARTY_NOTICES.md`: faster-whisper/CTranslate2 are MIT, OpenCV 4.5+ is Apache-2.0, and its bundled Haar cascade has a separate Intel BSD-style notice. FFmpeg licensing depends on the exact build (LGPL/GPL); this project does not bundle it. The repository still has no root project license, which requires the owner's explicit choice.

## Provenance

Record source checksum, model/tool versions, processing settings, EDL revision, render command/config, output checksum, and QC result. Provenance supports reproducibility; it does not prove copyright ownership or grant rights to source material.
