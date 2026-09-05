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


def assign_groups(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_pid = {p['pid']: p for p in rows}
    for p in rows:
        exe = p.get('executable', '')
        name = Path(exe).name or p['name']
        unit = application_unit(p.get('cgroup', ''))
        generic = name in GENERIC or bool(re.fullmatch(r'python\d+(?:\.\d+)*', name))
        if unit:
            identity, provenance = ('cgroup', p.get('uid'), unit), 'cgroup unit (observed)'
        elif exe and not generic:
            identity, provenance = ('executable', p.get('uid'), exe), 'same executable and UID (grouping)'
        elif generic:
            ancestor = p
            seen = set()
            while ancestor['ppid'] in by_pid and ancestor['ppid'] not in seen:
                parent = by_pid[ancestor['ppid']]
                if parent.get('executable') != exe or parent.get('uid') != p.get('uid') or parent['startTicks'] > ancestor['startTicks']:
                    break
                seen.add(parent['pid'])
                ancestor = parent
            identity, provenance = ('runtime-tree', exe, ancestor['key']), 'runtime ancestry (not name-only)'
        else:
            identity, provenance = ('instance', p['key']), 'process instance; insufficient grouping identity'
        p['groupKey'] = stable_id('application', *identity)
        p['groupName'] = unit or name
        p['groupProvenance'] = provenance
        parent = by_pid.get(p['ppid'])
        # A sampled parent younger than its child cannot be the original parent.
        p['parentKey'] = parent['key'] if parent and parent['startTicks'] <= p['startTicks'] else None
    return rows


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
            pids = sorted(int(p.name) for p in self.proc.iterdir() if p.name.isdigit())
            for index, pid in enumerate(pids):
                if len(rows) >= MAX_PROCESSES or time.monotonic() - started > self.budget:
                    truncated = len(pids) - index
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
            if inaccessible or truncated or io_denied:
                cap.status = 'partial'
                cap.complete = not (inaccessible or truncated)
                cap.errorKind = 'budget' if truncated else 'permission' if inaccessible or io_denied else ''
                cap.reason = f'{inaccessible} process records inaccessible; {io_denied} I/O records inaccessible; {truncated} outside scan budget'
                cap.suggestion = 'Missing ownership/I/O is normal under procfs permissions; do not elevate privileges.'
            assign_groups(rows)
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
