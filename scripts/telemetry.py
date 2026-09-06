#!/usr/bin/env python3
"""Tactical Display's real, unprivileged, bounded NDJSON helper (schema 3)."""
from __future__ import annotations
import argparse
import ctypes
import json
import os
from pathlib import Path
import selectors
import signal
import sys
import time

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from td_telemetry.engine import INSTRUMENTS, PROFILES, TelemetryEngine
from td_telemetry.network import SocketSampler, build_network_model
from td_telemetry.procfs import parse_ipv4, parse_ipv6, parse_proc_net_line, classify_socket
from td_telemetry.common import MAX_FRAME, SlidingWindowLimiter, clean


class StopHelper(BaseException):
    pass


def stop(_signal: int, _frame: object) -> None:
    raise StopHelper()


def emit(frame: dict) -> None:
    raw = json.dumps(frame, separators=(',', ':'), ensure_ascii=True, allow_nan=False)
    if len(raw.encode()) > MAX_FRAME:
        raise ValueError('outbound frame exceeds budget')
    sys.stdout.write(raw + '\n')
    sys.stdout.flush()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--once', action='store_true')
    parser.add_argument('--interval', type=float)
    parser.add_argument('--profile', choices=PROFILES, default='balanced')
    parser.add_argument('--instrument', choices=(*INSTRUMENTS, 'all'), default='connection')
    parser.add_argument('--socket-source', choices=('auto', 'proc'), default='auto')
    args = parser.parse_args()
    parent = os.getppid()
    if sys.platform == 'linux':
        try:
            ctypes.CDLL(None).prctl(1, signal.SIGTERM)  # PR_SET_PDEATHSIG
            if os.getppid() != parent:
                return 0
        except (OSError, AttributeError):
            pass
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    engine = TelemetryEngine(args.instrument, args.profile, args.interval, args.socket_source)
    selector = selectors.DefaultSelector()
    buffer = bytearray()
    dropping = False
    command_limiter = SlidingWindowLimiter(32, 1.0)
    try:
        if args.once:
            emit(engine.sample())
            return 0
        try:
            os.set_blocking(sys.stdin.fileno(), False)
            selector.register(sys.stdin, selectors.EVENT_READ)
        except (OSError, ValueError):
            pass
        next_at = time.monotonic()
        while True:
            for event, _ in selector.select(max(0, min(0.2, next_at - time.monotonic()))):
                chunk = os.read(event.fileobj.fileno(), 65536)
                if not chunk:
                    # Host closing stdin is a lifecycle close, not permission to orphan.
                    return 0
                buffer.extend(chunk)
                while b'\n' in buffer:
                    line, _, remainder = buffer.partition(b'\n')
                    buffer = bytearray(remainder)
                    if dropping or len(line) > 65536:
                        dropping = False
                        emit({'type': 'error', 'message': 'Command exceeded 64 KiB; discarded.'})
                        continue
                    if not command_limiter.allow():
                        emit({'type': 'error', 'message': 'Command rate exceeded 32 records/second; discarded.'})
                        continue
                    try:
                        command = json.loads(line)
                        answer = engine.command(command)
                        if answer is not None:
                            emit(answer)
                        if isinstance(command, dict) and command.get('op') in ('configure', 'scope'):
                            next_at = time.monotonic()
                    except (ValueError, TypeError, OSError, RuntimeError, TimeoutError) as error:
                        emit({'type': 'error', 'message': clean(error, 240)})
                if len(buffer) > 65536:
                    buffer.clear()
                    dropping = True
            if time.monotonic() >= next_at:
                try:
                    emit(engine.sample())
                except (ValueError, OSError, RuntimeError) as error:
                    emit({'type': 'error', 'message': 'Snapshot unavailable: ' + clean(error, 240)})
                next_at = time.monotonic() + engine.interval
    except (StopHelper, BrokenPipeError):
        return 0
    finally:
        selector.close()
        engine.close()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
