from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse
from typing import Any

from .cli import PipelineError, probe_media


def download_source(url: str, output_dir: Path, max_filesize_mb: int = 2048) -> dict[str, Any]:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise PipelineError("Source URL must use http:// or https://")
    if max_filesize_mb < 1 or max_filesize_mb > 20480:
        raise PipelineError("Maximum download size must be between 1 and 20480 MB")
    output_dir = output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    if any(output_dir.iterdir()):
        raise PipelineError("Download output directory must be empty")
    try:
        import yt_dlp
    except ImportError as exc:
        raise PipelineError("URL ingestion requires the optional download extra: pip install -e '.[download]'") from exc

    options = {
        "format": "bv*+ba/b",
        "merge_output_format": "mp4",
        "outtmpl": str(output_dir / "source.%(ext)s"),
        "noplaylist": True,
        "max_filesize": max_filesize_mb * 1024 * 1024,
        "restrictfilenames": True,
        "windowsfilenames": True,
        "quiet": True,
        "no_warnings": False,
        "retries": 2,
        "fragment_retries": 2,
        "continuedl": True,
        "overwrites": False,
    }
    def cleanup_partial_download() -> None:
        for partial in output_dir.iterdir():
            if partial.is_file():
                partial.unlink(missing_ok=True)

    try:
        with yt_dlp.YoutubeDL(options) as downloader:
            info = downloader.extract_info(url, download=True)
            downloaded = Path(downloader.prepare_filename(info))
            if not downloaded.exists():
                merged = downloaded.with_suffix(".mp4")
                if merged.exists():
                    downloaded = merged
            if not downloaded.is_file():
                candidates = [p for p in output_dir.iterdir() if p.is_file() and p.suffix.lower() in {".mp4", ".mkv", ".webm", ".mov"}]
                if len(candidates) != 1:
                    raise PipelineError("Downloader completed but did not produce one unambiguous media file")
                downloaded = candidates[0]
    except PipelineError:
        raise
    except Exception as exc:
        cleanup_partial_download()
        raise PipelineError(f"URL download failed: {type(exc).__name__}: {exc}") from exc

    if downloaded.stat().st_size > max_filesize_mb * 1024 * 1024:
        cleanup_partial_download()
        raise PipelineError("Downloaded file exceeded the configured maximum size")
    try:
        probe = probe_media(downloaded)
    except Exception:
        cleanup_partial_download()
        raise
    return {
        "source_path": str(downloaded),
        "source_fingerprint": probe["source"]["fingerprint"],
        "size_bytes": downloaded.stat().st_size,
        "title": str(info.get("title") or "")[:300],
        "extractor": str(info.get("extractor_key") or info.get("extractor") or "")[:100],
        "duration_seconds": probe.get("format", {}).get("duration"),
        "probe": probe,
        "notice": "Download only content you own or are authorized to use; platform terms and copyright law still apply."
    }
