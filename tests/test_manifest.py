import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ManifestContractTests(unittest.TestCase):
    def test_manifest_is_quattro_overlay(self):
        manifest = json.loads((ROOT / "manifest.json").read_text())
        self.assertEqual(manifest["schemaVersion"], 1)
        self.assertEqual(manifest["id"], "nshkr.tactical-display")
        self.assertEqual(manifest["kinds"], ["overlay", "bar-widget"])
        self.assertEqual(manifest["entryPoints"]["barWidget"], "BarWidget.qml")
        self.assertTrue((ROOT / "BarWidget.qml").is_file())
        self.assertFalse(manifest.get("keepLoaded", False))
        self.assertEqual(manifest["entryPoints"]["overlay"], "Overlay.qml")
        self.assertTrue((ROOT / manifest["entryPoints"]["overlay"]).is_file())
        self.assertFalse(manifest["id"].startswith("omarchy."))

    def test_repository_contains_no_symlinks(self):
        symlinks = [path for path in ROOT.rglob("*") if path.is_symlink()]
        self.assertEqual(symlinks, [])


if __name__ == "__main__":
    unittest.main()
