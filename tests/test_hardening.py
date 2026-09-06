"""Adversarial resource/lifecycle contracts for Tactical Display hardening."""
from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from td_telemetry.common import MAX_FRAME, SlidingWindowLimiter, command_env, proc_child_count, run_command
from td_telemetry.engine import TelemetryEngine
from td_telemetry.enrichment import Enricher
from td_telemetry.hardware import HardwareProvider
from td_telemetry.network import build_instance_model, build_network_model
from td_telemetry.processes import assign_groups
from td_telemetry.procfs import read_socket_table


def generic_chain(count: int) -> list[dict]:
    rows = []
    for i in range(count):
        pid = i + 10
        rows.append({
            'key': f'process:{pid}:{i + 1}', 'pid': pid, 'ppid': pid - 1 if i else 1,
            'startTicks': i + 1, 'executable': '/usr/bin/python3', 'name': 'python3',
            'uid': 1000, 'cgroup': '0::/user.slice',
        })
    return rows


def contact(i: int, owners: list[dict] | None = None) -> dict:
    owners = owners or [{
        'key': 'process:10:1', 'pid': 10, 'startTicks': 1, 'name': 'python3',
        'executable': '/usr/bin/python3', 'groupKey': 'application:test',
        'groupName': 'test', 'groupProvenance': 'fixture',
    }]
    return {
        'key': f'socket:{i}', 'proto': 'tcp', 'family': 4, 'state': 'ESTABLISHED',
        'kind': 'outbound', 'role': 'outbound-inferred', 'directionSource': 'fixture',
        'local': f'10.0.0.2:{30000 + i % 20000}', 'remote': f'198.51.{i // 250 % 250}.{i % 250}:443',
        'localAddress': '10.0.0.2', 'localPort': 30000 + i % 20000,
        'remoteAddress': f'198.51.{i // 250 % 250}.{i % 250}', 'remotePort': 443,
        'cookie': str(i), 'inode': str(100000 + i), 'uid': 1000,
        'owners': owners, 'pid': owners[0]['pid'], 'process': owners[0]['name'],
        'processKey': owners[0]['key'], 'groupKey': owners[0]['groupKey'],
        'command': owners[0]['executable'], 'executable': owners[0]['executable'],
        'queueBytes': 0, 'ackedBps': None, 'receivedBps': None,
        'ageMs': 1000, 'closed': False, 'closedAgeMs': 0, 'event': 'steady',
    }


