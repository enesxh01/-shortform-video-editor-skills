from __future__ import annotations

from pathlib import Path
import re
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
        highlight = word.get("highlight_color")
        if highlight is not None:
            if not isinstance(highlight, str) or not re.fullmatch(r"#[0-9A-Fa-f]{6}", highlight):
                raise PipelineError("Word highlight_color must be a #RRGGBB hex color")
            red, green, blue = highlight[1:3], highlight[3:5], highlight[5:7]
            pieces.append(r"{\c&H00" + blue + green + red + "&}")
        pieces.append(f"{{\\kf{duration}}}{_escape_ass(token)}")
        if highlight is not None:
            pieces.append(r"{\c}")
        previous_text = token
        previous_end = end
    return "".join(pieces) if pieces else _escape_ass(caption["text"])


def apply_face_aware_caption_positions(captions: list[dict[str, Any]],
                                     visual_samples: list[dict[str, Any]],
                                     source_width: int, source_height: int) -> list[dict[str, Any]]:
    """Move fullscreen captions away from detected/tracked faces when evidence is available.

    Coordinates are transformed from source-frame normalized boxes into each 9:16 crop.
    Ambiguous or conflicting evidence leaves the caption at its normal automatic position.
    """
    if source_width <= 0 or source_height <= 0:
        return [dict(caption) for caption in captions]
    positioned = []
    for caption in captions:
        item = dict(caption)
        if item.get("position", "auto") != "auto":
            positioned.append(item)
            continue
        start = timestamp_seconds(caption["start"])
        end = timestamp_seconds(caption["end"])
        top_collisions = 0
        bottom_collisions = 0
        for sample in visual_samples:
            sample_time = float(sample.get("time_seconds", -1))
            box = sample.get("subject_bbox_normalized")
            crop = sample.get("crop_9_16")
            if not (start <= sample_time <= end) or not isinstance(box, dict) or not isinstance(crop, dict):
                continue
            crop_width = float(crop.get("width", 0))
            crop_height = float(crop.get("height", 0))
            if crop_width <= 0 or crop_height <= 0:
                continue
            x1 = (float(box.get("x", 0)) * source_width - float(crop.get("x", 0))) / crop_width
            y1 = (float(box.get("y", 0)) * source_height - float(crop.get("y", 0))) / crop_height
            x2 = x1 + float(box.get("width", 0)) * source_width / crop_width
            y2 = y1 + float(box.get("height", 0)) * source_height / crop_height
            if x2 <= 0.08 or x1 >= 0.92:
                continue
            if y1 < 0.24 and y2 > 0.06:
                top_collisions += 1
            if y2 > 0.76 and y1 < 0.94:
                bottom_collisions += 1
        if bottom_collisions > top_collisions:
            item["position"] = "top"
            item["position_reason"] = "face_overlap_with_lower_caption_safe_area"
        elif top_collisions > bottom_collisions:
            item["position"] = "bottom"
            item["position_reason"] = "face_overlap_with_upper_caption_safe_area"
        positioned.append(item)
    return positioned


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
        elif position == "top":
            alignment_tag = r"\an8"
        else:
            alignment_tag = r"\an5" if layout == "split_vertical" else r"\an2"
        caption_font_size = int(caption.get("font_size", font_size))
        if not 28 <= caption_font_size <= 100:
            raise PipelineError("Caption font_size must be between 28 and 100")
        font_name = str(caption.get("font_name", "Arial"))
        if not re.fullmatch(r"[A-Za-z0-9 _-]{1,64}", font_name):
            raise PipelineError("Caption font_name must contain only letters, numbers, spaces, underscores or hyphens (1-64 characters)")
        caption_margin_v = int(caption.get("margin_v", margin_v))
        if not 0 <= caption_margin_v <= 600:
            raise PipelineError("Caption margin_v must be between 0 and 600")
        if layout in {"split_vertical", "blurred_bars_20_60_20"}:
            available_width = 940
            scale = min(100, max(55, int(available_width / max(1, len(caption["text"])) / caption_font_size * 100 / 0.55)))
        else:
            scale = 100
        tags = [alignment_tag]
        if layout in {"split_vertical", "blurred_bars_20_60_20"}:
            tags.append(r"\q2")
            tags.append(r"\fscx" + str(scale))
        if caption_font_size != font_size:
            tags.append(r"\fs" + str(caption_font_size))
        if font_name != "Arial":
            tags.append(r"\fn" + font_name)
        animation = caption.get("animation", "none")
        if animation not in {"none", "fade", "pop", "pop_fade"}:
            raise PipelineError(f"Unsupported caption animation: {animation}")
        if animation in {"pop", "pop_fade"}:
            tags.extend([
                r"\fscx" + str(max(1, round(scale * 0.9))), r"\fscy90",
                r"\t(0,140,\fscx" + str(scale) + r"\fscy100)"
            ])
        if animation in {"fade", "pop_fade"}:
            tags.append(r"\fad(90,80)")
        override = "{" + "".join(tags) + "}"
        text = _karaoke_text(caption)
        lines.append(
            f"Dialogue: 0,{_ass_time(start)},{_ass_time(end)},Default,,0,0,{caption_margin_v},,{override}{text}"
        )

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output_path


def ffmpeg_subtitles_filter(path: Path) -> str:
    escaped = str(path.resolve()).replace("\\", "/").replace(":", r"\:").replace("'", r"\'")
    return f"subtitles=filename='{escaped}'"
