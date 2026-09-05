import QtQuick

Column {
  id: root

  required property string label
  required property string value
  required property color accent
  required property color foreground
  property bool alignRight: false

  width: 140
  spacing: 2

  Text {
    width: root.width
    text: root.label
    color: root.accent
    opacity: 0.62
    horizontalAlignment: root.alignRight ? Text.AlignRight : Text.AlignLeft
    font.pixelSize: 9
    font.family: "monospace"
    font.letterSpacing: 1.4
  }

  Text {
    width: root.width
    text: root.value
    color: root.foreground
    opacity: 0.86
    horizontalAlignment: root.alignRight ? Text.AlignRight : Text.AlignLeft
    font.pixelSize: 15
    font.family: "monospace"
  }
}
