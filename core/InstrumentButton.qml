import QtQuick
import QtQuick.Controls
import qs.Commons

Button {
    id: root
    required property var paletteColors
    property string fontFamily: "monospace"
    property int textSize: Style.font.caption
    property bool chosen: false
    property bool bordered: false
    property string hint: ""
    leftPadding: Style.spacing.controlPaddingX
    rightPadding: Style.spacing.controlPaddingX
    topPadding: Style.spacing.controlPaddingY
    bottomPadding: Style.spacing.controlPaddingY
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
        border.width: root.activeFocus ? Style.space(2) : root.chosen ? 0 : (root.bordered || root.hovered ? Style.spacing.hairline : 0)
        border.color: root.activeFocus ? root.chosen ? root.paletteColors.foreground : root.paletteColors.accent : root.hovered ? root.paletteColors.line : root.bordered ? root.paletteColors.line : "transparent"
        radius: Style.cornerRadius
    }
    ToolTip.visible: hovered && hint.length > 0
    ToolTip.delay: 700
    ToolTip.text: hint
}
