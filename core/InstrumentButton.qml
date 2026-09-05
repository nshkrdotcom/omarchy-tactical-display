import QtQuick
import QtQuick.Controls

Button {
    id: root
    required property var paletteColors
    property string fontFamily: "monospace"
    property int textSize: 13
    property bool chosen: false
    property string hint: ""
    padding: 9
    topPadding: 7
    bottomPadding: 7
    hoverEnabled: true
    focusPolicy: Qt.StrongFocus
    Accessible.name: text
    Accessible.description: hint
    contentItem: Text {
        text: root.text
        textFormat: Text.PlainText
        color: root.enabled ? root.chosen ? root.paletteColors.background : root.paletteColors.foreground : root.paletteColors.subdued
        font.family: root.fontFamily
        font.pixelSize: root.textSize
        font.weight: root.chosen ? Font.DemiBold : Font.Normal
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
    }
    background: Rectangle {
        color: root.chosen ? root.paletteColors.accent : root.down ? root.paletteColors.plane : root.hovered ? root.paletteColors.panel : "transparent"
        border.width: root.chosen ? 0 : 1
        border.color: root.activeFocus ? root.paletteColors.accent : root.hovered ? root.paletteColors.line : "transparent"
        radius: 3
    }
    ToolTip.visible: hovered && hint.length > 0
    ToolTip.delay: 700
    ToolTip.text: hint
}
