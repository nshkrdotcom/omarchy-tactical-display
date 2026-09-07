pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import Quickshell
import qs.Commons
import "../model/Inspection.js" as Inspection

Item {
    id: root
    required property var controller
    required property var theme
    readonly property var selected: controller.selected
    readonly property var rows: Inspection.fields(selected,controller.currentDetail,controller.effectiveSettings.privacy,controller.displayFrame)
    readonly property var related: Inspection.related(controller.view,selected)
    readonly property var sockets: Inspection.socketRows((controller.currentDetail||{}).sockets || (controller.currentDetail||{}).socketPreview,controller.effectiveSettings.privacy)
    readonly property bool audioNode: selected && ["stream","sink","source","audio-node"].indexOf(selected.kind) >= 0
    readonly property string selectedIdentity: selected ? selected.key : ""
    property string copiedMessage: ""
    property int relatedLimit: 12
    signal nativePanelRequested(string id)
    Rectangle { anchors.fill: parent; color: root.theme.colors.panel; opacity: 0.97; radius: Style.cornerRadius }
    Rectangle { width: Style.spacing.hairline; height: parent.height; color: root.theme.colors.line }
    ScrollView {
        id: scroll
        anchors.fill: parent
        anchors.margins: Style.spacing.huge
        clip: true
        contentWidth: availableWidth
        ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
        Column {
            width: scroll.availableWidth
            spacing: Style.spacing.xxl
            Text {
                width: parent.width
                text: root.selected ? root.selected.name : "Inspect an entity"
                textFormat: Text.PlainText
                wrapMode: Text.WrapAnywhere
                color: root.theme.colors.foreground
                font.family: root.theme.fontFamily
                font.pixelSize: root.theme.bodySize + Style.spacing.xs
                font.weight: Font.DemiBold
            }
            Text {
                width: parent.width
                text: root.selected ? root.selected.kind + (root.controller.view.selection ? " / selected" : " / ended or outside current lens") : ""
                textFormat: Text.PlainText
                wrapMode: Text.Wrap
                color: root.controller.view.selection ? root.theme.colors.accent : root.theme.colors.warning
                font.family: root.theme.fontFamily
                font.pixelSize: root.theme.smallSize
            }
            Flow {
                width: parent.width; spacing: Style.spacing.sm
                InstrumentButton { visible: root.selected && root.selected.kind==="application"; text: "X Expand / collapse"; paletteColors: root.theme.colors; fontFamily: root.theme.fontFamily; textSize: root.theme.smallSize; onClicked: root.controller.expandSelection() }
                InstrumentButton { text: "Focus"; paletteColors: root.theme.colors; fontFamily: root.theme.fontFamily; textSize: root.theme.smallSize; onClicked: root.controller.focusSelection() }
                InstrumentButton { text: root.controller.selectedPinned ? "W Unpin" : "W Pin"; chosen: root.controller.selectedPinned; paletteColors: root.theme.colors; fontFamily: root.theme.fontFamily; textSize: root.theme.smallSize; onClicked: root.controller.togglePinSelection() }
                InstrumentButton { text: root.controller.navState.isolated ? "Context" : "Isolate"; chosen: root.controller.navState.isolated; paletteColors: root.theme.colors; fontFamily: root.theme.fontFamily; textSize: root.theme.smallSize; onClicked: root.controller.setFlag("isolated",!root.controller.navState.isolated) }
                InstrumentButton { text: "Copy"; paletteColors: root.theme.colors; fontFamily: root.theme.fontFamily; textSize: root.theme.smallSize; onClicked: { Quickshell.clipboardText = Inspection.clipboard(root.selected,root.controller.currentDetail,root.controller.effectiveSettings.privacy,root.controller.displayFrame); root.copiedMessage = root.controller.effectiveSettings.privacy ? "Redacted details copied" : "Details copied to the desktop clipboard" } }
                InstrumentButton { text: root.controller.navState.showAllDetails ? "Compact" : "Details"; chosen: root.controller.navState.showAllDetails; paletteColors: root.theme.colors; fontFamily: root.theme.fontFamily; textSize: root.theme.smallSize; onClicked: root.controller.inspectMore() }
            }
            Text { width: parent.width; visible: root.copiedMessage.length > 0; text: root.copiedMessage; textFormat: Text.PlainText; wrapMode: Text.Wrap; color: root.theme.colors.subdued; font.family: root.theme.fontFamily; font.pixelSize: root.theme.smallSize }
            Repeater {
                model: root.controller.navState.showAllDetails ? root.rows : root.rows.slice(0,10)
                delegate: Column {
                    id: detailRow
                    required property var modelData
                    width: scroll.availableWidth
                    spacing: Style.spacing.xs
                    Text { width: parent.width; text: detailRow.modelData.label; textFormat: Text.PlainText; wrapMode: Text.Wrap; color: root.theme.colors.subdued; font.family: root.theme.fontFamily; font.pixelSize: root.theme.smallSize }
                    Text { width: parent.width; text: detailRow.modelData.value; textFormat: Text.PlainText; wrapMode: Text.WrapAnywhere; color: root.theme.colors.foreground; font.family: root.theme.fontFamily; font.pixelSize: root.theme.bodySize }
                    Text { width: parent.width; visible: root.controller.navState.showAllDetails; text: detailRow.modelData.classification + " / " + detailRow.modelData.source; textFormat: Text.PlainText; wrapMode: Text.Wrap; color: root.theme.colors.subdued; font.family: root.theme.fontFamily; font.pixelSize: root.theme.smallSize }
                }
            }
            InstrumentButton { visible: !root.controller.navState.showAllDetails && root.rows.length > 10; text: "All " + root.rows.length + " fields + provenance"; paletteColors: root.theme.colors; fontFamily: root.theme.fontFamily; textSize: root.theme.smallSize; onClicked: root.controller.inspectMore() }
            Rectangle { width: parent.width; height: Style.spacing.hairline; color: root.theme.colors.line }
            Text { width: parent.width; text: "Follow context"; textFormat: Text.PlainText; color: root.theme.colors.subdued; font.family: root.theme.fontFamily; font.pixelSize: root.theme.smallSize }
            Flow {
                width: parent.width; spacing: Style.spacing.sm
                InstrumentButton { text: "Processes"; paletteColors: root.theme.colors; fontFamily: root.theme.fontFamily; textSize: root.theme.smallSize; onClicked: root.controller.chooseInstrument("processes") }
                InstrumentButton { text: "Connections"; paletteColors: root.theme.colors; fontFamily: root.theme.fontFamily; textSize: root.theme.smallSize; onClicked: root.controller.chooseInstrument("connection") }
                InstrumentButton { text: "Machine"; paletteColors: root.theme.colors; fontFamily: root.theme.fontFamily; textSize: root.theme.smallSize; onClicked: root.controller.chooseInstrument("machine") }
                InstrumentButton { text: "Storage"; paletteColors: root.theme.colors; fontFamily: root.theme.fontFamily; textSize: root.theme.smallSize; onClicked: root.controller.chooseInstrument("storage") }
                InstrumentButton { text: "Audio"; paletteColors: root.theme.colors; fontFamily: root.theme.fontFamily; textSize: root.theme.smallSize; onClicked: root.controller.chooseInstrument("audio") }
            }
            Text { width: parent.width; visible: root.related.length > 0; text: "Observed relationships / " + root.related.length; textFormat: Text.PlainText; color: root.theme.colors.subdued; font.family: root.theme.fontFamily; font.pixelSize: root.theme.smallSize }
            Repeater {
                model: root.related.slice(0,root.relatedLimit)
                delegate: InstrumentButton {
                    required property var modelData
                    width: scroll.availableWidth
                    text: modelData.name
                    hint: modelData.kind
                    paletteColors: root.theme.colors; fontFamily: root.theme.fontFamily; textSize: root.theme.smallSize
                    onClicked: root.controller.pickKey(modelData.key)
                }
            }
            InstrumentButton { visible: root.related.length > root.relatedLimit; text: "Show more related entities"; paletteColors: root.theme.colors; fontFamily: root.theme.fontFamily; textSize: root.theme.smallSize; onClicked: root.relatedLimit += 24 }
            Text { width: parent.width; visible: root.sockets.length > 0; text: "Kernel socket records"; textFormat: Text.PlainText; color: root.theme.colors.accent; font.family: root.theme.fontFamily; font.pixelSize: root.theme.bodySize }
            Repeater {
                model: root.controller.navState.showAllDetails ? root.sockets : root.sockets.slice(0,2)
                delegate: Column {
                    id: socketRow
                    required property var modelData
                    width: scroll.availableWidth; spacing: Style.spacing.sm
                    Text { width: parent.width; text: socketRow.modelData.title; textFormat: Text.PlainText; wrapMode: Text.WrapAnywhere; color: root.theme.colors.foreground; font.family: root.theme.fontFamily; font.pixelSize: root.theme.smallSize }
                    Text { width: parent.width; text: socketRow.modelData.details; textFormat: Text.PlainText; wrapMode: Text.WrapAnywhere; color: root.theme.colors.subdued; font.family: root.theme.fontFamily; font.pixelSize: root.theme.smallSize }
                    Text { width: parent.width; visible: root.controller.navState.showAllDetails; text: socketRow.modelData.source; textFormat: Text.PlainText; wrapMode: Text.Wrap; color: root.theme.colors.subdued; font.family: root.theme.fontFamily; font.pixelSize: root.theme.smallSize }
                    Rectangle { width: parent.width; height: Style.spacing.hairline; color: root.theme.colors.line; opacity: 0.5 }
                }
            }
            Flow {
                width: parent.width; spacing: Style.spacing.sm
                visible: root.controller.navState.showAllDetails && root.controller.detailFrame && root.controller.detailFrame.total > 24
                InstrumentButton { text: "Previous sockets"; enabled: (root.controller.detailFrame||{}).offset > 0; paletteColors: root.theme.colors; fontFamily: root.theme.fontFamily; textSize: root.theme.smallSize; onClicked: root.controller.detailPage(Math.max(0,root.controller.detailFrame.offset-24)) }
                InstrumentButton { text: "Next sockets"; enabled: root.controller.detailFrame && root.controller.detailFrame.nextOffset !== null && root.controller.detailFrame.nextOffset !== undefined; paletteColors: root.theme.colors; fontFamily: root.theme.fontFamily; textSize: root.theme.smallSize; onClicked: root.controller.detailPage(root.controller.detailFrame.nextOffset) }
            }
            Flow {
                width: parent.width; spacing: Style.spacing.sm
                visible: root.audioNode && root.controller.effectiveSettings.audioActions
                InstrumentButton { text: "Mute / unmute"; enabled: !root.controller.navState.frozen && (root.controller.currentDetail||{}).mute !== null; paletteColors: root.theme.colors; fontFamily: root.theme.fontFamily; textSize: root.theme.smallSize; onClicked: root.controller.requestAction("mute") }
                InstrumentButton { text: "Make default"; visible: root.selected && ["sink","source"].indexOf(root.selected.kind) >= 0; enabled: !root.controller.navState.frozen; paletteColors: root.theme.colors; fontFamily: root.theme.fontFamily; textSize: root.theme.smallSize; onClicked: root.controller.requestAction("default") }
                InstrumentButton { text: "Undo audio action"; enabled: !root.controller.navState.frozen; paletteColors: root.theme.colors; fontFamily: root.theme.fontFamily; textSize: root.theme.smallSize; onClicked: root.controller.requestAction("undo") }
            }
            InstrumentButton { visible: root.controller.navState.instrument === "audio"; text: "Open Omarchy audio"; paletteColors: root.theme.colors; fontFamily: root.theme.fontFamily; textSize: root.theme.smallSize; onClicked: root.nativePanelRequested("omarchy.audio") }
        }
    }
    onSelectedIdentityChanged: { copiedMessage = ""; relatedLimit = 12 }
}
