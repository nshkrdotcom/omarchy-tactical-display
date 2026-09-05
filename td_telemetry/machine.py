"""Kernel resource accounting with explicit warmup/reset and PSI semantics."""
from __future__ import annotations
import os
from pathlib import Path
import time
from typing import Any
from .common import Capability, CounterRate, failure, number, optional_text, read_text


def parse_memory(text: str) -> dict[str, Any]:
    values = {}
    for line in text.splitlines():
        f = line.replace(':', '').split()
        if len(f) >= 2:
            try:
                values[f[0]] = int(f[1]) * (1024 if len(f) > 2 and f[2] == 'kB' else 1)
            except ValueError:
                pass
    total = values.get('MemTotal')
    available = values.get('MemAvailable')
    cache = values.get('Cached', 0) + values.get('SReclaimable', 0) - values.get('Shmem', 0)
    return {'totalBytes': total, 'availableBytes': available, 'usedBytes': total - available if total is not None and available is not None else None,
            'cacheBytes': max(0, cache), 'buffersBytes': values.get('Buffers'),
            'swapTotalBytes': values.get('SwapTotal'), 'swapUsedBytes': values.get('SwapTotal', 0) - values.get('SwapFree', 0),
            'provenance': '/proc/meminfo; used=total-available, cache=Cached+SReclaimable-Shmem; RSS sums overlap shared pages'}


def parse_pressure(text: str) -> dict[str, Any]:
    out = {}
    for line in text.splitlines():
        f = line.split()
        if f and f[0] in ('some', 'full'):
            vals = {}
            for token in f[1:]:
                if '=' in token:
                    key, value = token.split('=', 1)
                    vals[key] = number(value)
            out[f[0]] = vals
    return out


class MachineProvider:
    def __init__(self, proc: str | Path = '/proc') -> None:
        self.proc = Path(proc)
        self.capability = Capability('machine', '/proc/{stat,meminfo,loadavg,uptime,net/dev,pressure/*}')
        self.cpu_previous: dict[str, tuple[int, int]] = {}
        self.rate = CounterRate()
        self.topology: dict[str, dict] = {}

    def sample(self, now: float) -> dict[str, Any]:
        started = time.monotonic()
        cap = self.capability = Capability('machine', '/proc/{stat,meminfo,loadavg,uptime,net/dev,pressure/*}', sampledAt=now)
        data: dict[str, Any] = {'cpuPercent': None, 'cores': [], 'memory': {}, 'load': [], 'netRxBps': None, 'netTxBps': None,
                                'uptimeSeconds': None, 'interfaces': [], 'pressure': {}, 'errors': []}
        try:
            current = {}
            for line in read_text(self.proc / 'stat').splitlines():
                f = line.split()
                if not f or not f[0].startswith('cpu'):
                    continue
                values = [int(n) for n in f[1:9]]
                if len(values) < 4:
                    continue
                total, idle = sum(values), values[3] + (values[4] if len(values) > 4 else 0)
                prev = self.cpu_previous.get(f[0])
                percent = None
                if prev and total > prev[0] and idle >= prev[1]:
                    percent = round(max(0, min(100, 100 * (1 - (idle - prev[1]) / (total - prev[0])))), 2)
                current[f[0]] = (total, idle)
                if f[0] == 'cpu':
                    data['cpuPercent'] = percent
                else:
                    if f[0] not in self.topology:
                        path = Path('/sys/devices/system/cpu') / f[0] / 'topology'
                        self.topology[f[0]] = {'package': optional_text(path / 'physical_package_id', limit=128),
                                              'core': optional_text(path / 'core_id', limit=128)}
                    data['cores'].append({'key': f[0], 'cpuPercent': percent, **self.topology[f[0]]})
            self.cpu_previous = current
        except (OSError, ValueError) as error:
            data['errors'].append('CPU: ' + str(error))
        try:
            data['memory'] = parse_memory(read_text(self.proc / 'meminfo', 32768))
            data['load'] = [float(v) for v in read_text(self.proc / 'loadavg', 1024).split()[:3]]
            data['uptimeSeconds'] = float(read_text(self.proc / 'uptime', 128).split()[0])
        except (OSError, ValueError, IndexError) as error:
            data['errors'].append('memory/load: ' + str(error))
        try:
            for line in read_text(self.proc / 'net/dev').splitlines():
                if ':' not in line:
                    continue
                name, raw = line.split(':', 1)
                f = raw.split()
                if len(f) < 16:
                    continue
                name = name.strip()
                # Include ifindex to reset baseline after interface replacement/reuse.
                index = optional_text(Path('/sys/class/net') / name / 'ifindex', limit=128)
                identity = name + ':' + index
                rx, tx = int(f[0]), int(f[8])
                data['interfaces'].append({'key': identity, 'name': name, 'rxBytes': rx, 'txBytes': tx,
                                           'rxBps': self.rate.rate(identity + ':rx', rx, now),
                                           'txBps': self.rate.rate(identity + ':tx', tx, now),
                                           'rxErrors': int(f[2]), 'txErrors': int(f[10])})
            non_loopback = [i for i in data['interfaces'] if i['name'] != 'lo']
            for source, target in [('rxBps', 'netRxBps'), ('txBps', 'netTxBps')]:
                rates = [i[source] for i in non_loopback if i[source] is not None]
                data[target] = sum(rates) if rates else None
            data['networkScope'] = 'sum of non-loopback interface counters; virtual/tunnel interfaces can double count traffic; never per-process attribution'
        except (OSError, ValueError) as error:
            data['errors'].append('network: ' + str(error))
        for subsystem in ('cpu', 'memory', 'io'):
            pressure = parse_pressure(optional_text(self.proc / 'pressure' / subsystem, limit=4096))
            data['pressure'][subsystem] = pressure or None
        if data['errors']:
            cap.status = 'partial'
            cap.complete = False
            cap.reason = '; '.join(data['errors'])[:512]
            cap.suggestion = 'Some kernel interfaces are unavailable in this namespace.'
        data['cpuSource'] = 'monotonic /proc/stat counter delta; guest time not double counted; iowait counted as idle'
        cap.durationMs = round((time.monotonic() - started) * 1000, 3)
        self.rate.prune(now)
        return data
