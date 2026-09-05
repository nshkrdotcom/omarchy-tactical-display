#!/usr/bin/env bash
# Explicit create-only local install; never execute this as an install hook.
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET="$HOME/.config/omarchy/plugins/nshkr.tactical-display"
if [[ $# != 0 ]]; then printf 'Usage: %s (create-only; existing installs use the overlay handoff)\n' "$0" >&2; exit 2; fi
python3 - "$ROOT" "$TARGET" <<'PY'
import json,os,shutil,sys
from pathlib import Path
src,dst=map(Path,sys.argv[1:])
if json.loads((src/'manifest.json').read_text())['id']!='nshkr.tactical-display':raise SystemExit('Wrong repository')
if dst.exists() or dst.is_symlink():raise SystemExit('Refusing to overwrite an existing install; use docs/HANDOFF.md overlay steps.')
if any(p.is_symlink() for p in src.rglob('*')):raise SystemExit('Refusing source symlinks')
for p in dst.parents:
    if p.is_symlink():raise SystemExit('Refusing destination symlink ancestor')
dst.parent.mkdir(parents=True,exist_ok=True)
shutil.copytree(src,dst,ignore=shutil.ignore_patterns('.git','__pycache__','*.pyc','*.zip','.pytest_cache'))
print('Created '+str(dst))
PY
printf '\nNext, explicitly run:\n  omarchy plugin validate "%s"\n  omarchy-shell shell rescanPlugins\n  omarchy plugin enable nshkr.tactical-display\n' "$TARGET"
printf 'Native enablement may place the widget according to Omarchy defaults; this helper does not edit shell.json.\n'
