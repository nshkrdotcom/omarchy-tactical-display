pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Quickshell
import qs.Commons
import "../model/Operator.js" as Operator

FocusScope {
    id: root
    required property var controller
    required property var theme
    property string section: "attention"
    property string activityInstrument: "all"
    property string activityKind: "all"
    property string copiedMessage: ""
    readonly property var events: Operator.activity(controller.displaySession,{instrument:activityInstrument,kind:activityKind,privacy:controller.effectiveSettings.privacy})
    readonly property var pinRows: Operator.pinRows(controller.pins,controller.displayFrame,controller.effectiveSettings.privacy)
    readonly property var comparisons: Operator.compare(controller.comparisonBaseline,controller.displayFrame,{now:controller.observationNow})
    function reveal(item) {
        var point=item.mapToItem(sheetContent,0,0)
        var flick=scroll.contentItem
        if (point.y<flick.contentY) flick.contentY=Math.max(0,point.y)
        else if (point.y+item.height>flick.contentY+scroll.height) flick.contentY=Math.min(Math.max(0,scroll.contentHeight-scroll.height),point.y+item.height-scroll.height)
    }
    function cycleDomain() {
        var values=["all","connection","processes","machine","storage","audio"]
        activityInstrument=values[(values.indexOf(activityInstrument)+1)%values.length]
    }
    function cycleKind() {
        var values=["all","opened","changed","closed"]
        activityKind=values[(values.indexOf(activityKind)+1)%values.length]
    }
    component Body: Text {
        width: parent.width
        textFormat: Text.PlainText
        wrapMode: Text.Wrap
        color: root.theme.colors.foreground
        font.family: root.theme.fontFamily
        font.pixelSize: root.theme.smallSize
    }
    component Action: InstrumentButton {
        paletteColors: root.theme.colors
        fontFamily: root.theme.fontFamily
        textSize: root.theme.smallSize
    }
    Keys.onPressed: event => {
        if (!(event.modifiers & (Qt.ControlModifier | Qt.AltModifier | Qt.MetaModifier)) && event.key === Qt.Key_Backspace) {
            root.controller.setFlag("showOperator",false)
            event.accepted=true
        }
    }
    Rectangle { anchors.fill: parent; color: root.theme.colors.background; opacity: 0.86 }
    MouseArea { anchors.fill: parent; onClicked: root.controller.setFlag("showOperator",false) }
    Rectangle {
        anchors.fill: parent
        anchors.margins: Style.spacing.xxl
        color: root.theme.colors.panel
        border.color: root.theme.colors.line
        radius: Style.cornerRadius
        MouseArea { anchors.fill: parent; onClicked: mouse => mouse.accepted=true }
        ColumnLayout {
            anchors.fill: parent
            anchors.margins: Style.spacing.xxl
            spacing: Style.spacing.xl
            RowLayout {
                Layout.fillWidth: true
                Text {
                    Layout.fillWidth: true
                    text: "Operator briefing"
                    textFormat: Text.PlainText
                    color: root.theme.colors.foreground
                    font.family: root.theme.fontFamily
                    font.pixelSize: root.theme.bodySize
                    font.weight: Font.DemiBold
                }
                Action {
                    text: root.controller.navState.frozen ? "Resume" : "Freeze"
                    enabled: !root.controller.freezePending && root.controller.displayFrame.schemaVersion === 3
                    chosen: root.controller.navState.frozen
                    hint: "Hold the displayed findings and activity steady; collection continues"
                    onClicked: root.controller.toggleFreeze()
                }
                Action {
                    text: "Copy report"
                    enabled: root.controller.displayFrame.schemaVersion === 3
                    onClicked: {
                        Quickshell.clipboardText=root.controller.operatorReport()
                        root.copiedMessage=root.controller.effectiveSettings.privacy ? "Redacted operator report copied" : "Operator report copied to clipboard"
                    }
                }
                Action { id: backButton; text: "Back"; hint: "Backspace / return to instrument. Esc closes Tactical Display."; bordered: true; onClicked: root.controller.setFlag("showOperator",false) }
            }
            Text {
                Layout.fillWidth: true
                text: (root.controller.navState.frozen ? "FROZEN" : "LIVE")+" · "+(root.controller.effectiveSettings.privacy ? "PRIVATE · " : "")+"Session only · close clears activity, pins and baseline"
                textFormat: Text.PlainText; wrapMode: Text.Wrap
                color: root.theme.colors.subdued; font.family: root.theme.fontFamily; font.pixelSize: root.theme.smallSize
            }
            Flow {
                Layout.fillWidth: true
                spacing: Style.spacing.sm
                Repeater {
                    model: [{id:"attention",name:"Attention",count:root.controller.attention.length},{id:"activity",name:"Activity",count:root.controller.displaySession.events.length},{id:"pins",name:"Pins",count:root.controller.pins.length},{id:"baseline",name:"Baseline",count:root.controller.comparisonBaseline ? 1 : 0}]
                    delegate: Action {
                        required property var modelData
                        text: modelData.name+" · "+modelData.count
                        chosen: root.section === modelData.id
                        onClicked: { root.section=modelData.id; scroll.contentItem.contentY=0 }
                    }
                }
            }
            Text {
                Layout.fillWidth: true; visible: !!root.copiedMessage
                text: root.copiedMessage; textFormat: Text.PlainText
                color: root.theme.colors.accent; font.family: root.theme.fontFamily; font.pixelSize: root.theme.smallSize
            }
            Rectangle { Layout.fillWidth: true; Layout.preferredHeight: Style.spacing.hairline; color: root.theme.colors.line }
            ScrollView {
                id: scroll
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                contentWidth: availableWidth
                ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
                Column {
                    id: sheetContent
                    width: scroll.availableWidth
                    spacing: Style.spacing.xxl
                    Column {
                        width: parent.width; spacing: Style.spacing.xxl; visible: root.section === "attention"
                        Body { text: "Prioritized observations with evidence and a next inspection step. Thresholds are triage heuristics; contributing activity does not establish a cause."; color: root.theme.colors.subdued }
                        Body {
                            visible: !root.controller.attention.length
                            text: root.controller.displayFrame.schemaVersion ? "No attention thresholds crossed in available observations. Select Machine to collect pressure and capacity. Uncollected resources are not a health guarantee." : "Awaiting local observations. The briefing appears as providers report."
                        }
                        Flow {
                            width: parent.width; spacing: Style.spacing.sm
                            Action { text: "Inspect machine"; onClicked: root.controller.jumpOperator({instrument:"machine",entityKey:""}); onActiveFocusChanged: if (activeFocus) root.reveal(this) }
                            Action { text: "Data sources"; onClicked: root.controller.jumpOperator({instrument:"capabilities"}); onActiveFocusChanged: if (activeFocus) root.reveal(this) }
                        }
                        Repeater {
                            model: root.section === "attention" ? root.controller.attention : []
                            delegate: Column {
                                id: finding
                                required property var modelData
                                width: sheetContent.width; spacing: Style.spacing.md
                                Body { text: finding.modelData.severity.toUpperCase()+" · "+finding.modelData.title; font.weight: Font.DemiBold; font.pixelSize: root.theme.bodySize; color: finding.modelData.severity === "high" ? root.theme.colors.critical : finding.modelData.severity === "watch" ? root.theme.colors.warning : root.theme.colors.foreground }
                                Body { text: finding.modelData.evidence }
                                Body { text: finding.modelData.next; color: root.theme.colors.subdued }
                                Body { text: "Source: "+finding.modelData.source; color: root.theme.colors.subdued }
                                Action { text: finding.modelData.instrument === "capabilities" ? "Inspect data sources" : "Inspect evidence"; hint: finding.modelData.title; onClicked: root.controller.jumpOperator(finding.modelData); onActiveFocusChanged: if (activeFocus) root.reveal(this) }
                                Rectangle { width: parent.width; height: Style.spacing.hairline; color: root.theme.colors.line }
                            }
                        }
                    }
                    Column {
                        width: parent.width; spacing: Style.spacing.xl; visible: root.section === "activity"
                        Body { text: "Observed lifecycle changes · up to 120 records / five minutes. Only active providers contribute; incomplete scans do not prove an entity ended."; color: root.theme.colors.subdued }
                        Flow {
                            width: parent.width; spacing: Style.spacing.sm
                            Action { text: "Instrument: "+root.activityInstrument; onClicked: root.cycleDomain() }
                            Action { text: "Event: "+root.activityKind; onClicked: root.cycleKind() }
                        }
                        Body { visible: !root.events.length; text: "No observed changes match these filters. Activity begins after the first observation." }
                        Repeater {
                            model: root.section === "activity" ? root.events : []
                            delegate: Action {
                                required property var modelData
                                width: sheetContent.width
                                text: modelData.age+" · "+modelData.kind.toUpperCase()+" · "+modelData.name
                                hint: modelData.instrument+" / inspect exact entity; departed entities may no longer be available"
                                onClicked: root.controller.jumpOperator(modelData)
                                onActiveFocusChanged: if (activeFocus) root.reveal(this)
                            }
                        }
                    }
                    Column {
                        width: parent.width; spacing: Style.spacing.xl; visible: root.section === "pins"
                        Body { text: "Keep up to eight entities together while investigating. Select an entity and press W to pin it. “Not observed” can mean an inactive provider or collection limit."; color: root.theme.colors.subdued }
                        Action { text: "Clear pins"; visible: root.pinRows.length>0; onClicked: root.controller.pins=[] }
                        Body { visible: !root.pinRows.length; text: "No entities pinned. Return to an instrument, select an entity, and use Pin or W." }
                        Repeater {
                            model: root.section === "pins" ? root.pinRows : []
                            delegate: Column {
                                id: pin
                                required property var modelData
                                width: sheetContent.width; spacing: Style.spacing.sm
                                Body { text: pin.modelData.name+" · "+pin.modelData.status; font.pixelSize: root.theme.bodySize }
                                Flow {
                                    width: parent.width; spacing: Style.spacing.sm
                                    Action { text: "Inspect in "+pin.modelData.instrument; onClicked: root.controller.jumpOperator(pin.modelData); onActiveFocusChanged: if (activeFocus) root.reveal(this) }
                                    Action { text: "Unpin"; hint: pin.modelData.name; onClicked: root.controller.removePin(pin.modelData.key); onActiveFocusChanged: if (activeFocus) root.reveal(this) }
                                }
                            }
                        }
                    }
                    Column {
                        width: parent.width; spacing: Style.spacing.xl; visible: root.section === "baseline"
                        Body { text: root.controller.comparisonBaseline ? "Compared with observation at "+new Date(root.controller.comparisonBaseline.wallTime*1000).toLocaleTimeString()+" · "+Math.max(0,(root.controller.displayFrame.monotonic||0)-root.controller.comparisonBaseline.at).toFixed(0)+"s earlier" : "Capture a baseline before changing a workload, then compare measured resource changes. For CPU/PSI, pp means percentage points."; color: root.theme.colors.subdued }
                        Flow {
                            width: parent.width; spacing: Style.spacing.sm
                            Action { text: root.controller.comparisonBaseline ? "Replace baseline" : "Capture baseline"; enabled: root.controller.displayFrame.schemaVersion === 3; onClicked: root.controller.captureBaseline() }
                            Action { text: "Clear baseline"; visible: !!root.controller.comparisonBaseline; onClicked: root.controller.comparisonBaseline=null }
                        }
                        Body { visible: !!root.controller.comparisonBaseline; text: "Before → current · change. Host network rates can include virtual-interface double counting; storage rates are measured at the device level."; color: root.theme.colors.subdued }
                        Repeater {
                            model: root.section === "baseline" ? root.comparisons : []
                            delegate: Column {
                                id: comparison
                                required property var modelData
                                width: sheetContent.width; spacing: Style.spacing.sm
                                Body { text: comparison.modelData.label; font.weight: Font.DemiBold }
                                Body { text: comparison.modelData.before+" → "+comparison.modelData.current+" · "+comparison.modelData.change+" · "+comparison.modelData.quality }
                            }
                        }
                    }
                }
            }
        }
    }
    Component.onCompleted: Qt.callLater(function() { backButton.forceActiveFocus() })
}
