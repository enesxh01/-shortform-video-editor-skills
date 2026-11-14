---
name: observability
description: Produce structured logs, stage metrics, resource measurements, and actionable diagnostics for local video processing.
---

# Observability

Record structured events for ingestion, model loading, analysis, candidate ranking, EDL generation, rendering, QC, approval, and cleanup.

## Required fields

- job ID, project ID, stage, timestamp, severity;
- source fingerprint (not sensitive full path in shared logs);
- tool/model name and version;
- duration, progress, result state;
- CPU/GPU device and utilization when available;
- peak RAM/VRAM and disk usage when measurable;
- warnings, error category, retry/fallback details;
- artifact references and checksums.

## Rules

- Never invent metrics or report unavailable measurements as zero.
- Separate observed facts from estimates.
- Redact secrets, tokens, and private data.
- Keep logs bounded with rotation/retention policy.
- Provide concise human-readable summaries plus machine-readable JSON logs.
- Diagnostics must point to likely cause and safe next step without hiding uncertainty.
