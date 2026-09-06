"""Source-level host contracts. These do NOT substitute for qmllint/runtime tests."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


class QmlContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.overlay = (ROOT / 'Overlay.qml').read_text()
        cls.panel = (ROOT / 'Panel.qml').read_text()
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
        self.assertIn('TacticalDisplayShell', self.panel)
        self.assertIn('Line width indicates socket count', model)

    def test_native_bar_uses_host_and_has_no_telemetry(self):
        bar = (ROOT / 'BarWidget.qml').read_text()
        self.assertIn('Ui.BarWidget', bar)
        self.assertIn('Ui.WidgetButton', bar)
        self.assertIn('Qt.RightButton', bar)
        self.assertIn('vertical', bar)
        self.assertIn('source: Qt.resolvedUrl("Panel.qml")', bar)
        self.assertIn('panelLoader.item.anchorItem = button', bar)
        self.assertIn('panelLoader.item.hostWidget = root', bar)
        self.assertIn('Qt.resolvedUrl("scripts/telemetry.py")', bar)
        self.assertIn('panelLoader.item.pluginDir', bar)
        self.assertNotIn('bar.shell.toggle', bar)
        self.assertNotIn('omarchy-shell', bar)
        self.assertNotIn('Process {', bar)
        self.assertNotIn('Timer {', bar)
        self.assertNotIn('Telemetry {', bar)
        self.assertNotIn('command: ["/usr/bin/python3"', bar)

    def test_bar_click_uses_native_omarchy_panel_geometry(self):
        panel = self.panel
        for token in (
            'Panel {',
            'manageIpc: false',
            'KeyboardPanel {',
            'anchorItem: root.anchorItem',
            'owner: root.hostWidget || root',
            'bar: root.bar',
            'focusTarget: displayShell',
            'centerOnBar: true',
            'contentWidth: panel.fittedContentWidth(Style.space(1280))',
            'contentHeight: panel.cappedContentHeight(Style.space(840))',
            'TacticalDisplayShell {',
        ):
            self.assertIn(token, panel)
        self.assertNotIn('PanelWindow {', panel)
        self.assertNotIn('WlrLayershell', panel)
        self.assertNotIn('PanelKeyCatcher', panel)
        self.assertNotIn('Style.space(48)', panel)

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

    def test_navigation_scopes_instance_topology_instead_of_streaming_all_instances(self):
        nav = (ROOT / 'core' / 'NavigationController.qml').read_text()
        telemetry = (ROOT / 'core' / 'Telemetry.qml').read_text()
        self.assertIn('setInstanceGroups', nav)
        self.assertIn('onNavStateChanged', nav)
        self.assertIn('function setInstanceGroups', telemetry)
        self.assertIn('op:"scope"', telemetry)
        self.assertIn('scope-result', telemetry)

    def test_helper_health_requires_valid_frames_and_uses_fixed_interpreter(self):
        telemetry = (ROOT / 'core/Telemetry.qml').read_text()
        for token in ('property bool started', 'firstFrameWatch', 'healthWatch', 'restartBackend', '/usr/bin/python3',
                      'clearEnvironment: true', 'PYTHONNOUSERSITE', 'terminationWatch', 'sampler.signal(15)', 'sampler.signal(9)'):
            self.assertIn(token, telemetry)
        self.assertIn('root.ready = true', telemetry)
        self.assertGreater(telemetry.index('root.ready = true'), telemetry.index('Protocol.validateSnapshot(frame)'))


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

    def test_shell_has_explicit_outer_viewport_frame(self):
        shell = (ROOT / 'core/TacticalDisplayShell.qml').read_text()
        for token in (
            'readonly property int margin: Math.max(10,Math.min(20,width*0.012))',
            'readonly property int frameInset: 4',
            'id: viewportFrame',
            'anchors.margins: root.frameInset',
            'border.color: root.theme.colors.accent',
            'border.width: 2',
        ):
            self.assertIn(token, shell)

    def test_picker_has_explicit_keyboard_navigation(self):
        sheet = (ROOT / 'core/CommandSheet.qml').read_text()
        shell = (ROOT / 'core/TacticalDisplayShell.qml').read_text()

        for token in (
            'property int pickerIndex',
            'id: instrumentRepeater',
            'instrumentRepeater.itemAt(root.pickerIndex)',
            'function choosePickerInstrument(index)',
            'event.key === Qt.Key_Down',
            'event.key === Qt.Key_Up',
            'event.key === Qt.Key_Return || event.key === Qt.Key_Enter',
        ):
            self.assertIn(token, sheet)

        for token in (
            'readonly property bool pickerSheetVisible:',
            'if (pickerSheetVisible &&',
            'event.key >= Qt.Key_1 && event.key <= Qt.Key_5',
            'var direct = Instruments.catalog[event.key - Qt.Key_1]',
            'controller.chooseInstrument(direct.id)',
        ):
            self.assertIn(token, shell)

        self.assertNotIn('handlePickerDigit', sheet)
        self.assertNotIn('context: Qt.WindowShortcut', sheet)
        self.assertNotIn('sequence: "5"', sheet)

    def test_overlay_shortcuts_yield_to_editors_sheets_and_command_modifiers(self):
        shell = (ROOT / 'core/TacticalDisplayShell.qml').read_text()
        nav = (ROOT / 'core/NavigationController.qml').read_text()
        sheet = (ROOT / 'core/CommandSheet.qml').read_text()
        self.assertIn('readonly property var focusedItem: Window.activeFocusItem', shell)
        self.assertIn('Item { id: fieldFocusTarget; width: 0; height: 0; activeFocusOnTab: false }', shell)
        self.assertIn('function focusField() { controlsFocus=false; fieldFocusTarget.forceActiveFocus() }', shell)
        self.assertIn('function focusControls() { controlsFocus=true; searchButton.forceActiveFocus() }', shell)
        self.assertIn('controlsFocus = !!focusedItem && focusedItem !== fieldFocusTarget', shell)
        self.assertIn('Keys.onPressed: event => root.controller.handleSearchKey(event)', shell)
        self.assertIn('Component.onCompleted: Qt.callLater(function() { root.focusField() })', shell)
        self.assertIn('if (editing || panelActive) return', nav)
        self.assertIn('Qt.ControlModifier | Qt.AltModifier | Qt.MetaModifier', nav)
        self.assertIn('function handleSearchKey(event)', nav)
        self.assertIn('Qt.ShiftModifier)) return', nav)
        self.assertNotIn('navState.showPicker && event.key >= Qt.Key_1', nav)
        self.assertIn('function choosePickerInstrument(index)', sheet)

    def test_all_command_sheets_handle_backspace_before_picker_gating(self):
        sheet = (ROOT / 'core/CommandSheet.qml').read_text()
        backspace = 'if (event.key === Qt.Key_Backspace && !(event.modifiers & (Qt.ControlModifier | Qt.AltModifier | Qt.MetaModifier)))'
        picker_gate = 'if (root.kind !== "picker" || event.modifiers & (Qt.ControlModifier | Qt.AltModifier | Qt.MetaModifier)) return'
        self.assertIn(backspace, sheet)
        self.assertIn(picker_gate, sheet)
        self.assertLess(sheet.index(backspace), sheet.index(picker_gate))

    def test_focus_reset_paths_clear_control_mode(self):
        shell = (ROOT / 'core/TacticalDisplayShell.qml').read_text()
        self.assertIn('onPicked: key => { root.controller.pickKey(key); root.focusField() }', shell)
        self.assertIn('onFocused: key => { root.controller.pickKey(key); root.controller.focusSelection(); root.focusField() }', shell)
        self.assertIn('onSheetVisibleChanged: if (!sheetVisible) Qt.callLater', shell)
        self.assertIn('function onInstrumentSelected(instrument) { modeTransition.restart(); root.focusField() }', shell)

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