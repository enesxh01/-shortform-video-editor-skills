# Semantic Candidate Review Procedure

Use the OpenCode model as a second editorial pass after the executable heuristic. This is reasoning over transcript evidence, not a learned virality predictor.

## Inputs

- `audio-analysis.json`: source fingerprint, timestamped transcript segments/words and audio metrics.
- `candidates.json`: heuristic proposals and their score breakdown.
- `visual-analysis.json`, only if present: sampled frame differences and frontal-face evidence. Never infer visual actions from transcript text alone.
- The source video itself, if the user has made it available for review.

## Full-transcript scan

1. Confirm the SHA-256 source fingerprint is identical across the analysis files.
2. Read the transcript in chronological chunks of about 3 minutes with 20 seconds of overlap. Keep exact source timestamps from transcript segments.
3. In each chunk, look for a complete question/answer, reveal, reversal, emotional reaction, demonstration, joke setup/payoff, disagreement, useful explanation or transformation.
4. Propose a candidate only when the transcript supplies enough setup and a complete payoff. Include a small amount of preceding/following context for review.
5. Use existing segment/word timestamps to set boundaries. Never invent or interpolate a timestamp that is not supported by transcript evidence.
6. Compare semantic proposals with the heuristic candidate list. Keep both high-scoring heuristic moments and strong semantic moments the heuristic missed.
7. Deduplicate overlapping proposals and reject candidates that require misleading edits or remove context.

## Evidence-based review record

For every kept candidate, record:
- source fingerprint, start/end time and exact transcript excerpt;
- candidate family;
- hook, setup, progression, payoff and ending;
- evidence-backed rubric score with a short reason for each category;
- confidence label: high / medium / low, with uncertainty;
- risk flags: missing context, ambiguous speaker, privacy, unclear audio, weak payoff, misleading framing;
- alternative start/end boundaries when uncertain.

Do not call the score a probability of views or virality. Do not invent audience response. Quiet moments can outrank loud moments.

## Output

Write a review JSON beside the baseline report using `schemas/semantic-review.schema.json` and with:
- `source_fingerprint`;
- `baseline_candidate_ids`;
- `semantic_candidates`;
- `rejected_candidates` with concise reasons;
- `final_ranked_candidates` with score breakdown and confidence label.

Validate the completed file with `shortform-editor validate-semantic-review review.json --probe probe.json --candidates candidates.json`. The validator checks schema, source fingerprint, timestamp bounds, score totals and ranking references. If invalid, correct the JSON rather than bypassing validation. For a semantic-only candidate selected for editing, create a candidate JSON record using its exact `candidate_id`, `source_fingerprint`, `source_in_seconds` and `source_out_seconds`, run `shortform-editor generate-captions audio-analysis.json semantic-candidate.json -o semantic-captions.json`, then create an EDL draft with the matching source fingerprint and `approval.status=draft`; validate it before human review. Never auto-approve. If the transcript is too long for the available model context, process more chunks; do not silently skip the end of the recording. If no strong moments exist, say so.
