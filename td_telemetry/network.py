"""Socket observations, safe ownership attribution and application relationships."""
from __future__ import annotations
from collections import defaultdict
import os
from pathlib import Path
import socket
import time
from typing import Any
from .common import Capability, CounterRate, clean, failure, read_text, stable_id
from .events import EventStore
from .processes import ProcessProvider, parse_stat
from .procfs import classify_socket, display_endpoint, is_loopback, is_unspecified, read_socket_table
from .inet_diag import dump_tcp
from .enrichment import Enricher


class SocketSampler:
    def __init__(self, proc: str | Path = '/proc', source: str = 'auto', max_contacts: int = 20000, **_compat: Any) -> None:
        self.proc = Path(proc)
        self.source = source
        self.max_contacts = min(24000, max(256, max_contacts))
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

    def owners(self, rows: list[dict], processes: list[dict]) -> tuple[dict[str, list[dict]], str]:
        wanted = {r['inode'] for r in rows if r['inode'] != '0'}
        found: dict[str, list[dict]] = defaultdict(list)
        started = time.monotonic()
        inaccessible = 0
        scanned = 0
        # Prior owners first, then current UID. Every result revalidates fd AND starttime.
        previous_pids = {p['pid'] for owners in self.owner_cache.values() for p in owners}
        ordered = sorted(processes, key=lambda p: (p['pid'] not in previous_pids, p.get('uid') != os.getuid(), p['pid']))
        for p in ordered:
            if time.monotonic() - started > 0.25:
                break
            owned = set()
            try:
                base = self.proc / str(p['pid'])
                for index, fd in enumerate((base / 'fd').iterdir()):
                    if index >= 8192 or time.monotonic() - started > 0.25:
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
        return dict(found), f'{unknown} sockets unattributed; {inaccessible} inaccessible PID scans; {scanned}/{len(processes)} PIDs scanned within 250ms' if unknown or inaccessible or scanned < len(processes) else ''

    def sample(self, now: float | None = None, processes: list[dict] | None = None) -> list[dict]:
        now = time.monotonic() if now is None else now
        started = time.monotonic()
        cap = self.capability = Capability('network', 'inet_diag TCP; procfs UDP', sampledAt=now)
        if processes is None:
            if self.proc_provider is None:
                self.proc_provider = ProcessProvider(self.proc)
            processes = self.proc_provider.sample(now)
        observed = []
        failures = []
        sources = []
        for proto, family, table in [('tcp', socket.AF_INET, 'tcp'), ('tcp', socket.AF_INET6, 'tcp6'),
                                      ('udp', socket.AF_INET, 'udp'), ('udp', socket.AF_INET6, 'udp6')]:
            try:
                rows = None
                if proto == 'tcp' and self.proc == Path('/proc') and self.source != 'proc' and now >= self.fallback_until:
                    try:
                        rows = dump_tcp(family, self.max_contacts)
                        sources.append('inet_diag')
                    except (OSError, RuntimeError, ValueError, TimeoutError):
                        self.fallback_until = now + 10
                if rows is None:
                    rows = read_socket_table(self.proc / 'net' / table, proto, family, self.max_contacts + 1)
                    sources.append('procfs')
                if len(rows) + len(observed) > self.max_contacts:
                    cap.complete = False
                    failures.append('socket count exceeds bounded scan; unseen closures not inferred')
                observed.extend(rows[:max(0, self.max_contacts - len(observed))])
            except FileNotFoundError:
                if family == socket.AF_INET6:
                    continue
                failures.append(table + ' unavailable')
                cap.complete = False
            except (OSError, ValueError) as error:
                failures.append(table + ': ' + clean(error, 120))
                cap.complete = False
        ownership, owner_note = self.owners(observed, processes)
        listeners = [r for r in observed if r['state'] in ('LISTEN', 'BOUND') or not r['remotePort'] or is_unspecified(r['remoteAddress'])]
        listener_ids = {id(r) for r in listeners}
        listener_index: dict[tuple[str, int], list[dict]] = defaultdict(list)
        for listener in listeners:
            listener_index[(listener['proto'], listener['localPort'])].append(listener)
        contacts = []
        for row in observed:
            owners = ownership.get(row['inode'], [])
            primary = owners[0] if owners else {}
            role = 'unknown'
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
            cap.reason = '; '.join(failures + ([owner_note] if owner_note else []))
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


