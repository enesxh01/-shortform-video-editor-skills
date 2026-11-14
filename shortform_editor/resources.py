from __future__ import annotations

import shutil
import subprocess
from typing import Any

import psutil


MODEL_VRAM_GB = {
    "tiny": 1.5,
    "base": 2.0,
    "small": 3.0,
    "medium": 6.0,
    "large-v3": 9.0
}
MODEL_RAM_GB = {
    "tiny": 1.5,
    "base": 2.0,
    "small": 2.5,
    "medium": 5.0,
    "large-v3": 8.0
}


def resource_snapshot() -> dict[str, Any]:
    memory = psutil.virtual_memory()
    gpu = {"available": False, "name": None, "memory_total_mb": None, "memory_free_mb": None}
    executable = shutil.which("nvidia-smi")
    if executable:
        try:
            result = subprocess.run(
                [executable, "--query-gpu=name,memory.total,memory.free", "--format=csv,noheader,nounits"],
                check=True, capture_output=True, text=True, timeout=5
            )
            first = result.stdout.strip().splitlines()[0].split(",")
            if len(first) >= 3:
                gpu = {
                    "available": True,
                    "name": first[0].strip(),
                    "memory_total_mb": int(first[1].strip()),
                    "memory_free_mb": int(first[2].strip())
                }
        except (OSError, subprocess.SubprocessError, ValueError, IndexError):
            pass
    return {
        "ram_total_gb": round(memory.total / (1024 ** 3), 2),
        "ram_available_gb": round(memory.available / (1024 ** 3), 2),
        "gpu": gpu
    }


def choose_inference_device(model_size: str, requested: str = "auto",
                            snapshot: dict[str, Any] | None = None) -> tuple[str, str, list[str]]:
    if model_size not in MODEL_VRAM_GB:
        raise ValueError(f"Unsupported model size: {model_size}")
    if requested not in {"auto", "cpu", "cuda"}:
        raise ValueError(f"Unsupported inference device: {requested}")
    resources = snapshot or resource_snapshot()
    notes = []
    available_ram = float(resources.get("ram_available_gb", 0))
    required_ram = MODEL_RAM_GB[model_size]
    if available_ram < required_ram:
        raise RuntimeError(
            f"Only {available_ram:.1f} GB RAM is available; {required_ram:.1f} GB is the minimum reserve for {model_size}."
        )
    gpu = resources.get("gpu", {})
    gpu_free_gb = float(gpu.get("memory_free_mb") or 0) / 1024
    required_vram = MODEL_VRAM_GB[model_size]
    cuda_ready = bool(gpu.get("available")) and gpu_free_gb >= required_vram

    if requested == "cpu":
        return "cpu", "int8", notes
    if requested == "cuda":
        if not cuda_ready:
            raise RuntimeError(
                f"CUDA requested but GPU memory is insufficient/unavailable: "
                f"{gpu_free_gb:.1f} GB free; {required_vram:.1f} GB recommended for {model_size}."
            )
        return "cuda", "int8_float16", notes
    if cuda_ready:
        return "cuda", "int8_float16", notes
    if gpu.get("available"):
        notes.append(
            f"CUDA skipped: {gpu_free_gb:.1f} GB free VRAM; {required_vram:.1f} GB recommended. Using CPU int8."
        )
    else:
        notes.append("NVIDIA GPU telemetry unavailable; using CPU int8.")
    return "cpu", "int8", notes
