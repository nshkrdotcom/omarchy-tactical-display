"""Structured PipeWire graph, no presentation scraping and no invented levels."""
from __future__ import annotations
import json
import os
from pathlib import Path
import shutil
import time
from typing import Any
from .common import Capability, clean, failure, number, run_command, stable_id


def normalize_graph(raw: list[dict[str, Any]], processes: dict[int, dict[str, Any]], epoch: str) -> dict[str, Any]:
    if not isinstance(raw, list) or len(raw) > 24000:
        raise ValueError('PipeWire object collection exceeds safety limit')
    nodes, devices, clients, ports, links = [], [], [], [], []
    by_id: dict[int, dict[str, Any]] = {}
    defaults: dict[str, str] = {}
    for obj in raw:
        if not isinstance(obj, dict):
            continue
        typ = str(obj.get('type', '')).rsplit(':', 1)[-1]
        if typ == 'Metadata':
            for m in obj.get('metadata', [])[:1024]:
                if m.get('key') in ('default.audio.sink', 'default.audio.source'):
                    try:
                        value = json.loads(m.get('value', '{}'))
                        if isinstance(value, dict):
                            defaults[m['key']] = clean(value.get('name', ''))
                    except (ValueError, TypeError):
                        pass
            continue
        info = obj.get('info') or {}
        props = info.get('props') or {}
        oid = obj.get('id')
        if not isinstance(oid, int):
            continue
        serial = str(props.get('object.serial', oid))
        key = stable_id('audio', epoch, typ, serial)
        row = {'key': key, 'objectId': oid, 'serial': serial, 'kind': typ.lower(),
               'name': clean(props.get('node.description') or props.get('node.nick') or props.get('application.name') or props.get('device.description') or props.get('node.name') or props.get('client.name') or f'{typ} {oid}'),
               'nodeName': clean(props.get('node.name', '')), 'mediaClass': clean(props.get('media.class', '')),
               'state': clean(info.get('state', 'unknown')), 'mute': None, 'volume': None, 'default': False,
               'processKey': None, 'groupKey': None, 'clientId': props.get('client.id'), 'deviceId': props.get('device.id'),
               'provenance': 'pw-dump JSON; volume is linear gain, not a live level; serial scoped to core session'}
        try:
            pid = int(props.get('application.process.id', -1))
        except (TypeError, ValueError):
            pid = -1
        row['pid'] = pid if pid >= 0 else None
        if pid in processes:
            row['processKey'], row['groupKey'] = processes[pid]['key'], processes[pid]['groupKey']
            row['ownershipProvenance'] = 'PipeWire application.process.id joined to current procfs instance (client-reported, not security identity)'
        for param in (info.get('params') or {}).get('Props', [])[:16]:
            if not isinstance(param, dict):
                continue
            if isinstance(param.get('mute'), bool):
                row['mute'] = param['mute']
            values = [number(v) for v in param.get('channelVolumes', [])[:64]]
            values = [v for v in values if v is not None and v >= 0]
            row['volume'] = sum(values) / len(values) if values else number(param.get('volume'))
        row['sampleRate'] = number(props.get('audio.rate'))
        row['sampleFormat'] = ''
        for fmt in (info.get('params') or {}).get('Format', [])[:16]:
            if isinstance(fmt, dict):
                row['sampleRate'] = number(fmt.get('rate')) or row['sampleRate']
                row['sampleFormat'] = clean(fmt.get('format', ''))
        row['channels'] = number(props.get('audio.channels'))
        row['bluetoothAddress'] = clean(props.get('api.bluez5.address', ''))
        by_id[oid] = row
        if typ == 'Node' and ('Audio' in row['mediaClass'] or 'audio' in str(props.get('media.type', '')).lower()):
            nodes.append(row)
        elif typ == 'Device':
            devices.append(row)
        elif typ == 'Client':
            clients.append(row)
        elif typ == 'Port':
            row.update(nodeId=props.get('node.id'), direction=clean(info.get('direction', '')))
            ports.append(row)
        elif typ == 'Link':
            row.update(outputNodeId=info.get('output-node-id'), inputNodeId=info.get('input-node-id'),
                       outputPortId=info.get('output-port-id'), inputPortId=info.get('input-port-id'))
            links.append(row)
    # Some clients put process metadata on Client rather than Node.
    client_ids = {r['objectId']: r for r in clients}
    device_ids = {r['objectId']: r for r in devices}
    for n in nodes:
        try:
            c = client_ids.get(int(n['clientId']))
        except (ValueError, TypeError):
            c = None
        if c and not n['processKey']:
            n['processKey'], n['groupKey'] = c['processKey'], c['groupKey']
            n['pid'] = c.get('pid')
            n['ownershipProvenance'] = c.get('ownershipProvenance', 'Client-reported process metadata')
        try:
            dev = device_ids.get(int(n['deviceId']))
        except (ValueError, TypeError):
            dev = None
        n['deviceKey'] = dev['key'] if dev else None
        n['default'] = n['nodeName'] in defaults.values()
    node_ids = {n['objectId'] for n in nodes}
    observed_links = []
    for link in links:
        if link['outputNodeId'] in node_ids and link['inputNodeId'] in node_ids:
            link['sourceKey'] = by_id[link['outputNodeId']]['key']
            link['targetKey'] = by_id[link['inputNodeId']]['key']
            observed_links.append(link)
    used_devices = {n['deviceKey'] for n in nodes if n['deviceKey']}
    devices = [d for d in devices if d['key'] in used_devices or 'Audio' in d['mediaClass']]
    ports = [p for p in ports if str(p.get('nodeId')) in {str(i) for i in node_ids}]
    return {'nodes': nodes, 'devices': devices, 'clients': clients, 'ports': ports,
            'links': observed_links, 'defaults': defaults, 'summary': {'nodes': len(nodes), 'links': len(observed_links), 'levelMeter': 'unavailable (not measured)'}}


