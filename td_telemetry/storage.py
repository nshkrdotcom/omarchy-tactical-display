"""Observed mount/block topology and accounting, not invented process-to-file flow."""
from __future__ import annotations
import json
import os
from pathlib import Path
import re
import sys
import time
from typing import Any
from .common import Capability, CounterRate, clean, failure, optional_text, read_text, run_command, stable_id

SAFE_CAPACITY_FS = {'ext2', 'ext3', 'ext4', 'btrfs', 'xfs', 'f2fs', 'tmpfs', 'ramfs', 'vfat', 'exfat', 'ntfs3', 'overlay', 'zfs'}


def unescape_mount(s: str) -> str:
    return re.sub(r'\\([0-7]{3})', lambda m: chr(int(m.group(1), 8)), s)


def parse_mountinfo(text: str) -> list[dict[str, Any]]:
    rows = []
    for line in text.splitlines()[:8192]:
        fields = line.split()
        try:
            sep = fields.index('-')
            if sep < 6 or len(fields) < sep + 4:
                continue
            mount_id, parent_id = int(fields[0]), int(fields[1])
            path, source = unescape_mount(fields[4]), unescape_mount(fields[sep + 2])
            major_minor = fields[2]
            rows.append({'key': stable_id('mount', mount_id, major_minor, fields[3], path), 'mountId': mount_id,
                         'parentMountId': parent_id, 'majorMinor': major_minor, 'path': clean(path),
                         'name': clean(path), 'root': clean(unescape_mount(fields[3])), 'fsType': clean(fields[sep + 1]),
                         'source': clean(source), 'options': clean(fields[5]), 'deviceKey': 'block:' + major_minor,
                         'capacitySafePath': path == clean(path), 'capacity': None, 'capacitySource': 'unavailable', 'provenance': '/proc/self/mountinfo'})
        except (ValueError, IndexError):
            continue
    return rows


def parse_diskstats(text: str) -> list[dict[str, Any]]:
    out = []
    for line in text.splitlines()[:8192]:
        f = line.split()
        if len(f) < 14:
            continue
        try:
            v = [int(x) for x in f[3:14]]
            mm = f'{int(f[0])}:{int(f[1])}'
            out.append({'key': 'block:' + mm, 'majorMinor': mm, 'name': clean(f[2]),
                        'readBytes': v[2] * 512, 'writeBytes': v[6] * 512,
                        'readsCompleted': v[0], 'writesCompleted': v[4], 'ioMs': v[9],
                        'readMs': v[3], 'writeMs': v[7], 'weightedIoMs': v[10], 'inFlight': v[8]})
        except (ValueError, IndexError):
            continue
    return out


