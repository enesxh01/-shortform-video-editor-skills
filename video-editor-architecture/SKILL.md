---
name: video-editor-architecture
description: Design and maintain the local-first architecture, module contracts, dependency policy, and failure boundaries for the short-form video editor.
---

# Video Editor Architecture

Act as a senior media-systems architect. Keep the system modular, testable, local-first, and understandable.

## Architecture rules

- Separate discovery/analysis, editorial decisions, timeline representation, rendering, and QC.
- The EDL is the canonical source of edit decisions; do not let modules independently mutate rendered media.
- Every module returns structured data with schema version, source identity, time base, confidence, warnings, and provenance.
- Keep source media immutable. Derived files live in a project workspace with clear cache/output boundaries.
- Use adapters around external tools (FFmpeg, ASR, VAD, scene detection, tracking) so alternatives can be substituted.
- Detect OS, CPU, GPU, VRAM, RAM, codecs, and installed tool versions at runtime. Do not assume a particular machine or OS.
- Prefer local and free/open-source dependencies. Before adoption, verify current license, model terms, hardware requirements, maintenance state, and redistribution restrictions.
- Never silently download multi-gigabyte models or send private footage to cloud services.
- Do not load every model simultaneously. Use a resource scheduler and explicit unload/release behavior.
- Keep optional capabilities optional; a missing optional model must degrade gracefully with a clear warning.
- Avoid brittle version pins without compatibility testing. Lock tested versions in a reproducible environment file once verified.

## Module boundaries

1. Ingestion: probe, validate, fingerprint, and stage source.
2. Audio intelligence: ASR, word timestamps, VAD, speaker-turn evidence, audio events.
3. Visual intelligence: scenes, subjects, objects, tracking, OCR, framing evidence.
4. Viral-moment detection: discover and rank editorially promising moments.
5. Retention/pacing: propose safe tightening for selected moments.
6. Editing director: resolve conflicts and author EDL.
7. Renderer: translate EDL into deterministic FFmpeg operations.
8. QC: validate technical and visual output.
9. Preview/approval: present alternatives and obtain human decisions.
10. Project memory: store explicit preferences and corrections only.

## Contracts

- All timestamps must declare units/time base. Prefer rational time bases or integer frame indices for frame-accurate operations.
- Every timestamp transformation must account for source start time, stream time base, audio offset, VFR, and any proxy mapping.
- Every recommendation carries rationale, confidence, and uncertainty.
- Modules must not overwrite upstream evidence. Store derived decisions separately.
- Errors must be typed: invalid input, unsupported codec, missing dependency/model, resource exhaustion, analysis failure, render failure, QC failure, cancellation, and internal defect.
- Every long-running job supports progress, cancellation, bounded retries, and safe recovery.

## Acceptance

Architecture is not complete until unit and integration tests cover contracts, failure handling, source immutability, time mapping, resource release, and deterministic EDL rendering. Document what is verified versus merely planned.
