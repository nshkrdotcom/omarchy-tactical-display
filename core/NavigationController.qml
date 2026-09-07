import QtQuick
import "../model/Navigation.js" as Navigation
import "../model/InstrumentModel.js" as Instruments
import "../model/Settings.js" as Settings
import "../model/Lenses.js" as Lenses
import "../model/Operator.js" as Operator

Item {
    id: root
    property var telemetry: null
    property var configuration: null
    property var navState: Navigation.fresh("connection")
    property var liveFrame: ({})
    property var displayFrame: ({})
    property var detailFrame: null
    property bool freezePending: false
    property int freezeRequestId: -1
    property var pendingAction: null
    property string invocationMode: "toggle"
    property string hoveredKey: ""
    property var operatorSession: Operator.freshSession()
    property var frozenSession: Operator.freshSession()
    property var pins: []
    property var comparisonBaseline: null
    readonly property var displaySession: navState.frozen ? frozenSession : operatorSession
    readonly property double observationNow: (displayFrame.monotonic || 0) + (navState.frozen || !telemetry ? 0 : Math.max(0,(telemetry.clock-telemetry.lastSampleAt)/1000))
    readonly property var attention: Operator.assess(displayFrame,{privacy:effectiveSettings.privacy,now:observationNow})
    readonly property bool selectedPinned: !!selected && pins.some(function(p) { return p.key === root.selected.key })
    readonly property var effectiveSettings: {
        var values = JSON.parse(JSON.stringify(configuration ? configuration.values : Settings.defaults))
        if (navState.privacyOverride !== null) values.privacy = navState.privacyOverride
        return values
    }
    readonly property var view: Instruments.build(displayFrame, navState, effectiveSettings)
    readonly property var selected: {
        var entity=view.selection || navState.selectedRecord
        if (entity && effectiveSettings.privacy && entity.kind!=="subsystem") {
            entity=Object.assign({},entity)
            entity.name=Instruments.alias(entity.kind,entity.key)
        }
        return entity
    }
    readonly property var currentDetail: detailFrame && selected && detailFrame.key === selected.key && !detailFrame.ended && (navState.frozen || detailFrame.monotonic >= displayFrame.monotonic) ? detailFrame.data : selected ? selected.raw : null
    signal dismissRequested()
    signal instrumentSelected(string instrument)
    signal searchRequested()

    function open(args) {
        var defaults = configuration ? configuration.values : Settings.defaults
        var next = Navigation.fresh(args.instrument || (defaults.introSeen ? defaults.lastInstrument : defaults.defaultInstrument))
        next.context = args.focus
        next.filters = args.filters
        next.privacyOverride = args.privacy
        next.showPicker = args.picker || !defaults.introSeen
        next.showIntro = !defaults.introSeen
        next.showHelp = args.help
        next.notice = args.errors.join(" ")
        navState = next
        if (args.instrument && configuration && configuration.values.lastInstrument!==args.instrument) configuration.setValue("lastInstrument",args.instrument)
        invocationMode = args.mode
        detailFrame = null
        freezePending = false
        freezeRequestId = -1
        freezeTimeout.stop()
        pendingAction = null
    }
    function close() {
        liveFrame = ({})
        displayFrame = ({})
        detailFrame = null
        navState = Navigation.fresh(configuration ? configuration.values.lastInstrument : "connection")
        pendingAction = null
        operatorSession = Operator.freshSession()
        frozenSession = Operator.freshSession()
        pins = []
        comparisonBaseline = null
        hoveredKey = ""
        resolveTimer.stop()
        freezePending = false
        freezeRequestId = -1
        freezeTimeout.stop()
    }
    function setFlag(name, value) {
        var next = Object.assign({}, navState)
        next[name] = value
        navState = next
    }
    function captureBaseline() {
        if (!displayFrame.schemaVersion) return
        comparisonBaseline = Operator.captureBaseline(displayFrame,{now:observationNow})
    }
    function togglePinSelection() {
        if (!selected) return
        if (!selectedPinned && pins.length >= 8) { setFlag("notice","Eight entities are pinned. Remove a pin in Briefing to make room."); return }
        pins = Operator.togglePin(pins,selected,navState.instrument)
    }
    function removePin(key) { pins = pins.filter(function(p) { return p.key !== key }) }
    function operatorReport() {
        return Operator.report(displayFrame,displaySession,pins,comparisonBaseline,{privacy:effectiveSettings.privacy,frozen:navState.frozen,now:observationNow})
    }
    function jumpOperator(target) {
        if (!target) return
        setFlag("showOperator",false)
        if (target.instrument === "capabilities") { setFlag("showCapabilities",true); return }
        if (!Instruments.catalog.some(function(i) { return i.id === target.instrument })) return
        chooseInstrument(target.instrument)
        var next = Object.assign({},navState)
        next.query = ""; next.filters = ({}); next.focusKey = ""; next.selectedKey = ""; next.selectedRecord = null
        next.isolated = false; next.showSearch = false
        next.context = target.entityKey ? {key:target.entityKey} : null
        next.notice = ""
        navState = next
    }
    function syncTelemetryScope() {
        if (!telemetry) return
        var groups = []
        if (navState.instrument === "connection") {
            groups = (navState.expanded || []).slice(0,64)
            var context = navState.context || {}
            if (context.groupKey && groups.indexOf(context.groupKey) < 0) groups.push(context.groupKey)
        }
        telemetry.setInstanceGroups(groups, navState.frozen === true)
    }
    function chooseInstrument(id) {
        if (id !== navState.instrument && (navState.frozen || freezePending)) {
            if (telemetry) telemetry.freeze(false)
            freezeRequestId = -1
            freezeTimeout.stop()
            setFlag("frozen",false)
            freezePending = false
            displayFrame = liveFrame
        }
        navState = Navigation.switchTo(navState,id)
        if (configuration) {
            configuration.setValue("lastInstrument",id)
            if (!configuration.values.introSeen) configuration.setValue("introSeen",true)
        }
        setFlag("showIntro",false)
        detailFrame = null
        instrumentSelected(id)
    }
    function pick(record) {
        navState = Navigation.select(navState,record)
        detailFrame = null
        if (telemetry && record && record.kind !== "subsystem") telemetry.inspect(record.key,0,navState.frozen)
    }
    function pickKey(key) {
        var n = view.allNodes.filter(n => n.key === key)[0]
        if (!n) {
            var e = view.edges.filter(e => e.key === key)[0]
            if (e) n = {key:e.key,kind:"relationship",name:e.label || "Observed relationship",subtitle:e.kind,raw:e.raw}
        }
        if (n) pick(n)
    }
    function focusSelection() {
        if (selected) navState = Navigation.focus(navState,selected)
    }
    function expandSelection() {
        if (!selected || selected.kind !== "application") return
        var expanded=view.visibleNodes.some(function(n){return n.kind==="process" && n.groupKey===selected.key})
        navState=Navigation.toggleGroup(navState,selected.key,expanded)
        // A group focus otherwise promotes hidden members; preserve selection but clear that lens.
        if (navState.instrument==="processes" && expanded) setFlag("focusKey","")
    }
    function step(delta) { navState = Navigation.traverse(navState,view.results,delta); detailFrame = null }
    function back() {
        if (pendingAction) { pendingAction = null; return }
        var result = Navigation.back(navState)
        if (navState.instrument !== result.state.instrument && (navState.frozen || freezePending)) {
            if (telemetry) telemetry.freeze(false)
            result.state.frozen = false
            freezePending = false
            freezeRequestId = -1
            freezeTimeout.stop()
            displayFrame = liveFrame
        }
        navState = result.state
        if (result.close) dismissRequested()
    }
    function reset() { navState = Navigation.reset(navState); detailFrame = null }
    function setQuery(text) { setFlag("query",text.slice(0,160)) }
    function filter(name,value) {
        var filters = Object.assign({},navState.filters)
        if (!value || value === "any" || value === "all") delete filters[name]
        else filters[name] = value
        setFlag("filters",filters)
    }
    function cycle(name,values) {
        var at = values.indexOf(navState.filters[name] || values[0])
        filter(name,values[(at+1)%values.length])
    }
    function toggleFreeze() {
        if (freezePending || !telemetry || !telemetry.ready || !liveFrame.schemaVersion) return
        freezePending = true
        freezeRequestId = telemetry.freeze(!navState.frozen)
        freezeTimeout.restart()
    }
    function privacy() {
        var value = !effectiveSettings.privacy
        setFlag("privacyOverride",null)
        if (configuration) configuration.setValue("privacy",value)
    }
    function inspectMore() {
        setFlag("showAllDetails",!navState.showAllDetails)
        if (telemetry && selected && selected.kind !== "subsystem") telemetry.inspect(selected.key,0,navState.frozen)
    }
    function detailPage(offset) { if (telemetry && selected) telemetry.inspect(selected.key,offset,navState.frozen) }
    function requestAction(action) {
        if (selected && !navState.frozen && effectiveSettings.audioActions) pendingAction = {action:action,key:selected.key,name:selected.name}
    }
    function confirmAction() {
        if (pendingAction && telemetry) telemetry.audioAction(pendingAction.action,pendingAction.key,null)
        pendingAction = null
    }
    function handleSearchKey(event) {
        // The TextField owns ordinary editing and modifier chords. Only the
        // unmodified result-navigation keys are promoted to overlay actions.
        if (event.modifiers & (Qt.ControlModifier | Qt.AltModifier | Qt.MetaModifier | Qt.ShiftModifier)) return
        if (event.key === Qt.Key_Down || event.key === Qt.Key_Up) {
            step(event.key === Qt.Key_Down ? 1 : -1)
            event.accepted = true
        } else if (event.key === Qt.Key_Return || event.key === Qt.Key_Enter) {
            if (!selected) step(1)
            focusSelection()
            event.accepted = true
        }
    }
    function handleKey(event, editing, panelActive) {
        // Tactical Display is an ephemeral Omarchy overlay: Escape is the invariant
        // one-stroke exit from every mode, including search, sheets and focused views.
        if (event.key === Qt.Key_Escape) { dismissRequested(); event.accepted = true; return }
        // Editors and command sheets get first refusal. Their own key handlers may
        // opt into semantic navigation without exposing normal editing/control keys
        // to the overlay shortcut layer.
        if (editing || panelActive) return
        if (event.modifiers & (Qt.ControlModifier | Qt.AltModifier | Qt.MetaModifier)) return
        if (!(event.modifiers & Qt.ShiftModifier) && event.key >= Qt.Key_1 && event.key <= Qt.Key_5) chooseInstrument(Instruments.catalog[event.key - Qt.Key_1].id)
        else if (event.key === Qt.Key_Tab || event.key === Qt.Key_Backtab) step(event.key === Qt.Key_Backtab || event.modifiers & Qt.ShiftModifier ? -1 : 1)
        else if (event.key === Qt.Key_Right || event.key === Qt.Key_Down) step(1)
        else if (event.key === Qt.Key_Left || event.key === Qt.Key_Up) step(-1)
        else if (event.key === Qt.Key_Return || event.key === Qt.Key_Enter) focusSelection()
        else if (event.key === Qt.Key_Backspace) back()
        else if (event.key === Qt.Key_R) reset()
        else if (event.key === Qt.Key_Space) toggleFreeze()
        else if (event.key === Qt.Key_Slash && !(event.modifiers & Qt.ShiftModifier)) { setFlag("showSearch",true); searchRequested() }
        else if (event.key === Qt.Key_Question || event.key === Qt.Key_H || event.key === Qt.Key_Slash && (event.modifiers & Qt.ShiftModifier)) setFlag("showHelp",!navState.showHelp)
        else if (event.key === Qt.Key_X) expandSelection()
        else if (event.key === Qt.Key_F) setFlag("isolated",!navState.isolated)
        else if (event.key === Qt.Key_I) setFlag("showPicker",!navState.showPicker)
        else if (event.key === Qt.Key_A && !(event.modifiers & Qt.ShiftModifier)) setFlag("showOperator",!navState.showOperator)
        else if (event.key === Qt.Key_W && !(event.modifiers & Qt.ShiftModifier)) togglePinSelection()
        else if (event.key === Qt.Key_D) inspectMore()
        else if (event.key === Qt.Key_P) privacy()
        else if (event.key === Qt.Key_Comma) setFlag("showSettings",!navState.showSettings)
        else if (event.key === Qt.Key_T && navState.instrument === "machine") setFlag("trend",!navState.trend)
        else if (event.key === Qt.Key_L && navState.instrument === "connection" && configuration) configuration.setValue("listeners",!effectiveSettings.listeners)
        else if (event.key === Qt.Key_O && navState.instrument === "connection" && configuration) configuration.setValue("loopback",!effectiveSettings.loopback)
        else if (event.key === Qt.Key_V || event.key === Qt.Key_E || event.key === Qt.Key_N || event.key === Qt.Key_B) {
            var controls=Lenses.controls(navState.instrument,navState,effectiveSettings)
            var index=navState.instrument==="connection" ? (event.key===Qt.Key_V?0:event.key===Qt.Key_N?1:event.key===Qt.Key_B?2:-1) : (navState.instrument==="processes"?event.key===Qt.Key_E:event.key===Qt.Key_V)?0:-1
            if(index>=0 && controls[index]) cycle(controls[index].key,controls[index].values)
            else return
        }
        else return
        event.accepted = true
    }
    Timer {
        id: freezeTimeout
        interval: 5000
        onTriggered: {
            root.freezePending = false
            root.freezeRequestId = -1
            if (root.telemetry) root.telemetry.freeze(false)
            root.setFlag("frozen",false)
            root.displayFrame = root.liveFrame
            root.setFlag("notice","Snapshot request timed out; resumed live state.")
        }
    }
    onNavStateChanged: syncTelemetryScope()
    onTelemetryChanged: syncTelemetryScope()
    onViewChanged: resolveTimer.restart()
    Timer {
        id: resolveTimer
        interval: 0
        onTriggered: {
            if (!root.navState.selectedKey && root.navState.context) {
                var context = root.navState.context || {}, net = root.displayFrame.network || {}
                var pendingProcessScope = root.navState.instrument === "connection" && context.processKey && context.groupKey &&
                    Array.isArray(net.instanceGroups) && net.instanceGroups.indexOf(context.groupKey) < 0
                if (pendingProcessScope) return
                var resolved = Navigation.resolveContext(root.navState,root.view.allNodes)
                if (resolved.selectedKey !== root.navState.selectedKey || resolved.notice !== root.navState.notice) root.navState = resolved
            }
        }
    }
    Connections {
        target: root.telemetry
        function onReceived(frame) {
            root.operatorSession = Operator.ingest(root.operatorSession,frame)
            root.liveFrame = frame
            if (!root.navState.frozen) {
                root.displayFrame = frame
                if (root.navState.showAllDetails && root.selected && root.selected.kind!=="subsystem") root.telemetry.inspect(root.selected.key,(root.detailFrame||{}).offset||0,false)
            }
        }
        function onDetailReceived(frame) { if (root.selected && frame.key === root.selected.key) root.detailFrame = frame }
        function onScopeReceived(frame) {
            if (root.navState.frozen && frame.frozen === true) { root.displayFrame = frame.snapshot; root.detailFrame = null }
        }
        function onFreezeReceived(frame) {
            if (!root.freezePending || frame.requestId !== root.freezeRequestId) return
            freezeTimeout.stop()
            root.freezeRequestId = -1
            root.freezePending = false
            root.setFlag("frozen",frame.frozen)
            root.displayFrame = frame.frozen ? frame.snapshot : root.liveFrame
            if (frame.frozen) root.frozenSession = Operator.ingest(root.operatorSession,frame.snapshot)
            root.detailFrame = null
        }
        function onBackendErrorChanged() { if (root.telemetry.backendError && root.freezePending) { root.freezePending = false; root.freezeRequestId = -1; freezeTimeout.stop(); root.setFlag("notice","Snapshot request failed; retry after the helper recovers.") } }
    }
}
