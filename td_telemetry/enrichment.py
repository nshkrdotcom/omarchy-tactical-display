"""Local-first names with explicit provenance; bounded, opt-in resolver worker."""
from __future__ import annotations
from collections import OrderedDict, deque
import ipaddress
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
from typing import Any
from .common import clean, optional_text, guarded_argv


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
        self.offline: Any = None
        self.offline_error = ''

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
            if self.offline:
                self.offline.close()
            self.offline, self.offline_error = None, ''
            self.offline_path = offline_db
            if offline_db:
                try:
                    import maxminddb  # optional, no download or external service
                    self.offline = maxminddb.open_database(os.path.expanduser(offline_db))
                except (ImportError, OSError, ValueError) as error:
                    self.offline_error = clean(error, 180)

    def tick(self, now: float) -> None:
        if self.worker:
            if self.worker.poll() is not None:
                raw = self.worker.stdout.read(4097) if self.worker.stdout else b''
                name = None
                try:
                    result = json.loads(raw)
                    name = clean(result.get('name'), 253) if result.get('name') else None
                except (ValueError, TypeError):
                    pass
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
            self.worker = subprocess.Popen(guarded_argv([sys.executable, '-S', str(Path(__file__).with_name('dns_worker.py')), self.worker_ip]),
                                           stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, start_new_session=True)

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
        if self.offline and not self.privacy:
            try:
                value = self.offline.get(address) or {}
                result['offline'] = {'asn': value.get('autonomous_system_number'),
                                     'organization': clean(value.get('autonomous_system_organization', '')),
                                     'country': clean(value.get('country', {}).get('iso_code', '')),
                                     'provenance': 'user-supplied local MMDB; approximate, not host identity'}
            except (ValueError, OSError, TypeError, AttributeError):
                pass
        return result

    def close_worker(self) -> None:
        if self.worker:
            if self.worker.poll() is None:
                try:
                    os.killpg(self.worker.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            self.worker.wait(timeout=1)
            if self.worker.stdout:
                self.worker.stdout.close()
            self.worker = None
            self.worker_ip = ''

    def close(self) -> None:
        self.close_worker()
        if self.offline:
            self.offline.close()
            self.offline = None
