#!/usr/bin/env python3
"""Exec a fixed argv with Linux parent-death protection, without unsafe preexec_fn.

This small wrapper remains the same PID after exec. It is only used for bounded
provider commands; it never evaluates shell text, imports site, or starts a daemon.
"""
from __future__ import annotations
import ctypes
import os
import signal
import sys


def main() -> int:
    if len(sys.argv) < 3:
        return 64
    expected = int(sys.argv[1])
    libc = ctypes.CDLL(None, use_errno=True)
    if libc.prctl(1, signal.SIGKILL, 0, 0, 0) != 0:
        raise OSError(ctypes.get_errno(), 'PR_SET_PDEATHSIG failed')
    if os.getppid() != expected:
        return 75
    try:
        os.execvpe(sys.argv[2], sys.argv[2:], os.environ)
    except OSError as error:
        print(f'{os.path.basename(sys.argv[2])}: {error.strerror}', file=sys.stderr)
        return 69
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
