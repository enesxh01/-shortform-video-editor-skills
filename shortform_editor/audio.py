from __future__ import annotations

import json
import math
import shutil
import struct
import subprocess
import tempfile
import wave
from array import array
from pathlib import Path
from typing import Any

from .cli import PipelineError, file_stat_signature, probe_media, require_tool, run_checked, sha256_file


def _audio_stream(report: dict[str, Any]) -> dict[str, Any]:
    streams = [item for item in report.get("streams", []) if item.get("codec_type") == "audio"]
    if not streams:
        raise PipelineError("Input has no audio stream")
    return streams[0]


def _extract_mono_wav(source: Path, destination: Path, stream_index: int) -> None:
    ffmpeg = require_tool("ffmpeg")
    run_checked([
        ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
        "-i", str(source), "-map", f"0:{stream_index}", "-vn",
        "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", str(destination)
    ])


def _window_metrics(wav_path: Path, window_seconds: float = 0.5, silence_dbfs: float = -38.0) -> dict[str, Any]:
    with wave.open(str(wav_path), "rb") as wav:
        if wav.getnchannels() != 1 or wav.getsampwidth() != 2:
            raise PipelineError("Internal audio analysis WAV must be mono 16-bit PCM")
        sample_rate = wav.getframerate()
        total_frames = wav.getnframes()
        window_frames = max(1, int(sample_rate * window_seconds))
        windows: list[dict[str, Any]] = []
        silence_start: float | None = None
        silence_regions: list[dict[str, float]] = []
        peak_dbfs = -120.0
        for frame_start in range(0, total_frames, window_frames):
            frame_count = min(window_frames, total_frames - frame_start)
            raw = wav.readframes(frame_count)
            samples = array("h")
            samples.frombytes(raw)
            if samples.itemsize != 2:
                raise PipelineError("Unsupported host sample representation")
            if struct.pack("=h", 1) != struct.pack("<h", 1):
                samples.byteswap()
            if not samples:
                continue
            square_sum = sum(int(sample) * int(sample) for sample in samples)
            rms = math.sqrt(square_sum / len(samples))
            dbfs = 20 * math.log10(max(rms / 32768.0, 1e-6))
            local_peak = max(abs(int(sample)) for sample in samples) / 32768.0
            local_peak_dbfs = 20 * math.log10(max(local_peak, 1e-6))
            peak_dbfs = max(peak_dbfs, local_peak_dbfs)
            start = frame_start / sample_rate
            end = (frame_start + frame_count) / sample_rate
            is_silence = dbfs < silence_dbfs
            windows.append({
                "start": round(start, 3),
                "end": round(end, 3),
                "rms_dbfs": round(dbfs, 2),
                "peak_dbfs": round(local_peak_dbfs, 2),
                "silence": is_silence
            })
            if is_silence and silence_start is None:
                silence_start = start
            elif not is_silence and silence_start is not None:
                if start - silence_start >= 0.5:
                    silence_regions.append({"start": round(silence_start, 3), "end": round(start, 3)})
                silence_start = None
        duration = total_frames / sample_rate
        if silence_start is not None and duration - silence_start >= 0.5:
            silence_regions.append({"start": round(silence_start, 3), "end": round(duration, 3)})
    return {
        "duration_seconds": round(duration, 3),
        "window_seconds": window_seconds,
        "silence_threshold_dbfs": silence_dbfs,
        "peak_dbfs": round(peak_dbfs, 2),
        "windows": windows,
        "silence_regions": silence_regions,
        "note": "Energy-based silence candidates only; quiet speech and meaningful pauses require human/context review."
    }


