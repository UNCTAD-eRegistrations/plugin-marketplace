#!/usr/bin/env bash
# Sync skills from skills/ into the service-documentation plugin.
# Run after updating any skill in skills/.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SKILLS_DIR="$REPO_ROOT/skills"
PLUGIN_SKILLS="$REPO_ROOT/plugins/service-documentation/skills"

for skill in service-manual service-manual-all eregistrations-docs; do
  src="$SKILLS_DIR/$skill/SKILL.md"
  dst="$PLUGIN_SKILLS/$skill/SKILL.md"
  if [ -f "$src" ]; then
    cp "$src" "$dst"
    echo "Synced: $skill"
  else
    echo "WARNING: $src not found"
  fi
done

echo "Done. service-documentation skills are up to date."
