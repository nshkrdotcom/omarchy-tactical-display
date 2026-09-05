#!/usr/bin/env python3
"""Use the documented Lua bindings; no shell/configuration mutation."""
from pathlib import Path
import argparse
import os
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from td_telemetry.invocation import invoke_hold


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('hold-press', 'hold-release'))
    parser.add_argument('--token', required=True)
    args = parser.parse_args()
    try:
        runtime = os.environ.get('XDG_RUNTIME_DIR')
        if not runtime:
            raise ValueError('XDG_RUNTIME_DIR is not set; run inside the Hyprland session')
        result = invoke_hold(args.action, args.token, Path(runtime), os.environ.get('HYPRLAND_INSTANCE_SIGNATURE', ''))
        print(result)
        return 0
    except (OSError, ValueError, RuntimeError, TimeoutError) as error:
        print(f'Tactical Display: {error}. Emergency dismiss: omarchy-shell shell hide nshkr.tactical-display', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
