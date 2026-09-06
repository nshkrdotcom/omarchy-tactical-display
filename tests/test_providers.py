"""Deterministic edge contracts plus real unprivileged Linux integration."""
import json
import os
from pathlib import Path
import socket
import struct
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from td_telemetry.common import CounterRate, run_command, stable_id, clean
from td_telemetry.engine import TelemetryEngine
from td_telemetry.events import EventStore, TrendWindow
from td_telemetry.processes import ProcessProvider, assign_groups, parse_stat
from td_telemetry.network import SocketSampler, build_network_model
from td_telemetry.storage import StorageProvider, parse_diskstats
from td_telemetry.audio import AudioProvider
from td_telemetry.inet_diag import parse_message, dump_tcp
from td_telemetry.enrichment import Enricher, parse_services
from td_telemetry.machine import MachineProvider, parse_memory


class NormalizationTests(unittest.TestCase):
    def test_clean_unicode_control_bidi(self):
        self.assertEqual(clean('a\n\x00\u202e\u03b2'), 'a\u03b2')
        self.assertEqual(len(clean('a' * 10000)), 512)

    def test_ids_are_stable_and_tuple_unambiguous(self):
        self.assertEqual(stable_id('x', 'a', 'b'), stable_id('x', 'a', 'b'))
        self.assertNotEqual(stable_id('x', 'a:b', 'c'), stable_id('x', 'a', 'b:c'))

    def test_unrelated_python_processes_not_merged(self):
        rows = [dict(key=f'process:{p}:1', pid=p, ppid=1, startTicks=1, executable='/usr/bin/python3', name='python3', uid=1000, cgroup='0::/user.slice') for p in (5, 6)]
        assign_groups(rows)
        self.assertNotEqual(rows[0]['groupKey'], rows[1]['groupKey'])
        rows[1]['ppid'] = 5
        assign_groups(rows)
        self.assertEqual(rows[0]['groupKey'], rows[1]['groupKey'])

    def test_parent_pid_reuse_not_ancestry(self):
        rows = [dict(key='process:5:10', pid=5, ppid=1, startTicks=10, executable='/x', name='x', uid=1),
                dict(key='process:6:2', pid=6, ppid=5, startTicks=2, executable='/y', name='y', uid=1)]
        assign_groups(rows)
        self.assertIsNone(rows[1]['parentKey'])

    def test_cpu_and_network_initial_unknown(self):
        sample = MachineProvider().sample(time.monotonic())
        self.assertIsNone(sample['cpuPercent'])
        self.assertIsNone(sample['netRxBps'])
        self.assertTrue(sample['cores'])

    def test_memavailable_accounting(self):
        p = parse_memory('MemTotal: 1000 kB\nMemAvailable: 300 kB\nCached: 200 kB\nSReclaimable: 40 kB\nShmem: 10 kB\n')
        self.assertEqual(p['usedBytes'], 700 * 1024)
        self.assertEqual(p['cacheBytes'], 230 * 1024)

    def test_diskstats_units_and_nonfinite_input(self):
        d = parse_diskstats('259 0 nvme0n1 1 0 10 2 3 0 20 4 0 5 6')[0]
        self.assertEqual(d['readBytes'], 5120)
        self.assertEqual(d['writeBytes'], 10240)
        self.assertEqual(parse_diskstats('malformed'), [])

    def test_inet_diag_length_checked_tcp_info(self):
        msg = bytearray(72)
        msg[0], msg[1] = socket.AF_INET, 1
        struct.pack_into('!HH', msg, 4, 1234, 443)
        msg[8:12], msg[24:28] = socket.inet_aton('127.0.0.1'), socket.inet_aton('192.0.2.3')
        struct.pack_into('=IIIII', msg, 52, 0, 12, 34, 1000, 123)
        info = bytearray(136)
        struct.pack_into('=I', info, 68, 1500)
        struct.pack_into('=QQ', info, 120, 123456, 654321)
        data = bytes(msg) + struct.pack('=HH', 140, 2) + info
        p = parse_message(data)
        self.assertEqual(p['rttMs'], 1.5)
        self.assertEqual(p['bytesAcked'], 123456)
        self.assertEqual(p['queueBytes'], 46)
        self.assertIsNone(parse_message(bytes(msg))['bytesAcked'])
        with self.assertRaises(ValueError):
            parse_message(bytes(msg) + struct.pack('=HH', 900, 2))

    def test_listener_backlog_is_not_bytes(self):
        msg = bytearray(72)
        msg[0], msg[1] = socket.AF_INET, 10
        struct.pack_into('=IIIII', msg, 52, 0, 3, 100, 1000, 123)
        p = parse_message(bytes(msg))
        self.assertIsNone(p['queueBytes'])
        self.assertEqual(p['listenBacklogCurrent'], 3)

    def test_events_and_trends_bounded(self):
        e = EventStore(limit=8, entity_limit=32)
        e.update('x', [], 0)
        for i in range(100):
            e.update('x', [{'key': str(i)}], 1 + i / 100)
        self.assertLessEqual(len(e.events(2)), 8)
        self.assertLessEqual(len(e.first_seen), 64)
        t = TrendWindow(seconds=10, limit=5)
        for i in range(100):
            t.add(i, {'cpu': i})
        self.assertEqual(len(t.rows), 5)
        self.assertEqual(len(t.add(150, {'cpu': 0})), 1)

    def test_command_output_is_bounded_and_child_reaped(self):
        with self.assertRaises(ValueError):
            run_command([sys.executable, '-S', '-c', 'print("x"*100000)'], timeout=2, max_bytes=1024)

    def test_malformed_missing_process_files_degrade(self):
        with tempfile.TemporaryDirectory() as td:
            d = Path(td) / '123'
            d.mkdir()
            (d / 'stat').write_text('broken')
            p = ProcessProvider(td)
            self.assertEqual(p.sample(1), [])
            self.assertEqual(p.capability.status, 'partial')
            self.assertFalse(p.capability.complete)

    def test_local_services_ambiguity_and_privacy_dns(self):
        self.assertEqual(parse_services('web 443/tcp\nother 443/tcp\n'), {})
        e = Enricher()
        e.configure('dns', {'192.0.2.4': 'my-host'}, privacy=True)
        self.assertEqual(e.resolve('192.0.2.4', 1)['name'], 'my-host')
        e.resolve('192.0.2.5', 1)
        self.assertEqual(len(e.pending), 0)
        self.assertIsNone(e.worker)
        e.close()

    def test_action_requires_explicit_confirmation_and_enable(self):
        e = TelemetryEngine()
        try:
            with self.assertRaises(PermissionError):
                e.command({'op': 'audio-action', 'action': 'mute', 'key': 'bogus'})
            with self.assertRaises(ValueError):
                e.command({'op': 'execute', 'command': 'never'})
        finally:
            e.close()


