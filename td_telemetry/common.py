"""Bounded I/O, explicit capability contracts, and monotonic counters."""
from __future__ import annotations

from collections import OrderedDict
from dataclasses import asdict, dataclass
import hashlib
import json
import math
import os
from pathlib import Path
import selectors
import signal
import subprocess
import sys
import time
from typing import Any, Protocol

MAX_TEXT = 1024 * 1024
MAX_FRAME = 4 * 1024 * 1024
MAX_COMMAND_OUTPUT = 8 * 1024 * 1024
MAX_STRING = 512


def clean(value: Any, limit: int = MAX_STRING) -> str:
    # Strip C0/C1 controls and bidi overrides so hostile local names cannot
    # masquerade as UI chrome. Ordinary Unicode is deliberately retained.
    return ''.join(c for c in str(value or '') if (ord(c) >= 32 and not 127 <= ord(c) < 160
                   and not 0x202A <= ord(c) <= 0x202E and not 0x2066 <= ord(c) <= 0x2069))[:limit]


def stable_id(kind: str, *parts: Any) -> str:
    raw = json.dumps(parts, ensure_ascii=True, separators=(',', ':')).encode()
    return kind + ':' + hashlib.blake2s(raw, digest_size=12).hexdigest()


def read_text(path: str | Path, limit: int = MAX_TEXT) -> str:
    with open(path, 'r', encoding='utf-8', errors='replace') as f:
        text = f.read(limit + 1)
    if len(text) > limit:
        raise ValueError('input exceeds read budget')
    return text


def optional_text(path: str | Path, default: str = '', limit: int = MAX_TEXT) -> str:
    try:
        return read_text(path, limit).strip()
    except (OSError, ValueError):
        return default


def number(value: Any) -> float | None:
    try:
        n = float(value)
        return n if math.isfinite(n) else None
    except (TypeError, ValueError, OverflowError):
        return None


@dataclass
class Capability:
    provider: str
    source: str
    status: str = 'available'
    level: str = 'measured'
    reason: str = ''
    sampledAt: float | None = None
    intervalSeconds: float = 1.0
    durationMs: float = 0.0
    complete: bool = True
    errorKind: str = ''
    suggestion: str = ''

    def json(self) -> dict[str, Any]:
        return asdict(self)


class Provider(Protocol):
    capability: Capability
    def sample(self, now: float) -> dict[str, Any] | list[dict[str, Any]]: ...


def failure(cap: Capability, error: Exception, suggestion: str = '') -> None:
    cap.status = 'unavailable'
    cap.complete = False
    cap.errorKind = ('permission' if isinstance(error, PermissionError) else
                     'missing-dependency' if isinstance(error, FileNotFoundError) else
                     'transient' if isinstance(error, (TimeoutError, OSError)) else 'malformed')
    cap.reason = clean(str(error), 240)
    cap.suggestion = suggestion


class CounterRate:
    """Missing baseline/reset is None, never a fabricated zero."""
    def __init__(self, limit: int = 32768) -> None:
        self.values: OrderedDict[str, tuple[float, float]] = OrderedDict()
        self.limit = limit

    def rate(self, key: str, value: float, now: float) -> float | None:
        prev = self.values.pop(key, None)
        self.values[key] = (float(value), now)
        while len(self.values) > self.limit:
            self.values.popitem(last=False)
        if prev is None or now <= prev[1] or value < prev[0]:
            return None
        return round((value - prev[0]) / (now - prev[1]), 3)

    def prune(self, now: float, ttl: float = 60) -> None:
        for key, (_, seen) in list(self.values.items()):
            if now - seen > ttl:
                self.values.pop(key, None)


def guarded_argv(argv: list[str]) -> list[str]:
    """Parent-death safety without executing Python in a forked preexec hook."""
    if not argv or any(not isinstance(a, str) or '\x00' in a for a in argv):
        raise ValueError('invalid command argument array')
    return [sys.executable, '-S', str(Path(__file__).with_name('guardexec.py')), str(os.getpid()), *argv]


def run_command(argv: list[str], *, timeout: float = 2,
                max_bytes: int = MAX_COMMAND_OUTPUT, input_data: bytes | None = None) -> bytes:
    """No shell, bounded output/time, and always reap the real subprocess.

    Stderr is included in the same budget but separated from stdout. A hung
    optional provider therefore cannot leave an orphan or grow memory forever.
    Commands accepting input here are deliberately limited to <=64 KiB.
    """
    if input_data is not None and len(input_data) > 65536:
        raise ValueError('command input exceeds budget')
    proc = subprocess.Popen(guarded_argv(argv), stdin=subprocess.PIPE if input_data is not None else subprocess.DEVNULL,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True,
                            env={**os.environ, 'LC_ALL': 'C'})
    out, err = bytearray(), bytearray()
    deadline = time.monotonic() + timeout
    try:
        if input_data is not None and proc.stdin is not None:
            # Small nonblocking writes avoid deadlock on a non-reading process.
            os.set_blocking(proc.stdin.fileno(), False)
        with selectors.DefaultSelector() as sel:
            assert proc.stdout is not None and proc.stderr is not None
            for stream, target in ((proc.stdout, out), (proc.stderr, err)):
                os.set_blocking(stream.fileno(), False)
                sel.register(stream, selectors.EVENT_READ, target)
            if input_data is not None and proc.stdin is not None:
                sel.register(proc.stdin, selectors.EVENT_WRITE, None)
            sent = 0
            while sel.get_map():
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError(f'{Path(argv[0]).name}: timed out')
                for key, mask in sel.select(min(0.1, remaining)):
                    if mask & selectors.EVENT_WRITE:
                        try:
                            sent += os.write(key.fileobj.fileno(), input_data[sent:])
                        except BrokenPipeError:
                            sent = len(input_data)
                        if sent >= len(input_data):
                            sel.unregister(key.fileobj)
                            key.fileobj.close()
                        continue
                    chunk = os.read(key.fileobj.fileno(), 65536)
                    if not chunk:
                        sel.unregister(key.fileobj)
                        continue
                    key.data.extend(chunk)
                    if len(out) + len(err) > max_bytes:
                        raise ValueError(f'{Path(argv[0]).name}: output exceeds budget')
        # Observe exit without reaping, keeping PID/PGID reserved until cleanup.
        # A command may close stdout/stderr and then hang, so this is bounded too.
        while os.waitid(os.P_PID, proc.pid, os.WEXITED | os.WNOWAIT | os.WNOHANG) is None:
            if time.monotonic() >= deadline:
                raise TimeoutError(f'{Path(argv[0]).name}: timed out after output closed')
            time.sleep(0.005)
    finally:
        # Kill remaining members even if the original command has already exited.
        # The unreaped original PID above prevents an unrelated PGID from reusing it.
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        proc.wait()
        for stream in (proc.stdin, proc.stdout, proc.stderr):
            if stream is not None:
                stream.close()
    if proc.returncode:
        raise RuntimeError(f'{Path(argv[0]).name} exited {proc.returncode}: {clean(err.decode(errors="replace"), 180)}')
    return bytes(out)
