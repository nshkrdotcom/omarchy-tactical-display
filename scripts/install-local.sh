#!/usr/bin/env bash
set -euo pipefail

PLUGIN_ID="nshkr.tactical-display"
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
DEST="${XDG_CONFIG_HOME:-$HOME/.config}/omarchy/plugins/$PLUGIN_ID"

if [[ -e "$DEST" ]]; then
  printf 'Refusing to overwrite existing plugin: %s\n' "$DEST" >&2
  printf 'Remove it explicitly first if you intend to replace it.\n' >&2
  exit 1
fi

mkdir -p "$(dirname -- "$DEST")"
cp -a "$ROOT" "$DEST"
rm -rf "$DEST/.git" "$DEST/.pytest_cache" "$DEST/__pycache__" "$DEST/tests/__pycache__"

if command -v omarchy-shell >/dev/null 2>&1; then
  omarchy-shell shell rescanPlugins || true
fi
if command -v omarchy >/dev/null 2>&1; then
  omarchy plugin enable "$PLUGIN_ID"
fi

printf 'Installed local copy at %s\n' "$DEST"
printf 'Try: omarchy-shell shell summon %s '\''{"instrument":"radar"}'\''\n' "$PLUGIN_ID"
