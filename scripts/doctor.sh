#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
printf 'Tactical Display 1.0.0-rc.1 / read-only environment inventory\n'
printf 'Repository: %s\nKernel: ' "$ROOT"; uname -sr
python3 --version
for tool in omarchy omarchy-shell quickshell hyprctl pw-dump wpctl node; do
  if command -v "$tool" >/dev/null 2>&1; then printf 'AVAILABLE %-16s %s\n' "$tool" "$(command -v "$tool")"; else printf 'NOT RUN   %-16s not installed\n' "$tool"; fi
done
if command -v qmllint >/dev/null 2>&1; then qmllint --version
elif [[ -x /usr/lib/qt6/bin/qmllint ]]; then /usr/lib/qt6/bin/qmllint --version
else printf 'NOT RUN   qmllint          Qt QML tooling not installed\n'; fi
printf 'OMARCHY_PATH: %s\nWAYLAND_DISPLAY: %s\n' "${OMARCHY_PATH:-unset}" "${WAYLAND_DISPLAY:-unset}"
if [[ -n ${OMARCHY_PATH:-} ]] && command -v git >/dev/null 2>&1; then
  git -C "$OMARCHY_PATH" describe --tags --always 2>/dev/null || true
  git -C "$OMARCHY_PATH" rev-parse HEAD 2>/dev/null || true
fi
python3 - "$ROOT" <<'PY'
import sys
sys.path.insert(0,sys.argv[1])
from td_telemetry.engine import TelemetryEngine
engine=TelemetryEngine('all')
try:
    frame=engine.sample()
    for name,c in frame['capabilities'].items():
        print('%-12s %-12s source=%s'%(name,c['status'],c['source']))
        if c.get('reason'):print('  '+c['reason'])
        if c.get('suggestion'):print('  '+c['suggestion'])
    print('No raw process, socket or audio history written. Inventory is not desktop acceptance.')
finally:engine.close()
PY
