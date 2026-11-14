---
name: kino-editing
description: Apply restrained premium editorial styling, readable captions, purposeful motion, and the project's three approved vertical layouts.
---

# Kino Editing

Create polished, modern editorial short-form videos. Restraint and readability beat visual noise.

## Executable caption baseline

Generate word-timed caption groups with `shortform-editor generate-captions audio-analysis.json candidates.json -o captions.json --layout fullscreen`. Add the resulting caption array to the selected EDL segment before approval and rendering. The renderer burns ASS/libass captions with outlined bold typography and optional word-level karaoke highlighting. Split captions are centered; fullscreen and blurred-bars captions use bottom placement by default.

This is the initial static/Karaoke baseline only. Per-word scale/position animation, custom font packaging, advanced emphasis rules and typography preview are not implemented. Fullscreen drafts with face-analysis evidence can conservatively move captions between top and bottom safe areas; this does not detect HUDs or arbitrary objects. Review spelling and timing against the source.

## Captions

- Use accurate, speech-synchronized captions. Verify hook/payoff wording against audio.
- Fullscreen: up to three lines with clear hierarchy.
- Vertical split: exactly one caption line centered in the divider; EDL validation rejects explicit positions that move it away from the divider.
- Blurred-bars layout: exactly one caption line, positioned safely over the sharp main composition (never in the blurred top/bottom bars).
- Use premium sans-serif typography with selective italic serif accents only when they improve emphasis.
- Highlight important words through text styling/color, not colored boxes. Do not make every highlight red.
- Use consistent baseline, line spacing, margins, and safe areas.
- Animate with subtle scale/position/fade synchronized to speech. Avoid bouncing every word or distracting karaoke effects.
- Never cover faces, key objects, gameplay HUD, or important source text.

## Motion

Use subtle push-ins, pull-outs, or drift only when they add emphasis or maintain visual interest. Starting ranges (not rigid presets):
- normal framing: 100–110%;
- emphasis: 110–118%;
- strong emphasis: 118–125%.

Use gradual moves around 0.8–1.5 s and quicker punch-ins around 0.4–0.7 s only when motivated. Use smooth easing. Avoid cropping beyond source bounds or hiding context. Motion blur is optional and subtle.

## Transitions and optional effects

- Use hard cuts by default.
- Transitions must be motivated by a scene/story transition.
- No background music by default.
- No B-roll or sound effects unless explicitly requested.
- Do not add decorative effects merely to make the edit appear busy.

## Three layouts only

1. `fullscreen`: subject-aware 9:16 crop; up to three caption lines.
2. `split_vertical`: two stacked top/bottom panels, never side-by-side; one caption line centered in divider; synchronize sources.
3. `blurred_bars_20_60_20`: blurred 20% top, sharp 60% center, blurred 20% bottom; blur from relevant footage.

Run safe-area and readability checks at phone-size preview dimensions.


## Color correction and sharpening

- Apply restrained, source-aware color correction only when it improves consistency or readability. The EDL supports bounded per-segment `brightness` (-0.2 to 0.2), `contrast` (0.5–2.0), `saturation` (0–2.0), and `gamma` (0.5–2.0).
- Sharpening is optional and bounded (0–1.5). Use a low amount (typically 0.2–0.5) only when the source is genuinely soft; do not sharpen compression noise, ringing, skin texture, or already-crisp footage.
- Defaults are neutral and sharpening is off. Never apply a one-size-fits-all grade to every source. Avoid clipping highlights/shadows or oversaturating skin.
- This is deterministic FFmpeg correction, not scene-referred color management, RAW grading, LUT emulation, or a calibrated display workflow. Inspect representative frames before final approval.


## Caption safe areas and motion presets

The EDL supports per-caption `font_name` (safe name for a font already installed on the rendering system), `font_size` (28–100), vertical safe-area margin `margin_v` (0–600), and optional `animation` (`none`, `fade`, `pop`, `pop_fade`). Keep split-layout captions centered and single-line in the divider. A requested font must already be installed on the machine rendering the video; font files are not bundled or redistributed. For fullscreen, choose a bottom margin that clears platform UI and faces; inspect at phone size. Use short, restrained pop/fade entrances only when they help emphasis; avoid animating every word or causing jitter. Defaults preserve the existing static/Kino treatment.
