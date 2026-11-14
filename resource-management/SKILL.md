---
name: resource-management
description: Schedule local analysis and rendering jobs safely across CPU, GPU, RAM, VRAM, and disk with graceful fallbacks and recovery.
---

# Resource Management

## Executable baseline

The `shortform_editor.resources` module uses psutil for available system RAM and `nvidia-smi` for NVIDIA GPU/VRAM telemetry. The render command also performs a conservative free-disk preflight on both the output volume and system temporary volume before encoding; it includes a 512 MiB safety reserve and estimates temporary segment plus assembly space from requested clip duration. This estimate is intentionally conservative and cannot guarantee final encoded size. Audio ASR preflight selects CUDA only when the model-specific VRAM reserve is met; otherwise it uses CPU int8, and it refuses to start when available RAM is below 2.5 GB. The default ASR model is `small`. The selected device, compute type and resource snapshot are written to the audio-analysis report.

This is preflight selection, not a complete scheduler. There is no job queue, concurrent-job coordinator, disk reservation, live peak VRAM/RAM sampler or automatic OOM retry yet.

- Detect actual hardware and runtime capabilities; do not infer from a model name or assume CUDA availability.
- Measure free disk, RAM, VRAM, GPU encoder support, and CPU load before scheduling.
- Avoid loading multiple large models concurrently unless benchmarks prove it is safe.
- Use bounded queues, explicit resource reservations, timeouts, and cancellation.
- Unload models and release GPU memory after each stage where practical.
- Prefer lower-resolution proxies for analysis only; final render uses original source.
- Fall back to smaller model, alternate compute type, or CPU only with a clear report.
- Handle OOM by releasing resources and retrying once with a defined fallback; avoid infinite retries.
- Protect approved outputs and source media during cleanup.
- Log stage duration, peak RAM/VRAM, device, model, fallback, and failure reason.
- Do not optimize for speed at the expense of measurable clip quality or source integrity.
