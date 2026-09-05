"""Serialized, user-session-local hold invocation; no resident process.

A release tombstone is written even when the press process has not arrived.
The flock is held across IPC, so a delayed summon cannot overtake a hide.
"""
from __future__ import annotations

from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import time
from typing import Callable, Iterator

from .common import run_command

PLUGIN_ID = 'nshkr.tactical-display'
TOKEN = re.compile(r'^[0-9]{10,12}:[A-Za-z0-9_.:-]{1,110}$')


def _owned_directory(path: Path) -> None:
    info = path.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise PermissionError('hold state requires an owned, non-symlink 0700 runtime directory')


@contextmanager
def locked_state(runtime: Path) -> Iterator[tuple[int, int]]:
    _owned_directory(runtime)
    path = runtime / PLUGIN_ID
    try:
        path.mkdir(mode=0o700)
    except FileExistsError:
        pass
    _owned_directory(path)
    directory = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    lock = -1
    try:
        lock = os.open('hold.lock', os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600, dir_fd=directory)
        info = os.fstat(lock)
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_nlink != 1:
            raise PermissionError('unsafe hold lock')
        os.fchmod(lock, 0o600)
        deadline = time.monotonic() + 8
        while True:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    raise TimeoutError('hold command lock timed out; use shell hide to dismiss')
                time.sleep(0.01)
        yield directory, lock
    finally:
        if lock >= 0:
            os.close(lock)
        os.close(directory)


def _load(directory: int) -> dict:
    try:
        fd = os.open('hold.json', os.O_RDONLY | os.O_NOFOLLOW, dir_fd=directory)
    except FileNotFoundError:
        return {}
    with os.fdopen(fd, 'rb') as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_nlink != 1:
            raise PermissionError('unsafe hold state')
        raw = stream.read(65537)
    if len(raw) > 65536:
        raise ValueError('hold state exceeds budget')
    try:
        value = json.loads(raw)
        return value if isinstance(value, dict) else {}
    except ValueError:
        return {}


def _save(directory: int, state: dict) -> None:
    # Atomic replace inside an already-open, checked directory. Never follow
    # user-controlled state symlinks or truncate a hardlinked file.
    name = f'.hold-{os.getpid()}.tmp'
    fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=directory)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            json.dump(state, stream, separators=(',', ':'))
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, 'hold.json', src_dir_fd=directory, dst_dir_fd=directory)
    finally:
        try:
            os.unlink(name, dir_fd=directory)
        except FileNotFoundError:
            pass


def invoke_hold(action: str, token: str, runtime: Path, session: str,
                runner: Callable[[list[str]], object] | None = None,
                wall_time: float | None = None) -> str:
    if action not in ('hold-press', 'hold-release') or not TOKEN.fullmatch(token):
        raise ValueError('invalid hold action/token')
    if not session:
        raise ValueError('HYPRLAND_INSTANCE_SIGNATURE is required for hold invocation')
    now = time.time() if wall_time is None else wall_time
    created = int(token.split(':', 1)[0])
    # Old delayed processes must not resurrect an overlay after tombstones expire.
    if action == 'hold-press' and not now - 30 <= created <= now + 5:
        return 'ignored-expired-press'
    def real_ipc(argv: list[str]) -> bytes:
        reply = run_command(argv, timeout=4, max_bytes=65536)
        if reply.strip().lower() in (b'false', b'unknown', b'error'):
            raise RuntimeError('Shell rejected invocation; check plugin enablement and shell logs.')
        return reply
    runner = runner or real_ipc
    session_id = hashlib.blake2s(session.encode(), digest_size=12).hexdigest()
    with locked_state(runtime) as (directory, _):
        state = _load(directory)
        if state.get('session') != session_id:
            state = {'version': 1, 'session': session_id, 'active': '', 'released': {}}
        released = state.get('released', {})
        released = {str(k): float(v) for k, v in released.items()
                    if isinstance(v, (int, float)) and now - 60 <= v <= now + 5} if isinstance(released, dict) else {}
        if action == 'hold-release':
            released[token] = now
            state['released'] = dict(sorted(released.items(), key=lambda item: item[1])[-256:])
            # Persist first: an IPC error must not allow a delayed press to open.
            active = state.get('active') == token
            if active:
                state['active'] = ''
            _save(directory, state)
            if active:
                runner(['omarchy-shell', 'shell', 'hide', PLUGIN_ID])
                return 'hidden'
            return 'release-recorded'
        if token in released or state.get('active') == token:
            return 'ignored-release-or-repeat'
        state['released'] = released
        state['active'] = token
        _save(directory, state)
        try:
            runner(['omarchy-shell', 'shell', 'summon', PLUGIN_ID,
                    json.dumps({'mode': 'hold'}, separators=(',', ':'))])
        except Exception:
            state['active'] = ''
            state['released'][token] = now
            _save(directory, state)
            raise
        return 'summoned'
