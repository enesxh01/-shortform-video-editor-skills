#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEST="${1:-$HOME/.config/opencode/skills}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
STAGE="$(mktemp -d "${TMPDIR:-/tmp}/shortform-skills.XXXXXX")"
BACKUP="$DEST/.shortform-backups/$STAMP"

cleanup() { rm -rf "$STAGE"; }
trap cleanup EXIT

mkdir -p "$DEST" "$BACKUP"

# Stage every skill before touching the installation.
for skill_dir in "$ROOT"/*; do
  [[ -d "$skill_dir" && -f "$skill_dir/SKILL.md" ]] || continue
  skill_name="$(basename "$skill_dir")"
  cp -a "$skill_dir" "$STAGE/$skill_name"
done

# Package shared references inside each skill that explicitly uses them.
if [[ -f "$ROOT/references/viral-scoring.md" ]]; then
  mkdir -p "$STAGE/shortform-video-editor/references" "$STAGE/viral-moment-detection/references"
  cp "$ROOT/references/viral-scoring.md" "$STAGE/shortform-video-editor/references/"
  cp "$ROOT/references/viral-scoring.md" "$STAGE/viral-moment-detection/references/"
fi
if [[ -f "$ROOT/references/export-and-fps.md" ]]; then
  mkdir -p "$STAGE/shortform-video-editor/references" "$STAGE/ffmpeg-rendering/references"
  cp "$ROOT/references/export-and-fps.md" "$STAGE/shortform-video-editor/references/"
  cp "$ROOT/references/export-and-fps.md" "$STAGE/ffmpeg-rendering/references/"
fi
if [[ -f "$ROOT/schemas/edit-decision-list.schema.json" ]]; then
  mkdir -p "$STAGE/edit-decision-list/schemas"
  cp "$ROOT/schemas/edit-decision-list.schema.json" "$STAGE/edit-decision-list/schemas/"
fi
if [[ -f "$ROOT/config/project-defaults.json" ]]; then
  mkdir -p "$STAGE/shortform-video-editor/config"
  cp "$ROOT/config/project-defaults.json" "$STAGE/shortform-video-editor/config/"
fi

# Keep a timestamped backup instead of deleting an existing skill installation.
for staged_skill in "$STAGE"/*; do
  [[ -d "$staged_skill" ]] || continue
  skill_name="$(basename "$staged_skill")"
  target="$DEST/$skill_name"
  if [[ -e "$target" ]]; then
    mkdir -p "$BACKUP"
    mv "$target" "$BACKUP/$skill_name"
  fi
  mv "$staged_skill" "$target"
done

echo "Installed OpenCode skills to: $DEST"
if [[ -d "$BACKUP" ]] && find "$BACKUP" -mindepth 1 -print -quit | grep -q .; then
  echo "Previous versions backed up to: $BACKUP"
fi
echo "Reload OpenCode if the skills are not discovered."
