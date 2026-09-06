"""Process instances, ancestry and accounting. Never opens cmdline/environ."""
from __future__ import annotations
import os
from pathlib import Path
import re
import time
from typing import Any
from .common import Capability, CounterRate, clean, failure, optional_text, read_text, stable_id

MAX_PROCESSES = 8192
GENERIC = {'python', 'python3', 'node', 'nodejs', 'ruby', 'java', 'bash', 'sh', 'zsh', 'fish', 'perl', 'php', 'elixir', 'beam.smp'}


def parse_stat(text: str, page_size: int = 4096) -> dict[str, Any]:
    start, end = text.index('('), text.rindex(')')
    pid = int(text[:start].strip())
    fields = text[end + 1:].split()
    ticks = int(fields[19])
    return {'key': f'process:{pid}:{ticks}', 'pid': pid, 'ppid': int(fields[1]),
            'startTicks': ticks, 'name': clean(text[start + 1:end]), 'state': fields[0],
            'cpuTicks': int(fields[11]) + int(fields[12]), 'threads': int(fields[17]),
            'rssBytes': max(0, int(fields[21])) * page_size}


def application_unit(cgroup: str) -> str:
    # A session/user/container slice is NOT an application identity.
    candidates = [p for p in cgroup.split('/') if p.endswith(('.scope', '.service'))]
    for unit in reversed(candidates):
        if unit.startswith(('session-', 'user@', 'init.scope', 'systemd-', 'dbus.', 'docker-', 'containerd-')):
            continue
        if unit.startswith(('app-', 'app.')) or unit.endswith('.service'):
            return unit
    return ''


def assign_groups(rows: list[dict[str, Any]], deadline: float | None = None) -> list[dict[str, Any]]:
    if deadline is not None and time.monotonic() >= deadline:
        return []
    bounded: list[dict[str, Any]] = []
    for p in rows:
        if deadline is not None and time.monotonic() >= deadline:
            break
        bounded.append(p)
    rows = bounded
    by_pid = {p['pid']: p for p in rows}
    # Runtime-tree ancestry is shared by descendants. Path compression avoids
    # walking the same deep Python/Node/BEAM chain once per process (O(N^2)).
    runtime_roots: dict[str, dict[str, Any]] = {}

    def runtime_root(process: dict[str, Any], exe: str) -> dict[str, Any]:
        cached = runtime_roots.get(process['key'])
        if cached is not None:
            return cached
        path: list[dict[str, Any]] = []
        ancestor = process
        hops = 0
        while True:
            if deadline is not None and hops % 32 == 0 and time.monotonic() >= deadline:
                raise TimeoutError('process grouping deadline exceeded')
            hops += 1
            cached = runtime_roots.get(ancestor['key'])
            if cached is not None:
                root = cached
                break
            path.append(ancestor)
            parent = by_pid.get(ancestor['ppid'])
            if (not parent or parent.get('executable') != exe or parent.get('uid') != process.get('uid')
                    or parent['startTicks'] > ancestor['startTicks']):
                root = ancestor
                break
            ancestor = parent
        for item in path:
            runtime_roots[item['key']] = root
        return root

    grouped: list[dict[str, Any]] = []
    for p in rows:
        if deadline is not None and time.monotonic() >= deadline:
            break
        exe = p.get('executable', '')
        name = Path(exe).name or p['name']
        unit = application_unit(p.get('cgroup', ''))
        generic = name in GENERIC or bool(re.fullmatch(r'python\d+(?:\.\d+)*', name))
        if unit:
            identity, provenance = ('cgroup', p.get('uid'), unit), 'cgroup unit (observed)'
        elif exe and not generic:
            identity, provenance = ('executable', p.get('uid'), exe), 'same executable and UID (grouping)'
        elif generic:
            try:
                ancestor = runtime_root(p, exe)
            except TimeoutError:
                break
            identity, provenance = ('runtime-tree', exe, ancestor['key']), 'runtime ancestry (not name-only)'
        else:
            identity, provenance = ('instance', p['key']), 'process instance; insufficient grouping identity'
        p['groupKey'] = stable_id('application', *identity)
        p['groupName'] = unit or name
        p['groupProvenance'] = provenance
        parent = by_pid.get(p['ppid'])
        # A sampled parent younger than its child cannot be the original parent.
        p['parentKey'] = parent['key'] if parent and parent['startTicks'] <= p['startTicks'] else None
        grouped.append(p)
    live_keys = {p['key'] for p in grouped}
    for p in grouped:
        if p.get('parentKey') not in live_keys:
            p['parentKey'] = None
    return grouped