class AudioProvider:
    def __init__(self) -> None:
        self.capability = Capability('audio', 'pw-dump JSON', intervalSeconds=2)
        self.rows: dict[str, Any] = {'nodes': [], 'devices': [], 'clients': [], 'ports': [], 'links': [], 'defaults': {}, 'summary': {}}
        self.epoch = 'unconnected'
        self.last_attempt = -100.0
        self.last_success = -100.0
        self.undo: dict[str, Any] | None = None

    def sample(self, now: float, processes: list[dict[str, Any]]) -> dict[str, Any]:
        if now - self.last_attempt < 2:
            return self.rows
        self.last_attempt = now
        cap = self.capability = Capability('audio', 'pw-dump JSON', sampledAt=now, intervalSeconds=2)
        started = time.monotonic()
        try:
            if not shutil.which('pw-dump'):
                raise FileNotFoundError('pw-dump is not installed (Arch package: pipewire)')
            raw = json.loads(run_command(['pw-dump'], timeout=1.2, max_bytes=2 * 1024 * 1024))
            core = next((o for o in raw if str(o.get('type', '')).endswith(':Core')), {})
            info = core.get('info') or {}
            props = info.get('props') or {}
            # cookie changes on daemon restart; no collision when IDs/serials restart at 1.
            epoch = str(info.get('cookie', props.get('core.name', ''))) + ':' + str(props.get('core.id', ''))
            if not epoch.strip(':'):
                epoch = str(os.stat(Path(os.environ.get('XDG_RUNTIME_DIR', '/nonexistent')) / 'pipewire-0').st_ino)
            self.epoch = epoch
            self.rows = normalize_graph(raw, {p['pid']: p for p in processes}, epoch)
            self.last_success = now
            if not self.rows['nodes']:
                cap.reason = 'Connected to PipeWire, but no audio nodes are present.'
        except (OSError, RuntimeError, ValueError, TimeoutError, TypeError) as error:
            failure(cap, error, 'Run pw-dump in your graphical user session; install pipewire/wireplumber if absent. Do not use sudo.')
            if self.last_success >= 0:
                cap.sampledAt = self.last_success
                cap.status = 'stale'
        cap.durationMs = round((time.monotonic() - started) * 1000, 3)
        return self.rows

    def action(self, op: str, key: str, processes: list[dict[str, Any]], value: Any = None) -> dict[str, Any]:
        if op not in ('mute', 'default', 'undo'):
            raise ValueError('unsupported audio action; rerouting requires a confirmed route API')
        if op == 'undo':
            if not self.undo:
                raise ValueError('no action to undo')
            undo, self.undo = self.undo, None
            return self.action(undo['op'], undo['key'], processes, undo['value'])
        # Refresh on every action; never send stale displayed object IDs to wpctl.
        self.last_attempt = -100
        self.sample(time.monotonic(), processes)
        if self.capability.status not in ('available', 'partial'):
            raise RuntimeError('audio graph not current')
        node = next((n for n in self.rows['nodes'] if n['key'] == key), None)
        if not node:
            raise ValueError('selected PipeWire serial no longer exists')
        if not shutil.which('wpctl'):
            raise FileNotFoundError('wpctl missing (Arch package: wireplumber)')
        if op == 'mute':
            if node['mute'] is None:
                raise ValueError('mute control not exposed by this node')
            requested = not node['mute'] if value is None else value
            if not isinstance(requested, bool):
                raise ValueError('mute value must be boolean')
            run_command(['wpctl', 'set-mute', str(node['objectId']), '1' if requested else '0'], timeout=1)
            self.undo = {'op': 'mute', 'key': key, 'value': node['mute']}
        else:
            if node['mediaClass'] not in ('Audio/Sink', 'Audio/Source'):
                raise ValueError('only sinks/sources may become default')
            old = next((n for n in self.rows['nodes'] if n['default'] and n['mediaClass'] == node['mediaClass']), None)
            run_command(['wpctl', 'set-default', str(node['objectId'])], timeout=1)
            self.undo = {'op': 'default', 'key': old['key'], 'value': None} if old else None
        self.last_attempt = -100
        return {'ok': True, 'message': 'Audio action sent; graph will refresh. IDs validated immediately before wpctl; daemon-level atomic serial targeting is unavailable.'}