def build_network_model(contacts: list[dict], enricher: Enricher | None = None, now: float | None = None) -> dict[str, Any]:
    now = time.monotonic() if now is None else now
    processes: dict[str, dict] = {}
    remotes: dict[str, dict] = {}
    links: dict[str, dict] = {}
    listeners: dict[str, dict] = {}
    active = [c for c in contacts if not c.get('closed')]
    summary = {'connections': 0, 'processes': 0, 'remoteSystems': 0, 'listeners': 0, 'inbound': 0, 'outbound': 0,
               'loopback': 0, 'recentClosed': sum(bool(c.get('closed')) for c in contacts), 'newConnections': 0}
    for raw_contact in contacts:
        c = dict(raw_contact)
        c['command'] = c.get('executable', '')
        owners = c.get('owners') or [{'key': c.get('processKey') or f"process:{c.get('pid', 'unknown')}:unverified", 'pid': c.get('pid'),
                                     'name': c.get('process', 'Unattributed'), 'executable': c.get('executable', ''),
                                     'groupKey': c.get('groupKey') or stable_id('application', c.get('pid'), c.get('executable')),
                                     'groupName': c.get('process', 'Unattributed'), 'groupProvenance': 'compatibility/unknown process identity'}]
        owners_by_group: dict[str, list[dict]] = defaultdict(list)
        for owner in owners:
            owners_by_group[owner['groupKey']].append(owner)
        closed = bool(c.get('closed'))
        new = not closed and c.get('event', 'opened' if c.get('ageMs', 99999) < 1000 else '') == 'opened'
        if c['kind'] != 'listen' and not closed:
            summary['connections'] += 1
            summary[c['kind']] = summary.get(c['kind'], 0) + 1
            summary['newConnections'] += int(new)
        for group_key, group_owners in owners_by_group.items():
            owner = group_owners[0]
            p = processes.setdefault(group_key, {'key': group_key, 'name': owner.get('groupName') or owner['name'],
                                                'pids': [], 'processKeys': [], 'groupKey': owner.get('applicationKey', group_key), 'command': owner.get('executable', ''), 'executable': owner.get('executable', ''),
                                                'socketCount': 0, 'remoteKeys': [], 'listenerPorts': [], 'provenance': owner.get('groupProvenance', ''), 'active': False})
            for o in group_owners:
                if o.get('pid') is not None and o['pid'] not in p['pids']:
                    p['pids'].append(o['pid'])
                if o['key'] not in p['processKeys']:
                    p['processKeys'].append(o['key'])
            p['active'] = p['active'] or not closed
            p['socketCount'] += int(not closed)
            if c['kind'] == 'listen':
                key = stable_id('listener', group_key, c['proto'], c['family'], c['localAddress'], c['localPort'])
                l = listeners.setdefault(key, {'key': key, 'name': f"{c['proto'].upper()} {c['localPort']}", 'processKey': group_key,
                                              'groupKey': group_key, 'processKeys': p['processKeys'], 'proto': c['proto'], 'local': c['local'],
                                              'port': c['localPort'], 'state': c['state'], 'socketCount': 0, 'active': False, 'sockets': [],
                                              'role': c.get('role', 'listener'), 'provenance': c.get('directionSource', 'kernel listener state')})
                l['socketCount'] += int(not closed)
                l['active'] = l['active'] or not closed
                l['sockets'].append(c)
                if c['localPort'] not in p['listenerPorts']:
                    p['listenerPorts'].append(c['localPort'])
                continue
            remote_key = stable_id('remote', c['family'], c['remoteAddress'])
            name = enricher.resolve(c['remoteAddress'], now) if enricher else {'name': c['remoteAddress'], 'nameSource': 'numeric address', 'address': c['remoteAddress']}
            r = remotes.setdefault(remote_key, {'key': remote_key, **name, 'family': c['family'], 'scope': 'loopback' if c['kind'] == 'loopback' else 'remote',
                                               'processKeys': [], 'socketCount': 0, 'ports': [], 'active': False})
            if group_key not in r['processKeys']:
                r['processKeys'].append(group_key)
            r['socketCount'] += int(not closed)
            r['active'] = r['active'] or not closed
            if remote_key not in p['remoteKeys']:
                p['remoteKeys'].append(remote_key)
            service_port = c['localPort'] if c['kind'] == 'inbound' or c.get('role') == 'accepted-inferred' else c['remotePort']
            if service_port not in r['ports']:
                r['ports'].append(service_port)
            key = stable_id('relationship', group_key, remote_key, c['proto'], c['kind'], service_port)
            link = links.setdefault(key, {'key': key, 'sourceKey': group_key, 'targetKey': remote_key, 'processKey': group_key,
                                          'remoteKey': remote_key, 'proto': c['proto'], 'kind': c['kind'], 'direction': {'inbound': 'in', 'loopback': 'local'}.get(c['kind'], 'out'),
                                          'servicePort': service_port, 'serviceName': enricher.services.get((service_port, c['proto']), '') if enricher else '',
                                          'states': [], 'socketCount': 0, 'totalSocketCount': 0, 'newCount': 0, 'closedCount': 0, 'closedAgeMs': 0,
                                          'active': False, 'queueBytes': None, 'ackedBps': None, 'receivedBps': None,
                                          'sockets': [], 'sharedOwnership': len(owners_by_group) > 1, 'processKeys': [],
                                          'ageMs': c.get('ageMs', 0), 'provenance': c.get('directionSource', 'connection direction inferred'),
                                          'rateSource': 'inet_diag tcp_info cumulative acknowledged/received payload bytes; NOT wire rate; absent when unavailable'})
            link['active'] = link['active'] or not closed
            link['totalSocketCount'] += 1
            link['socketCount'] += int(not closed)
            link['closedCount'] += int(closed)
            link['newCount'] += int(new)
            link['closedAgeMs'] = max(link['closedAgeMs'], c.get('closedAgeMs', 0))
            link['ageMs'] = max(link['ageMs'], c.get('ageMs', 0))
            if c['state'] not in link['states']:
                link['states'].append(c['state'])
            for o in group_owners:
                if o['key'] not in link['processKeys']:
                    link['processKeys'].append(o['key'])
            if not closed:
                for field in ('queueBytes', 'ackedBps', 'receivedBps'):
                    if c.get(field) is not None and (field == 'queueBytes' or len(owners_by_group) == 1):
                        link[field] = (link[field] or 0) + c[field]
            link['sockets'].append(c)
    summary['processes'] = sum(p['active'] for p in processes.values())
    summary['remoteSystems'] = sum(r['active'] and r['scope'] == 'remote' for r in remotes.values())
    summary['listeners'] = sum(l['active'] for l in listeners.values())
    summary['relationships'] = sum(l['active'] for l in links.values())
    return {'processes': list(processes.values()), 'remotes': list(remotes.values()), 'links': list(links.values()), 'listeners': list(listeners.values()), 'summary': summary}


