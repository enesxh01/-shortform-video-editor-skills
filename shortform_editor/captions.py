from __future__ import annotations

from pathlib import Path
from typing import Any

from .cli import PipelineError, timestamp_seconds


def _ass_time(seconds: float) -> str:
    centiseconds = max(0, round(seconds * 100))
    hours, remainder = divmod(centiseconds, 360000)
    minutes, remainder = divmod(remainder, 6000)
    secs, cs = divmod(remainder, 100)
    return f"{hours}:{minutes:02d}:{secs:02d}.{cs:02d}"


def _escape_ass(text: str) -> str:
    return text.replace("\\", "\\\\").replace("{", "\\{").replace("}", "\\}")


def _karaoke_text(caption: dict[str, Any], clip_start: float) -> str:
    words = caption.get("words") or []
    if not words:
        return _escape_ass(caption["text"])
    pieces = []
    previous_end = None
    for word in words:
        start = timestamp_seconds(word["start"])
        end = timestamp_seconds(word["end"])
        if end <= start:
            continue
        duration = max(1, round((end - start) * 100))
        if previous_end is not None and start > previous_end:
            pieces.append(" ")
        pieces.append(f"{{\\kf{duration}}}{_escape_ass(word['text'])}")
        previous_end = end
    return " ".join(pieces) if pieces else _escape_ass(caption["text"])


def write_ass_subtitles(segment: dict[str, Any], layout: str, clip_start: float,
                        output_path: Path) -> Path | None:
    captions = segment.get("captions", [])
    if not captions:
        return None
    if layout == "split_vertical":
        font_size, margin_v, alignment = 48, 0, 5
    elif layout == "blurred_bars_20_60_20":
        font_size, margin_v, alignment = 58, 480, 2
    else:
        font_size, margin_v, alignment = 68, 250, 2

    lines = [
        "[Script Info]", "ScriptType: v4.00+", "PlayResX: 1080", "PlayResY: 1920",
        "WrapStyle: 2", "ScaledBorderAndShadow: yes", "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        f"Style: Default,Arial,{font_size},&H00FFFFFF,&H0000D7FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,5,2,{alignment},70,70,{margin_v},1",
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"
    ]
    for caption in captions:
        start = timestamp_seconds(caption["start"]) - clip_start
        end = timestamp_seconds(caption["end"]) - clip_start
        if end <= start:
            raise PipelineError("Caption end must be after caption start")
        position = caption.get("position", "auto")
        if position == "center":
            override = r"{\an5}"
        elif position == "bottom":
            override = r"{\an2}"
        else:
            override = r"{\an5}" if layout == "split_vertical" else r"{\an2}"
        text = _karaoke_text(caption, clip_start)
        lines.append(
            f"Dialogue: 0,{_ass_time(start)},{_ass_time(end)},Default,,0,0,0,,{override}{text}"
        )
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output_path


def ffmpeg_subtitles_filter(path: Path) -> str:
    escaped = str(path.resolve()).replace("\\", "/").replace(":", r"\:").replace("'", r"\'")
    return f"subtitles=filename='{escaped}'"
