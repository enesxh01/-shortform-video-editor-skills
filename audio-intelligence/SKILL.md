---
name: audio-intelligence
description: Analyze source audio for transcription, word timing, speech regions, speaker-turn evidence, and useful delivery cues while preserving uncertainty and meaningful pauses.
---

# Audio Intelligence

## Executable implementation

The repository CLI now provides `shortform-editor analyze-audio SOURCE -o audio-analysis.json`.
Install ASR support with `python -m pip install -e ".[audio]"`. The default is the small faster-whisper model, with automatic CUDA int8_float16 attempt and CPU int8 fallback. Use `--no-transcribe` for deterministic energy/silence analysis without model downloads. Model weights are downloaded by faster-whisper on first use and are not bundled with this repository.

This is a first usable audio pass, not full audio intelligence: diarization, overlap detection, laughter classification, emotion/delivery classification, multi-microphone separation, and audio/video synchronization QC remain unimplemented. Silence windows are evidence only and never create edit cuts automatically.

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

- Default to `small` rather than loading a large model on a 16 GB RAM desktop.
- Run one transcription model at a time. The default `auto` mode tries CUDA and falls back to CPU; the report records the actual selected device and compute type.
- If CUDA initialization fails, check the installed NVIDIA driver, CUDA 12.x runtime, cuBLAS and the cuDNN version supported by the installed CTranslate2/faster-whisper release before concluding the GPU is unsupported. The upstream faster-whisper documentation currently describes CUDA 12 with cuDNN 9; verify the exact dependency combination because CTranslate2 release requirements can differ.
- faster-whisper and CTranslate2 are MIT-licensed software; the selected Whisper model card/weight terms and any future VAD/diarization models must still be checked before redistribution.

Load one large model at a time unless measured resources justify concurrency. Record model name/version, compute type, device, settings, and fallback. Never claim GPU use without verifying it.
