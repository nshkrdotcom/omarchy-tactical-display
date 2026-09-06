import QtQuick
import qs.Ui as Ui
import qs.Commons
import "model/Settings.js" as Settings
import "model/InstrumentModel.js" as Instruments

Ui.BarWidget {
    id: root
    moduleName: "nshkr.tactical-display"
    property string omarchyPath: ""
    property var shell: null
    property var manifest: null
    readonly property string sourceDir: String(Qt.resolvedUrl("scripts/telemetry.py")).replace(/^file:\/\//, "").replace(/\/scripts\/telemetry\.py$/, "")

    readonly property var preferences: Settings.normalize(settings).values
    readonly property bool opened: panelLoader.item ? panelLoader.item.opened === true : false
    readonly property bool popoutSwitchClosing: panelLoader.item ? panelLoader.item.popoutSwitchClosing === true : false

    function open(payloadJson) {
        if (panelLoader.item) panelLoader.item.open(payloadJson || "{}")
    }

    function close() {
        if (panelLoader.item) panelLoader.item.close()
    }

    function toggle(payloadJson) {
        if (root.opened) root.close()
        else root.open(payloadJson || "{}")
    }

    function closeForPopoutSwitch() {
        if (panelLoader.item) panelLoader.item.closeForPopoutSwitch()
    }

    function invoke(picker) {
        var payload = JSON.stringify({mode:"toggle",picker:picker})
        if (picker) root.open(payload)
        else root.toggle(payload)
    }

    function injectPanel() {
        if (!panelLoader.item) return
        panelLoader.item.bar = root.bar
        panelLoader.item.anchorItem = button
        panelLoader.item.hostWidget = root
        panelLoader.item.pluginDir = root.manifest && root.manifest.__sourceDir ? String(root.manifest.__sourceDir) : root.sourceDir
        panelLoader.item.settings = root.settings
    }

    implicitWidth: button.implicitWidth
    implicitHeight: button.implicitHeight

    onBarChanged: injectPanel()
    onManifestChanged: injectPanel()
    onSettingsChanged: injectPanel()

    Loader {
        id: panelLoader
        active: true
        source: Qt.resolvedUrl("Panel.qml")
        visible: false
        onLoaded: {
            root.injectPanel()
            Qt.callLater(root.injectPanel)
        }
    }

    Ui.WidgetButton {
        id: button
        anchors.fill: parent
        bar: root.bar
        property bool compactMode:
            root.vertical || root.preferences.barMode !== "label"

        fixedWidth:
            !root.vertical && compactMode
                ? Style.bar.statusSlot
                : -1

        fixedHeight:
            root.vertical
                ? Style.bar.statusSlot
                : -1

        horizontalMargin: compactMode ? 0 : 8.5
        labelVisible: !compactMode

        text:
            !root.vertical && root.preferences.barMode === "label"
                ? "Tactical"
                : "TD"
        tooltipText: "Tactical Display · "+Instruments.info(root.preferences.lastInstrument).name+"\nLeft-click: Toggle panel · Right-click: Choose instrument"
        Ui.OpticalGlyph {
            visible: button.compactMode

            anchors.centerIn: parent
            anchors.horizontalCenterOffset:
                root.vertical ? 0 : -Style.spacing.xxs

            width: Style.bar.iconCanvas
            height: Style.bar.iconCanvas

            text: "TD"
            fontFamily: button.fontFamily
            fontSize: button.fontSize
            color:
                button.active && button.useActiveColor
                    ? button.activeColor
                    : button.foreground
        }

        onPressed: mouseButton => root.invoke(mouseButton === Qt.RightButton)
    }
}
