"""Socket observations, bounded ownership attribution and normalized relationships."""
from __future__ import annotations
from collections import defaultdict
import os
from pathlib import Path
import socket
import time
from typing import Any
from .common import Capability, CounterRate, WorkBudget, clean, read_text, stable_id
from .events import EventStore
from .processes import ProcessProvider, parse_stat
from .procfs import display_endpoint, is_loopback, is_unspecified, read_socket_table
from .inet_diag import dump_tcp
from .enrichment import Enricher


class SocketSampler:
    def __init__(self, proc: str | Path = '/proc', source: str = 'auto', max_contacts: int = 20000,
                 budget: float = 0.45, owner_interval: float = 0.75, **_compat: Any) -> None:
        self.proc = Path(proc)
        self.source = source
        self.max_contacts = min(24000, max(256, max_contacts))
        self.budget = max(0.05, min(2.0, budget))
        self.owner_interval = max(0.25, min(5.0, owner_interval))
        self.owner_at = -100.0
        self.capability = Capability('network', 'inet_diag + procfs')
        self.rate = CounterRate()
        self.events = EventStore(entity_limit=self.max_contacts)
        self.owner_cache: dict[str, list[dict[str, Any]]] = {}
        self.fallback_until = -1.0
        self.proc_provider: ProcessProvider | None = None
        self.last_rows: list[dict[str, Any]] = []
        try:
            self.namespace = os.readlink(self.proc / 'self/ns/net')
        except OSError:
            self.namespace = 'current-netns'

    def set_cadence(self, sample_interval: float) -> None:
        # Socket state may refresh rapidly; expensive /proc/<pid>/fd ownership does not.
        self.owner_interval = max(0.75, min(3.0, sample_interval * 2.0))

    def _cached_owners(self, rows: list[dict], processes: list[dict]) -> tuple[dict[str, list[dict]], str]:
        wanted = {r['inode'] for r in rows if r['inode'] != '0'}
        live = {p['key'] for p in processes}
        found = {inode: [o for o in owners if o.get('key') in live]
                 for inode, owners in self.owner_cache.items() if inode in wanted}
        found = {inode: owners for inode, owners in found.items() if owners}
        unknown = len(wanted - found.keys())
        return found, f'ownership cache reused; {unknown} sockets awaiting next bounded ownership scan'

    def owners(self, rows: list[dict], processes: list[dict], *, deadline: float | None = None,
               use_cache: bool = False) -> tuple[dict[str, list[dict]], str]:
        if use_cache:
            cached, note = self._cached_owners(rows, processes)
            missing = [r for r in rows if r.get('inode') not in ('0', None) and r['inode'] not in cached]
            # Keep the expensive full scan multi-rate, but spend at most 80ms on
            # newly observed socket inodes so fresh connections are not falsely
            # unattributed until the next cadence boundary.
            if missing and (deadline is None or time.monotonic() < deadline):
                old_cache = dict(self.owner_cache)
                short_deadline = min(deadline if deadline is not None else time.monotonic() + 0.08, time.monotonic() + 0.08)
                fresh, fresh_note = self.owners(missing, processes, deadline=short_deadline, use_cache=False)
                merged = dict(cached)
                merged.update(fresh)
                wanted = {r['inode'] for r in rows if r.get('inode') not in ('0', None)}
                self.owner_cache = {inode: owners for inode, owners in old_cache.items() if inode in wanted}
                self.owner_cache.update(merged)
                unknown = len(wanted - merged.keys())
                note = (f'ownership cache reused with bounded new-inode scan; {unknown} sockets unattributed'
                        + (('; ' + fresh_note) if fresh_note else ''))
                return merged, note if unknown or fresh_note else ''
            return cached, note
        wanted = {r['inode'] for r in rows if r['inode'] != '0'}
        found: dict[str, list[dict]] = defaultdict(list)
        started = time.monotonic()
        end = min(deadline if deadline is not None else started + 0.25, started + 0.25)
        inaccessible = 0
        scanned = 0
        # Prior owners first, then current UID. Every scanned result revalidates fd AND starttime.
        previous_pids = {p['pid'] for owners in self.owner_cache.values() for p in owners}
        ordered = sorted(processes, key=lambda p: (p['pid'] not in previous_pids, p.get('uid') != os.getuid(), p['pid']))
        for p in ordered:
            if time.monotonic() >= end:
                break
            owned = set()
            try:
                base = self.proc / str(p['pid'])
                for index, fd in enumerate((base / 'fd').iterdir()):
                    if index >= 8192 or time.monotonic() >= end:
                        break
                    try:
                        target = os.readlink(fd)
                    except OSError:
                        continue
                    if target.startswith('socket:[') and target.endswith(']') and target[8:-1] in wanted:
                        owned.add(target[8:-1])
                if parse_stat(read_text(base / 'stat', 8192))['key'] != p['key']:
                    continue
                scanned += 1
                for inode in owned:
                    found[inode].append({'key': p['key'], 'pid': p['pid'], 'startTicks': p['startTicks'],
                                         'name': p['name'], 'executable': p['executable'], 'groupKey': p['groupKey'],
                                         'groupName': p['groupName'], 'groupProvenance': p['groupProvenance']})
            except (OSError, ValueError, IndexError):
                inaccessible += 1
        self.owner_cache = dict(found)
        unknown = len(wanted - found.keys())
        elapsed_ms = int((time.monotonic() - started) * 1000)
        return dict(found), (f'{unknown} sockets unattributed; {inaccessible} inaccessible PID scans; '
                             f'{scanned}/{len(processes)} PIDs scanned within {elapsed_ms}ms') \
            if unknown or inaccessible or scanned < len(processes) else ''

    def sample(self, now: float | None = None, processes: list[dict] | None = None) -> list[dict]:
        now = time.monotonic() if now is None else now
        started = time.monotonic()
        budget = WorkBudget.for_seconds(self.budget, self.max_contacts)
        cap = self.capability = Capability('network', 'inet_diag TCP; procfs UDP', sampledAt=now)
        if processes is None:
            if self.proc_provider is None:
                self.proc_provider = ProcessProvider(self.proc)
            processes = self.proc_provider.sample(now)
        observed: list[dict] = []
        failures: list[str] = []
        sources: list[str] = []
        tables = [('tcp', socket.AF_INET, 'tcp'), ('tcp', socket.AF_INET6, 'tcp6'),
                  ('udp', socket.AF_INET, 'udp'), ('udp', socket.AF_INET6, 'udp6')]
        for proto, family, table in tables:
            remaining = budget.remaining_rows() or 0
            if remaining <= 0 or budget.expired():
                cap.complete = False
                failures.append('global socket work budget exhausted; remaining tables not scanned')
                break
            try:
                rows = None
                if proto == 'tcp' and self.proc == Path('/proc') and self.source != 'proc' and now >= self.fallback_until:
                    try:
                        diag_deadline = max(0.001, min(0.18, budget.remaining_seconds()))
                        rows = dump_tcp(family, remaining, deadline=diag_deadline)
                        sources.append('inet_diag')
                    except (OSError, RuntimeError, ValueError, TimeoutError):
                        self.fallback_until = now + 10
                if rows is None:
                    rows = read_socket_table(self.proc / 'net' / table, proto, family, remaining,
                                             deadline=budget.deadline)
                    sources.append('procfs')
                accepted = rows[:remaining]
                observed.extend(accepted)
                budget.consume(len(accepted))
                if len(rows) >= remaining:
                    cap.complete = False
                    failures.append('socket count reaches global bounded scan; unseen closures not inferred')
                    break
            except FileNotFoundError:
                if family == socket.AF_INET6:
                    continue
                failures.append(table + ' unavailable')
                cap.complete = False
            except (OSError, ValueError) as error:
                failures.append(table + ': ' + clean(error, 120))
                cap.complete = False
        do_owner_scan = now - self.owner_at >= self.owner_interval and not budget.expired()
        ownership, owner_note = self.owners(observed, processes, deadline=budget.deadline, use_cache=not do_owner_scan)
        if do_owner_scan:
            self.owner_at = now
        listeners = [r for r in observed if r['state'] in ('LISTEN', 'BOUND') or not r['remotePort'] or is_unspecified(r['remoteAddress'])]
        listener_ids = {id(r) for r in listeners}
        listener_index: dict[tuple[str, int], list[dict]] = defaultdict(list)
        for listener in listeners:
            listener_index[(listener['proto'], listener['localPort'])].append(listener)
        contacts = []
        for row in observed:
            owners = ownership.get(row['inode'], [])
            primary = owners[0] if owners else {}
            if id(row) in listener_ids:
                kind = 'listen'
                role = 'listener' if row['proto'] == 'tcp' else 'bound-datagram'
                evidence = 'kernel socket state; UDP binding is not a TCP listener'
                # A listening socket queue measures backlog, not payload bytes.
                row['queueBytes'] = row['rxQueueBytes'] = row['txQueueBytes'] = None
            else:
                matching = []
                ownerkeys = {o['key'] for o in owners}
                for listener in listener_index.get((row['proto'], row['localPort']), []):
                    address_match = listener['localAddress'] == row['localAddress'] or (is_unspecified(listener['localAddress']) and (listener['family'] == row['family'] or listener['family'] == 6))
                    owner_match = not ownerkeys or bool(ownerkeys & {o['key'] for o in ownership.get(listener['inode'], [])})
                    if address_match and owner_match:
                        matching.append(listener)
                role = 'accepted-inferred' if matching and row['proto'] == 'tcp' else 'outbound-inferred'
                kind = 'loopback' if is_loopback(row['remoteAddress']) else 'inbound' if role == 'accepted-inferred' else 'outbound'
                evidence = 'matching live listener/protocol/bind address/owner; inferred, not connect provenance' if role == 'accepted-inferred' else 'no matching visible listener; inferred, origin may be unknown'
            identity = [self.namespace, row['proto'], row['family'], row['localAddress'], row['localPort'], row['remoteAddress'], row['remotePort'], row['cookie'] or row['inode']]
            key = stable_id('socket', *identity)
            row.update(key=key, kind=kind, role=role, directionSource=evidence,
                       local=display_endpoint(row['localAddress'], row['localPort']), remote=display_endpoint(row['remoteAddress'], row['remotePort']),
                       owners=owners, ownershipComplete=not owner_note, pid=primary.get('pid'), process=primary.get('name', 'Unattributed'),
                       processKey=primary.get('key'), groupKey=primary.get('groupKey'), command=primary.get('executable', ''),
                       executable=primary.get('executable', ''), ackedBps=None, receivedBps=None)
            for count, field in [('bytesAcked', 'ackedBps'), ('bytesReceived', 'receivedBps')]:
                if row.get(count) is not None:
                    row[field] = self.rate.rate(key + ':' + count, row[count], now)
            contacts.append(row)
        cap.source = '+'.join(sorted(set(sources))) + '; socket inode -> readable procfs fd; current network namespace only'
        if failures or owner_note:
            cap.status = 'partial' if observed else 'unavailable' if failures else 'partial'
            cap.reason = '; '.join(failures + ([owner_note] if owner_note else []))[:1024]
            cap.errorKind = 'budget-or-permission'
            cap.suggestion = 'Partial process attribution is normal without privilege. Namespace visibility is limited to the helper.'
        self.events.update('socket', contacts, now, complete=cap.complete)
        contacts = self.events.decorate('socket', contacts, now, ghosts=True)
        for contact in contacts:
            if contact.get('closed'):
                contact['lastState'] = contact.get('state')
                contact['state'] = 'CLOSED'
        self.last_rows = contacts
        self.rate.prune(now)
        cap.durationMs = round((time.monotonic() - started) * 1000, 3)
        return contacts


