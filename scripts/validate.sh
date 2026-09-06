#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
REQUIRE_NATIVE=0
if [[ ${1:-} == --require-native ]]; then REQUIRE_NATIVE=1
elif [[ $# != 0 ]]; then printf 'Usage: %s [--require-native]\n' "$0" >&2; exit 2; fi
export PYTHONDONTWRITEBYTECODE=1
python3 -m unittest discover -s tests -p 'test_*.py' -v
python3 scripts/release-gate.py --source-only
if command -v node >/dev/null 2>&1; then node --test --test-reporter=spec tests/js/*.test.js
else printf 'NOT RUN: Node.js model/layout tests (install nodejs for development).\n'; exit 77; fi
for script in scripts/*.sh; do bash -n "$script"; done
python3 - <<'PY'
from pathlib import Path
for path in [*Path('td_telemetry').glob('*.py'),*Path('scripts').glob('*.py'),*Path('tests').glob('*.py')]:
    compile(path.read_bytes(),str(path),'exec')
print('PASS: Python syntax and shell syntax')
PY
native_missing=0
if command -v omarchy >/dev/null 2>&1; then omarchy plugin validate .
else printf 'NOT RUN: omarchy plugin validate (Omarchy absent).\n'; native_missing=1; fi
LINT="$(command -v qmllint || true)"
[[ -n "$LINT" || ! -x /usr/lib/qt6/bin/qmllint ]] || LINT=/usr/lib/qt6/bin/qmllint
if [[ -n "$LINT" && -n ${OMARCHY_PATH:-} && -d "$OMARCHY_PATH/shell" ]]; then
  qml=(
    core/CommandSheet.qml
    core/Configuration.qml
    core/InspectionPanel.qml
    core/InstrumentButton.qml
    core/NavigationController.qml
    core/TacticalDisplayShell.qml
    visual/Field.qml
    visual/Trend.qml
  )
  "$LINT" -I "$OMARCHY_PATH/shell" "${qml[@]}"
else printf 'NOT RUN: native QML lint (Qt/Quattro imports absent).\n'; native_missing=1; fi
if (( native_missing )); then
  printf 'PARTIAL: available automated gates passed; native runtime/lint not validated.\n'
  (( REQUIRE_NATIVE == 0 )) || exit 77
else printf 'PASS: automated/static/native-lint gates. Live interaction and soak are separate.\n'; fi