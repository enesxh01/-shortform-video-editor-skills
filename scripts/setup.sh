#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEST="${1:-$HOME/.config/opencode/skills}"
PYTHON="${PYTHON:-python3}"

if ! command -v "$PYTHON" >/dev/null 2>&1; then
  echo "Python 3.10+ was not found. Install Python and rerun this script." >&2
  exit 2
fi

echo "Installing the shortform-editor CLI and audio/visual/download extras..."
"$PYTHON" -m pip install --upgrade pip
"$PYTHON" -m pip install -e "${ROOT}[audio,visual,download]"

echo "Installing OpenCode skills..."
bash "$ROOT/scripts/install.sh" "$DEST"

if ! command -v ffmpeg >/dev/null 2>&1 || ! command -v ffprobe >/dev/null 2>&1; then
  echo "The CLI and skills are installed, but FFmpeg and ffprobe are required before rendering." >&2
  if command -v apt-get >/dev/null 2>&1; then
    echo "On Debian/Ubuntu: sudo apt-get update && sudo apt-get install -y ffmpeg" >&2
  elif command -v brew >/dev/null 2>&1; then
    echo "On macOS with Homebrew: brew install ffmpeg" >&2
  else
    echo "Install an FFmpeg build that includes ffprobe, libx264 (or NVENC), and the subtitles filter, then ensure both executables are on PATH." >&2
  fi
  exit 1
fi

echo "Running the environment doctor..."
"$PYTHON" -m shortform_editor.cli doctor
echo "Setup complete. Reload OpenCode if it does not discover the installed skills."
