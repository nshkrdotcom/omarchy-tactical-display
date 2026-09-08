import QtQuick
import qs.Commons
import qs.Ui as Ui
import "core"
import "model/Settings.js" as Settings

Ui.Panel {
    id: root
    moduleName: "com.nshkr.tactical-display"
    manageIpc: false

    property var anchorItem: null
    property var hostWidget: null
    property string pluginDir: ""
    property var renderStatistics: ({})
    property bool navigationPrimed: false

    function configureNavigation(payloadJson) {
        preferences.reload()
        navigation.open(Settings.payload(payloadJson || "{}"))
        navigationPrimed = true
    }

    function open(payloadJson) {
        configureNavigation(payloadJson)
        root.controller.show()
    }

    function close() {
        navigation.close()
        navigationPrimed = false
        renderStatistics = ({})
        root.controller.hide()
    }

    function openNativePanel(id) {
        if (["omarchy.audio","omarchy.network"].indexOf(id) < 0) return
        var host = root.bar && root.bar.shell ? root.bar.shell : null
        root.close()
        if (host && typeof host.summon === "function") host.summon(id,"{}")
    }

    onOpenedChanged: {
        if (root.opened && !navigationPrimed) configureNavigation("{}")
        if (!root.opened) {
            navigation.close()
            navigationPrimed = false
            renderStatistics = ({})
        }
    }

    Configuration {
        id: preferences
        host: root.bar && root.bar.shell ? root.bar.shell : null
        pluginId: root.moduleName
    }

    ThemeAdapter { id: themeAdapter }

    NavigationController {
        id: navigation
        configuration: preferences
        telemetry: telemetryService
        onDismissRequested: root.close()
    }

    Telemetry {
        id: telemetryService
        pluginDir: root.pluginDir
        active: root.opened
        configuration: navigation.effectiveSettings
        instrument: navigation.navState.instrument
    }

    Ui.KeyboardPanel {
        id: panel
        anchorItem: root.anchorItem
        owner: root.hostWidget || root
        bar: root.bar
        open: root.opened
        focusTarget: displayShell
        centerOnBar: true
        // Match the shared cockpit frame rather than inheriting generic popup padding.
        padding: Style.space(8)

        contentWidth: panel.fittedContentWidth(Style.space(1280))
        contentHeight: panel.cappedContentHeight(Style.space(840))

        TacticalDisplayShell {
            id: displayShell
            anchors.fill: parent
            controller: navigation
            theme: themeAdapter
            active: root.opened
            onStatisticsChanged: root.renderStatistics = displayShell.statistics
            Component.onCompleted: root.renderStatistics = displayShell.statistics
            onNativePanelRequested: id => root.openNativePanel(id)
        }
    }

    Component.onDestruction: telemetryService.stop()
}