class AlgorithmicHardeningTests(unittest.TestCase):
    def test_grouping_honors_caller_absolute_deadline(self):
        rows = generic_chain(8192)
        started = time.monotonic()
        grouped = assign_groups(rows, deadline=started - 0.001)
        self.assertEqual(grouped, [])
        self.assertLess(time.monotonic() - started, 0.05)

    def test_generic_runtime_grouping_is_near_linear_at_scan_ceiling(self):
        rows = generic_chain(8192)
        started = time.monotonic()
        assign_groups(rows)
        elapsed = time.monotonic() - started
        self.assertLess(elapsed, 0.75, f'grouping took {elapsed:.3f}s')
        self.assertEqual(len({row['groupKey'] for row in rows}), 1)

    def test_engine_network_model_uses_single_canonical_socket_store(self):
        contacts = [contact(i) for i in range(5000)]
        store = {row['key']: row for row in contacts}
        aggregate = build_network_model(contacts, retain_socket_details=False)
        instances = build_instance_model(contacts, retain_socket_details=False)
        all_links = aggregate['links'] + aggregate['listeners'] + instances['instanceLinks']
        self.assertTrue(all('sockets' not in row for row in all_links))
        self.assertTrue(all(row.get('socketKeys') for row in aggregate['links']))
        self.assertEqual(len(store), len(contacts))

    def test_instance_topology_is_demand_scoped_to_requested_groups(self):
        owner_a = [{
            'key': 'process:10:1', 'pid': 10, 'startTicks': 1, 'name': 'a',
            'executable': '/usr/bin/a', 'groupKey': 'application:a',
            'groupName': 'a', 'groupProvenance': 'fixture',
        }]
        owner_b = [{
            'key': 'process:11:1', 'pid': 11, 'startTicks': 1, 'name': 'b',
            'executable': '/usr/bin/b', 'groupKey': 'application:b',
            'groupName': 'b', 'groupProvenance': 'fixture',
        }]
        contacts = [contact(1, owner_a), contact(2, owner_b)]
        none = build_instance_model(contacts, retain_socket_details=False, group_keys=set())
        only_a = build_instance_model(contacts, retain_socket_details=False, group_keys={'application:a'})
        self.assertEqual(none, {'instances': [], 'instanceLinks': []})
        self.assertEqual({row['groupKey'] for row in only_a['instances']}, {'application:a'})
        self.assertEqual({row['groupKey'] for row in only_a['instanceLinks']}, {'application:a'})

    def test_frozen_scope_can_derive_instances_without_mutating_pinned_snapshot(self):
        engine = TelemetryEngine()
        try:
            contacts = [contact(i) for i in range(8)]
            store = {row['key']: row for row in contacts}
            model = build_network_model(contacts, retain_socket_details=False)
            model.update({'instances': [], 'instanceLinks': []})
            full = {
                'schemaVersion': 3, 'version': 3, 'type': 'snapshot', 'sequence': 1,
                'monotonic': 1.0, 'wallTime': 1.0, 'instrument': 'connection',
                'intervalSeconds': 0.75, 'capabilities': {}, 'processes': [], 'groups': [],
                'system': {}, 'network': model,
                'storage': {'devices': [], 'mounts': [], 'links': [], 'contributors': [], 'summary': {}},
                'audio': {'nodes': [], 'devices': [], 'clients': [], 'ports': [], 'links': [], 'defaults': {}, 'summary': {}},
                'hardware': {'gpus': [], 'thermals': [], 'fans': []}, 'events': [], 'trend': [],
                'limits': {'maxFrameBytes': MAX_FRAME, 'transportTruncated': False, 'omitted': {}},
            }
            engine.full, engine.socket_store = full, store
            engine.command({'op': 'freeze', 'state': True, 'requestId': 1})
            pinned = engine.frozen_full
            answer = engine.command({'op': 'scope', 'instanceGroups': ['application:test'], 'frozen': True})
            self.assertIs(engine.frozen_full, pinned)
            self.assertFalse(pinned['network']['instances'])
            self.assertEqual(answer['type'], 'scope-result')
            self.assertTrue(answer['snapshot']['network']['instances'])
        finally:
            engine.close()

    def test_freeze_pins_generation_instead_of_copying_full_snapshot(self):
        engine = TelemetryEngine()
        try:
            engine.sample()
            live = engine.full
            answer = engine.command({'op': 'freeze', 'state': True, 'requestId': 7})
            self.assertIs(engine.frozen_full, live)
            self.assertIs(engine.frozen_socket_store, engine.socket_store)
            self.assertTrue(answer['frozen'])
        finally:
            engine.close()

    def test_transport_is_constructively_bounded_below_emergency_ceiling(self):
        engine = TelemetryEngine()
        try:
            contacts = [contact(i) for i in range(20000)]
            store = {row['key']: row for row in contacts}
            model = build_network_model(contacts, retain_socket_details=False)
            model.update(build_instance_model(contacts, retain_socket_details=False))
            full = {
                'schemaVersion': 3, 'version': 3, 'type': 'snapshot', 'sequence': 1,
                'monotonic': 1.0, 'wallTime': 1.0, 'instrument': 'connection',
                'intervalSeconds': 0.75, 'capabilities': {}, 'processes': [], 'groups': [],
                'system': {}, 'network': model,
                'storage': {'devices': [], 'mounts': [], 'links': [], 'contributors': [], 'summary': {}},
                'audio': {'nodes': [], 'devices': [], 'clients': [], 'ports': [], 'links': [], 'defaults': {}, 'summary': {}},
                'hardware': {'gpus': [], 'thermals': [], 'fans': []}, 'events': [], 'trend': [],
                'limits': {'maxFrameBytes': MAX_FRAME, 'transportTruncated': False, 'omitted': {}},
            }
            frame = engine.transport(full, store)
            encoded = json.dumps(frame, separators=(',', ':'), ensure_ascii=True, allow_nan=False).encode()
            self.assertLess(len(encoded), MAX_FRAME)
            self.assertLessEqual(len(encoded), frame['limits']['transportTargetBytes'] + 65536)
            self.assertTrue(frame['limits']['transportTruncated'])
        finally:
            engine.close()


class CommandFloodTests(unittest.TestCase):
    def test_command_limiter_is_window_scoped_not_read_chunk_scoped(self):
        limiter = SlidingWindowLimiter(32, 1.0)
        self.assertTrue(all(limiter.allow(10.0) for _ in range(32)))
        self.assertFalse(limiter.allow(10.0))
        self.assertTrue(limiter.allow(11.01))


