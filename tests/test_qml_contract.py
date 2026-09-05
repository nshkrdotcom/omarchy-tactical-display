"""Source-level host contracts. These do NOT substitute for qmllint/runtime tests."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


class QmlContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.overlay = (ROOT / 'Overlay.qml').read_text()
        cls.qml_text = '\n'.join(path.read_text() for path in ROOT.rglob('*.qml'))

    def test_entry_point_is_hosted_item(self):
        self.assertRegex(self.overlay, r'(?m)^Item\s*\{')
        self.assertNotIn('ShellRoot {', self.qml_text)
        for name in ('open', 'close', 'requestHide'):
            self.assertRegex(self.overlay, r'function\s+'+name+r'\s*\(')

    def test_one_backend_outside_screen_variants(self):
        self.assertEqual(self.overlay.count('Telemetry {'), 1)
        self.assertLess(self.overlay.index('Telemetry {'), self.overlay.index('Variants {'))
        self.assertIn('active: root.telemetryNeeded', self.overlay)
        self.assertIn('opened && currentScreens.length>0', self.overlay)
        self.assertNotIn('quickshell -p', self.qml_text.lower())
        self.assertNotIn('quickshell -n', self.qml_text.lower())

    def test_fullscreen_selected_screen_keyboard_and_hotplug(self):
        for term in ('PanelWindow', 'WlrLayer.Overlay', 'ExclusionMode.Ignore', 'WlrKeyboardFocus.Exclusive',
                     'model: Quickshell.screens', 'onCurrentScreensChanged', 'chooseScreen', 'surface.visible'):
            self.assertIn(term, self.overlay)
        self.assertIn('visible: root.opened && selectedScreen', self.overlay)

    def test_no_fragile_panel_parent_size_bindings(self):
        panel = self.overlay[self.overlay.index('PanelWindow {'):]
        self.assertNotRegex(panel, r'\b(?:width|height)\s*:\s*parent\.(?:width|height)\b')
        self.assertIn('anchors.fill: parent', panel)

    def test_all_five_real_view_models_share_shell(self):
        model = (ROOT / 'model/InstrumentModel.js').read_text()
        for name in ('connection', 'processTopology', 'machineAnatomy', 'storageFlow', 'audioRouting'):
            self.assertIn('function '+name+'(', model)
        self.assertIn('TacticalDisplayShell', self.overlay)
        self.assertIn('not measured per-link bandwidth', model)

    def test_native_bar_uses_host_and_has_no_telemetry(self):
        bar = (ROOT / 'BarWidget.qml').read_text()
        self.assertIn('Ui.BarWidget', bar)
        self.assertIn('Ui.WidgetButton', bar)
        self.assertIn('Qt.RightButton', bar)
        self.assertIn('vertical', bar)
        self.assertNotIn('Timer {', bar)
        self.assertNotIn('telemetry.py', bar)

    def test_no_infinite_or_decorative_render_loop(self):
        self.assertNotIn('Animation.Infinite', self.qml_text)
        self.assertNotIn('FrameAnimation', self.qml_text)
        self.assertNotIn('Scanlines', self.qml_text)
        self.assertIn('onViewChanged: schedule()', (ROOT / 'visual/Field.qml').read_text())

    def test_freeze_correlation_and_bounded_restart(self):
        telemetry = (ROOT / 'core/Telemetry.qml').read_text()
        nav = (ROOT / 'core/NavigationController.qml').read_text()
        for token in ('validateSnapshot', 'validateDetail', '4194304', 'root.failures <= 6', 'Component.onDestruction'):
            self.assertIn(token, telemetry)
        self.assertIn('frame.requestId !== root.freezeRequestId', nav)
        self.assertIn('freezeTimeout', nav)


    def test_overlay_escape_is_immediate_and_density_status_is_outside_field(self):
        shell = (ROOT / 'core/TacticalDisplayShell.qml').read_text()
        nav = (ROOT / 'core/NavigationController.qml').read_text()
        self.assertIn('event.key === Qt.Key_Escape) { dismissRequested()', nav)
        self.assertIn('event.key === Qt.Key_Backspace) back()', nav)
        self.assertIn('event.key === Qt.Key_R) reset()', nav)
        self.assertNotIn('text: "? Legend"', shell)
        self.assertNotIn('text: ", Settings"', shell)
        self.assertIn('text: "Legend"', shell)
        self.assertIn('text: "Settings"', shell)
        self.assertIn('id: densityStatus', shell)
        self.assertLess(shell.index('id: field'), shell.index('id: densityStatus'))
        self.assertIn('ESC close  /  BACKSPACE back', shell)

    def test_picker_has_explicit_keyboard_navigation(self):
        sheet = (ROOT / 'core/CommandSheet.qml').read_text()
        for token in ('property int pickerIndex', 'id: instrumentRepeater',
                      'instrumentRepeater.itemAt(root.pickerIndex)',
                      'event.key === Qt.Key_Down', 'event.key === Qt.Key_Up',
                      'event.key === Qt.Key_Return || event.key === Qt.Key_Enter',
                      'root.controller.chooseInstrument(instrument.id)'):
            self.assertIn(token, sheet)
        self.assertIn('Qt.callLater(function() { root.focusPicker(root.currentInstrumentIndex()) })', sheet)
        self.assertNotIn('row.button', sheet)

    def test_qml_relative_import_targets_exist(self):
        for file in ROOT.rglob('*.qml'):
            for target in re.findall(r'^import\s+"([^"]+)"', file.read_text(), re.M):
                self.assertTrue((file.parent / target).exists(), (file, target))
        self.assertNotIn('fixtures/', self.qml_text)

    def test_no_duplicate_signal_handler_in_same_object(self):
        # A deliberately small lexical guard for a Qt compile-time error we found.
        # This does not claim to parse/validate QML types, bindings or imports.
        def duplicates(source):
            token = re.compile(r'''//[^\n]*|/\*[\s\S]*?\*/|"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|`(?:\\.|[^`\\])*`|[{}]|\bon[A-Z]\w*\s*:''')
            scopes, found = [set()], []
            for match in token.finditer(source):
                value = match.group()
                if value == '{':
                    scopes.append(set())
                elif value == '}':
                    if len(scopes) > 1:
                        scopes.pop()
                elif re.fullmatch(r'on[A-Z]\w*\s*:', value):
                    name = value.rstrip(':').strip()
                    if name in scopes[-1]:
                        found.append((name, source[:match.start()].count('\n') + 1))
                    scopes[-1].add(name)
            return found
        self.assertEqual(duplicates('Item { onVisibleChanged: f(); onVisibleChanged: g() }'), [('onVisibleChanged', 1)])
        self.assertEqual(duplicates('Item { onVisibleChanged: f(); Item { onVisibleChanged: g() } }'), [])
        self.assertEqual(duplicates('Item { onVisibleChanged: f(); text: "onVisibleChanged: {}"; /* onVisibleChanged: */ }'), [])
        for file in ROOT.rglob('*.qml'):
            self.assertEqual(duplicates(file.read_text()), [], str(file.relative_to(ROOT)))
