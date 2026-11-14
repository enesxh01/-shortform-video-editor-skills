from __future__ import annotations

import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .cli import PipelineError, probe_media, validate_edl



def edl_approval_hash(edl: dict[str, Any]) -> str:
    payload = {key: value for key, value in edl.items() if key != "approval"}
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def approve_edl_file(edl_path: Path, source_path: Path, confirm: bool = False) -> dict[str, Any]:
    if not confirm:
        raise PipelineError("Approval requires explicit --confirm from the user")
    edl_path = edl_path.expanduser().resolve(strict=True)
    source_path = source_path.expanduser().resolve(strict=True)
    if edl_path == source_path:
        raise PipelineError("EDL path cannot be the source media path")
    try:
        edl = json.loads(edl_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PipelineError(f"Cannot read EDL: {exc}") from exc

    probe = probe_media(source_path)
    duration = float(probe.get("format", {}).get("duration") or 0)
    errors = validate_edl(edl, duration, probe["source"]["fingerprint"])
    if errors:
        raise PipelineError("Cannot approve invalid EDL:\n- " + "\n- ".join(errors))

    edl["approval"] = {
        "status": "approved",
        "approved_by_user": True,
        "approved_edl_sha256": edl_approval_hash(edl),
        "approved_at": datetime.now(timezone.utc).isoformat()
    }
    errors = validate_edl(edl, duration, probe["source"]["fingerprint"])
    if errors:
        raise PipelineError("Approved EDL failed validation:\n- " + "\n- ".join(errors))

    staged = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", prefix=".shortform-approval-",
                                         suffix=".tmp", dir=edl_path.parent, delete=False) as handle:
            staged = Path(handle.name)
            handle.write(json.dumps(edl, indent=2, ensure_ascii=False) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(staged, edl_path)
        staged = None
    finally:
        if staged is not None:
            staged.unlink(missing_ok=True)

    return {
        "status": "approved",
        "edl": str(edl_path),
        "source_fingerprint": probe["source"]["fingerprint"],
        "segments": len(edl["segments"]),
        "human_confirmation": True
    }
