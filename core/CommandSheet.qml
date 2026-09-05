pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../model/InstrumentModel.js" as Instruments
import "../model/Lenses.js" as Lenses

FocusScope {
    id: root
    required property var controller
    required property var theme
    readonly property string kind: controller.pendingAction ? "confirm" : controller.navState.showSettings ? "settings" : controller.navState.showCapabilities ? "capabilities" : controller.navState.showHelp ? "help" : "picker"
    readonly property string heading: kind === "confirm" ? "Confirm audio change" : kind === "settings" ? "Instrument settings" : kind === "capabilities" ? "Data sources and freshness" : kind === "help" ? controller.view.info.name + " / legend" : controller.navState.showIntro ? "See how your machine behaves" : "Choose an instrument"
    readonly property var capabilities: Object.keys(controller.displayFrame.capabilities||{}).map(key => controller.displayFrame.capabilities[key])
    property int pickerIndex: 0
    function currentInstrumentIndex() {
        for (var i=0;i<Instruments.catalog.length;i++)
            if (Instruments.catalog[i].id === controller.navState.instrument) return i
        return 0
    }
    function focusPicker(index) {
        if (Instruments.catalog.length === 0) return
        root.pickerIndex = Math.max(0,Math.min(Instruments.catalog.length-1,index))
        var row = instrumentRepeater.itemAt(root.pickerIndex)
        if (row) {
            row.forceActiveFocus()
            root.reveal(row)
        }
    }
    function reveal(item) {
        var point=item.mapToItem(sheetContent,0,0)
        if (point.y<scroll.contentY) scroll.contentY=Math.max(0,point.y)
        else if (point.y+item.height>scroll.contentY+scroll.height) scroll.contentY=Math.min(Math.max(0,scroll.contentHeight-scroll.height),point.y+item.height-scroll.height)
    }
    function capabilityLabel(instrument) {
        var ids=instrument.providers, caps=root.controller.displayFrame.capabilities||{}, found=false, partial=false
        for(var i=0;i<ids.length;i++){var c=caps[ids[i]];if(c&&c.status!=="inactive"){found=true;if(c.status!=="available")partial=true;}}
        return !found?"Collected on selection":partial?"Partial capability / select to inspect":"Available in this session"
    }
    focus: visible
    Keys.priority: Keys.BeforeItem
    Keys.onPressed: event => {
        if (root.kind !== "picker" || event.modifiers & (Qt.ControlModifier | Qt.AltModifier | Qt.MetaModifier)) return
        if (event.key === Qt.Key_Down || event.key === Qt.Key_Right) root.focusPicker(root.pickerIndex + 1)
        else if (event.key === Qt.Key_Up || event.key === Qt.Key_Left) root.focusPicker(root.pickerIndex - 1)
        else if (event.key === Qt.Key_Home) root.focusPicker(0)
        else if (event.key === Qt.Key_End) root.focusPicker(Instruments.catalog.length - 1)
        else if (event.key === Qt.Key_Return || event.key === Qt.Key_Enter) {
            var instrument = Instruments.catalog[root.pickerIndex]
            if (instrument) root.controller.chooseInstrument(instrument.id)
        } else if (event.key === Qt.Key_Backspace) root.controller.back()
        else return
        event.accepted = true
    }
    onVisibleChanged: {
        if (!visible) return
        forceActiveFocus()
        if (root.kind === "picker") Qt.callLater(function() { root.focusPicker(root.currentInstrumentIndex()) })
    }
    onKindChanged: {
        if (visible && root.kind === "picker") Qt.callLater(function() { root.focusPicker(root.currentInstrumentIndex()) })
    }
    Rectangle { anchors.fill: parent; color: root.theme.colors.background; opacity: 0.78 }
    MouseArea { anchors.fill: parent; onClicked: root.controller.back() }
    Rectangle {
        id: panel
        anchors.centerIn: parent
        width: Math.min(780,Math.max(260,root.width-40))
        height: Math.min(Math.max(160,root.height-40),sheetContent.implicitHeight+88)
        radius: 5
        color: root.theme.colors.panel
        border.color: root.theme.colors.line
        border.width: 1
        MouseArea { anchors.fill: parent; onClicked: mouse => mouse.accepted = true }
        RowLayout {
            id: sheetHeader
            anchors.top: parent.top; anchors.left: parent.left; anchors.right: parent.right; anchors.margins: 20
            Text { Layout.fillWidth: true; text: root.heading; textFormat: Text.PlainText; wrapMode: Text.Wrap; color: root.theme.colors.foreground; font.family: root.theme.fontFamily; font.pixelSize: root.theme.bodySize+4; font.weight: Font.DemiBold }
            InstrumentButton { text: "Back"; hint: "Backspace / Return to instrument"; paletteColors: root.theme.colors; fontFamily: root.theme.fontFamily; textSize: root.theme.smallSize; onClicked: root.controller.back(); onActiveFocusChanged: if (activeFocus) root.reveal(this) }
        }
        Flickable {
            id: scroll
            anchors.fill: parent; anchors.topMargin: sheetHeader.height+30; anchors.bottomMargin: 20; anchors.leftMargin: 24; anchors.rightMargin: 24
            clip: true
            boundsBehavior: Flickable.StopAtBounds
            contentWidth: width
            contentHeight: sheetContent.implicitHeight
            readonly property real availableWidth: width
            ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }
            ScrollBar.horizontal: ScrollBar { policy: ScrollBar.AlwaysOff }
            Column {
                id: sheetContent
                width: scroll.availableWidth
                spacing: 16
                Column {
                    width: parent.width; spacing: 14; visible: root.kind === "picker"
                    Text { width: parent.width; text: "Tactical Display is local, live instrumentation over your desktop. Press 1-5 to switch, / to search, Space to freeze, ? for the legend, and Escape to close immediately."; textFormat: Text.PlainText; wrapMode: Text.Wrap; color: root.theme.colors.subdued; font.family: root.theme.fontFamily; font.pixelSize: root.theme.bodySize }
                    Repeater {
                        id: instrumentRepeater
                        model: Instruments.catalog
                        delegate: FocusScope {
                            id: instrumentRow
                            required property var modelData
                            required property int index
                            width: scroll.availableWidth
                            implicitHeight: instrumentColumn.implicitHeight
                            activeFocusOnTab: true
                            Column {
                                id: instrumentColumn
                                width: parent.width; spacing: 4
                                InstrumentButton { id: instrumentButton; focus: true; width: parent.width; text: instrumentRow.modelData.key+"  "+instrumentRow.modelData.name; chosen: root.controller.navState.instrument===instrumentRow.modelData.id; paletteColors: root.theme.colors; fontFamily: root.theme.fontFamily; textSize: root.theme.bodySize; onClicked: root.controller.chooseInstrument(instrumentRow.modelData.id); onActiveFocusChanged: if (activeFocus) { root.pickerIndex=instrumentRow.index; root.reveal(instrumentRow) } }
                                Text { width: parent.width; text: instrumentRow.modelData.purpose+"\n"+root.capabilityLabel(instrumentRow.modelData); textFormat: Text.PlainText; wrapMode: Text.Wrap; color: root.theme.colors.subdued; font.family: root.theme.fontFamily; font.pixelSize: root.theme.smallSize }
                            }
                        }
                    }
                }
                Column {
                    width: parent.width; spacing: 15; visible: root.kind === "help"
                    Repeater {
                        model: root.controller.view.info.legend
                        delegate: Text { required property string modelData; width: scroll.availableWidth; text: modelData; textFormat: Text.PlainText; wrapMode: Text.Wrap; color: root.theme.colors.foreground; font.family: root.theme.fontFamily; font.pixelSize: root.theme.bodySize }
                    }
                    Rectangle { width: parent.width; height: 1; color: root.theme.colors.line }
                    Text { width: parent.width; text: "1-5  switch instrument\nTab / arrows  traverse entities    F6  navigate controls\nEnter  focus    X  expand / collapse    F  isolate\nEscape  close immediately    Backspace  back    R  reset\n/  search    Space  freeze / resume    D  exact details\nV  origin / storage / audio lens    E  process emphasis\nN  TCP / UDP    B  connection state    L  listeners    O  loopback\nT  machine trend    C  copy selected details\nP  privacy    I  instrument picker    ,  settings"; textFormat: Text.PlainText; wrapMode: Text.Wrap; color: root.theme.colors.subdued; font.family: root.theme.fontFamily; font.pixelSize: root.theme.smallSize }
                    Text { width: parent.width; text: "Freeze keeps an exact snapshot for inspection while collection continues. Switching instrument resumes live collection. Privacy hides labels and the desktop; it is not a security boundary. The helper never reads full process arguments."; textFormat: Text.PlainText; wrapMode: Text.Wrap; color: root.theme.colors.subdued; font.family: root.theme.fontFamily; font.pixelSize: root.theme.smallSize }
                    InstrumentButton { text: "Show introduction / picker"; paletteColors: root.theme.colors; fontFamily: root.theme.fontFamily; textSize: root.theme.smallSize; onClicked: { root.controller.setFlag("showHelp",false); root.controller.setFlag("showPicker",true) } }
                }
                Column {
                    width: parent.width; spacing: 18; visible: root.kind === "settings"
                    Text { width: parent.width; visible: !!root.controller.configuration && (!!root.controller.configuration.persistenceMessage || root.controller.configuration.warnings.length > 0); text: root.controller.configuration ? root.controller.configuration.persistenceMessage+" "+root.controller.configuration.warnings.join(" ") : ""; textFormat: Text.PlainText; wrapMode: Text.Wrap; color: root.theme.colors.warning; font.family: root.theme.fontFamily; font.pixelSize: root.theme.smallSize }
                    Repeater {
                        model: Lenses.settingsRows()
                        delegate: Column {
                            id: preference
                            required property var modelData
                            width: scroll.availableWidth; spacing: 5
                            Text { width: parent.width; text: preference.modelData.label; textFormat: Text.PlainText; color: root.theme.colors.foreground; font.family: root.theme.fontFamily; font.pixelSize: root.theme.bodySize }
                            Flow {
                                width: parent.width; spacing: 5
                                Repeater {
                                    model: preference.modelData.choices
                                    delegate: InstrumentButton {
                                        required property var modelData
                                        text: typeof modelData === "boolean" ? modelData ? "On" : "Off" : String(modelData)
                                        chosen: root.controller.effectiveSettings[preference.modelData.key] === modelData
                                        enabled: root.controller.configuration && !root.controller.configuration.readOnly
                                        paletteColors: root.theme.colors; fontFamily: root.theme.fontFamily; textSize: root.theme.smallSize
                                        onClicked: { if (preference.modelData.key === "privacy") root.controller.setFlag("privacyOverride",null); root.controller.configuration.setValue(preference.modelData.key,modelData) }
                                        onActiveFocusChanged: if (activeFocus) root.reveal(this)
                                    }
                                }
                            }
                            Text { width: parent.width; text: preference.modelData.hint; textFormat: Text.PlainText; wrapMode: Text.Wrap; color: root.theme.colors.subdued; font.family: root.theme.fontFamily; font.pixelSize: root.theme.smallSize }
                        }
                    }
                    Text { width: parent.width; text: "Aliases, an optional local MMDB, and the race-safe hold shortcut are documented in docs/HANDOFF.md. No binding or bar-layout change occurs automatically."; textFormat: Text.PlainText; wrapMode: Text.Wrap; color: root.theme.colors.subdued; font.family: root.theme.fontFamily; font.pixelSize: root.theme.smallSize }
                }
                Column {
                    width: parent.width; spacing: 16; visible: root.kind === "capabilities"
                    Text { width: parent.width; text: root.controller.telemetry ? (root.controller.effectiveSettings.privacy && root.controller.telemetry.backendError ? "Backend issue; identity-bearing messages hidden by privacy." : root.controller.telemetry.backendError) || "The renderer receives versioned local snapshots. Missing values are not substituted with zero." : ""; textFormat: Text.PlainText; wrapMode: Text.Wrap; color: root.theme.colors.subdued; font.family: root.theme.fontFamily; font.pixelSize: root.theme.bodySize }
                    Repeater {
                        model: root.capabilities
                        delegate: Column {
                            id: capability
                            required property var modelData
                            width: scroll.availableWidth; spacing: 5
                            Text { width: parent.width; text: capability.modelData.provider+" / "+capability.modelData.status; textFormat: Text.PlainText; wrapMode: Text.Wrap; color: capability.modelData.status==="available" ? root.theme.colors.accent : root.theme.colors.warning; font.family: root.theme.fontFamily; font.pixelSize: root.theme.bodySize }
                            Text { width: parent.width; text: root.controller.effectiveSettings.privacy ? "Provider "+capability.modelData.provider+" / "+(capability.modelData.errorKind||"No reported error")+". Identity-bearing messages hidden." : capability.modelData.source+"\n"+(capability.modelData.reason||"")+"\n"+(capability.modelData.suggestion||""); textFormat: Text.PlainText; wrapMode: Text.WrapAnywhere; color: root.theme.colors.foreground; font.family: root.theme.fontFamily; font.pixelSize: root.theme.smallSize }
                            Text { width: parent.width; text: "Cadence "+capability.modelData.intervalSeconds+" s / sample "+capability.modelData.durationMs+" ms / age "+(typeof capability.modelData.sampledAt==="number" && root.controller.displayFrame.monotonic ? Math.max(0,root.controller.displayFrame.monotonic-capability.modelData.sampledAt).toFixed(1)+" s" : "not sampled"); textFormat: Text.PlainText; wrapMode: Text.Wrap; color: root.theme.colors.subdued; font.family: root.theme.fontFamily; font.pixelSize: root.theme.smallSize }
                        }
                    }
                    Text { width: parent.width; text: "Bounds and omissions: "+JSON.stringify(root.controller.displayFrame.limits||{}); textFormat: Text.PlainText; wrapMode: Text.WrapAnywhere; color: root.theme.colors.subdued; font.family: root.theme.fontFamily; font.pixelSize: root.theme.smallSize }
                    InstrumentButton { text: "Retry helper"; paletteColors: root.theme.colors; fontFamily: root.theme.fontFamily; textSize: root.theme.smallSize; onClicked: if (root.controller.telemetry) root.controller.telemetry.retry() }
                }
                Column {
                    width: parent.width; spacing: 16; visible: root.kind === "confirm"
                    Text { width: parent.width; text: root.controller.pendingAction ? "Apply "+root.controller.pendingAction.action+" to "+(root.controller.effectiveSettings.privacy ? "selected audio entity" : root.controller.pendingAction.name)+"?\nThe current PipeWire object serial is checked again before wpctl. This changes real audio state. A previous successful change can be undone from the detail rail." : ""; textFormat: Text.PlainText; wrapMode: Text.Wrap; color: root.theme.colors.foreground; font.family: root.theme.fontFamily; font.pixelSize: root.theme.bodySize }
                    Flow {
                        width: parent.width; spacing: 8
                        InstrumentButton { text: "Cancel"; paletteColors: root.theme.colors; fontFamily: root.theme.fontFamily; textSize: root.theme.bodySize; onClicked: root.controller.pendingAction = null }
                        InstrumentButton { text: "Confirm change"; chosen: true; paletteColors: root.theme.colors; fontFamily: root.theme.fontFamily; textSize: root.theme.bodySize; onClicked: root.controller.confirmAction() }
                    }
                }
            }
        }
    }
}
