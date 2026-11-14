---
name: job-orchestration
description: Manage long-running media jobs with progress reporting, pause/cancel/retry semantics, bounded recovery, and safe artifact handling.
---

# Job Orchestration

## Job lifecycle

Use explicit states: queued, inspecting, analyzing, selecting, editing, rendering, quality_check, awaiting_approval, completed, failed, cancelled.

Each transition records start/end time, progress, inputs, outputs, warnings, and failure details.

## Reliability

- Support cancellation at safe boundaries and interrupt subprocesses without corrupting approved files.
- Use bounded retries only for transient failures; never retry deterministic invalid input indefinitely.
- Keep checkpoints after expensive stages.
- Write render outputs to temporary paths and atomically promote only after validation.
- Never overwrite the last approved export with a failed retry.
- Detect disk-space exhaustion before rendering and during long jobs.
- On restart, reconcile incomplete jobs and offer resume or clean cancellation.
- Keep logs actionable and redact secrets.

## Progress

Report meaningful stage progress rather than fake precision. Separate analysis progress from render progress. Include estimated remaining time only when based on measured throughput and label it as an estimate.

## Cancellation

Cancellation must preserve source media, EDL history, prior approved exports, and useful intermediate reports. Clean only known temporary artifacts.
