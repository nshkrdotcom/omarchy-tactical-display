import QtQuick
import Quickshell.Io
import qs.Ui as Ui
import qs.Commons
import "model/Settings.js" as Settings
import "model/InstrumentModel.js" as Instruments

Ui.BarWidget {
    id: root
    moduleName: "nshkr.tactical-display"
    readonly property var preferences: Settings.normalize(settings).values
    property string invocationError: ""
    implicitWidth: button.implicitWidth
    implicitHeight: button.implicitHeight
    function invoke(picker) {
        var payload=JSON.stringify({mode:"toggle",picker:picker})
        // The native bar exposes its owning shell. Prefer its in-process lifecycle route.
        if (bar && bar.shell && typeof bar.shell.toggle === "function") {
            if (picker) bar.shell.summon(moduleName,payload)
            else bar.shell.toggle(moduleName,payload)
            return
        }
        if (ipc.running) return
        ipc.command=["omarchy-shell","shell",picker?"summon":"toggle",moduleName,payload]
        ipc.running=true
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
        tooltipText: "Tactical Display · "+Instruments.info(root.preferences.lastInstrument).name+"\nLeft-click: Toggle overlay · Right-click: Choose instrument"+(root.invocationError?"\n"+root.invocationError:"")
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

        onPressed: button => root.invoke(button===Qt.RightButton)
    }
    Process {
        id: ipc
        running: false
        onExited: exitCode => root.invocationError = exitCode===0 ? "" : "Shell invocation failed; run plugin doctor."
    }
}
