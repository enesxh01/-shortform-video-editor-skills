---
name: audio-intelligence
description: Analyze source audio for transcription, word timing, speech regions, speaker-turn evidence, and useful delivery cues while preserving uncertainty and meaningful pauses.
---

# Audio Intelligence

## Pipeline

1. Probe audio streams, channels, sample rates, layouts, offsets, and duration.
2. Preserve the original audio. Create analysis copies (typically mono 16 kHz PCM WAV) with documented channel/downmix decisions.
3. If channels contain distinct microphones, inspect them separately before downmixing.
4. Run ASR with word-level timestamps. Benchmark compatible faster-whisper model sizes/variants on available hardware; use GPU acceleration when supported and fall back cleanly when memory is constrained.
5. Use conservative VAD to locate likely speech regions. VAD is not an instruction to cut pauses.
6. Speaker diarization is optional and must be explicitly configured with model access/license checks. If unavailable, return unknown speaker labels rather than inventing identities.
7. Detect useful cues such as laughter, long pauses, overlap, clipping, and delivery changes. Treat emotional labels as uncertain interpretations, never facts.

## Output

Return transcript segments and words with:
- text, start/end, time base, speaker ID or unknown;
- ASR confidence where available;
- language/code-switch notes;
- overlap and uncertainty flags;
- VAD regions and detected audio events;
- source stream and channel provenance.

## Accuracy rules

- Preserve original timestamps and map analysis timestamps back to source time.
- Never infer a person's identity from voice.
- Do not silently normalize or denoise source audio in a way that changes meaning.
- Keep names, numbers, slang, and non-English speech under review when confidence is low.
- ASR output is evidence; inspect critical hook/payoff words against audio before finalizing captions.

## Testing

Test clean single-speaker audio, multiple speakers, overlapping speech, laughter, meaningful pauses, noisy livestreams, non-English/code-switching, proper names, long quiet recordings, clipping, and low-volume speech. Track WER where reference transcripts exist, timestamp drift, VAD false positives/negatives, diarization errors, runtime, RAM, and VRAM.

## Resource policy

Load one large model at a time unless measured resources justify concurrency. Record model name/version, compute type, device, settings, and fallback. Never claim GPU use without verifying it.
