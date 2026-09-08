import QtQuick
import "../model/Settings.js" as Settings

QtObject {
    id: root
    property var host: null
    property string pluginId: "com.nshkr.tactical-display"
    property var values: Settings.normalize({}).values
    property var warnings: []
    property bool readOnly: false
    property string persistenceMessage: ""
    property bool loading: false
    property var observedConfig: host && host.shellConfig ? host.shellConfig : ({})
    onObservedConfigChanged: reload()
    function reload() {
        loading = true
        var result = Settings.normalize(Settings.entryFromShell(observedConfig, pluginId))
        values = result.values
        warnings = result.warnings
        readOnly = result.readOnly
        loading = false
    }
    function setValue(name, value) {
        if (readOnly) { persistenceMessage = "Newer configuration is read-only; no data was overwritten."; return }
        var next = Settings.mergedEntry({}, values)
        if (!Settings.keys[name]) return
        next[Settings.keys[name]] = value
        values = Settings.normalize(next).values
        if (host && typeof host.updateEntryInline === "function") {
            var existing = Settings.entryFromShell(host.shellConfig, pluginId)
            if (existing.id) {
                host.updateEntryInline(pluginId, Settings.mergedEntry(existing, values))
                persistenceMessage = ""
            } else {
                persistenceMessage = "Session-only settings: enable the plugin to create its native configuration entry."
            }
        } else {
            persistenceMessage = "Session-only settings: Quattro's inline settings API is unavailable."
        }
    }
    Component.onCompleted: reload()
}
