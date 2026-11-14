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
    normalized = text.replace("\\r\\n", "\\n").replace("\\n", "\n")
    normalized = normalized.replace("\r\\n", "\n").replace("\r", "\n")
    escaped = normalized.replace("\\", "\\\\").replace("{", "\\{").replace("}", "\\}")
    return escaped.replace("\n", r"\N")


def _needs_space(previous: str, current: str) -> bool:
    return bool(previous and current and current[0] not in ".,!?;:%)]}”")


def _karaoke_text(caption: dict[str, Any]) -> str:
    words = caption.get("words") or []
    if not words:
        return _escape_ass(caption["text"])
    pieces = []
    previous_end = timestamp_seconds(caption["start"])
    previous_text = ""
    for word in words:
        start = timestamp_seconds(word["start"])
        end = timestamp_seconds(word["end"])
        if end <= start:
            continue
        if start > previous_end:
            pieces.append(f"{{\\k{max(1, round((start - previous_end) * 100))}}}")
        duration = max(1, round((end - start) * 100))
        token = str(word["text"]).strip()
        if _needs_space(previous_text, token):
            pieces.append(" ")
        pieces.append(f"{{\\kf{duration}}}{_escape_ass(token)}")
        previous_text = token
        previous_end = end
    return "".join(pieces) if pieces else _escape_ass(caption["text"])


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
        "WrapStyle: 0", "ScaledBorderAndShadow: yes", "",
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
            alignment_tag = r"\an5"
        elif position == "bottom":
            alignment_tag = r"\an2"
        else:
            alignment_tag = r"\an5" if layout == "split_vertical" else r"\an2"
        if layout in {"split_vertical", "blurred_bars_20_60_20"}:
            available_width = 940
            scale = min(100, max(55, int(available_width / max(1, len(caption["text"])) / font_size * 100 / 0.55)))
            override = "{" + alignment_tag + r"\q2\fscx" + str(scale) + "}"
        else:
            override = "{" + alignment_tag + "}"
        text = _karaoke_text(caption)
        lines.append(
            f"Dialogue: 0,{_ass_time(start)},{_ass_time(end)},Default,,0,0,0,,{override}{text}"
        )
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output_path


def ffmpeg_subtitles_filter(path: Path) -> str:
    escaped = str(path.resolve()).replace("\\", "/").replace(":", r"\:").replace("'", r"\'")
    return f"subtitles=filename='{escaped}'"
