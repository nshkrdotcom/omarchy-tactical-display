from pathlib import Path
import os
import unittest

ROOT = Path(__file__).resolve().parents[1]


class RepositoryCompletenessTests(unittest.TestCase):
    def test_required_public_repository_files_exist(self):
        required = [
            "README.md",
            "LICENSE",
            "manifest.json",
            "Makefile",
            "docs/ARCHITECTURE.md",
            "docs/CONFIGURATION.md",
            "docs/DATA-MODEL.md",
            "docs/SECURITY-PRIVACY.md",
            "docs/TESTING.md",
            "docs/UPSTREAM-CONTRACT.md",
            "docs/VISUAL-DESIGN.md",
        ]
        missing = [path for path in required if not (ROOT / path).is_file()]
        self.assertEqual(missing, [])
        self.assertTrue((ROOT / "visual" / "Field.qml").is_file())
        self.assertTrue((ROOT / "model" / "InstrumentModel.js").is_file())

    def test_runtime_scripts_are_executable(self):
        for relative in ["scripts/telemetry.py", "scripts/doctor.sh", "scripts/validate.sh", "scripts/print-bindings.sh"]:
            path = ROOT / relative
            self.assertTrue(os.access(path, os.X_OK), relative)


if __name__ == "__main__":
    unittest.main()
