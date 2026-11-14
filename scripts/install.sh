#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEST="${1:-$HOME/.config/opencode/skills}"

mkdir -p "$DEST"
for skill_dir in "$ROOT"/*; do
  [[ -d "$skill_dir" && -f "$skill_dir/SKILL.md" ]] || continue
  skill_name="$(basename "$skill_dir")"
  rm -rf "$DEST/$skill_name"
  cp -R "$skill_dir" "$DEST/$skill_name"
  echo "Installed $skill_name"
done

RUNTIME_SOURCE="$ROOT/shortform_editor"
SKILL_RUNTIME="$DEST/shortform-video-editor/runtime"
if [[ -d "$RUNTIME_SOURCE" ]]; then
  mkdir -p "$SKILL_RUNTIME"
  cp -R "$RUNTIME_SOURCE"/. "$SKILL_RUNTIME"/
  echo "Installed shortform editor runtime"
fi

echo "OpenCode skills installed to: $DEST"
echo "Restart/reload OpenCode if the new skills are not discovered."
