---
name: viral-moment-detection
description: Find and rank genuinely compelling, context-complete short-form moments across the full source video without relying on simplistic loudness or keyword heuristics.
---

# Viral Moment Detection

Find moments people may want to keep watching and share. Do not promise virality. The goal is editorial quality, not a guaranteed outcome.

## Analyze the whole recording

- Search the full timeline, including quiet sections and later segments.
- Generate candidates from transcript structure, semantic shifts, questions, answers, story beats, reactions, scene/action changes, and audio/visual cues.
- Loudness, profanity, fast speech, laughter, movement, and cuts are supporting signals only.
- A quiet revelation, funny pause, useful explanation, emotional reaction, or visual payoff may be stronger than a loud outburst.
- Keep enough preceding and following context to understand what happened.

## Candidate families

- curiosity, surprise, and revelation;
- emotion and human connection;
- comedy with setup, escalation, and punchline;
- conflict, disagreement, and debate;
- useful knowledge or a clear explanation;
- story, transformation, and before/after;
- visual action, skill, or demonstration.

Do not force equal representation across categories. Do not invent categories to fill a quota.

## Scoring

Use the weighted 100-point rubric in `references/viral-scoring.md`. Scores are editorial estimates, not objective probabilities. Include evidence for every score and confidence in the candidate's interpretation.

## Boundary selection

- Opening: start as close as possible to the compelling hook without making the viewer confused.
- Setup: include only the context needed to understand the moment.
- Progression: preserve escalation, turn-taking, demonstration, and cause/effect.
- Payoff: include the full answer, joke, reveal, result, or reaction.
- Ending: leave a clean finish; do not cut off the key word, response, or emotional beat.
- Tighten only non-contributing silence, repetition, or tangents. Preserve meaningful pauses.
- Do not impose one universal duration. Let the moment determine its length, subject to user/platform constraints.

## Candidate report

For each candidate include:
- stable candidate ID and source identity;
- source in/out timestamps and time base;
- candidate family and concise description;
- opening hook and why it works;
- setup/context required;
- payoff and whether it is complete;
- score breakdown and total;
- confidence and uncertainty;
- risks: misleading framing, missing context, privacy, inaudible speech, visual ambiguity, repeated content;
- boundary alternatives if uncertain.

## Rejection rules

Reject or flag moments with missing context, no payoff, misleading hook, repetition, filler, unintelligible key audio, privacy concerns, incomplete demonstration, or a cut that changes meaning. Do not lower thresholds just to produce more clips. If none qualify, report that honestly.

## Source-specific strategy

Adapt evidence collection to podcasts/interviews, livestreams/gaming, tutorials/education, sports, commentary/debate, and storytime/documentary. Never assume a single content genre.
