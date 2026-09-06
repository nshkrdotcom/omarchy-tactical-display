"""Versioned orchestration with bounded work, normalized detail and transport snapshots."""
from __future__ import annotations
import json
import time
from typing import Any, Callable
from . import SCHEMA_VERSION
from .common import MAX_FRAME, Capability, failure
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

# The protocol ceiling remains 4 MiB. Normal construction aims materially lower so
# JSON parse/model work cannot consume the long-lived shell simply because a host
# has pathological cardinality.
TRANSPORT_TARGET = 1536 * 1024
TRANSPORT_RESERVE = 48 * 1024
THROTTLE_MULTIPLIERS = (1.0, 1.5, 2.0, 3.0)

# Fair byte shares for independently useful collections. Unused shares stay unused:
# this is deliberately predictable resource containment, not a fill-the-pipe loop.
TRANSPORT_COLLECTIONS = (
    ('processes', 0.12, 4096), ('groups', 0.08, 4096),
    ('network.processes', 0.07, 4096), ('network.remotes', 0.10, 4096),
    ('network.links', 0.14, 4096), ('network.listeners', 0.04, 2048),
    ('network.instances', 0.08, 4096), ('network.instanceLinks', 0.14, 4096),
    ('storage.devices', 0.03, 2048), ('storage.mounts', 0.04, 2048),
    ('storage.links', 0.02, 4096), ('storage.contributors', 0.03, 128),
    ('audio.nodes', 0.03, 4096), ('audio.devices', 0.02, 2048),
    ('audio.clients', 0.015, 4096), ('audio.ports', 0.025, 4096),
    ('audio.links', 0.03, 4096),
)


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
        self.throttle_level = 0
        self._slow_samples = 0
        self._fast_samples = 0
        self.last_duty_cycle = 0.0
        self.last_active: set[str] = set()
        self.sequence = 0
        self.generation = 0
        self.full: dict[str, Any] = {}
        self.socket_store: dict[str, dict[str, Any]] = {}
        self.frozen_full: dict[str, Any] | None = None
        self.frozen_socket_store: dict[str, dict[str, Any]] | None = None
        self.frozen_generation: int | None = None
        self.instance_groups: set[str] = set()
        self.allow_actions = False
        self.closed = False
        self.network_provider.set_cadence(self.interval)

    @property
    def base_interval(self) -> float:
        return self.interval_override or PROFILES[self.profile]

    @property
    def interval(self) -> float:
        return min(10.0, self.base_interval * THROTTLE_MULTIPLIERS[self.throttle_level])

    def observe_duration(self, seconds: float) -> None:
        """Adaptive backoff from sustained sampler duty cycle, with slow recovery."""
        ratio = max(0.0, seconds) / max(0.001, self.interval)
        self.last_duty_cycle = ratio
        if ratio >= 0.65:
            self._slow_samples += 1
            self._fast_samples = 0
        elif ratio <= 0.20:
            self._fast_samples += 1
            self._slow_samples = 0
        else:
            self._slow_samples = self._fast_samples = 0
        changed = False
        if self._slow_samples >= 3 and self.throttle_level < len(THROTTLE_MULTIPLIERS) - 1:
            self.throttle_level += 1
            self._slow_samples = 0
            changed = True
        elif self._fast_samples >= 8 and self.throttle_level > 0:
            self.throttle_level -= 1
            self._fast_samples = 0
            changed = True
        if changed:
            self.network_provider.set_cadence(self.interval)

    def configure(self, command: dict[str, Any]) -> None:
        instrument = command.get('instrument', self.instrument)
        if instrument in INSTRUMENTS:
            self.instrument = instrument
        profile = command.get('profile', self.profile)
        if profile in PROFILES:
            self.profile = profile
        self.network_provider.set_cadence(self.interval)
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
        data: dict[str, Any] = {
            'schemaVersion': SCHEMA_VERSION, 'version': SCHEMA_VERSION, 'type': 'snapshot', 'sequence': self.sequence,
            'monotonic': now, 'wallTime': time.time(), 'instrument': self.instrument,
            'intervalSeconds': self.interval, 'capabilities': caps, 'processes': [], 'groups': [], 'system': {},
            'network': {'processes': [], 'remotes': [], 'links': [], 'listeners': [], 'instances': [], 'instanceLinks': [], 'instanceGroups': [], 'summary': {}},
            'storage': {'devices': [], 'mounts': [], 'links': [], 'contributors': [], 'summary': {}},
            'audio': {'nodes': [], 'devices': [], 'clients': [], 'ports': [], 'links': [], 'defaults': {}, 'summary': {}},
            'hardware': {'gpus': [], 'thermals': [], 'fans': []}, 'events': [], 'trend': [],
            'limits': {'maxFrameBytes': MAX_FRAME, 'transportTargetBytes': TRANSPORT_TARGET,
                       'transportTruncated': False, 'transportBytes': 0, 'omitted': {},
                       'adaptiveThrottleLevel': self.throttle_level, 'targetIntervalSeconds': self.base_interval,
                       'samplerDutyCycle': round(self.last_duty_cycle, 3)},
        }

        def collect(name: str, provider: Any, fn: Callable[[], Any], default: Any) -> Any:
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
        socket_store: dict[str, dict[str, Any]] = {}
        if 'network' in active:
            self.enricher.tick(now)
            # One canonical detail copy; both aggregate and instance layers retain only keys.
            socket_store = {str(c['key']): c for c in contacts if c.get('key')}
            model = build_network_model(contacts, self.enricher, now, retain_socket_details=False)
            for collection, domain in [('links', 'relationship'), ('remotes', 'remote'), ('listeners', 'listener')]:
                observed = [r for r in model[collection] if r.get('active', True)]
                self.events.update(domain, observed, now, complete=caps['network']['complete'])
                model[collection] = self.events.decorate(domain, observed, now, ghosts=True)
            model.update(build_instance_model(contacts, self.enricher, now, retain_socket_details=False,
                                              group_keys=self.instance_groups))
            model['instanceGroups'] = sorted(self.instance_groups)
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
        data['storage'] = collect('storage', self.storage_provider,
                                  lambda: self.storage_provider.sample(now, rows, topology=self.instrument in ('all', 'storage', 'machine')), data['storage'])
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
        caps['enrichment'] = Capability(
            'enrichment', 'aliases,/etc/hosts,/etc/services' + ('; opt-in system reverse DNS' if self.enricher.mode == 'dns' and not self.enricher.privacy else '') +
            ('; isolated local MMDB worker' if self.enricher.offline_path else ''),
            sampledAt=now, intervalSeconds=self.interval,
            status='partial' if self.enricher.offline_error else 'available', reason=self.enricher.offline_error).json()
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
        self.full = data
        self.socket_store = socket_store
        self.generation += 1
        self.sequence += 1
        frame = self.transport(data, socket_store)
        duration = time.monotonic() - started
        self.observe_duration(duration)
        duration_ms = round(duration * 1000, 3)
        data['sampleDurationMs'] = frame['sampleDurationMs'] = duration_ms
        data['intervalSeconds'] = frame['intervalSeconds'] = self.interval
        for target in (data['limits'], frame['limits']):
            target['adaptiveThrottleLevel'] = self.throttle_level
            target['samplerDutyCycle'] = round(self.last_duty_cycle, 3)
        return frame

    @staticmethod
    def _preview_socket(row: dict[str, Any]) -> dict[str, Any]:
        keys = ('key', 'proto', 'family', 'state', 'local', 'remote', 'pid', 'processKey', 'groupKey',
                'queueBytes', 'ackedBps', 'receivedBps', 'role', 'closed', 'ageMs')
        return {key: row.get(key) for key in keys if key in row}

    @staticmethod
    def _transport_row(label: str, row: dict[str, Any], socket_store: dict[str, dict[str, Any]]) -> dict[str, Any]:
        if label == 'processes':
            return {k: v for k, v in row.items() if k not in ('command', 'provenance', 'networkSource')}
        if label == 'storage.contributors':
            return {k: row.get(k) for k in ('key', 'pid', 'name', 'groupKey', 'readBps', 'writeBps', 'readBytes', 'writeBytes')}
        if label in ('network.links', 'network.listeners', 'network.instanceLinks'):
            result = {k: v for k, v in row.items() if k not in ('sockets', 'socketKeys')}
            keys = row.get('socketKeys') or [s.get('key') for s in row.get('sockets', []) if isinstance(s, dict)]
            preview = [TelemetryEngine._preview_socket(socket_store[k]) for k in keys[:2] if k in socket_store]
            if not preview and row.get('sockets'):
                preview = [TelemetryEngine._preview_socket(s) for s in row['sockets'][:2] if isinstance(s, dict)]
            result['socketPreview'] = preview
            result['socketDetailCount'] = len(keys) if keys else len(row.get('sockets', []))
            return result
        return dict(row)

    @staticmethod
    def _path(data: dict[str, Any], label: str) -> tuple[dict[str, Any], str]:
        parts = label.split('.')
        holder = data
        for part in parts[:-1]:
            holder = holder[part]
        return holder, parts[-1]

    def transport(self, full: dict[str, Any], socket_store: dict[str, dict[str, Any]] | None = None) -> dict[str, Any]:
        """Construct a transport snapshot to a byte budget before final serialization."""
        socket_store = socket_store or {}
        data = {k: v for k, v in full.items() if k not in ('processes', 'groups', 'network', 'storage', 'audio')}
        data['limits'] = dict(full.get('limits', {}))
        data['limits'].setdefault('omitted', {})
        data['limits']['omitted'] = dict(data['limits']['omitted'])
        data['limits']['transportTargetBytes'] = TRANSPORT_TARGET
        data['limits']['transportBytes'] = 0
        data['processes'], data['groups'] = [], []
        data['network'] = {'processes': [], 'remotes': [], 'links': [], 'listeners': [], 'instances': [], 'instanceLinks': [],
                           'instanceGroups': list(full.get('network', {}).get('instanceGroups', []))[:64],
                           'summary': dict(full.get('network', {}).get('summary', {}))}
        data['storage'] = {'devices': [], 'mounts': [], 'links': [], 'contributors': [],
                           'summary': dict(full.get('storage', {}).get('summary', {}))}
        audio = full.get('audio', {})
        data['audio'] = {'nodes': [], 'devices': [], 'clients': [], 'ports': [], 'links': [],
                         'defaults': dict(audio.get('defaults', {})), 'summary': dict(audio.get('summary', {}))}

        base_size = len(json.dumps(data, separators=(',', ':'), ensure_ascii=True, allow_nan=False).encode())
        available = max(65536, TRANSPORT_TARGET - base_size - TRANSPORT_RESERVE)
        for label, share, row_cap in TRANSPORT_COLLECTIONS:
            source_holder, source_name = self._path(full, label)
            target_holder, target_name = self._path(data, label)
            source = source_holder.get(source_name, [])
            quota = max(4096, int(available * share))
            used = 2
            kept: list[dict[str, Any]] = []
            for row in source[:row_cap]:
                if not isinstance(row, dict):
                    continue
                item = self._transport_row(label, row, socket_store)
                encoded_size = len(json.dumps(item, separators=(',', ':'), ensure_ascii=True, allow_nan=False).encode()) + 1
                if used + encoded_size > quota:
                    continue
                kept.append(item)
                used += encoded_size
            target_holder[target_name] = kept
            omitted = len(source) - len(kept)
            if omitted > 0:
                data['limits']['omitted'][label] = omitted
                data['limits']['transportTruncated'] = True
        raw = json.dumps(data, separators=(',', ':'), ensure_ascii=True, allow_nan=False).encode()
        if len(raw) > MAX_FRAME:
            raise ValueError('constructive snapshot exceeded emergency transport safety limit')
        data['limits']['transportBytes'] = len(raw)
        return data

    def inspect(self, key: str, offset: int = 0, limit: int = 32, frozen: bool = False) -> dict[str, Any]:
        offset, limit = max(0, min(24000, offset)), max(1, min(64, limit))
        if frozen and self.frozen_full is None:
            return {'type': 'detail', 'key': key, 'ended': True,
                    'message': 'Frozen helper snapshot was lost after restart. Resume live state; no live data was substituted.'}
        source = self.frozen_full if frozen else self.full
        socket_store = self.frozen_socket_store if frozen else self.socket_store
        socket_store = socket_store or {}
        collections = [source.get('processes', []), source.get('groups', [])]
        for section, names in [('network', ('processes', 'remotes', 'links', 'listeners', 'instances', 'instanceLinks')),
                               ('storage', ('devices', 'mounts', 'contributors')), ('audio', ('nodes', 'devices', 'clients')),
                               ('hardware', ('gpus', 'thermals', 'fans'))]:
            collections.extend(source.get(section, {}).get(n, []) for n in names)
        row = next((r for group in collections for r in group if r.get('key') == key), None)
        if row is None:
            return {'type': 'detail', 'key': key, 'ended': True, 'message': 'Entity is no longer in the current helper snapshot.'}
        result = {k: v for k, v in row.items() if k not in ('sockets', 'socketKeys')}
        keys = row.get('socketKeys', [])
        children = [socket_store[k] for k in keys if k in socket_store] if keys else row.get('sockets', [])
        result['sockets'] = children[offset:offset + limit]
        return {'type': 'detail', 'key': key, 'ended': False, 'data': result, 'offset': offset, 'total': len(children),
                'nextOffset': offset + limit if offset + limit < len(children) else None, 'monotonic': source.get('monotonic')}

    @staticmethod
    def _scope_groups(value: Any) -> set[str]:
        if not isinstance(value, list):
            return set()
        groups: set[str] = set()
        for raw in value[:64]:
            if not isinstance(raw, str):
                continue
            key = raw[:512]
            if key.startswith('application:'):
                groups.add(key)
        return groups

    def _scoped_snapshot(self, full: dict[str, Any], socket_store: dict[str, dict[str, Any]], groups: set[str]) -> dict[str, Any]:
        # Derive only the requested instance layer. The pinned source generation is
        # never mutated, so frozen inspection remains exact while X-expand still works.
        scoped = dict(full)
        network = dict(full.get('network', {}))
        contacts = list(socket_store.values())
        network.update(build_instance_model(contacts, self.enricher, full.get('monotonic'),
                                            retain_socket_details=False, group_keys=groups))
        network['instanceGroups'] = sorted(groups)
        scoped['network'] = network
        return self.transport(scoped, socket_store)

    def command(self, command: Any) -> dict[str, Any] | None:
        if not isinstance(command, dict):
            raise ValueError('command must be an object')
        op = command.get('op')
        if op == 'configure':
            self.configure(command)
            return None
        if op == 'scope':
            self.instance_groups = self._scope_groups(command.get('instanceGroups'))
            if command.get('frozen') is True and self.frozen_full is not None:
                return {'type': 'scope-result', 'frozen': True,
                        'snapshot': self._scoped_snapshot(self.frozen_full, self.frozen_socket_store or {}, self.instance_groups)}
            return None
        if op == 'inspect':
            return self.inspect(str(command.get('key', ''))[:512], int(command.get('offset', 0)),
                                int(command.get('limit', 32)), command.get('frozen') is True)
        if op == 'freeze':
            if command.get('state') is True:
                # Pin immutable-by-replacement generation references; do not deepcopy a
                # pathological full object graph merely because the user pressed Space.
                self.frozen_full = self.full
                self.frozen_socket_store = self.socket_store
                self.frozen_generation = self.generation
            else:
                self.frozen_full = None
                self.frozen_socket_store = None
                self.frozen_generation = None
            return {'type': 'freeze-result', 'requestId': int(command.get('requestId', 0)),
                    'frozen': self.frozen_full is not None,
                    'snapshot': self.transport(self.frozen_full, self.frozen_socket_store or {}) if self.frozen_full else None}
        if op == 'audio-action':
            if self.frozen_full is not None:
                raise PermissionError('Resume live state before an audio action.')
            if not self.allow_actions or command.get('confirmed') is not True:
                raise PermissionError('Enable audioActions and confirm this operation first.')
            result = self.audio_provider.action(str(command.get('action')), str(command.get('key')), self.process_provider.rows, command.get('value'))
            return {'type': 'action-result', **result}
        if op == 'ping':
            return {'type': 'pong', 'schemaVersion': SCHEMA_VERSION, 'generation': self.generation}
        raise ValueError('unknown command operation')

    def close(self) -> None:
        self.enricher.close()
        self.full = {}
        self.socket_store = {}
        self.frozen_full = None
        self.frozen_socket_store = None
        self.frozen_generation = None
        self.instance_groups = set()
        self.events = EventStore()
        self.trend = TrendWindow()
        self.closed = True