def _transcribe(wav_path: Path, model_size: str, device: str, language: str | None) -> dict[str, Any]:
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise PipelineError("ASR requires the optional audio extra: pip install -e '.[audio]'") from exc

    from .resources import choose_inference_device, resource_snapshot

    snapshot = resource_snapshot()
    try:
        selected_device, selected_compute, selection_notes = choose_inference_device(
            model_size, requested=device, snapshot=snapshot
        )
    except RuntimeError as exc:
        raise PipelineError(str(exc)) from exc

    attempts = [(selected_device, selected_compute)]
    if device == "auto" and selected_device == "cuda":
        try:
            cpu_device, cpu_compute, _ = choose_inference_device(
                model_size, requested="cpu", snapshot=snapshot
            )
            attempts.append((cpu_device, cpu_compute))
        except RuntimeError:
            selection_notes.append("CPU fallback skipped because available RAM is below the model reserve.")

    last_error: Exception | None = None
    for attempt_index, (candidate_device, compute_type) in enumerate(attempts):
        model = None
        try:
            model = WhisperModel(model_size, device=candidate_device, compute_type=compute_type)
            segments_iter, info = model.transcribe(
                str(wav_path),
                language=language,
                beam_size=5,
                word_timestamps=True,
                vad_filter=True,
                vad_parameters={"min_silence_duration_ms": 500, "speech_pad_ms": 200},
                condition_on_previous_text=False
            )
            # Materialize the generator inside the try block: CUDA can initialize
            # successfully and still fail later when the first inference runs.
            segments = []
            words = []
            for segment in segments_iter:
                segment_words = []
                for word in (segment.words or []):
                    item = {
                        "text": word.word,
                        "start": round(float(word.start), 3),
                        "end": round(float(word.end), 3),
                        "probability": round(float(word.probability), 4) if word.probability is not None else None
                    }
                    words.append(item)
                    segment_words.append(item)
                segments.append({
                    "id": len(segments),
                    "text": segment.text.strip(),
                    "start": round(float(segment.start), 3),
                    "end": round(float(segment.end), 3),
                    "avg_logprob": round(float(segment.avg_logprob), 4),
                    "no_speech_prob": round(float(segment.no_speech_prob), 4),
                    "words": segment_words
                })
            if candidate_device == "cpu" and selected_device == "cuda":
                selection_notes.append(f"CUDA inference failed; completed the full transcription using CPU {compute_type}.")
            return {
                "status": "completed",
                "model": model_size,
                "device": candidate_device,
                "compute_type": compute_type,
                "resource_snapshot": snapshot,
                "device_selection_notes": selection_notes,
                "language": info.language,
                "language_probability": round(float(info.language_probability), 4),
                "segments": segments,
                "words": words,
                "limitations": [
                    "Word probabilities are model estimates, not calibrated confidence.",
                    "VAD regions are proposals and must not automatically determine edit boundaries.",
                    "Speaker diarization is not implemented; speaker labels are intentionally omitted."
                ]
            }
        except Exception as exc:
            last_error = exc
            if candidate_device != "cuda" or attempt_index + 1 >= len(attempts):
                break
            selection_notes.append(f"CUDA initialization or inference failed ({type(exc).__name__}); retrying from the source WAV on CPU.")
            model = None
            import gc
            gc.collect()

    raise PipelineError(f"Could not complete faster-whisper transcription ({device}): {last_error}") from last_error


def analyze_audio(source: Path, model_size: str = "small", device: str = "auto",
                  language: str | None = None, transcribe: bool = True,
                  silence_dbfs: float = -38.0) -> dict[str, Any]:
    source = source.expanduser().resolve(strict=True)
    if not source.is_file():
        raise PipelineError(f"Source is not a regular file: {source}")
    report = probe_media(source)
    source_signature = file_stat_signature(source)
    audio_stream = _audio_stream(report)
    stream_index = int(audio_stream["index"])
    try:
        stream_offset = float(audio_stream.get("start_time") or 0.0)
    except (TypeError, ValueError):
        stream_offset = 0.0

    with tempfile.TemporaryDirectory(prefix="shortform-audio-") as temp:
        wav_path = Path(temp) / "analysis.wav"
        _extract_mono_wav(source, wav_path, stream_index)
        metrics = _window_metrics(wav_path, silence_dbfs=silence_dbfs)
        transcription = (
            _transcribe(wav_path, model_size, device, language)
            if transcribe else {"status": "skipped", "reason": "transcription disabled"}
        )

    def shift_time(item: dict[str, Any]) -> None:
        item["start"] = round(item["start"] + stream_offset, 3)
        item["end"] = round(item["end"] + stream_offset, 3)

    for item in metrics["windows"] + metrics["silence_regions"]:
        shift_time(item)
    if transcription["status"] == "completed":
        for segment in transcription["segments"]:
            shift_time(segment)
            for word in segment["words"]:
                shift_time(word)

    if file_stat_signature(source) != source_signature:
        raise PipelineError("Source media changed during audio analysis; discard this analysis and restart from the new source version")

    return {
        "schema_version": "1.0",
        "source": {
            "path": str(source),
            "fingerprint": report["source"]["fingerprint"],
            "audio_stream_index": stream_index,
            "audio_codec": audio_stream.get("codec_name"),
            "channels": audio_stream.get("channels"),
            "sample_rate": audio_stream.get("sample_rate"),
            "channel_layout": audio_stream.get("channel_layout"),
            "source_time_offset_seconds": stream_offset
        },
        "analysis": {
            "audio_metrics": metrics,
            "transcription": transcription
        }
    }
