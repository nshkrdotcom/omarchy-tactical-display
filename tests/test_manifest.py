import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ManifestContractTests(unittest.TestCase):
    def test_manifest_is_quattro_overlay(self):
        manifest = json.loads((ROOT / "manifest.json").read_text())
        self.assertEqual(manifest["schemaVersion"], 1)
        self.assertEqual(manifest["id"], "com.nshkr.tactical-display")
        self.assertEqual(manifest["kinds"], ["overlay", "bar-widget"])
        self.assertEqual(manifest["entryPoints"]["barWidget"], "BarWidget.qml")
        self.assertTrue((ROOT / "BarWidget.qml").is_file())
        self.assertFalse(manifest.get("keepLoaded", False))
        self.assertEqual(manifest["entryPoints"]["overlay"], "Overlay.qml")
        self.assertTrue((ROOT / manifest["entryPoints"]["overlay"]).is_file())
        self.assertFalse(manifest["id"].startswith("omarchy."))

    def test_marketplace_required_manifest_metadata(self):
        manifest = json.loads((ROOT / "manifest.json").read_text())
        for key in ("schemaVersion", "id", "name", "version", "author", "description", "kinds", "entryPoints"):
            self.assertIn(key, manifest)
        self.assertRegex(manifest["id"], r"^[a-z0-9][a-z0-9._-]*$")
        self.assertIn(".", manifest["id"])
        self.assertLessEqual(len(manifest["version"]), 64)
        self.assertTrue(manifest["author"].strip())
        self.assertTrue(manifest["description"].strip())
        self.assertEqual(manifest.get("license"), "MIT")
        self.assertEqual(manifest.get("barWidget", {}).get("defaultSection"), "right")

    def test_marketplace_root_docs_cover_install_removal_and_dependencies(self):
        readme = (ROOT / "README.md").read_text()
        self.assertRegex(readme, r"(?mi)^## Install\s*$")
        self.assertIn("omarchy plugin add", readme)
        self.assertRegex(readme, r"(?mi)^### Remove\s*$")
        self.assertIn("omarchy plugin remove com.nshkr.tactical-display", readme)
        self.assertRegex(readme, r"(?mi)^## Requirements and External Dependencies\s*$")
        for dependency in ("Python", "pw-dump", "wpctl", "nvidia-smi", "maxminddb"):
            self.assertIn(dependency, readme)
        self.assertTrue((ROOT / "LICENSE").is_file())
        self.assertIn("MIT License", (ROOT / "LICENSE").read_text())

    def test_repository_contains_no_symlinks(self):
        symlinks = [path for path in ROOT.rglob("*") if path.is_symlink()]
        self.assertEqual(symlinks, [])


if __name__ == "__main__":
    unittest.main()