class ProcMetricTests(unittest.TestCase):
    def test_child_count_is_capability_aware(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            pid = 42
            self.assertIsNone(proc_child_count(pid, root))
            path = root / str(pid) / "task" / str(pid)
            path.mkdir(parents=True)
            (path / "children").write_text("11 12 13\n")
            self.assertEqual(proc_child_count(pid, root), 3)


class BudgetAndIsolationTests(unittest.TestCase):
    def test_proc_socket_reader_honors_absolute_deadline(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / 'tcp'
            line = '  0: 0100007F:1F90 00000000:0000 0A 00000000:00000000 00:00000000 00000000  1000 0 424242\n'
            path.write_text('sl local_address rem_address st tx_queue rx_queue tr tm->when retrnsmt uid timeout inode\n' + line * 5000)
            rows = read_socket_table(path, 'tcp', 2, limit=5000, deadline=time.monotonic() - 0.001)
            self.assertLess(len(rows), 10)

    def test_provider_commands_strip_python_and_loader_injection_environment(self):
        old = {k: os.environ.get(k) for k in ('PYTHONPATH', 'PYTHONHOME', 'LD_PRELOAD', 'LD_LIBRARY_PATH')}
        try:
            os.environ['PYTHONPATH'] = '/tmp/poison'
            os.environ['PYTHONHOME'] = '/tmp/poison-home'
            os.environ['LD_PRELOAD'] = '/tmp/poison.so'
            os.environ['LD_LIBRARY_PATH'] = '/tmp/poison-lib'
            code = 'import os,json;print(json.dumps({k:os.environ.get(k) for k in ("PYTHONPATH","PYTHONHOME","LD_PRELOAD","LD_LIBRARY_PATH")}))'
            result = json.loads(run_command([sys.executable, '-S', '-c', code], max_bytes=4096).decode())
            self.assertEqual(result, {'PYTHONPATH': None, 'PYTHONHOME': None, 'LD_PRELOAD': None, 'LD_LIBRARY_PATH': None})
        finally:
            for key, value in old.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value

    def test_optional_mmdb_worker_loads_system_site_but_disables_user_site(self):
        self.assertEqual(command_env().get('PYTHONNOUSERSITE'), '1')
        enricher = Enricher()
        enricher.offline_path = '/tmp/test.mmdb'
        enricher.offline_pending.append('192.0.2.1')
        try:
            with mock.patch('td_telemetry.enrichment.guarded_argv', side_effect=lambda argv: argv) as guarded, \
                 mock.patch('td_telemetry.enrichment.subprocess.Popen', return_value=mock.Mock()):
                enricher.tick(1.0)
                target = guarded.call_args[0][0]
                self.assertEqual(target[0], sys.executable)
                self.assertNotIn('-S', target)
                self.assertTrue(str(target[1]).endswith('mmdb_worker.py'))
        finally:
            enricher.offline_worker = None
            enricher.close()

    def test_offline_mmdb_configuration_never_opens_database_in_main_helper(self):
        enricher = Enricher()
        try:
            with mock.patch.dict(sys.modules, {'maxminddb': mock.Mock()}):
                fake = sys.modules['maxminddb']
                enricher.configure(offline_db='/definitely/not/opened/in-parent.mmdb')
                self.assertFalse(fake.open_database.called)
                self.assertEqual(enricher.offline_path, '/definitely/not/opened/in-parent.mmdb')
        finally:
            enricher.close()

    def test_nvidia_smi_is_fallback_only_when_drm_produces_gpu(self):
        provider = HardwareProvider()
        with tempfile.TemporaryDirectory() as td:
            fake = Path(td) / 'device'
            fake.mkdir()
            (fake / 'gpu_busy_percent').write_text('17')
            (fake / 'mem_info_vram_used').write_text('1024')
            (fake / 'mem_info_vram_total').write_text('2048')
            with mock.patch('td_telemetry.hardware.Path.glob', return_value=[fake]), \
                 mock.patch('td_telemetry.hardware.shutil.which', return_value='/usr/bin/nvidia-smi'), \
                 mock.patch('td_telemetry.hardware.run_command') as command:
                rows = provider.sample(time.monotonic())
                self.assertTrue(rows['gpus'])
                command.assert_not_called()


class AdaptiveCadenceTests(unittest.TestCase):
    def test_engine_backs_off_after_sustained_high_sampler_duty_cycle(self):
        engine = TelemetryEngine(profile='responsive')
        try:
            base = engine.interval
            for _ in range(3):
                engine.observe_duration(base * 0.9)
            self.assertGreater(engine.interval, base)
            self.assertGreater(engine.throttle_level, 0)
        finally:
            engine.close()


if __name__ == '__main__':
    unittest.main()