class RealProviderTests(unittest.TestCase):
    def test_ipv6_and_udp_ownership(self):
        sampler = SocketSampler(source='proc')
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp:
            udp.bind(('127.0.0.1', 0))
            rows = sampler.sample()
            match = next(r for r in rows if r['proto'] == 'udp' and r['localPort'] == udp.getsockname()[1])
            self.assertEqual(match['pid'], os.getpid())
            self.assertEqual(match['role'], 'bound-datagram')
        try:
            server = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
            server.bind(('::1', 0))
        except OSError as error:
            self.skipTest('IPv6 unavailable: ' + str(error))
        with server:
            server.listen()
            with socket.socket(socket.AF_INET6, socket.SOCK_STREAM) as client:
                client.connect(server.getsockname())
                accepted, _ = server.accept()
                with accepted:
                    rows = sampler.sample()
                    matches = [r for r in rows if r['family'] == 6 and r['localPort'] == server.getsockname()[1]]
                    self.assertTrue(any(r['state'] == 'ESTABLISHED' for r in matches))
                    self.assertTrue(all(r['pid'] == os.getpid() for r in matches))

    def test_real_nonloopback_accepted_direction_and_aggregation(self):
        addresses = []
        try:
            addresses = [a[4][0] for a in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET) if not a[4][0].startswith('127.')]
        except OSError:
            pass
        if not addresses:
            self.skipTest('No resolvable non-loopback address for controlled inbound test')
        sampler = SocketSampler(source='proc')
        with socket.socket() as server:
            server.bind(('0.0.0.0', 0)); server.listen()
            clients, accepted = [], []
            try:
                for _ in range(3):
                    c = socket.socket(); c.connect((addresses[0], server.getsockname()[1])); clients.append(c)
                    a, _ = server.accept(); accepted.append(a)
                rows = sampler.sample()
                incoming = [r for r in rows if r['localPort'] == server.getsockname()[1] and r['state'] == 'ESTABLISHED']
                self.assertEqual(len(incoming), 3)
                self.assertTrue(all(r['kind'] == 'inbound' and 'inferred' in r['directionSource'] for r in incoming))
                model = build_network_model(incoming)
                self.assertEqual(len(model['links']), 1)
                self.assertEqual(model['links'][0]['socketCount'], 3)
            finally:
                for s in clients + accepted:
                    s.close()

    def test_real_shared_socket_has_multiple_owners(self):
        with socket.socket() as server:
            server.bind(('127.0.0.1', 0)); server.listen()
            child = subprocess.Popen([sys.executable, '-S', '-c', 'import time;time.sleep(10)'], pass_fds=[server.fileno()])
            try:
                rows = SocketSampler(source='proc').sample()
                row = next(r for r in rows if r['localPort'] == server.getsockname()[1] and r['state'] == 'LISTEN')
                self.assertTrue({os.getpid(), child.pid}.issubset({o['pid'] for o in row['owners']}))
            finally:
                child.terminate(); child.wait(timeout=2)

    def test_real_process_tree_cpu_io_and_exit(self):
        provider = ProcessProvider()
        child = subprocess.Popen([sys.executable, '-S', '-c', 'import time; a=bytearray(8*1024*1024);t=time.monotonic()+5\nwhile time.monotonic()<t: sum(range(5000))', 'SENSITIVE_SENTINEL_DO_NOT_READ'])
        try:
            time.sleep(0.04)
            first = provider.sample(time.monotonic())
            p = next(r for r in first if r['pid'] == child.pid)
            self.assertEqual(p['ppid'], os.getpid())
            self.assertIn(f'process:{child.pid}:', p['key'])
            time.sleep(0.04)
            second = provider.sample(time.monotonic())
            p2 = next(r for r in second if r['pid'] == child.pid)
            self.assertEqual(p['key'], p2['key'])
            self.assertGreater(p2['rssBytes'], 0)
            self.assertGreater(p2['cpuPercent'], 0)
            self.assertNotIn('SENSITIVE_SENTINEL', json.dumps(second))
        finally:
            child.terminate(); child.wait(timeout=2)
        self.assertFalse(any(p['pid'] == child.pid for p in provider.sample(time.monotonic())))

    def test_real_filesystem_io_accounting_and_mounts(self):
        proc = ProcessProvider(); storage = StorageProvider()
        first = proc.sample(time.monotonic())
        before = next(r for r in first if r['pid'] == os.getpid())
        with tempfile.NamedTemporaryFile() as f:
            f.write(os.urandom(2 * 1024 * 1024)); f.flush(); os.fsync(f.fileno())
            second = proc.sample(time.monotonic())
            after = next(r for r in second if r['pid'] == os.getpid())
            if before['writeBytes'] is None:
                self.skipTest('Kernel denies current process I/O accounting')
            self.assertGreaterEqual(after['writeBytes'], before['writeBytes'])
            if after['writeBytes'] == before['writeBytes']:
                self.skipTest('Filesystem does not charge temporary write to process storage counters (e.g. tmpfs)')
            self.assertGreater(after['writeBps'], 0)
            data = storage.sample(time.monotonic(), second)
            self.assertTrue(data['mounts'])
            self.assertTrue(any(m['path'] == '/' for m in data['mounts']))
            self.assertNotIn('mountBps', json.dumps(data))
            self.assertIn('NOT MEASURED', data['summary']['processMountAttribution'])

    def test_real_inet_diag_when_kernel_allows(self):
        try:
            rows = dump_tcp(socket.AF_INET)
        except (OSError, ValueError, TimeoutError, RuntimeError) as error:
            self.skipTest('inet_diag unavailable; production procfs fallback separately exercised: ' + str(error))
        self.assertIsInstance(rows, list)

    def test_real_pipewire_session_when_available(self):
        provider = AudioProvider()
        graph = provider.sample(time.monotonic(), ProcessProvider().sample(time.monotonic()))
        if provider.capability.status != 'available':
            self.skipTest(provider.capability.reason)
        self.assertIsInstance(graph['nodes'], list)
        for link in graph['links']:
            self.assertIn(link['sourceKey'], {n['key'] for n in graph['nodes']})

    def test_real_engine_switches_providers_and_bounds_frames(self):
        engine = TelemetryEngine()
        try:
            frame = engine.sample()
            self.assertEqual(frame['capabilities']['audio']['status'], 'inactive')
            self.assertEqual(frame['schemaVersion'], 3)
            key = next(p['key'] for p in engine.full['processes'] if p['pid'] == os.getpid())
            self.assertFalse(engine.inspect(key)['ended'])
            if not any(p['pid'] == os.getpid() for p in frame['processes']):
                self.assertGreater(frame['limits']['omitted'].get('processes', 0), 0)
            engine.configure({'instrument': 'audio', 'profile': 'efficient'})
            frame = engine.sample()
            self.assertEqual(frame['capabilities']['network']['status'], 'inactive')
            self.assertEqual(engine.interval, 1.5)
            self.assertLess(len(json.dumps(frame)), 4194304)
        finally:
            engine.close()
        self.assertTrue(engine.closed)
        self.assertEqual(engine.full, {})


if __name__ == '__main__':
    unittest.main()