class StorageProvider:
    def __init__(self, proc: str | Path = '/proc', sysfs: str | Path = '/sys') -> None:
        self.proc, self.sys = Path(proc), Path(sysfs)
        self.capability = Capability('storage', '/proc/{diskstats,self/mountinfo}, /sys/class/block, statvfs')
        self.rate = CounterRate()
        self.capacities: dict[str, dict[str, Any]] = {}
        self.capacity_at = -100.0
        self.fd_at = -100.0
        self.fd_links: list[dict[str, Any]] = []
        self.fd_note = ''
        self.metadata: dict[str, tuple[float, dict[str, Any]]] = {}
        self.rows: dict[str, Any] = {}

    def sample(self, now: float, processes: list[dict[str, Any]] | None = None, topology: bool = True) -> dict[str, Any]:
        started = time.monotonic()
        cap = self.capability = Capability('storage', '/proc/diskstats + sysfs + mountinfo', sampledAt=now)
        data: dict[str, Any] = {'devices': [], 'mounts': [], 'links': [], 'contributors': [], 'summary': {}}
        try:
            devices = parse_diskstats(read_text(self.proc / 'diskstats', 2 * 1024 * 1024))
            links = []
            for d in devices:
                path = self.sys / 'class/block' / d['name']
                cached = self.metadata.get(d['key'])
                if cached and now - cached[0] < 10:
                    meta = cached[1]
                else:
                    partition = (path / 'partition').exists()
                    parent_key = None
                    if partition:
                        try:
                            parent_mm = optional_text(path.resolve().parent / 'dev', limit=128)
                            parent_key = 'block:' + parent_mm if parent_mm else None
                        except OSError:
                            pass
                    slaves = []
                    try:
                        for slave in (path / 'slaves').iterdir():
                            mm = optional_text(slave / 'dev', limit=128)
                            if mm:
                                slaves.append('block:' + mm)
                    except OSError:
                        pass
                    meta = {'partition': partition, 'parentKey': parent_key, 'slaves': slaves,
                            'model': clean(optional_text(path / 'device/model', limit=1024)),
                            'rotational': optional_text(path / 'queue/rotational', limit=128) == '1',
                            'physical': not partition and not slaves and not d['name'].startswith(('loop', 'ram', 'zram', 'dm-', 'md'))}
                    self.metadata[d['key']] = (now, meta)
                d.update(meta)
                d['readBps'] = self.rate.rate(d['key'] + ':read', d['readBytes'], now)
                d['writeBps'] = self.rate.rate(d['key'] + ':write', d['writeBytes'], now)
                busy = self.rate.rate(d['key'] + ':busy', d['ioMs'], now)
                d['busyPercent'] = min(100, busy / 10) if busy is not None else None
                rd = self.rate.rate(d['key'] + ':rc', d['readsCompleted'], now)
                wr = self.rate.rate(d['key'] + ':wc', d['writesCompleted'], now)
                rm = self.rate.rate(d['key'] + ':rm', d['readMs'], now)
                wm = self.rate.rate(d['key'] + ':wm', d['writeMs'], now)
                d['readAwaitMs'] = round(rm / rd, 3) if rd and rm is not None else None
                d['writeAwaitMs'] = round(wm / wr, 3) if wr and wm is not None else None
                d['provenance'] = {'rates': 'diskstats 512-byte sectors, monotonic delta', 'busyPercent': 'io_ticks proxy; not saturation on parallel devices',
                                   'await': 'delta request milliseconds / completed requests; no per-process attribution'}
                for lower in ([d['parentKey']] if d['parentKey'] else []) + d['slaves']:
                    links.append({'key': stable_id('storage-edge', d['key'], lower), 'sourceKey': d['key'], 'targetKey': lower, 'kind': 'backing', 'provenance': 'sysfs observed topology'})
            data['devices'] = devices
            active_keys = {d['key'] for d in devices}
            if topology:
                mounts = parse_mountinfo(read_text(self.proc / 'self/mountinfo', 4 * 1024 * 1024))
                if now - self.capacity_at > 15:
                    self.capacity_at = now
                    eligible = [m['path'] for m in mounts if m['fsType'] in SAFE_CAPACITY_FS and m.get('capacitySafePath', False) and m['root'] == '/'][:64]
                    try:
                        raw = run_command([sys.executable, '-S', str(Path(__file__).with_name('capacity.py'))], timeout=0.5, input_data=json.dumps(eligible).encode())
                        self.capacities = {r['path']: {**r, 'sampledAt': now} for r in (json.loads(line) for line in raw.splitlines())}
                    except (OSError, TimeoutError, RuntimeError, ValueError):
                        cap.status = 'partial'
                        cap.reason = 'Capacity probe unavailable/timed out; previous values retain their sample timestamp.'
                for m in mounts:
                    capacity = self.capacities.get(m['path'])
                    m['capacity'] = capacity
                    m['capacitySource'] = 'statvfs; safe local filesystem allowlist; cached <=15s' if capacity else 'not probed or unavailable'
                    if m['deviceKey'] in active_keys:
                        links.append({'key': stable_id('storage-edge', m['key'], m['deviceKey']), 'sourceKey': m['key'], 'targetKey': m['deviceKey'], 'kind': 'mount', 'provenance': 'mountinfo major:minor'})
                    else:
                        m['deviceKey'] = None
                data['mounts'] = mounts
                if processes is not None and now - self.fd_at >= 3:
                    self.fd_at = now
                    self.fd_links, self.fd_note = self.open_mounts(processes, mounts)
                current_processes = {p['key'] for p in processes or []}
                current_mounts = {m['key'] for m in mounts}
                links.extend(l for l in self.fd_links if l['sourceKey'] in current_processes and l['targetKey'] in current_mounts)
            data['links'] = links
            data['contributors'] = [dict(p) for p in sorted(processes or [], key=lambda p: (p.get('readBps') or 0) + (p.get('writeBps') or 0), reverse=True) if p.get('ioAvailable')][:128]
            physical = [d for d in devices if d['physical']]
            def total(field: str) -> float | None:
                vals = [d[field] for d in physical if d[field] is not None]
                return sum(vals) if vals else None
            data['summary'] = {'readBps': total('readBps'), 'writeBps': total('writeBps'), 'physicalDevices': len(physical),
                               'aggregateScope': 'whole non-virtual leaf devices only; partitions/dm/md excluded to avoid double counting',
                               'processMountAttribution': 'NOT MEASURED. Dashed process/mount links mean open descriptors, never byte flow.',
                               'openDescriptorCoverage': self.fd_note}
            self.metadata = {k: v for k, v in self.metadata.items() if k in active_keys}
        except (OSError, ValueError) as error:
            failure(cap, error, 'Check readable procfs/sysfs; virtual/container mounts may have no visible backing device.')
        self.rate.prune(now)
        cap.durationMs = round((time.monotonic() - started) * 1000, 3)
        self.rows = data
        return data

    def open_mounts(self, processes: list[dict[str, Any]], mounts: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], str]:
        from .processes import parse_stat
        started = time.monotonic()
        by_id = {m['mountId']: m['key'] for m in mounts}
        found: dict[tuple[str, str], int] = {}
        scanned = denied = 0
        try:
            own_ns = os.readlink(self.proc / 'self/ns/mnt')
        except OSError:
            return [], 'mount namespace comparison unavailable'
        candidates = sorted(processes, key=lambda p: (p.get('readBps') or 0) + (p.get('writeBps') or 0), reverse=True)[:32]
        for p in candidates:
            if time.monotonic() - started > 0.12:
                break
            local: dict[str, int] = {}
            try:
                base = self.proc / str(p['pid'])
                if os.readlink(base / 'ns/mnt') != own_ns:
                    continue
                for index, fd in enumerate((base / 'fdinfo').iterdir()):
                    if index >= 128 or time.monotonic() - started > 0.12:
                        break
                    info = optional_text(fd, limit=4096)
                    match = re.search(r'^mnt_id:\s*(\d+)', info, re.MULTILINE)
                    if match and int(match[1]) in by_id:
                        key = by_id[int(match[1])]
                        local[key] = local.get(key, 0) + 1
                if parse_stat(read_text(base / 'stat', 8192))['key'] != p['key']:
                    continue
                scanned += 1
                for key, count in local.items():
                    found[(p['key'], key)] = count
            except (OSError, ValueError, IndexError):
                denied += 1
        links = [{'key': stable_id('fd-mount', a, b), 'sourceKey': a, 'targetKey': b, 'kind': 'open-fd', 'count': n,
                  'provenance': 'fdinfo mnt_id; same mount namespace; bounded scan; NOT I/O attribution'} for (a, b), n in found.items()]
        return links, f'{scanned} processes sampled (top 32, <=128 FDs/process, 120ms); {denied} inaccessible'
