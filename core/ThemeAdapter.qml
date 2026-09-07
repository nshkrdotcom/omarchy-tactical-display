import QtQuick
import qs.Commons
import "../visual/Palette.js" as Palette

QtObject {
    // One presentation for the bar panel and fullscreen host. Window geometry
    // is not a typography or palette profile.
    readonly property color baseBackground: Color.popups.background
    readonly property color baseForeground: Color.popups.text
    readonly property var colors: Palette.derive(baseBackground, baseForeground, Color.accent, Color.urgent)
    readonly property string fontFamily: Style.font.family
    readonly property int bodySize: Style.font.body
    readonly property int smallSize: Style.font.caption
    readonly property int titleSize: Style.font.title
}