def _socket_detail(contact: dict) -> dict:
    detail = dict(contact)
    # Never preserve an argv-like compatibility field in relationship children.
    detail['command'] = detail.get('executable', '')
    return detail


def _owners(contact: dict, instance_mode: bool) -> list[dict]:
    owners = contact.get('owners') or []
    if not owners:
        owners = [{
            'key': contact.get('processKey') or f"process:{contact.get('pid', 'None')}:unverified",
            'pid': contact.get('pid'), 'name': contact.get('process') or 'Unattributed',
            'executable': contact.get('executable') or '',
            'groupKey': contact.get('groupKey') or stable_id('application', contact.get('pid'), contact.get('executable')),
            'groupName': contact.get('process') or 'Unattributed',
            'groupProvenance': 'unattributed socket; process ownership unavailable',
        }]
    return owners


def build_network_model(contacts: list[dict], enricher: Enricher | None = None, now: float | None = None,
                        retain_socket_details: bool = True, instance_mode: bool = False) -> dict[str, Any]:
    """Aggregate contacts without duplicating socket dictionaries when requested.

    Engine snapshots use ``socketKeys`` into one canonical socket store. The
    compatibility/default API still exposes ``sockets`` for direct callers/tests.
    """
    now = time.monotonic() if now is None else now
    processes: dict[str, dict] = {}
    remotes: dict[str, dict] = {}
    links: dict[str, dict] = {}
    listeners: dict[str, dict] = {}
    summary = {'connections': 0, 'processes': 0, 'remoteSystems': 0, 'listeners': 0, 'inbound': 0, 'outbound': 0,
               'loopback': 0, 'recentClosed': sum(bool(c.get('closed')) for c in contacts), 'newConnections': 0}

    for c in contacts:
        owners = _owners(c, instance_mode)
        owners_by_group: dict[str, list[dict]] = defaultdict(list)
        application_by_group: dict[str, str] = {}
        for owner in owners:
            group_key = owner['key'] if instance_mode else owner['groupKey']
            application_by_group[group_key] = owner['groupKey'] if instance_mode else owner.get('applicationKey', group_key)
            owners_by_group[group_key].append(owner)
        closed = bool(c.get('closed'))
        new = not closed and c.get('event', 'opened' if c.get('ageMs', 99999) < 1000 else '') == 'opened'
        if c['kind'] != 'listen' and not closed:
            summary['connections'] += 1
            summary[c['kind']] = summary.get(c['kind'], 0) + 1
            summary['newConnections'] += int(new)
        for group_key, group_owners in owners_by_group.items():
            owner = group_owners[0]
            p = processes.setdefault(group_key, {
                'key': group_key, 'name': owner.get('name') if instance_mode else owner.get('groupName') or owner['name'],
                'groupKey': application_by_group[group_key], 'command': owner.get('executable', ''), 'executable': owner.get('executable', ''),
                'socketCount': 0, 'provenance': owner.get('groupProvenance', ''), 'active': False,
                '_pids': set(), '_processKeys': set(), '_remoteKeys': set(), '_listenerPorts': set(),
            })
            for o in group_owners:
                if o.get('pid') is not None:
                    p['_pids'].add(o['pid'])
                p['_processKeys'].add(o['key'])
            p['active'] = p['active'] or not closed
            p['socketCount'] += int(not closed)
            if c['kind'] == 'listen':
                key = stable_id('listener', group_key, c['proto'], c['family'], c['localAddress'], c['localPort'])
                l = listeners.setdefault(key, {
                    'key': key, 'name': f"{c['proto'].upper()} {c['localPort']}", 'processKey': group_key,
                    'groupKey': application_by_group[group_key], 'proto': c['proto'], 'local': c['local'],
                    'port': c['localPort'], 'state': c['state'], 'socketCount': 0, 'active': False,
                    'role': c.get('role', 'listener'), 'provenance': c.get('directionSource', 'kernel listener state'),
                    '_processKeys': set(), 'sockets' if retain_socket_details else 'socketKeys': [],
                })
                l['socketCount'] += int(not closed)
                l['active'] = l['active'] or not closed
                l['_processKeys'].update(o['key'] for o in group_owners)
                l['sockets' if retain_socket_details else 'socketKeys'].append(_socket_detail(c) if retain_socket_details else c['key'])
                p['_listenerPorts'].add(c['localPort'])
                continue
            remote_key = stable_id('remote', c['family'], c['remoteAddress'])
            name = enricher.resolve(c['remoteAddress'], now) if enricher else {'name': c['remoteAddress'], 'nameSource': 'numeric address', 'address': c['remoteAddress']}
            r = remotes.setdefault(remote_key, {'key': remote_key, **name, 'family': c['family'], 'scope': 'loopback' if c['kind'] == 'loopback' else 'remote',
                                               'socketCount': 0, 'active': False, '_processKeys': set(), '_ports': set()})
            r['_processKeys'].add(group_key)
            r['socketCount'] += int(not closed)
            r['active'] = r['active'] or not closed
            p['_remoteKeys'].add(remote_key)
            service_port = c['localPort'] if c['kind'] == 'inbound' or c.get('role') == 'accepted-inferred' else c['remotePort']
            r['_ports'].add(service_port)
            key = stable_id('relationship', group_key, remote_key, c['proto'], c['kind'], service_port)
            link = links.setdefault(key, {
                'key': key, 'sourceKey': group_key, 'targetKey': remote_key, 'processKey': group_key,
                'remoteKey': remote_key, 'proto': c['proto'], 'kind': c['kind'],
                'direction': {'inbound': 'in', 'loopback': 'local'}.get(c['kind'], 'out'),
                'servicePort': service_port, 'serviceName': enricher.services.get((service_port, c['proto']), '') if enricher else '',
                'socketCount': 0, 'totalSocketCount': 0, 'newCount': 0, 'closedCount': 0, 'closedAgeMs': 0,
                'active': False, 'queueBytes': None, 'ackedBps': None, 'receivedBps': None,
                'sharedOwnership': len(owners_by_group) > 1, 'ageMs': c.get('ageMs', 0),
                'provenance': c.get('directionSource', 'connection direction inferred'),
                'rateSource': 'inet_diag tcp_info cumulative acknowledged/received payload bytes; NOT wire rate; absent when unavailable',
                '_states': set(), '_processKeys': set(), 'sockets' if retain_socket_details else 'socketKeys': [],
            })
            link['active'] = link['active'] or not closed
            link['totalSocketCount'] += 1
            link['socketCount'] += int(not closed)
            link['closedCount'] += int(closed)
            link['newCount'] += int(new)
            link['closedAgeMs'] = max(link['closedAgeMs'], c.get('closedAgeMs', 0))
            link['ageMs'] = max(link['ageMs'], c.get('ageMs', 0))
            link['_states'].add(c['state'])
            link['_processKeys'].update(o['key'] for o in group_owners)
            if not closed:
                for field in ('queueBytes', 'ackedBps', 'receivedBps'):
                    if c.get(field) is not None and (field == 'queueBytes' or len(owners_by_group) == 1):
                        link[field] = (link[field] or 0) + c[field]
            link['sockets' if retain_socket_details else 'socketKeys'].append(_socket_detail(c) if retain_socket_details else c['key'])

    for p in processes.values():
        p['pids'] = sorted(p.pop('_pids'))
        p['processKeys'] = sorted(p.pop('_processKeys'))
        p['remoteKeys'] = sorted(p.pop('_remoteKeys'))
        p['listenerPorts'] = sorted(p.pop('_listenerPorts'))
        if instance_mode:
            p['pid'] = p['pids'][0] if p['pids'] else None
    for r in remotes.values():
        r['processKeys'] = sorted(r.pop('_processKeys'))
        r['ports'] = sorted(r.pop('_ports'))
    for l in listeners.values():
        l['processKeys'] = sorted(l.pop('_processKeys'))
        if not retain_socket_details:
            l['socketDetailCount'] = len(l['socketKeys'])
    for link in links.values():
        link['states'] = sorted(link.pop('_states'))
        link['processKeys'] = sorted(link.pop('_processKeys'))
        if instance_mode:
            link['groupKey'] = processes.get(link['processKey'], {}).get('groupKey')
        if not retain_socket_details:
            link['socketDetailCount'] = len(link['socketKeys'])

    summary['processes'] = sum(p['active'] for p in processes.values())
    summary['remoteSystems'] = sum(r['active'] and r['scope'] == 'remote' for r in remotes.values())
    summary['listeners'] = sum(l['active'] for l in listeners.values())
    summary['relationships'] = sum(l['active'] for l in links.values())
    return {'processes': list(processes.values()), 'remotes': list(remotes.values()),
            'links': list(links.values()), 'listeners': list(listeners.values()), 'summary': summary}


def build_instance_model(contacts: list[dict], enricher: Enricher | None = None, now: float | None = None,
                         retain_socket_details: bool = True, group_keys: set[str] | None = None) -> dict:
    if group_keys is not None:
        wanted = {str(key) for key in group_keys if key}
        if not wanted:
            return {'instances': [], 'instanceLinks': []}
        scoped: list[dict] = []
        for contact in contacts:
            owners = contact.get('owners') or []
            groups = {str(owner.get('groupKey')) for owner in owners if owner.get('groupKey')}
            if contact.get('groupKey'):
                groups.add(str(contact['groupKey']))
            if not groups and not owners:
                groups.add(stable_id('application', contact.get('pid'), contact.get('executable')))
            if groups & wanted:
                scoped.append(contact)
        contacts = scoped
        if not contacts:
            return {'instances': [], 'instanceLinks': []}
    model = build_network_model(contacts, enricher, now, retain_socket_details=retain_socket_details, instance_mode=True)
    return {'instances': model['processes'], 'instanceLinks': model['links']}
