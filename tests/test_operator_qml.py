"""Execute the production navigation controller under Qt, without a desktop helper."""
from pathlib import Path
import os
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
RUNNER = shutil.which('qmltestrunner') or '/usr/lib/qt6/bin/qmltestrunner'


class OperatorQmlTests(unittest.TestCase):
    @unittest.skipUnless(Path(RUNNER).is_file(), 'Qt Quick Test runner unavailable')
    def test_operator_controller_in_qt(self):
        result = subprocess.run(
            [RUNNER, '-input', str(ROOT / 'tests/qml')],
            env={**os.environ, 'QT_QPA_PLATFORM': 'offscreen', 'QT_QUICK_BACKEND': 'software'},
            capture_output=True, text=True, timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
