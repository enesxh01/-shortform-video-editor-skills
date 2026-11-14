# Third-Party Notices and Licensing

This file records the current intended runtime choices. It is not a substitute for checking the exact package versions, wheel metadata, model cards and binary build flags used in a release.

## Runtime components

| Component | Use | Upstream license / obligations | Distribution note |
|---|---|---|---|
| faster-whisper | Optional ASR adapter | MIT; retain copyright and license notice | Installed as an optional Python extra; code is not vendored. |
| CTranslate2 | faster-whisper inference runtime | MIT; retain copyright and license notice | Transitive dependency; exact installed version should be captured in an SBOM. |
| OpenCV 4.10+ headless | Optional frame sampling and Haar face detection | Apache-2.0 for OpenCV 4.5+ | Installed as an optional Python extra; not vendored. |
| OpenCV frontal-face Haar cascade | Frontal-face detector data shipped with OpenCV | Cascade XML contains an Intel License Agreement with BSD-style attribution, redistribution and non-endorsement conditions | Preserve the asset's complete license notice when redistributing the cascade or a binary containing it. |
| PyAV / NumPy / tokenizers / Hugging Face Hub / ONNX Runtime | Transitive faster-whisper dependencies | Common upstream licenses include BSD-3-Clause, Apache-2.0 and MIT; verify each exact installed package | Generate a dependency license report before packaging a standalone build. |
| FFmpeg | Media probing, extraction, rendering and QC | LGPL-2.1+ or GPL depending on build configuration and enabled components | The project expects a separately installed FFmpeg; it does not bundle FFmpeg binaries. Check `ffmpeg -L` and build configuration before redistribution. |
| libass | ASS caption rendering through FFmpeg subtitles filter | Separate upstream license; inherited through the user's FFmpeg build | The project does not bundle libass. Captions require an FFmpeg build with the subtitles/libass filter. |

## Model weights

- faster-whisper downloads model weights from the Hugging Face Hub at first use; weights are not included in this repository.
- The default `small` model is selected by name through faster-whisper. Confirm the exact repository/model card and license at download time.
- Do not assume that all alternative, distilled, fine-tuned or community models share the same license as the software runtime.
- No diarization, object-detection or segmentation model weights are currently bundled or selected.

## Project license

The repository currently has no root `LICENSE` file. The owner must choose a license before others can safely assume rights to reuse, modify, redistribute or commercialize the project's own code and skill prompts. Do not add a permissive license without the owner's explicit choice.

## Release checklist

1. Generate an SBOM and exact dependency license inventory for the release environment.
2. Preserve MIT, Apache, BSD and model-specific notices as required.
3. Verify the exact OpenCV Haar cascade notice shipped in the selected wheel.
4. Inspect FFmpeg and libass build configuration; do not redistribute GPL-enabled binaries unintentionally.
5. Check model-card terms for every downloaded weight set.
6. Add the owner's chosen root project license.
