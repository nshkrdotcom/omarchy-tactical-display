#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

python3 -m unittest discover -s tests -p 'test_*.py' -v
bash -n scripts/doctor.sh scripts/validate.sh scripts/install-local.sh scripts/print-bindings.sh
python3 scripts/telemetry.py --once --interval 0.25 | python3 -m json.tool >/dev/null

if command -v omarchy >/dev/null 2>&1; then
  omarchy plugin validate "$ROOT"
else
  echo "SKIP: omarchy not installed; manifest runtime validation unavailable" >&2
fi

QMLLINT="$(command -v qmllint 2>/dev/null || true)"
if [[ -z "$QMLLINT" && -x /usr/lib/qt6/bin/qmllint ]]; then
  QMLLINT=/usr/lib/qt6/bin/qmllint
fi

if [[ -n "$QMLLINT" ]]; then
  if [[ -n "${OMARCHY_PATH:-}" && -d "${OMARCHY_PATH}/shell" ]]; then
    "$QMLLINT" -I "${OMARCHY_PATH}/shell" Overlay.qml core/*.qml instruments/*.qml
  else
    echo "SKIP: qmllint present but OMARCHY_PATH/shell is unavailable" >&2
  fi
else
  echo "SKIP: qmllint not installed" >&2
fi
