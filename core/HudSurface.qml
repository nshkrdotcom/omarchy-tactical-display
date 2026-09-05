import QtQuick

Item {
  id: root

  property bool active: false
  property string title: "TACTICAL DISPLAY"
  property string subtitle: ""
  property string statusText: "STANDBY"
  property string footerText: "CLICK NODE INSPECT   H HELP   ESC CLOSE"
  property color accent: "#7fffd4"
  property color foreground: "#f0f0f0"
  property color background: "#080b0d"
  property color urgent: "#ff4d5a"
  default property alias contentData: content.data

  Rectangle {
    anchors.fill: parent
    color: Qt.rgba(root.background.r, root.background.g, root.background.b, 0.975)
  }

  // A slight tint keeps the display integrated with the active Omarchy theme
  // without turning the entire surface into generic sci-fi chrome.
  Rectangle {
    anchors.fill: parent
    color: Qt.rgba(root.accent.r, root.accent.g, root.accent.b, 0.012)
  }

  Scanlines {
    anchors.fill: parent
    opacity: 0.055
  }

  Canvas {
    id: chrome
    anchors.fill: parent
    antialiasing: true

    onPaint: {
      var ctx = getContext("2d")
      ctx.clearRect(0, 0, width, height)
      var margin = Math.max(26, Math.min(width, height) * 0.034)
      var topY = margin + 56
      var bottomY = height - margin - 26

      ctx.strokeStyle = Qt.rgba(root.accent.r, root.accent.g, root.accent.b, 0.12)
      ctx.lineWidth = 1
      ctx.beginPath()
      ctx.moveTo(margin, topY)
      ctx.lineTo(width - margin, topY)
      ctx.moveTo(margin, bottomY)
      ctx.lineTo(width - margin, bottomY)
      ctx.stroke()

      // Sparse registration ticks communicate an instrument surface without
      // wasting the field on ornamental frames.
      ctx.strokeStyle = Qt.rgba(root.accent.r, root.accent.g, root.accent.b, 0.28)
      for (var i = 0; i < 9; i++) {
        var x = margin + (width - margin * 2) * i / 8
        var size = i === 4 ? 8 : 4
        ctx.beginPath()
        ctx.moveTo(x, topY - size)
        ctx.lineTo(x, topY + size)
        ctx.moveTo(x, bottomY - size)
        ctx.lineTo(x, bottomY + size)
        ctx.stroke()
      }
    }

    Connections {
      target: root
      function onAccentChanged() { chrome.requestPaint() }
      function onActiveChanged() { chrome.requestPaint() }
    }

    onWidthChanged: requestPaint()
    onHeightChanged: requestPaint()
  }

  Column {
    anchors.left: parent.left
    anchors.top: parent.top
    anchors.leftMargin: Math.max(34, parent.width * 0.042)
    anchors.topMargin: Math.max(24, parent.height * 0.034)
    spacing: 2

    Text {
      text: root.title
      color: root.foreground
      font.pixelSize: Math.max(16, Math.min(24, parent.parent.width / 68))
      font.weight: Font.DemiBold
      font.letterSpacing: 3.2
    }
    Text {
      text: root.subtitle
      color: root.accent
      opacity: 0.68
      font.pixelSize: 10
      font.family: "monospace"
      font.letterSpacing: 1.7
    }
  }

  Row {
    anchors.right: parent.right
    anchors.top: parent.top
    anchors.rightMargin: Math.max(34, parent.width * 0.042)
    anchors.topMargin: Math.max(28, parent.height * 0.038)
    spacing: 9

    Rectangle {
      width: 6
      height: 6
      radius: 3
      anchors.verticalCenter: parent.verticalCenter
      color: root.statusText === "LIVE" ? root.accent : root.urgent

      SequentialAnimation on opacity {
        running: root.active
        loops: Animation.Infinite
        NumberAnimation { to: 0.30; duration: 720 }
        NumberAnimation { to: 0.95; duration: 720 }
      }
    }

    Text {
      text: root.statusText
      color: root.foreground
      opacity: 0.62
      font.pixelSize: 10
      font.family: "monospace"
      font.letterSpacing: 1.3
    }
  }

  Item {
    id: content
    anchors.left: parent.left
    anchors.right: parent.right
    anchors.top: parent.top
    anchors.bottom: parent.bottom
    anchors.leftMargin: Math.max(30, parent.width * 0.040)
    anchors.rightMargin: Math.max(30, parent.width * 0.040)
    anchors.topMargin: Math.max(86, parent.height * 0.100)
    anchors.bottomMargin: Math.max(54, parent.height * 0.065)
  }

  Text {
    anchors.left: parent.left
    anchors.bottom: parent.bottom
    anchors.leftMargin: Math.max(34, parent.width * 0.042)
    anchors.bottomMargin: Math.max(18, parent.height * 0.026)
    text: root.footerText
    color: root.foreground
    opacity: 0.32
    font.pixelSize: 9
    font.family: "monospace"
    font.letterSpacing: 1.1
  }
}
