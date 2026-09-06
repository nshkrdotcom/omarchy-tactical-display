import QtQuick
import qs.Commons
import "../visual/Palette.js" as Palette

QtObject {
    property bool popupSurface: false
    readonly property color baseBackground: popupSurface ? Color.popups.background : Color.background
    readonly property color baseForeground: popupSurface ? Color.popups.text : Color.foreground
    readonly property var colors: Palette.derive(baseBackground, baseForeground, Color.accent, Color.urgent)
    readonly property string fontFamily: popupSurface ? Style.font.family : Style.fontFamily
    readonly property int bodySize: popupSurface ? Style.font.body : Math.max(16, Style.fontBaseSize)
    readonly property int smallSize: popupSurface ? Style.font.caption : Math.max(13, Style.fontBaseSize - 1)
    readonly property int titleSize: popupSurface ? Style.font.title : Math.max(26, Style.fontBaseSize * 2)
}
