import QtQuick
import qs.Commons
import "../visual/Palette.js" as Palette

QtObject {
    readonly property var colors: Palette.derive(Color.background, Color.foreground, Color.accent, Color.urgent)
    readonly property string fontFamily: Style.fontFamily
    readonly property int bodySize: Math.max(16, Style.fontBaseSize)
    readonly property int smallSize: Math.max(13, Style.fontBaseSize - 1)
    readonly property int titleSize: Math.max(26, Style.fontBaseSize * 2)
}
