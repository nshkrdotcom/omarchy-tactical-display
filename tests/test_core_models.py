import importlib.util
import os
from pathlib import Path
import socket
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


class CoreModelTests(unittest.TestCase):
    def test_counter_has_no_fabricated_initial_rate_and_resets(self):
        from td_telemetry.common import CounterRate
        r = CounterRate()
        self.assertIsNone(r.rate('a', 100, 1.0))
        self.assertEqual(r.rate('a', 150, 2.0), 50)
        self.assertIsNone(r.rate('a', 10, 3.0))
        self.assertEqual(r.rate('a', 20, 4.0), 10)

    def test_proc_stat_parentheses_and_pid_reuse(self):
        from td_telemetry.processes import parse_stat
        # fields following comm begin with state (field 3).
        fields = ['S', '1'] + ['0'] * 48
        fields[11], fields[12], fields[17], fields[19], fields[21] = '2', '3', '4', '123', '5'
        p = parse_stat('44 (a ) strange process) ' + ' '.join(fields))
        self.assertEqual(p['name'], 'a ) strange process')
        self.assertEqual(p['ppid'], 1)
        self.assertEqual(p['cpuTicks'], 5)
        self.assertEqual(p['startTicks'], 123)
        self.assertEqual(p['key'], 'process:44:123')
        other = parse_stat(('44 (a) ' + ' '.join(fields)).replace('123', '124'))
        self.assertNotEqual(p['key'], other['key'])

    def test_mountinfo_decoding_and_layer(self):
        from td_telemetry.storage import parse_mountinfo
        rows = parse_mountinfo('38 25 8:1 / /home/a\\040b rw,relatime shared:1 - ext4 /dev/sda1 rw\n')
        self.assertEqual(rows[0]['path'], '/home/a b')
        self.assertEqual(rows[0]['majorMinor'], '8:1')

    def test_events_expire_and_do_not_invent_closes_on_incomplete_scan(self):
        from td_telemetry.events import EventStore
        e = EventStore(ttl=3, limit=8)
        a = {'key': 'a', 'name': 'first'}
        e.update('process', [a], 1, complete=True)
        self.assertEqual(e.events(1), [])
        e.update('process', [], 2, complete=False)
        self.assertEqual(e.events(2), [])
        e.update('process', [], 3, complete=True)
        self.assertEqual(e.events(3)[0]['kind'], 'closed')
        self.assertEqual(e.events(7), [])

    def test_bounded_command_has_real_timeout(self):
        from td_telemetry.common import run_command
        with self.assertRaises(TimeoutError):
            run_command([sys.executable, '-c', 'import time; time.sleep(5)'], timeout=0.05)

    def test_audio_graph_structured_links_and_defaults(self):
        from td_telemetry.audio import normalize_graph
        raw = [
            {'id': 9, 'type': 'PipeWire:Interface:Node', 'info': {'props': {'object.serial': 90, 'node.name': 'speaker', 'media.class': 'Audio/Sink'}, 'state': 'running'}},
            {'id': 10, 'type': 'PipeWire:Interface:Node', 'info': {'props': {'object.serial': 100, 'node.name': 'player', 'media.class': 'Stream/Output/Audio'}, 'params': {'Props': [{'mute': True, 'channelVolumes': [0.5, 0.5]}]}}},
            {'id': 11, 'type': 'PipeWire:Interface:Link', 'info': {'props': {'object.serial': 110}, 'output-node-id': 10, 'input-node-id': 9, 'state': 'active'}},
            {'id': 12, 'type': 'PipeWire:Interface:Metadata', 'metadata': [{'key': 'default.audio.sink', 'value': '{"name":"speaker"}'}]}
        ]
        graph = normalize_graph(raw, {}, 'session')
        self.assertEqual(len(graph['links']), 1)
        self.assertEqual(graph['links'][0]['state'], 'active')
        self.assertTrue(next(n for n in graph['nodes'] if n['objectId'] == 9)['default'])
        self.assertTrue(next(n for n in graph['nodes'] if n['objectId'] == 10)['mute'])

    def test_local_hosts_enrichment_does_not_require_resolver(self):
        from td_telemetry.enrichment import parse_hosts
        self.assertEqual(parse_hosts('127.0.0.1 localhost\n192.0.2.1 example # note\n')['192.0.2.1'], 'example')


if __name__ == '__main__':
    unittest.main()