class ProcessProvider:
    def __init__(self, proc: str | Path = '/proc', budget: float = 0.35) -> None:
        self.proc = Path(proc)
        self.budget = budget
        self.page_size = os.sysconf('SC_PAGE_SIZE')
        self.hz = os.sysconf('SC_CLK_TCK')
        self.rate = CounterRate()
        self.capability = Capability('processes', '/proc/<pid>/{stat,status,exe,cgroup,io}')
        self.identities: dict[str, tuple[float, str, str]] = {}
        self.rows: list[dict[str, Any]] = []

    def sample(self, now: float) -> list[dict[str, Any]]:
        started = time.monotonic()
        cap = self.capability = Capability('processes', '/proc/<pid>/{stat,status,exe,cgroup,io}', sampledAt=now)
        rows: list[dict[str, Any]] = []
        inaccessible = 0
        io_denied = 0
        truncated = 0
        try:
            deadline = started + self.budget
            grouping_reserve = min(0.075, max(0.01, self.budget * 0.22))
            scan_deadline = max(started, deadline - grouping_reserve)
            pids: list[int] = []
            discovery_truncated = False
            for entry in self.proc.iterdir():
                if time.monotonic() >= scan_deadline:
                    discovery_truncated = True
                    break
                if entry.name.isdigit():
                    pids.append(int(entry.name))
                    if len(pids) >= MAX_PROCESSES * 4:
                        discovery_truncated = True
                        break
            pids.sort()
            for index, pid in enumerate(pids):
                if len(rows) >= MAX_PROCESSES or time.monotonic() >= scan_deadline:
                    truncated = max(1 if discovery_truncated else 0, len(pids) - index)
                    break
                path = self.proc / str(pid)
                try:
                    p = parse_stat(read_text(path / 'stat', 8192), self.page_size)
                    status = read_text(path / 'status', 32768)
                    uidline = next((s for s in status.splitlines() if s.startswith('Uid:')), '')
                    p['uid'] = int(uidline.split()[1]) if uidline else path.stat().st_uid
                    cached = self.identities.get(p['key'])
                    if cached and now - cached[0] < 5:
                        _, exe, cgroup = cached
                    else:
                        try:
                            exe = clean(os.readlink(path / 'exe'))
                        except OSError:
                            exe = ''
                        cgroups = optional_text(path / 'cgroup', limit=32768).splitlines()
                        cgroup = clean(next((line for line in cgroups if line.startswith('0::')), cgroups[0] if cgroups else ''))
                        self.identities[p['key']] = (now, exe, cgroup)
                    p.update(executable=exe, cgroup=cgroup, command=exe or p['name'])
                    cpu = self.rate.rate(p['key'] + ':cpu', p['cpuTicks'], now)
                    p['cpuPercent'] = None if cpu is None else round(cpu / self.hz * 100, 2)
                    p['readBps'] = p['writeBps'] = None
                    p['readBytes'] = p['writeBytes'] = None
                    try:
                        io = dict(line.split(':', 1) for line in read_text(path / 'io', 4096).splitlines() if ':' in line)
                        for field, source in (('read', 'read_bytes'), ('write', 'write_bytes')):
                            val = int(io[source])
                            p[field + 'Bytes'] = val
                            p[field + 'Bps'] = self.rate.rate(p['key'] + ':' + field, val, now)
                        p['ioAvailable'] = True
                    except (OSError, ValueError, KeyError):
                        io_denied += 1
                        p['ioAvailable'] = False
                    # Recheck identity after the set of reads: reject PID reuse races.
                    if parse_stat(read_text(path / 'stat', 8192))['key'] != p['key']:
                        continue
                    p['provenance'] = {'identity': '/proc/pid/stat starttime', 'cpuPercent': 'derived ticks/sec; one core=100%',
                                       'rssBytes': '/proc/pid/stat resident pages (shared pages not deduplicated)',
                                       'io': '/proc/pid/io storage-accounted bytes; no mount attribution'}
                    rows.append(p)
                except FileNotFoundError:
                    continue  # normal process exit race, not a provider outage
                except (PermissionError, ValueError, IndexError, OSError):
                    inaccessible += 1
            if discovery_truncated and not truncated:
                truncated = 1
            if inaccessible or truncated or io_denied:
                cap.status = 'partial'
                cap.complete = not (inaccessible or truncated)
                cap.errorKind = 'budget' if truncated else 'permission' if inaccessible or io_denied else ''
                cap.reason = f'{inaccessible} process records inaccessible; {io_denied} I/O records inaccessible; {truncated} outside scan budget'
                cap.suggestion = 'Missing ownership/I/O is normal under procfs permissions; do not elevate privileges.'
            before_grouping = len(rows)
            rows = assign_groups(rows, deadline=deadline)
            if len(rows) < before_grouping:
                truncated += before_grouping - len(rows)
                cap.status = 'partial'
                cap.complete = False
                cap.errorKind = 'budget'
                cap.reason = (cap.reason + '; ' if cap.reason else '') + f'{before_grouping - len(rows)} outside grouping deadline'
        except (OSError, ValueError) as error:
            failure(cap, error, 'Mount readable procfs for this user/namespace.')
        live = {p['key'] for p in rows}
        self.identities = {k: v for k, v in self.identities.items() if k in live}
        self.rate.prune(now)
        self.rows = rows
        cap.durationMs = round((time.monotonic() - started) * 1000, 3)
        return rows


def group_processes(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[str, dict[str, Any]] = {}
    for p in rows:
        key = p['groupKey']
        g = groups.setdefault(key, {'key': key, 'name': p['groupName'], 'processKeys': [], 'pids': [],
                                   'rssBytes': 0, 'threads': 0, 'cpuPercent': None, 'readBps': None, 'writeBps': None,
                                   'provenance': p['groupProvenance'], 'executable': p['executable'], 'cgroup': p['cgroup']})
        g['processKeys'].append(p['key'])
        g['pids'].append(p['pid'])
        g['rssBytes'] += p['rssBytes']
        g['threads'] += p['threads']
        for field in ('cpuPercent', 'readBps', 'writeBps'):
            if p.get(field) is not None:
                g[field] = (g[field] or 0) + p[field]
    return sorted(groups.values(), key=lambda g: g['key'])