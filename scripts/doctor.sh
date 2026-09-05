#!/usr/bin/env bash
set -euo pipefail

PLUGIN_ID="nshkr.tactical-display"
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"

say() { printf '%-28s %s\n' "$1" "$2"; }
check_cmd() {
  if command -v "$1" >/dev/null 2>&1; then say "$1" "OK ($(command -v "$1"))"; else say "$1" "MISSING"; fi
}

printf 'Tactical Display doctor\n\n'
say "repo" "$ROOT"
check_cmd python3
check_cmd omarchy
check_cmd omarchy-shell
check_cmd quickshell
if command -v qmllint >/dev/null 2>&1; then
  say "qmllint" "OK ($(command -v qmllint))"
elif [[ -x /usr/lib/qt6/bin/qmllint ]]; then
  say "qmllint" "OK (/usr/lib/qt6/bin/qmllint)"
else
  say "qmllint" "MISSING"
fi
check_cmd hyprctl
check_cmd nvidia-smi
printf '\n'

if command -v omarchy-shell >/dev/null 2>&1; then
  if omarchy-shell shell ping >/dev/null 2>&1; then say "omarchy-shell" "RUNNING"; else say "omarchy-shell" "NOT RESPONDING"; fi
fi

if command -v omarchy >/dev/null 2>&1; then
  if omarchy plugin validate "$ROOT" >/dev/null 2>&1; then say "manifest" "VALID"; else say "manifest" "VALIDATION FAILED"; fi
fi

if command -v hyprctl >/dev/null 2>&1; then
  errors="$(hyprctl configerrors 2>/dev/null || true)"
  if [[ -z "$errors" ]]; then say "hyprland config" "CLEAN"; else say "hyprland config" "ERRORS PRESENT"; fi
fi

if command -v omarchy >/dev/null 2>&1; then
  found="$(omarchy plugin list --json 2>/dev/null | python3 -c 'import json,sys; p=json.load(sys.stdin); print(any(x.get("id")=="nshkr.tactical-display" for x in p))' 2>/dev/null || true)"
  say "plugin discovered" "${found:-UNKNOWN}"
fi

printf '\nLive backend probe:\n'
frame="$(python3 "$ROOT/scripts/telemetry.py" --once --interval 0.25)"
printf '%s\n' "$frame" | python3 -m json.tool >/dev/null
say "telemetry frame" "VALID JSON"
summary="$(printf '%s\n' "$frame" | python3 -c 'import json,sys; d=json.load(sys.stdin); s=d.get("network",{}).get("summary",{}); print("{} connections / {} processes / {} remotes / {} listeners".format(s.get("connections",0), s.get("processes",0), s.get("remoteSystems",0), s.get("listeners",0)))')"
say "network model" "$summary"
