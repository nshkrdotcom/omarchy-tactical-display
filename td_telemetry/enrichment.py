"""Local-first names with isolated, bounded optional enrichment workers."""
from __future__ import annotations
from collections import OrderedDict, deque
import ipaddress
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
from typing import Any
from .common import clean, command_env, optional_text, guarded_argv


def parse_hosts(text: str) -> dict[str, str]:
    out = {}
    for line in text.splitlines()[:10000]:
        f = line.split('#', 1)[0].split()
        if len(f) > 1:
            try:
                out[str(ipaddress.ip_address(f[0]))] = clean(f[1], 253)
            except ValueError:
                pass
    return out


def parse_services(text: str) -> dict[tuple[int, str], str]:
    out: dict[tuple[int, str], str] = {}
    ambiguous = set()
    for line in text.splitlines()[:20000]:
        f = line.split('#', 1)[0].split()
        if len(f) < 2 or '/' not in f[1]:
            continue
        try:
            port, proto = f[1].split('/', 1)
            key = (int(port), proto)
            if key in out and out[key] != f[0]:
                ambiguous.add(key)
            out[key] = clean(f[0], 64)
        except ValueError:
            continue
    return {k: v for k, v in out.items() if k not in ambiguous}


class Enricher:
    def __init__(self) -> None:
        self.hosts = parse_hosts(optional_text(Path('/etc/hosts')))
        self.services = parse_services(optional_text(Path('/etc/services'), limit=2 * 1024 * 1024))
        self.cache: OrderedDict[str, tuple[float, str | None]] = OrderedDict()
        self.pending: deque[str] = deque(maxlen=64)
        self.worker: subprocess.Popen[bytes] | None = None
        self.worker_ip = ''
        self.worker_at = 0.0
        self.mode = 'local'
        self.aliases: dict[str, str] = {}
        self.privacy = False
        self.offline_path = ''
        self.offline_error = ''
        self.offline_cache: OrderedDict[str, tuple[float, dict[str, Any] | None]] = OrderedDict()
        self.offline_pending: deque[str] = deque(maxlen=64)
        self.offline_worker: subprocess.Popen[bytes] | None = None
        self.offline_worker_ip = ''
        self.offline_worker_at = 0.0

    def configure(self, mode: str = 'local', aliases: dict[str, str] | None = None, privacy: bool = False, offline_db: str = '') -> None:
        self.mode = mode if mode in ('raw', 'local', 'dns') else 'local'
        self.aliases = {}
        if isinstance(aliases, dict):
            for address, name in list(aliases.items())[:512]:
                try:
                    self.aliases[str(ipaddress.ip_address(address))] = clean(name, 253)
                except (ValueError, TypeError):
                    continue
        self.privacy = privacy
        if self.mode != 'dns' or privacy:
            self.close_worker()
            self.pending.clear()
        if offline_db != self.offline_path:
            self.close_offline_worker()
            self.offline_pending.clear()
            self.offline_cache.clear()
            self.offline_error = ''
            # The main helper deliberately does not stat/open/resolve this path.
            # Any slow filesystem/MMDB behavior occurs only in the killable worker.
            self.offline_path = offline_db
        if privacy:
            self.close_offline_worker()
            self.offline_pending.clear()

    @staticmethod
    def _read_result(worker: subprocess.Popen[bytes], limit: int = 4096) -> dict[str, Any] | None:
        raw = worker.stdout.read(limit + 1) if worker.stdout else b''
        if len(raw) > limit:
            return None
        try:
            value = json.loads(raw)
            return value if isinstance(value, dict) else None
        except (ValueError, TypeError):
            return None

    def tick(self, now: float) -> None:
        if self.worker:
            if self.worker.poll() is not None:
                result = self._read_result(self.worker)
                name = clean(result.get('name'), 253) if result and result.get('name') else None
                self.cache[self.worker_ip] = (now, name)
                self.close_worker()
            elif now - self.worker_at > 1.5:
                self.cache[self.worker_ip] = (now, None)
                self.close_worker()
        while len(self.cache) > 512:
            self.cache.popitem(last=False)
        if not self.worker and self.pending and self.mode == 'dns' and not self.privacy:
            self.worker_ip = self.pending.popleft()
            self.worker_at = now
            self.worker = subprocess.Popen(
                guarded_argv([sys.executable, '-S', str(Path(__file__).with_name('dns_worker.py')), self.worker_ip]),
                stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                start_new_session=True, env=command_env())

        if self.offline_worker:
            if self.offline_worker.poll() is not None:
                result = self._read_result(self.offline_worker)
                if result and result.get('ok') is True and isinstance(result.get('offline'), dict):
                    value = result['offline']
                    self.offline_cache[self.offline_worker_ip] = (now, {
                        'asn': value.get('asn'), 'organization': clean(value.get('organization', '')),
                        'country': clean(value.get('country', '')),
                        'provenance': 'user-supplied local MMDB via isolated worker; approximate, not host identity',
                    })
                else:
                    self.offline_cache[self.offline_worker_ip] = (now, None)
                    self.offline_error = clean((result or {}).get('error') or 'offline MMDB worker returned invalid data', 180)
                self.close_offline_worker()
            elif now - self.offline_worker_at > 1.5:
                self.offline_cache[self.offline_worker_ip] = (now, None)
                self.offline_error = 'offline MMDB lookup timed out; worker was terminated'
                self.close_offline_worker()
        while len(self.offline_cache) > 512:
            self.offline_cache.popitem(last=False)
        if (not self.offline_worker and self.offline_pending and self.offline_path and not self.privacy
                and not self.offline_error):
            self.offline_worker_ip = self.offline_pending.popleft()
            self.offline_worker_at = now
            self.offline_worker = subprocess.Popen(
                guarded_argv([sys.executable, str(Path(__file__).with_name('mmdb_worker.py')),
                              self.offline_path, self.offline_worker_ip]),
                stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                start_new_session=True, env=command_env())

    def resolve(self, address: str, now: float) -> dict[str, Any]:
        result: dict[str, Any] = {'name': address, 'address': address, 'nameSource': 'numeric address', 'nameTrusted': False, 'offline': None}
        if address in self.aliases:
            result.update(name=self.aliases[address], nameSource='explicit local user alias', nameTrusted=True)
        elif self.mode != 'raw' and address in self.hosts:
            result.update(name=self.hosts[address], nameSource='/etc/hosts (local)', nameTrusted=True)
        elif self.mode == 'dns' and not self.privacy:
            cache = self.cache.get(address)
            if cache and now - cache[0] < 300:
                if cache[1]:
                    result.update(name=cache[1], nameSource='reverse DNS via configured resolver; unverified PTR', nameTrusted=False)
            elif address != self.worker_ip and address not in self.pending and len(self.pending) < 64:
                self.pending.append(address)
        if self.offline_path and not self.privacy:
            cached = self.offline_cache.get(address)
            if cached and now - cached[0] < 300:
                result['offline'] = cached[1]
            elif (not self.offline_error and address != self.offline_worker_ip
                  and address not in self.offline_pending and len(self.offline_pending) < 64):
                self.offline_pending.append(address)
        return result

    @staticmethod
    def _close_process(worker: subprocess.Popen[bytes] | None) -> None:
        if not worker:
            return
        if worker.poll() is None:
            try:
                os.killpg(worker.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        try:
            worker.wait(timeout=1)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(worker.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            worker.wait(timeout=1)
        if worker.stdout:
            worker.stdout.close()

    def close_worker(self) -> None:
        self._close_process(self.worker)
        self.worker = None
        self.worker_ip = ''

    def close_offline_worker(self) -> None:
        self._close_process(self.offline_worker)
        self.offline_worker = None
        self.offline_worker_ip = ''

    def close(self) -> None:
        self.close_worker()
        self.close_offline_worker()
        self.pending.clear()
        self.offline_pending.clear()
