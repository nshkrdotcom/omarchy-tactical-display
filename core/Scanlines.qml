import QtQuick

Canvas {
  id: root
  property color lineColor: "#ffffff"

  onPaint: {
    var ctx = getContext("2d")
    ctx.clearRect(0, 0, width, height)
    ctx.strokeStyle = Qt.rgba(lineColor.r, lineColor.g, lineColor.b, 0.085)
    ctx.lineWidth = 1
    for (var y = 1; y < height; y += 5) {
      ctx.beginPath()
      ctx.moveTo(0, y + 0.5)
      ctx.lineTo(width, y + 0.5)
      ctx.stroke()
    }
  }

  onWidthChanged: requestPaint()
  onHeightChanged: requestPaint()
  onLineColorChanged: requestPaint()
}
