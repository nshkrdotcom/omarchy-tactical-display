"""Versioned, instrument-scoped orchestration and bounded transport snapshots."""
from __future__ import annotations
from copy import deepcopy
import json
import time
from typing import Any
from . import SCHEMA_VERSION
from .common import MAX_FRAME, Capability, clean, failure
from .processes import ProcessProvider, group_processes
from .network import SocketSampler, build_network_model, build_instance_model
from .machine import MachineProvider
from .storage import StorageProvider
from .audio import AudioProvider
from .hardware import HardwareProvider
from .enrichment import Enricher
from .events import EventStore, TrendWindow

INSTRUMENTS = ('connection', 'processes', 'machine', 'storage', 'audio')
PROFILES = {'efficient': 1.5, 'balanced': 0.75, 'responsive': 0.35}
PROVIDERS = {'connection': {'processes', 'network', 'machine'},
             'processes': {'processes', 'network', 'machine'},
             'machine': {'processes', 'network', 'machine', 'storage', 'hardware'},
             'storage': {'processes', 'machine', 'storage'},
             'audio': {'processes', 'audio'}}


class TelemetryEngine:
    def __init__(self, instrument: str = 'connection', profile: str = 'balanced', interval: float | None = None, source: str = 'auto') -> None:
        self.process_provider = ProcessProvider()
        self.network_provider = SocketSampler(source=source)
        self.machine_provider = MachineProvider()
        self.storage_provider = StorageProvider()
        self.audio_provider = AudioProvider()
        self.hardware_provider = HardwareProvider()
        self.enricher = Enricher()
        self.events = EventStore()
        self.trend = TrendWindow()
        self.instrument = instrument if instrument in INSTRUMENTS + ('all',) else 'connection'
        self.profile = profile if profile in PROFILES else 'balanced'
        self.interval_override = max(0.25, min(10, interval)) if interval is not None else None
        self.last_active: set[str] = set()
        self.sequence = 0
        self.full: dict[str, Any] = {}
        self.frozen_full: dict[str, Any] | None = None
        self.allow_actions = False
        self.closed = False

    @property
    def interval(self) -> float:
        return self.interval_override or PROFILES[self.profile]

    def configure(self, command: dict[str, Any]) -> None:
        instrument = command.get('instrument', self.instrument)
        if instrument in INSTRUMENTS:
            self.instrument = instrument
        profile = command.get('profile', self.profile)
        if profile in PROFILES:
            self.profile = profile
        self.enricher.configure(mode=command.get('naming', self.enricher.mode), aliases=command.get('aliases', self.enricher.aliases),
                                privacy=command.get('privacy') is True, offline_db=str(command.get('offlineDb', self.enricher.offline_path))[:4096])
        self.allow_actions = command.get('audioActions') is True

    def sample(self) -> dict[str, Any]:
        started = now = time.monotonic()
        active = set().union(*PROVIDERS.values()) if self.instrument == 'all' else PROVIDERS[self.instrument]
        if 'network' in active and 'network' not in self.last_active:
            self.network_provider.events.reset_domain('socket')
            for domain in ('relationship', 'remote', 'listener'):
                self.events.reset_domain(domain)
        if 'audio' in active and 'audio' not in self.last_active:
            self.events.reset_domain('audio-node')
            self.events.reset_domain('audio-link')
        if 'storage' in active and 'storage' not in self.last_active:
            self.events.reset_domain('mount')
        self.last_active = active
        caps: dict[str, dict] = {}
        data: dict[str, Any] = {'schemaVersion': SCHEMA_VERSION, 'version': SCHEMA_VERSION, 'type': 'snapshot', 'sequence': self.sequence,
                               'monotonic': now, 'wallTime': time.time(), 'instrument': self.instrument,
                               'intervalSeconds': self.interval, 'capabilities': caps, 'processes': [], 'groups': [], 'system': {},
                               'network': {'processes': [], 'remotes': [], 'links': [], 'listeners': [], 'instances': [], 'instanceLinks': [], 'summary': {}},
                               'storage': {'devices': [], 'mounts': [], 'links': [], 'contributors': [], 'summary': {}},
                               'audio': {'nodes': [], 'devices': [], 'clients': [], 'ports': [], 'links': [], 'defaults': {}, 'summary': {}},
                               'hardware': {'gpus': [], 'thermals': [], 'fans': []}, 'events': [], 'trend': [],
                               'limits': {'maxFrameBytes': MAX_FRAME, 'transportTruncated': False, 'omitted': {}}}
        def collect(name: str, provider: Any, fn: Any, default: Any) -> Any:
            if name not in active:
                caps[name] = Capability(name, provider.capability.source, status='inactive', level='not sampled', complete=False,
                                        reason='Provider is not needed by the active instrument.', intervalSeconds=self.interval).json()
                return default
            try:
                value = fn()
            except Exception as error:
                # A defective/malformed optional source must not kill the helper or shell.
                provider.capability = Capability(name, provider.capability.source, sampledAt=now)
                failure(provider.capability, error, 'Inspect provider capability details; retry or run doctor.')
                value = default
            cap = provider.capability.json()
            if name != 'audio':
                cap['intervalSeconds'] = self.interval
            caps[name] = cap
            return value
        rows = collect('processes', self.process_provider, lambda: self.process_provider.sample(now), [])
        self.events.update('process', rows, now, complete=caps['processes']['complete'])
        data['processes'] = self.events.decorate('process', rows, now, ghosts=True)
        data['groups'] = group_processes(rows)
        contacts = collect('network', self.network_provider, lambda: self.network_provider.sample(now, rows), [])
        if 'network' in active:
            self.enricher.tick(now)
            model = build_network_model(contacts, self.enricher, now)
            for collection, domain in [('links', 'relationship'), ('remotes', 'remote'), ('listeners', 'listener')]:
                observed = [r for r in model[collection] if r.get('active', True)]
                self.events.update(domain, observed, now, complete=caps['network']['complete'])
                model[collection] = self.events.decorate(domain, observed, now, ghosts=True)
            model.update(build_instance_model(contacts, self.enricher, now))
            if caps['network']['status'] == 'unavailable':
                model['summary'] = {k: None for k in model['summary']}
            data['network'] = model
            summaries = {p['key']: p for p in model['processes']}
            for p in data['processes']:
                net = summaries.get(p['groupKey'], {})
                p['groupNetworkSockets'] = net.get('socketCount', None if caps['network']['status'] != 'available' else 0)
                p['networkSource'] = 'application-group socket count, not per-process byte throughput'
            for g in data['groups']:
                g['networkSockets'] = summaries.get(g['key'], {}).get('socketCount', None if caps['network']['status'] != 'available' else 0)
        data['system'] = collect('machine', self.machine_provider, lambda: self.machine_provider.sample(now), {})
        data['storage'] = collect('storage', self.storage_provider, lambda: self.storage_provider.sample(now, rows, topology=self.instrument in ('all', 'storage', 'machine')), data['storage'])
        if 'storage' in active:
            self.events.update('mount', data['storage']['mounts'], now, complete=caps['storage']['complete'])
            data['storage']['mounts'] = self.events.decorate('mount', data['storage']['mounts'], now, ghosts=True)
        data['audio'] = collect('audio', self.audio_provider, lambda: self.audio_provider.sample(now, rows), data['audio'])
        data['audio'] = dict(data['audio'])
        if 'audio' in active:
            for collection, domain in [('nodes', 'audio-node'), ('links', 'audio-link')]:
                self.events.update(domain, data['audio'][collection], now, complete=caps['audio']['complete'])
                data['audio'][collection] = self.events.decorate(domain, data['audio'][collection], now, ghosts=True)
        if 'hardware' in active:
            try:
                data['hardware'] = self.hardware_provider.sample(now)
                caps.update(self.hardware_provider.capabilities)
            except Exception as error:
                for name in ('gpu', 'thermal'):
                    cap = Capability(name, 'optional hardware', sampledAt=now)
                    failure(cap, error)
                    caps[name] = cap.json()
        else:
            for name in ('gpu', 'thermal'):
                caps[name] = Capability(name, 'optional hardware', status='inactive', level='optional', complete=False, intervalSeconds=5).json()
        caps['enrichment'] = Capability('enrichment', 'aliases,/etc/hosts,/etc/services' + ('; opt-in system reverse DNS' if self.enricher.mode == 'dns' and not self.enricher.privacy else ''),
                                        sampledAt=now, intervalSeconds=self.interval, status='partial' if self.enricher.offline_error else 'available',
                                        reason=self.enricher.offline_error).json()
        if 'machine' in active:
            pressure_rows = []
            for subsystem, key in [('cpu', 'cpu'), ('memory', 'memory'), ('io', 'storage')]:
                pressure = data['system'].get('pressure', {}).get(subsystem) or {}
                value = (pressure.get('some') or {}).get('avg10')
                if value is not None:
                    pressure_rows.append({'key': 'subsystem:' + key, 'pressure': 'elevated' if value >= 5 else 'normal'})
            self.events.update('pressure', pressure_rows, now, complete=False)
        data['events'] = self.events.events(now)
        if 'machine' in active:
            m = data['system']
            data['trend'] = self.trend.add(now, {'cpuPercent': m.get('cpuPercent'), 'memoryUsedBytes': m.get('memory', {}).get('usedBytes'),
                                               'netRxBps': m.get('netRxBps'), 'netTxBps': m.get('netTxBps'),
                                               'readBps': data['storage']['summary'].get('readBps'), 'writeBps': data['storage']['summary'].get('writeBps')})
        data['sampleDurationMs'] = round((time.monotonic() - started) * 1000, 3)
        self.full = data
        self.sequence += 1
        return self.transport(data)

    @staticmethod
    def transport(full: dict[str, Any]) -> dict[str, Any]:
        # Keep child socket details in helper memory; preview/paging avoids quadratic wire duplication.
        data = dict(full)
        data['limits'] = deepcopy(full['limits'])
        data['network'] = dict(full['network'])
        for name in ('links', 'listeners', 'instanceLinks'):
            data['network'][name] = []
            for row in full['network'].get(name, []):
                r = {k: v for k, v in row.items() if k != 'sockets'}
                sockets = row.get('sockets', [])
                r['socketPreview'] = sockets[:2]
                r['socketDetailCount'] = len(sockets)
                data['network'][name].append(r)
        data['processes'] = [{k: v for k, v in p.items() if k not in ('command', 'provenance', 'networkSource')} for p in full['processes']]
        data['audio'] = dict(full['audio'])
        data['storage'] = dict(full['storage'])
        data['storage']['contributors'] = [{k: p.get(k) for k in ('key', 'pid', 'name', 'groupKey', 'readBps', 'writeBps', 'readBytes', 'writeBytes')} for p in full['storage']['contributors']]
        # Pathological hosts still produce a valid frame. Omission counts are never hidden.
        def size() -> int:
            return len(json.dumps(data, separators=(',', ':'), ensure_ascii=True, allow_nan=False).encode())
        arrays = [(data, 'processes'), (data, 'groups'), (data['network'], 'links'), (data['network'], 'remotes'),
                  (data['network'], 'processes'), (data['network'], 'listeners'), (data['network'], 'instances'), (data['network'], 'instanceLinks'), (data['storage'], 'devices'),
                  (data['storage'], 'mounts'), (data['storage'], 'links'), (data['audio'], 'nodes'), (data['audio'], 'ports'), (data['audio'], 'links')]
        for _ in range(16):
            if size() <= MAX_FRAME - 1024:
                return data
            holder, name = max(arrays, key=lambda h: len(h[0][h[1]]))
            previous = holder[name]
            keep = max(0, len(previous) // 2)
            label = 'network.' + name if holder is data['network'] else 'storage.' + name if holder is data['storage'] else 'audio.' + name if holder is data['audio'] else name
            data['limits']['omitted'][label] = data['limits']['omitted'].get(label, 0) + len(previous) - keep
            holder[name] = previous[:keep]
            data['limits']['transportTruncated'] = True
        raise ValueError('snapshot could not fit transport safety limit')

    def inspect(self, key: str, offset: int = 0, limit: int = 32, frozen: bool = False) -> dict[str, Any]:
        offset, limit = max(0, min(24000, offset)), max(1, min(64, limit))
        if frozen and self.frozen_full is None:
            return {'type': 'detail', 'key': key, 'ended': True, 'message': 'Frozen helper snapshot was lost after restart. Resume live state; no live data was substituted.'}
        source = self.frozen_full if frozen else self.full
        collections = [source.get('processes', []), source.get('groups', [])]
        for section, names in [('network', ('processes', 'remotes', 'links', 'listeners', 'instances', 'instanceLinks')),
                               ('storage', ('devices', 'mounts', 'contributors')), ('audio', ('nodes', 'devices', 'clients')),
                               ('hardware', ('gpus', 'thermals', 'fans'))]:
            collections.extend(source.get(section, {}).get(n, []) for n in names)
        row = next((r for group in collections for r in group if r.get('key') == key), None)
        if row is None:
            return {'type': 'detail', 'key': key, 'ended': True, 'message': 'Entity is no longer in the current helper snapshot.'}
        result = {k: v for k, v in row.items() if k != 'sockets'}
        children = row.get('sockets', [])
        result['sockets'] = children[offset:offset + limit]
        return {'type': 'detail', 'key': key, 'ended': False, 'data': result, 'offset': offset, 'total': len(children), 'nextOffset': offset + limit if offset + limit < len(children) else None,
                'monotonic': source.get('monotonic')}

    def command(self, command: Any) -> dict[str, Any] | None:
        if not isinstance(command, dict):
            raise ValueError('command must be an object')
        op = command.get('op')
        if op == 'configure':
            self.configure(command)
            return None
        if op == 'inspect':
            return self.inspect(str(command.get('key', ''))[:512], int(command.get('offset', 0)), int(command.get('limit', 32)), command.get('frozen') is True)
        if op == 'freeze':
            self.frozen_full = deepcopy(self.full) if command.get('state') is True else None
            return {'type': 'freeze-result', 'requestId': int(command.get('requestId', 0)), 'frozen': self.frozen_full is not None, 'snapshot': self.transport(self.frozen_full) if self.frozen_full else None}
        if op == 'audio-action':
            if self.frozen_full is not None:
                raise PermissionError('Resume live state before an audio action.')
            if not self.allow_actions or command.get('confirmed') is not True:
                raise PermissionError('Enable audioActions and confirm this operation first.')
            result = self.audio_provider.action(str(command.get('action')), str(command.get('key')), self.process_provider.rows, command.get('value'))
            return {'type': 'action-result', **result}
        if op == 'ping':
            return {'type': 'pong', 'schemaVersion': SCHEMA_VERSION}
        raise ValueError('unknown command operation')

    def close(self) -> None:
        self.enricher.close()
        self.full = {}
        self.frozen_full = None
        self.events = EventStore()
        self.trend = TrendWindow()
        self.closed = True
