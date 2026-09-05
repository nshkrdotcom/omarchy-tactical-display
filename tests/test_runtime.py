"""Production helper framing/lifecycle tests, using actual procfs and subprocesses."""
import json
import os
from pathlib import Path
import selectors
import subprocess
import sys
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
from td_telemetry.common import run_command
from td_telemetry.engine import TelemetryEngine


class RuntimeTests(unittest.TestCase):
    def test_frozen_inspection_never_substitutes_live_after_restart(self):
        e = TelemetryEngine('processes', source='proc')
        self.addCleanup(e.close)
        frame = e.sample()
        key = frame['processes'][0]['key']
        frozen = e.command({'op': 'freeze', 'state': True, 'requestId': 7})
        self.assertEqual(frozen['requestId'], 7)
        e.sample()
        self.assertEqual(e.inspect(key, frozen=True)['monotonic'], frozen['snapshot']['monotonic'])
        e.frozen_full = None
        result = e.inspect(key, frozen=True)
        self.assertTrue(result['ended'])
        self.assertNotIn('data', result)

    def test_closed_stdout_hung_child_is_bounded(self):
        start = time.monotonic()
        with self.assertRaises(TimeoutError):
            run_command([sys.executable, '-S', '-c', 'import os,time;os.close(1);os.close(2);time.sleep(9)'], timeout=0.15)
        self.assertLess(time.monotonic()-start, 1)

    def test_real_helper_partial_lines_bad_json_and_eof_teardown(self):
        p = subprocess.Popen([sys.executable, '-u', str(ROOT/'scripts/telemetry.py'), '--socket-source', 'proc', '--interval', '0.25'],
                             stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.addCleanup(lambda: p.poll() is None and p.kill())
        p.stdin.write(b'{"op":"pi');p.stdin.flush()
        time.sleep(0.03)
        p.stdin.write(b'ng"}\nnot-json\n{"op":"freeze","state":true,"requestId":92}\n');p.stdin.flush()
        frames=[]
        with selectors.DefaultSelector() as sel:
            os.set_blocking(p.stdout.fileno(),False);sel.register(p.stdout,selectors.EVENT_READ)
            buf=b'';until=time.monotonic()+3
            while time.monotonic()<until and not {'pong','error','freeze-result','snapshot'}.issubset({f['type'] for f in frames}):
                for _,_ in sel.select(0.1):
                    buf+=os.read(p.stdout.fileno(),65536)
                    while b'\n' in buf:
                        line,buf=buf.split(b'\n',1);frames.append(json.loads(line))
        self.assertTrue({'pong','error','freeze-result','snapshot'}.issubset({f['type'] for f in frames}))
        self.assertEqual(next(f for f in frames if f['type']=='freeze-result')['requestId'],92)
        p.stdin.close();p.wait(timeout=2)
        self.assertEqual(p.returncode,0)
        p.stdout.close();p.stderr.close()

    def test_fifty_real_helper_start_sample_stop_cycles(self):
        for i in range(50):
            p=subprocess.Popen([sys.executable,'-u',str(ROOT/'scripts/telemetry.py'),'--instrument','processes','--socket-source','proc'],
                               stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
            try:
                with selectors.DefaultSelector() as sel:
                    sel.register(p.stdout,selectors.EVENT_READ)
                    self.assertTrue(sel.select(3),'helper did not produce a frame')
                frame=json.loads(p.stdout.readline())
                self.assertEqual(frame['schemaVersion'],3)
                self.assertTrue(frame['processes'])
                p.stdin.close();p.wait(timeout=2)
                self.assertEqual(p.returncode,0)
            finally:
                if p.poll() is None:p.kill();p.wait()
                for stream in (p.stdin,p.stdout,p.stderr):stream.close()

    def test_actions_fail_closed_by_default(self):
        e=TelemetryEngine();self.addCleanup(e.close)
        with self.assertRaises(PermissionError):
            e.command({'op':'audio-action','action':'mute','key':'stale','confirmed':True})
        with self.assertRaises(ValueError):e.command({'op':'run-shell','command':'touch /tmp/not-run'})
