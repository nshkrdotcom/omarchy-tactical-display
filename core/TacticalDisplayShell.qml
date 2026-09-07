pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Quickshell
import qs.Commons
import "../visual" as Visual
import "../model/InstrumentModel.js" as Instruments
import "../model/Lenses.js" as Lenses
import "../model/Inspection.js" as Inspection

FocusScope {
    id: root
    required property var controller
    required property var theme
    property bool active: true
    readonly property var statistics: ({nodes:field.scene.nodes.length,edges:field.scene.edges.length,
        labels:field.scene.labels.length,omittedNodes:field.hiddenCount,
        omittedEdges:field.scene.omittedEdges || 0,layoutDurationMs:field.layoutDurationMs})
    readonly property bool compact: height < Style.space(680)
    readonly property bool compactWidth: width < Style.space(1050)
    // The clicked panel is the presentation reference for every host. Outer
    // borders/padding belong to KeyboardPanel or the fullscreen BorderSurface.
    readonly property int contentSpacing: Style.spacing.xxl
    readonly property bool sheetVisible: !!controller.pendingAction || controller.navState.showPicker || controller.navState.showIntro || controller.navState.showHelp || controller.navState.showSettings || controller.navState.showCapabilities || controller.navState.showOperator
    readonly property bool pickerSheetVisible:
        !controller.pendingAction &&
        !controller.navState.showOperator &&
        !controller.navState.showSettings &&
        !controller.navState.showCapabilities &&
        !controller.navState.showHelp &&
        (controller.navState.showPicker || controller.navState.showIntro)
    readonly property var lenses: Lenses.controls(controller.navState.instrument,controller.navState,controller.effectiveSettings)
    readonly property var hoverEntity: controller.view.allNodes.filter(n => n.key === controller.hoveredKey)[0] || null
    readonly property string headerState: controller.navState.frozen ? "FROZEN" : controller.telemetry ? controller.telemetry.statusText : "ACQUIRING"
    readonly property string headerContext: {
        var parts = [controller.view.info.name]
        if (controller.view.degraded.length) parts.push("PARTIAL")
        if (controller.effectiveSettings.privacy) parts.push("PRIVACY")
        if (controller.navState.frozen && controller.displayFrame.wallTime)
            parts.push(new Date(controller.displayFrame.wallTime * 1000).toLocaleTimeString())
        return parts.join(" · ")
    }
    signal nativePanelRequested(string id)
    property bool controlsFocus: false
    readonly property var focusedItem: Window.activeFocusItem
    focus: true
    Item { id: fieldFocusTarget; width: 0; height: 0; activeFocusOnTab: false }
    function focusField() { controlsFocus=false; fieldFocusTarget.forceActiveFocus() }
    function focusControls() { controlsFocus=true; searchButton.forceActiveFocus() }
    function copySelection() { if (controller.selected) Quickshell.clipboardText=Inspection.clipboard(controller.selected,controller.currentDetail,controller.effectiveSettings.privacy,controller.displayFrame) }

    Keys.priority: Keys.BeforeItem
    Keys.onPressed: event => {
        if (event.key === Qt.Key_F6 && !sheetVisible) {
            if (controlsFocus) focusField()
            else focusControls()
            event.accepted = true
            return
        }

        // Modal instrument selection belongs to the Tactical surface keyboard
        // router. This path is independent of whichever picker child owns focus.
        if (pickerSheetVisible &&
            !(event.modifiers & (Qt.ControlModifier | Qt.AltModifier | Qt.MetaModifier | Qt.ShiftModifier)) &&
            event.key >= Qt.Key_1 && event.key <= Qt.Key_5) {
            var direct = Instruments.catalog[event.key - Qt.Key_1]
            if (direct) controller.chooseInstrument(direct.id)
            event.accepted = true
            return
        }

        if (!sheetVisible &&
            !searchInput.activeFocus &&
            !controlsFocus &&
            event.key === Qt.Key_C &&
            !(event.modifiers & (Qt.ControlModifier | Qt.AltModifier | Qt.MetaModifier))) {
            copySelection()
            event.accepted = true
            return
        }

        controller.handleKey(
            event,
            searchInput.activeFocus,
            sheetVisible || controlsFocus
        )
    }
    Rectangle {
        anchors.fill: parent
        color: root.theme.colors.background
    }
    ColumnLayout {
        id: content
        anchors.fill: parent
        spacing: root.contentSpacing
        enabled: !root.sheetVisible
        RowLayout {
            id: headerBar
            Layout.fillWidth: true
            spacing: Style.spacing.huge

            ColumnLayout {
                id: identityBlock
                Layout.alignment: Qt.AlignVCenter
                spacing: Style.spacing.xxs

                Text {
                    text: "TACTICAL DISPLAY"
                    textFormat: Text.PlainText
                    color: root.theme.colors.foreground
                    font.family: root.theme.fontFamily
                    font.pixelSize: Style.font.subtitle
                    font.weight: Font.DemiBold
                    font.letterSpacing: 0.4
                }

                RowLayout {
                    spacing: Style.spacing.sm

                    Text {
                        id: headerStatus
                        objectName: "providerStatus"
                        activeFocusOnTab: true
                        Layout.alignment: Qt.AlignBaseline
                        text: root.headerState
                        textFormat: Text.PlainText
                        color: root.controller.view.degraded.length || root.controller.navState.frozen ? root.theme.colors.warning : root.theme.colors.accent
                        font.family: root.theme.fontFamily
                        font.pixelSize: root.theme.smallSize
                        font.weight: Font.DemiBold
                        font.underline: statusHitArea.containsMouse || activeFocus
                        Accessible.role: Accessible.Button
                        Accessible.name: text
                        Accessible.description: "Inspect provider availability, age, errors and provenance"
                        Accessible.onPressAction: root.controller.setFlag("showCapabilities",true)
                        Keys.onPressed: event => {
                            if (!(event.modifiers & (Qt.ControlModifier | Qt.AltModifier | Qt.MetaModifier | Qt.ShiftModifier)) &&
                                (event.key === Qt.Key_Return || event.key === Qt.Key_Enter || event.key === Qt.Key_Space)) {
                                root.controller.setFlag("showCapabilities",true)
                                event.accepted=true
                            }
                        }
                        Rectangle {
                            anchors.fill: parent
                            anchors.margins: -Style.spacing.xxs
                            visible: headerStatus.activeFocus
                            color: "transparent"
                            border.color: root.theme.colors.accent
                            border.width: Style.spacing.hairline
                            radius: Style.cornerRadius
                        }
                        MouseArea {
                            id: statusHitArea
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: root.controller.setFlag("showCapabilities",true)
                        }
                        ToolTip.visible: statusHitArea.containsMouse
                        ToolTip.delay: 700
                        ToolTip.text: "Inspect provider availability, age, errors and provenance"
                    }

                    Text {
                        Layout.alignment: Qt.AlignBaseline
                        text: "·"
                        textFormat: Text.PlainText
                        color: root.theme.colors.subdued
                        font.family: root.theme.fontFamily
                        font.pixelSize: root.theme.smallSize
                    }

                    Text {
                        id: headerContext
                        Layout.alignment: Qt.AlignBaseline
                        Layout.maximumWidth: Style.space(320)
                        text: root.headerContext
                        textFormat: Text.PlainText
                        elide: Text.ElideRight
                        color: root.theme.colors.subdued
                        font.family: root.theme.fontFamily
                        font.pixelSize: root.theme.smallSize
                    }
                }
            }

            Item { Layout.fillWidth: true }

            RowLayout {
                id: headerActions
                spacing: Style.spacing.sm
                Layout.alignment: Qt.AlignVCenter | Qt.AlignRight

                InstrumentButton {
                    id: searchButton
                    text: "/ Search"
                    chosen: root.controller.navState.showSearch
                    paletteColors: root.theme.colors
                    fontFamily: root.theme.fontFamily
                    textSize: root.theme.smallSize
                    onClicked: { root.controller.setFlag("showSearch",!root.controller.navState.showSearch); if (root.controller.navState.showSearch) searchInput.forceActiveFocus() }
                }
                InstrumentButton {
                    text: root.controller.freezePending ? "Freezing..." : root.controller.navState.frozen ? "Resume" : "Freeze"
                    chosen: root.controller.navState.frozen
                    enabled: !root.controller.freezePending
                    hint: "Space / Exact snapshot; collection continues"
                    paletteColors: root.theme.colors
                    fontFamily: root.theme.fontFamily
                    textSize: root.theme.smallSize
                    onClicked: root.controller.toggleFreeze()
                }
                InstrumentButton {
                    visible: !root.compactWidth
                    text: "Legend"
                    hint: "? / H"
                    paletteColors: root.theme.colors
                    fontFamily: root.theme.fontFamily
                    textSize: root.theme.smallSize
                    onClicked: root.controller.setFlag("showHelp",true)
                }
                InstrumentButton {
                    visible: !root.compactWidth
                    text: "Settings"
                    hint: ","
                    paletteColors: root.theme.colors
                    fontFamily: root.theme.fontFamily
                    textSize: root.theme.smallSize
                    onClicked: root.controller.setFlag("showSettings",true)
                }
                InstrumentButton {
                    text: "Close"
                    hint: "Esc / Dismiss Tactical Display immediately"
                    bordered: true
                    paletteColors: root.theme.colors
                    fontFamily: root.theme.fontFamily
                    textSize: root.theme.smallSize
                    onClicked: root.controller.dismissRequested("close-control")
                }
            }
        }

        Flow {
            id: instrumentSelectorBar
            Layout.fillWidth: true
            spacing: Style.spacing.md
            Repeater {
                model: Instruments.catalog
                delegate: InstrumentButton {
                    required property var modelData
                    text: modelData.key+" "+modelData.shortName
                    chosen: root.controller.navState.instrument === modelData.id
                    paletteColors: root.theme.colors
                    fontFamily: root.theme.fontFamily
                    textSize: root.theme.smallSize
                    onClicked: root.controller.chooseInstrument(modelData.id)
                }
            }
            InstrumentButton {
                text: "A Briefing"+(root.controller.attention.length ? " · "+root.controller.attention.length : "")
                hint: "Attention, recent activity, pinned entities and baseline comparison"
                bordered: true
                paletteColors: root.theme.colors; fontFamily: root.theme.fontFamily; textSize: root.theme.smallSize
                onClicked: root.controller.setFlag("showOperator",true)
            }
        }

        Rectangle {
            id: chromeSeparator
            Layout.fillWidth: true
            Layout.preferredHeight: Style.spacing.hairline
            color: root.theme.colors.line
        }
        Flow {
            Layout.fillWidth: true
            spacing: Style.spacing.xxl
            Repeater {
                model: root.controller.view.status
                delegate: Text {
                    required property var modelData
                    text: modelData[0]+"  "+(modelData[1]===undefined||modelData[1]===null?"\u2014":String(modelData[1]))
                    textFormat: Text.PlainText; color: root.theme.colors.foreground; font.family: root.theme.fontFamily; font.pixelSize: root.theme.smallSize
                }
            }
        }
        Flow {
            Layout.fillWidth: true
            spacing: Style.spacing.md
            visible: root.lenses.length>0 || root.controller.navState.instrument === "machine" || root.controller.navState.query.length>0 || root.controller.navState.focusKey.length>0
            Repeater {
                model: root.lenses
                delegate: InstrumentButton {
                    required property var modelData
                    text: modelData.label; hint: modelData.hint
                    chosen: !!root.controller.navState.filters[modelData.key]
                    paletteColors: root.theme.colors; fontFamily: root.theme.fontFamily; textSize: root.theme.smallSize
                    onClicked: root.controller.cycle(modelData.key,modelData.values)
                }
            }
            InstrumentButton { visible: root.controller.navState.instrument === "connection"; text: root.controller.effectiveSettings.listeners ? "Listeners on" : "Listeners off"; hint: "L"; paletteColors: root.theme.colors; fontFamily: root.theme.fontFamily; textSize: root.theme.smallSize; onClicked: root.controller.configuration.setValue("listeners",!root.controller.effectiveSettings.listeners) }
            InstrumentButton { visible: root.controller.navState.instrument === "connection"; text: root.controller.effectiveSettings.loopback ? "Loopback on" : "Loopback off"; hint: "O"; paletteColors: root.theme.colors; fontFamily: root.theme.fontFamily; textSize: root.theme.smallSize; onClicked: root.controller.configuration.setValue("loopback",!root.controller.effectiveSettings.loopback) }
            InstrumentButton { visible: root.controller.navState.instrument === "machine"; text: root.controller.navState.trend ? "T  60-second trend" : "T  Instant state"; chosen: root.controller.navState.trend; paletteColors: root.theme.colors; fontFamily: root.theme.fontFamily; textSize: root.theme.smallSize; onClicked: root.controller.setFlag("trend",!root.controller.navState.trend) }
            InstrumentButton { visible: root.controller.navState.query.length>0 || root.controller.navState.focusKey.length>0 || Object.keys(root.controller.navState.filters).length>0; text: "Reset view"; hint: "R / Backspace"; paletteColors: root.theme.colors; fontFamily: root.theme.fontFamily; textSize: root.theme.smallSize; onClicked: root.controller.reset() }
            Text { visible: root.controller.navState.query.length>0; text: root.controller.effectiveSettings.privacy ? "Search active / hidden" : "Search: "+root.controller.navState.query; textFormat: Text.PlainText; color: root.theme.colors.accent; font.family: root.theme.fontFamily; font.pixelSize: root.theme.smallSize; width: Math.min(Style.space(300),implicitWidth); elide: Text.ElideRight; height: Style.spacing.controlHeight; verticalAlignment: Text.AlignVCenter }
        }
        TextField {
            id: searchInput
            Layout.fillWidth: true
            visible: root.controller.navState.showSearch
            text: root.controller.navState.query
            placeholderText: root.controller.effectiveSettings.privacy ? "Search identities (input hidden in privacy mode)" : "Search process, PID, host, port, mount, device or audio stream..."
            echoMode: root.controller.effectiveSettings.privacy ? TextInput.Password : TextInput.Normal
            maximumLength: 160
            color: root.theme.colors.foreground
            placeholderTextColor: root.theme.colors.subdued
            selectionColor: root.theme.colors.accent
            selectedTextColor: root.theme.colors.background
            font.family: root.theme.fontFamily; font.pixelSize: root.theme.bodySize
            leftPadding: Style.spacing.controlPaddingX
            rightPadding: Style.spacing.controlPaddingX
            topPadding: Style.spacing.inputPaddingY
            bottomPadding: Style.spacing.inputPaddingY
            background: Rectangle { radius: Style.cornerRadius; color: root.theme.colors.panel; border.width: Style.spacing.hairline; border.color: searchInput.activeFocus ? root.theme.colors.accent : root.theme.colors.line }
            onTextEdited: root.controller.setQuery(text)
            onVisibleChanged: {
                if (visible) forceActiveFocus()
                else if (!root.sheetVisible) root.focusField()
            }
            Keys.priority: Keys.BeforeItem
            Keys.onPressed: event => root.controller.handleSearchKey(event)
        }
        ListView {
            id: searchResults
            Layout.fillWidth: true
            Layout.preferredHeight: Math.min(root.compact ? Style.space(88) : Style.space(132),contentHeight)
            visible: root.controller.navState.showSearch && root.controller.view.results.length>0
            clip: true
            model: root.controller.view.results
            currentIndex: root.controller.view.results.findIndex(n => n.key===root.controller.navState.selectedKey)
            onCurrentIndexChanged: if (currentIndex>=0) positionViewAtIndex(currentIndex,ListView.Contain)
            delegate: InstrumentButton {
                required property var modelData
                width: searchResults.width; height: root.theme.bodySize+Style.space(20)
                text: modelData.name+" / "+modelData.kind+" / "+modelData.subtitle
                chosen: modelData.selected
                paletteColors: root.theme.colors; fontFamily: root.theme.fontFamily; textSize: root.theme.smallSize
                onClicked: { root.controller.pick(modelData); root.controller.focusSelection() }
            }
        }
        Text { Layout.fillWidth: true; visible: !!root.controller.navState.notice; text: root.controller.navState.notice; textFormat: Text.PlainText; wrapMode: Text.Wrap; color: root.theme.colors.warning; font.family: root.theme.fontFamily; font.pixelSize: root.theme.smallSize }
        Item {
            id: worldArea
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.minimumHeight: Style.space(180)
            clip: true
            readonly property bool hasDetail: !!root.controller.selected
            readonly property bool detailRight: width>=Style.space(870)
            readonly property real detailWidth: hasDetail && detailRight ? Math.min(Style.space(380),Math.max(Style.space(300),width*0.24)) : 0
            readonly property real detailHeight: hasDetail && !detailRight ? Math.max(0,Math.min(Style.space(260),height-Style.space(240))) : 0
            readonly property real trendHeight: root.controller.navState.instrument==="machine" && root.controller.navState.trend ? Math.min(Style.space(200),height*0.4) : 0
            Visual.Field {
                id: field
                x: 0; y: 0
                width: worldArea.width-(worldArea.detailWidth?worldArea.detailWidth+Style.spacing.xxl:0)
                height: worldArea.height-(worldArea.detailHeight?worldArea.detailHeight+Style.spacing.xxl:0)-(worldArea.trendHeight?worldArea.trendHeight+Style.spacing.lg:0)
                view: root.controller.view
                theme: root.theme
                active: root.active
                focusKey: root.controller.navState.focusKey
                labelDensity: root.controller.effectiveSettings.labels
                animation: root.controller.effectiveSettings.animation
                onPicked: key => { root.controller.pickKey(key); root.focusField() }
                onFocused: key => { root.controller.pickKey(key); root.controller.focusSelection(); root.focusField() }
                onHovered: key => root.controller.hoveredKey = key
            }
            Text {
                x: Style.space(20); y: Math.max(Style.space(52),field.height*0.38)
                width: Math.max(Style.space(100),field.width-Style.space(40))
                text: root.controller.displayFrame.schemaVersion ? root.controller.view.empty : "Acquiring local machine state...\nThe field appears as each provider becomes available."
                textFormat: Text.PlainText; wrapMode: Text.Wrap; horizontalAlignment: Text.AlignHCenter
                color: root.theme.colors.subdued; font.family: root.theme.fontFamily; font.pixelSize: root.theme.bodySize
                visible: !root.controller.view.visibleNodes.length
            }
            Visual.Trend {
                x: 0; y: field.height+Style.spacing.lg
                width: field.width; height: worldArea.trendHeight
                visible: height>0
                theme: root.theme
                samples: root.controller.displayFrame.trend||[]
                intervalSeconds: root.controller.displayFrame.intervalSeconds || 1
                selectedKey: root.controller.navState.focusKey || root.controller.navState.selectedKey || "subsystem:cpu"
            }
            InspectionPanel {
                x: worldArea.detailRight ? worldArea.width-worldArea.detailWidth : 0
                y: worldArea.detailRight ? 0 : worldArea.height-worldArea.detailHeight
                width: worldArea.detailRight ? worldArea.detailWidth : worldArea.width
                height: worldArea.detailRight ? worldArea.height : worldArea.detailHeight
                visible: worldArea.hasDetail && width>0 && height>0
                controller: root.controller
                theme: root.theme
                onNativePanelRequested: id => root.nativePanelRequested(id)
            }
        }
        Text {
            id: densityStatus
            Layout.fillWidth: true
            visible: field.hiddenCount > 0
            text: "Density: showing "+field.scene.nodes.length+" of "+field.scene.allNodeCount+" candidates; "+field.hiddenCount+" hidden. Search or focus to reveal them."
            textFormat: Text.PlainText
            elide: Text.ElideRight
            color: root.theme.colors.subdued
            font.family: root.theme.fontFamily
            font.pixelSize: root.theme.smallSize
        }
        Rectangle { Layout.fillWidth: true; Layout.preferredHeight: Style.spacing.hairline; color: root.theme.colors.line; opacity: 0.6 }
        Text {
            Layout.fillWidth: true
            text: root.hoverEntity ? root.hoverEntity.name+" / "+root.hoverEntity.kind+" / "+root.hoverEntity.subtitle : root.controller.telemetry && root.controller.telemetry.backendError ? root.controller.effectiveSettings.privacy ? "Backend issue / details hidden by privacy. Open data sources." : root.controller.telemetry.backendError : root.controller.view.note
            textFormat: Text.PlainText; elide: Text.ElideRight
            color: root.controller.telemetry && root.controller.telemetry.backendError ? root.theme.colors.warning : root.theme.colors.subdued
            font.family: root.theme.fontFamily; font.pixelSize: root.theme.smallSize
        }
        Text {
            Layout.fillWidth: true; visible: !root.compact
            text: root.controller.telemetry && root.controller.telemetry.actionMessage ? root.controller.telemetry.actionMessage : "ESC close  /  BACKSPACE back  /  TAB inspect  /  ENTER focus  /  SPACE freeze  /  ? legend"
            textFormat: Text.PlainText; elide: Text.ElideRight; color: root.theme.colors.subdued; font.family: root.theme.fontFamily; font.pixelSize: root.theme.smallSize
        }
    }
    CommandSheet { anchors.fill: parent; visible: root.sheetVisible && !root.controller.navState.showOperator; controller: root.controller; theme: root.theme; compactChrome: true }
    Loader {
        anchors.fill: parent
        active: root.controller.navState.showOperator
        sourceComponent: OperatorSheet { controller: root.controller; theme: root.theme }
    }
    NumberAnimation { id: modeTransition; target: field; property: "opacity"; from: 0.68; to: 1; duration: root.controller.effectiveSettings.animation === "reduced" ? 0 : root.controller.effectiveSettings.animation === "vivid" ? 220 : 130; easing.type: Easing.OutCubic }
    Connections { target: root.controller; function onInstrumentSelected(instrument) { modeTransition.restart(); root.focusField() } function onSearchRequested() { searchInput.forceActiveFocus() } }
    onFocusedItemChanged: {
        if (sheetVisible || searchInput.activeFocus) return
        controlsFocus = !!focusedItem && focusedItem !== fieldFocusTarget
    }
    onSheetVisibleChanged: if (!sheetVisible) Qt.callLater(function() { if (!root.sheetVisible && !searchInput.visible) root.focusField() })
    Component.onCompleted: Qt.callLater(function() { root.focusField() })
}
