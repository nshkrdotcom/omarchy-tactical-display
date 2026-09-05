from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


class QmlContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.overlay = (ROOT / "Overlay.qml").read_text()
        cls.qml_text = "\n".join(path.read_text() for path in ROOT.rglob("*.qml"))

    def test_entry_point_is_item_not_shellroot(self):
        self.assertRegex(self.overlay, r"(?m)^Item\s*\{")
        self.assertNotIn("ShellRoot {", self.overlay)

    def test_overlay_exposes_quattro_lifecycle(self):
        self.assertRegex(self.overlay, r"function\s+open\s*\(")
        self.assertRegex(self.overlay, r"function\s+close\s*\(")

    def test_overlay_uses_one_shell_host_pattern(self):
        lowered = self.qml_text.lower()
        self.assertNotIn("quickshell -p", lowered)
        self.assertNotIn("quickshell -n", lowered)

    def test_fullscreen_layer_shell_contract(self):
        self.assertIn("PanelWindow", self.overlay)
        self.assertIn("WlrLayer.Overlay", self.overlay)
        self.assertIn("ExclusionMode.Ignore", self.overlay)
        self.assertIn("WlrKeyboardFocus.Exclusive", self.overlay)
        self.assertIn("model: Quickshell.screens", self.overlay)

    def test_avoids_known_variants_parent_width_crash_pattern(self):
        # Qt 6.11.2 / Quickshell regression: direct width: parent.width under
        # per-screen PanelWindow variants has caused construction crashes.
        panel_start = self.overlay.index("PanelWindow {")
        panel_text = self.overlay[panel_start:]
        panel_header = panel_text[:panel_text.index("HudSurface {")]
        self.assertNotRegex(panel_header, r"\bwidth\s*:\s*parent\.width\b")
        self.assertNotRegex(panel_header, r"\bheight\s*:\s*parent\.height\b")
        self.assertIn("anchors.fill: parent", panel_text)


    def test_connection_field_is_primary_instrument(self):
        self.assertIn("NetworkFieldInstrument", self.overlay)
        self.assertIn("THIS MACHINE", self.overlay)
        self.assertIn("THE WORLD", self.overlay)
        self.assertNotIn("ReactorInstrument {", self.overlay)

    def test_connection_field_documents_direction_truthfully(self):
        field = (ROOT / "instruments" / "NetworkFieldInstrument.qml").read_text()
        self.assertIn("direction, not measured per-link bandwidth", field)
        self.assertIn("processKey", field)
        self.assertIn("remoteKey", field)

    def test_only_left_click_mouse_area_is_used(self):
        self.assertNotIn("Qt.RightButton", self.qml_text)


if __name__ == "__main__":
    unittest.main()
