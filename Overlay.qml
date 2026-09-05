pragma ComponentBehavior: Bound
import QtQuick
import Quickshell
import Quickshell.Hyprland
import Quickshell.Wayland
import "core"
import "model/Settings.js" as Settings

Item {
    id: root
    // Injected by Quattro v4.0.1; this is hosted, never a standalone ShellRoot.
    property string omarchyPath: Quickshell.env("OMARCHY_PATH")
    property var shell: null
    property var manifest: ({})
    property var pluginRegistry: null
    property var barWidgetRegistry: null
    property bool opened: false
    property string targetScreen: ""
    property var renderStatistics: ({})
    property var currentScreens: Quickshell.screens
    readonly property string pluginDir: manifest && manifest.__sourceDir ? String(manifest.__sourceDir) : ""
    readonly property string pluginId: manifest && manifest.id ? String(manifest.id) : "nshkr.tactical-display"
    readonly property bool telemetryNeeded: opened && currentScreens.length>0

    // Read-only, identity-free evidence for the native operator acceptance runner.
    function diagnostics(_payload) {
        var f=telemetryService.snapshot || {}
        return JSON.stringify({version:"1.0.0",opened:opened,instrument:navigation.navState.instrument,
            mode:navigation.invocationMode,monitor:targetScreen,helperPid:telemetryService.helperPid,
            ready:telemetryService.ready,fresh:telemetryService.fresh,status:telemetryService.statusText,
            frozen:navigation.navState.frozen,sequence:f.sequence===undefined?null:f.sequence,
            sampleDurationMs:f.sampleDurationMs===undefined?null:f.sampleDurationMs,
            privacy:navigation.effectiveSettings.privacy,render:renderStatistics})
    }
    function chooseScreen(requested) {
        var names=[]
        for (var i=0;i<currentScreens.length;i++) names.push(String(currentScreens[i].name))
        if (requested && names.indexOf(requested)>=0) return requested
        var focused=Hyprland.focusedMonitor ? String(Hyprland.focusedMonitor.name) : ""
        if (names.indexOf(focused)>=0) return focused
        return names.length ? names[0] : ""
    }
    function open(payloadJson) {
        // A canceled cold summon can leave a queued payload in Quattro 4.0.1.
        // Never display it when the host no longer marks this plugin open.
        if (shell && shell.openPanelIds && shell.openPanelIds[pluginId] !== true) return
        var args=Settings.payload(payloadJson)
        preferences.reload()
        navigation.open(args)
        targetScreen=chooseScreen(args.monitor)
        if (args.monitor && targetScreen!==args.monitor) navigation.setFlag("notice","Requested monitor is unavailable; using the focused display.")
        if (!targetScreen) { navigation.setFlag("notice","No display is currently available."); return }
        opened=true
    }
    function close() {
        opened=false
        navigation.close()
        targetScreen=""
        renderStatistics=({})
    }
    function requestHide() {
        if (shell && typeof shell.hide === "function") shell.hide(pluginId)
        else close()
    }
    function openNativePanel(id) {
        // Only hard-coded observational shell panels may be invoked here.
        if (["omarchy.audio","omarchy.network"].indexOf(id)<0) return
        var host=shell
        requestHide()
        if (host && typeof host.summon === "function") host.summon(id,"{}")
    }
    onCurrentScreensChanged: {
        var present=false
        for (var i=0;i<currentScreens.length;i++) if (String(currentScreens[i].name)===targetScreen) present=true
        if (opened && !present) {
            targetScreen=chooseScreen("")
            if (!targetScreen) requestHide()
        }
    }
    Configuration { id: preferences; host: root.shell; pluginId: root.pluginId }
    ThemeAdapter { id: themeAdapter }
    NavigationController {
        id: navigation
        configuration: preferences
        telemetry: telemetryService
        onDismissRequested: root.requestHide()
    }
    Telemetry {
        id: telemetryService
        pluginDir: root.pluginDir
        active: root.telemetryNeeded
        configuration: navigation.effectiveSettings
        instrument: navigation.navState.instrument
    }
    Variants {
        model: Quickshell.screens
        PanelWindow {
            id: surface
            required property var modelData
            readonly property bool selectedScreen: String(modelData.name)===root.targetScreen
            screen: modelData
            visible: root.opened && selectedScreen
            color: "transparent"
            exclusionMode: ExclusionMode.Ignore
            anchors { top: true; bottom: true; left: true; right: true }
            WlrLayershell.namespace: "nshkr-tactical-display"
            WlrLayershell.layer: WlrLayer.Overlay
            WlrLayershell.keyboardFocus: surface.visible ? WlrKeyboardFocus.Exclusive : WlrKeyboardFocus.None
            Loader {
                anchors.fill: parent
                active: surface.visible
                sourceComponent: TacticalDisplayShell {
                    id: displayShell
                    controller: navigation
                    theme: themeAdapter
                    active: root.opened
                    onStatisticsChanged: root.renderStatistics=displayShell.statistics
                    Component.onCompleted: root.renderStatistics=displayShell.statistics
                    onNativePanelRequested: id => root.openNativePanel(id)
                }
            }
        }
    }
    Component.onDestruction: { opened=false; telemetryService.stop() }
}
