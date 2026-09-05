import QtQuick
import "../core"

Item {
  id: root

  property var system: ({})
  property color accent: "#7fffd4"
  property color foreground: "#f4f4f4"
  property color urgent: "#ff4d5a"
  property real phase: 0

  function clamp(value, low, high) {
    var n = Number(value)
    if (!isFinite(n)) n = low
    return Math.max(low, Math.min(high, n))
  }

  function pct(value) { return clamp(Number(value || 0) / 100, 0, 1) }

  function gpuUtil() {
    return system.gpu && system.gpu.utilization !== undefined ? Number(system.gpu.utilization) : 0
  }

  function temperature() {
    if (system.temperature !== null && system.temperature !== undefined) return Number(system.temperature)
    if (system.gpu && system.gpu.temperature !== null && system.gpu.temperature !== undefined) return Number(system.gpu.temperature)
    return 0
  }

  NumberAnimation on phase {
    from: 0
    to: 360
    duration: 9000
    loops: Animation.Infinite
    running: root.visible
  }

  onPhaseChanged: reactor.requestPaint()
  onSystemChanged: reactor.requestPaint()
  onAccentChanged: reactor.requestPaint()
  onForegroundChanged: reactor.requestPaint()
  onUrgentChanged: reactor.requestPaint()

  Canvas {
    id: reactor
    anchors.fill: parent
    antialiasing: true

    function metricArc(ctx, cx, cy, radius, thickness, startDeg, progress, color, alpha) {
      var start = (startDeg - 90) * Math.PI / 180
      var end = (startDeg - 90 + Math.max(2, progress * 300)) * Math.PI / 180
      ctx.beginPath()
      ctx.arc(cx, cy, radius, start, end, false)
      ctx.strokeStyle = Qt.rgba(color.r, color.g, color.b, alpha)
      ctx.lineWidth = thickness
      ctx.lineCap = "round"
      ctx.stroke()
    }

    onPaint: {
      var ctx = getContext("2d")
      ctx.clearRect(0, 0, width, height)

      var cx = width / 2
      var cy = height / 2
      var base = Math.min(width, height) * 0.31
      var cpu = root.pct(root.system.cpu)
      var memory = root.pct(root.system.memory)
      var gpu = root.pct(root.gpuUtil())
      var net = root.clamp((Number(root.system.netRxBps || 0) + Number(root.system.netTxBps || 0)) / (64 * 1024 * 1024), 0, 1)
      var temp = root.temperature()
      var heat = root.clamp((temp - 45) / 50, 0, 1)
      var heatColor = heat > 0.72 ? root.urgent : root.accent

      // Faint structural rings.
      for (var r = 0; r < 6; r++) {
        ctx.beginPath()
        ctx.arc(cx, cy, base * (0.36 + r * 0.135), 0, Math.PI * 2)
        ctx.strokeStyle = Qt.rgba(root.accent.r, root.accent.g, root.accent.b, 0.05 + r * 0.018)
        ctx.lineWidth = 1
        ctx.stroke()
      }

      // Rotating segmented rails.
      for (var rail = 0; rail < 24; rail++) {
        var startDeg = root.phase * (rail % 2 === 0 ? 0.22 : -0.15) + rail * 15
        var start = (startDeg - 90) * Math.PI / 180
        var end = (startDeg - 90 + 7) * Math.PI / 180
        ctx.beginPath()
        ctx.arc(cx, cy, base * 1.06, start, end)
        ctx.strokeStyle = Qt.rgba(root.accent.r, root.accent.g, root.accent.b, rail % 4 === 0 ? 0.45 : 0.16)
        ctx.lineWidth = rail % 4 === 0 ? 2 : 1
        ctx.stroke()
      }

      // Metric rings: geometry is the reading.
      metricArc(ctx, cx, cy, base * 0.93, 7, root.phase * 0.12, cpu, root.accent, 0.92)
      metricArc(ctx, cx, cy, base * 0.78, 6, 180 - root.phase * 0.08, gpu, root.foreground, 0.74)
      metricArc(ctx, cx, cy, base * 0.63, 6, root.phase * 0.05 + 35, memory, root.accent, 0.58)
      metricArc(ctx, cx, cy, base * 0.49, 5, 250 - root.phase * 0.10, net, root.foreground, 0.45)

      // Thermal flare spokes.
      var flares = 18
      for (var i = 0; i < flares; i++) {
        var deg = i * (360 / flares) + root.phase * 0.18
        var rad = (deg - 90) * Math.PI / 180
        var inner = base * 0.28
        var outer = inner + 8 + heat * (14 + (i % 3) * 5)
        ctx.beginPath()
        ctx.moveTo(cx + Math.cos(rad) * inner, cy + Math.sin(rad) * inner)
        ctx.lineTo(cx + Math.cos(rad) * outer, cy + Math.sin(rad) * outer)
        ctx.strokeStyle = Qt.rgba(heatColor.r, heatColor.g, heatColor.b, 0.18 + heat * 0.48)
        ctx.lineWidth = 1.3
        ctx.stroke()
      }

      // Core.
      ctx.beginPath()
      ctx.arc(cx, cy, base * 0.22 + cpu * 3, 0, Math.PI * 2)
      ctx.fillStyle = Qt.rgba(root.accent.r, root.accent.g, root.accent.b, 0.08 + cpu * 0.11)
      ctx.fill()
      ctx.strokeStyle = Qt.rgba(root.accent.r, root.accent.g, root.accent.b, 0.72)
      ctx.lineWidth = 2
      ctx.stroke()

      ctx.beginPath()
      ctx.arc(cx, cy, 5 + cpu * 4, 0, Math.PI * 2)
      ctx.fillStyle = heat > 0.78 ? root.urgent : root.foreground
      ctx.fill()
    }

    onWidthChanged: requestPaint()
    onHeightChanged: requestPaint()
  }

  Column {
    anchors.centerIn: parent
    spacing: 3

    Text {
      anchors.horizontalCenter: parent.horizontalCenter
      text: Math.round(Number(root.system.cpu || 0)) + "%"
      color: root.foreground
      font.pixelSize: Math.max(34, Math.min(62, root.width / 20))
      font.weight: Font.Light
      font.family: "monospace"
    }
    Text {
      anchors.horizontalCenter: parent.horizontalCenter
      text: "CPU CORE LOAD"
      color: root.accent
      opacity: 0.70
      font.pixelSize: 10
      font.family: "monospace"
      font.letterSpacing: 1.8
    }
  }

  Column {
    anchors.left: parent.left
    anchors.verticalCenter: parent.verticalCenter
    spacing: 13

    MetricReadout { label: "CPU"; value: Number(root.system.cpu || 0).toFixed(0) + "%"; accent: root.accent; foreground: root.foreground }
    MetricReadout { label: "GPU"; value: root.system.gpu ? Number(root.gpuUtil()).toFixed(0) + "%" : "N/A"; accent: root.accent; foreground: root.foreground }
    MetricReadout { label: "RAM"; value: Number(root.system.memory || 0).toFixed(0) + "%"; accent: root.accent; foreground: root.foreground }
    MetricReadout { label: "LOAD"; value: Number(root.system.load1 || 0).toFixed(2); accent: root.accent; foreground: root.foreground }
  }

  Column {
    anchors.right: parent.right
    anchors.verticalCenter: parent.verticalCenter
    spacing: 13

    MetricReadout { label: "TEMP"; value: root.temperature() > 0 ? root.temperature().toFixed(0) + " C" : "N/A"; accent: root.temperature() > 80 ? root.urgent : root.accent; foreground: root.foreground; alignRight: true }
    MetricReadout { label: "RX"; value: root.formatRate(root.system.netRxBps || 0); accent: root.accent; foreground: root.foreground; alignRight: true }
    MetricReadout { label: "TX"; value: root.formatRate(root.system.netTxBps || 0); accent: root.accent; foreground: root.foreground; alignRight: true }
    MetricReadout { label: "UP"; value: root.formatUptime(root.system.uptimeSeconds || 0); accent: root.accent; foreground: root.foreground; alignRight: true }
  }


  function formatRate(value) {
    var n = Number(value || 0)
    if (n >= 1024 * 1024 * 1024) return (n / (1024 * 1024 * 1024)).toFixed(1) + "G/s"
    if (n >= 1024 * 1024) return (n / (1024 * 1024)).toFixed(1) + "M/s"
    if (n >= 1024) return (n / 1024).toFixed(1) + "K/s"
    return Math.round(n) + "B/s"
  }

  function formatUptime(seconds) {
    var total = Math.max(0, Math.floor(Number(seconds || 0)))
    var days = Math.floor(total / 86400)
    var hours = Math.floor((total % 86400) / 3600)
    if (days > 0) return days + "d " + hours + "h"
    var minutes = Math.floor((total % 3600) / 60)
    return hours + "h " + minutes + "m"
  }
}
