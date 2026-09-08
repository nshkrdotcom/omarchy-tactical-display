from pathlib import Path
import os
import tempfile
import threading
import time
import unittest

from td_telemetry.invocation import invoke_hold


class HoldTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.now = int(time.time())
        self.token = str(self.now) + ':test:1'
        self.calls = []

    def invoke(self, action, token=None, runner=None):
        return invoke_hold(action, token or self.token, self.root, 'test-session',
                           runner or self.calls.append, self.now)

    def test_release_before_press_never_summons(self):
        self.invoke('hold-release')
        self.invoke('hold-press')
        self.assertEqual(self.calls, [])

    def test_repeated_press_and_late_release_do_not_close_new_hold(self):
        self.invoke('hold-press')
        self.invoke('hold-press')
        next_token = str(self.now) + ':test:2'
        self.invoke('hold-press', next_token)
        self.invoke('hold-release')
        self.assertEqual([c[2] for c in self.calls], ['summon', 'summon'])
        self.invoke('hold-release', next_token)
        self.assertEqual(self.calls[-1][2], 'hide')

    def test_lock_covers_actual_ipc_completion(self):
        entered = threading.Event()
        finish = threading.Event()
        errors = []
        def runner(argv):
            self.calls.append(argv)
            if argv[2] == 'summon':
                entered.set()
                finish.wait(2)
        def run(action):
            try:
                self.invoke(action, runner=runner)
            except Exception as error:
                errors.append(error)
        press = threading.Thread(target=run, args=('hold-press',))
        release = threading.Thread(target=run, args=('hold-release',))
        press.start()
        self.assertTrue(entered.wait(1))
        release.start()
        time.sleep(0.03)
        self.assertEqual(len(self.calls), 1)
        finish.set()
        press.join(2)
        release.join(2)
        self.assertEqual(errors, [])
        self.assertEqual([c[2] for c in self.calls], ['summon', 'hide'])

    def test_expired_press_and_shell_text_rejected(self):
        old = str(self.now - 100) + ':test'
        self.assertEqual(self.invoke('hold-press', old), 'ignored-expired-press')
        with self.assertRaises(ValueError):
            self.invoke('hold-press', self.token + ';touch /tmp/no')
        self.assertEqual(self.calls, [])

    def test_runtime_symlink_refused(self):
        link = self.root / 'link'
        link.symlink_to(self.root, target_is_directory=True)
        with self.assertRaises(PermissionError):
            invoke_hold('hold-press', self.token, link, 'test', self.calls.append, self.now)

    def test_ipc_failure_tombstones_press(self):
        def fail(_):
            raise RuntimeError('test-only runner failure')
        with self.assertRaises(RuntimeError):
            self.invoke('hold-press', runner=fail)
        self.invoke('hold-press')
        self.assertEqual(self.calls, [])
        state = self.root / 'com.nshkr.tactical-display' / 'hold.json'
        self.assertEqual(state.stat().st_mode & 0o777, 0o600)
