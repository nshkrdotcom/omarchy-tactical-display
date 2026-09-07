"""Native lint must resolve qs imports and fail when an import is missing."""
from importlib.util import module_from_spec, spec_from_file_location
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
import shutil
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
LINT = shutil.which('qmllint') or '/usr/lib/qt6/bin/qmllint'


@unittest.skipUnless(Path(LINT).is_file(), 'qmllint unavailable')
class NativeLintTests(unittest.TestCase):
    def test_host_import_mapping_and_fail_closed_missing_module(self):
        spec = spec_from_file_location('tactical_qml_lint', ROOT / 'scripts/lint-qml.py')
        lint = module_from_spec(spec)
        spec.loader.exec_module(lint)
        with tempfile.TemporaryDirectory(prefix='tactical-lint-test-') as folder:
            root = Path(folder)
            module = root / 'shell/Commons'
            module.mkdir(parents=True)
            (module / 'qmldir').write_text('module qs.Commons\nsingleton Style 1.0 Style.qml\n')
            (module / 'Style.qml').write_text('pragma Singleton\nimport QtQuick\nQtObject { property int size: 4 }\n')
            valid = root / 'Valid.qml'
            valid.write_text('import QtQuick\nimport qs.Commons\nItem { width: Style.size }\n')
            self.assertEqual(lint.run(LINT, root / 'shell', [str(valid)]), 0)
            invalid = root / 'Missing.qml'
            invalid.write_text('import QtQuick\nimport qs.DoesNotExist\nItem {}\n')
            with redirect_stdout(StringIO()) as errors:
                self.assertNotEqual(lint.run(LINT, root / 'shell', [str(invalid)]), 0)
            self.assertIn('qs.DoesNotExist', errors.getvalue())