def build_instance_model(contacts: list[dict], enricher: Enricher | None = None, now: float | None = None) -> dict:
    per_instance = []
    for contact in contacts:
        owners = contact.get('owners') or []
        if not owners:
            # Keep ownerless sockets visible when an application is expanded.  The
            # aggregate model already represents these sockets with the same
            # synthetic identity; dropping them here made root-owned services such
            # as sshd disappear from Connection Field as soon as the group switched
            # to per-instance rendering.
            owners = [{
                'key': contact.get('processKey') or f"process:{contact.get('pid', 'None')}:unverified",
                'pid': contact.get('pid'),
                'name': contact.get('process') or 'Unattributed',
                'executable': contact.get('executable') or '',
                'groupKey': contact.get('groupKey') or stable_id('application', contact.get('pid'), contact.get('executable')),
                'groupName': contact.get('process') or 'Unattributed',
                'groupProvenance': 'unattributed socket; process ownership unavailable',
            }]
        c = dict(contact)
        c['owners'] = [{**owner, 'applicationKey': owner['groupKey'], 'groupKey': owner['key'], 'groupName': owner['name']} for owner in owners]
        # Shared file descriptors cannot be uniquely attributed to individual processes.
        if len(owners) > 1:
            c['ackedBps'] = c['receivedBps'] = None
        per_instance.append(c)
    model = build_network_model(per_instance, enricher, now)
    groups = {p['key']: p['groupKey'] for p in model['processes']}
    for p in model['processes']:
        p['pid'] = p['pids'][0] if p['pids'] else None
    for link in model['links']:
        link['groupKey'] = groups.get(link['processKey'])
    return {'instances': model['processes'], 'instanceLinks': model['links']}
