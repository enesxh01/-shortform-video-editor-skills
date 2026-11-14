# Shortform Video Editor Skills

A local-first OpenCode skill suite for building and operating a quality-focused short-form video clipping and editing pipeline.

## Project goals

- Analyze long-form source videos and identify self-contained, compelling short-form moments.
- Preserve context, truthful hooks, complete payoffs, and meaningful reactions.
- Produce polished vertical edits for Shorts, Reels, and TikTok.
- Use local, free/open-source tooling wherever practical.
- Prioritize creative quality, source integrity, and verifiable quality control over speed.
- Keep the workflow human-reviewable, recoverable, and resource-aware.

## Non-goals

- No YouTube Analytics, channel-performance ingestion, OAuth, views/retention dashboards, or analytics-driven optimization.
- No automatic background music.
- No automatic B-roll or sound effects unless explicitly requested for a particular edit.
- No promise or guarantee of virality.

## Visual layouts

The editing system supports exactly three primary layouts:

1. **Fullscreen** — vertical 9:16 composition with careful subject-aware reframing and editorial captions.
2. **Vertical split** — two panels stacked top/bottom, never side-by-side; one caption line centered in the divider.
3. **Blurred bars (20/60/20)** — vertical 9:16 composition with a blurred 20% top region, 60% sharp main footage, and blurred 20% bottom region, derived from relevant footage.

Layout changes must be motivated by the content, not used as arbitrary visual variety.

## Skill suite

The repository will contain an orchestrator skill and specialist skills for architecture, media ingestion, audio intelligence, viral-moment detection, visual storytelling, pacing, Kino-style editing, timeline/EDL, rendering, resource management, quality assurance, testing, and project memory.

## Quality policy

A feature is not considered verified merely because code or documentation exists. Verification status must distinguish implemented-and-tested behavior from unverified implementation, partial work, design-only work, and blocked work. Technical QC does not replace human review of the actual exported video.

## Repository status

This repository is being built in stages. See the skill directories and project documentation for current implementation guidance and validation status.
