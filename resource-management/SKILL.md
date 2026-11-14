---
name: resource-management
description: Schedule local analysis and rendering jobs safely across CPU, GPU, RAM, VRAM, and disk with graceful fallbacks and recovery.
---

# Resource Management

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
