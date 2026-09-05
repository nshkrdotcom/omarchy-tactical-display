import QtQuick

Item {
  id: root

  property var contacts: []
  property var system: ({})
  property color accent: "#7fffd4"
  property color foreground: "#f4f4f4"
  property color urgent: "#ff4d5a"
  property string selectedKey: ""
  property real sweepAngle: 0

  readonly property var selectedContact: {
    for (var i = 0; i < contacts.length; i++) {
      if (String(contacts[i].key) === selectedKey) return contacts[i]
    }
    return null
  }

  function clamp(value, low, high) {
    var n = Number(value)
    if (!isFinite(n)) n = low
    return Math.max(low, Math.min(high, n))
  }

  function hashText(text) {
    var value = 2166136261
    var s = String(text || "")
    for (var i = 0; i < s.length; i++) {
      value ^= s.charCodeAt(i)
      value = Math.imul(value, 16777619)
    }
    return value >>> 0
  }

  function angleFor(contact) {
    return (hashText(contact.key) % 3600) / 10
  }

  function radiusFactor(contact) {
    var kind = String(contact.kind || "outbound")
    if (kind === "listen") return 0.20
    if (kind === "loopback") return 0.42
    if (kind === "inbound") return 0.65
    if (kind === "outbound") return 0.88
    return 0.67
  }

  function pointFor(contact, width, height) {
    var cx = width / 2
    var cy = height / 2
    var radius = Math.min(width, height) * 0.44 * radiusFactor(contact)
    var radians = (angleFor(contact) - 90) * Math.PI / 180
    return { x: cx + Math.cos(radians) * radius, y: cy + Math.sin(radians) * radius }
  }

  function contactOpacity(contact) {
    if (contact.closed === true) {
      return clamp(1 - Number(contact.closedAgeMs || 0) / 2600, 0.08, 0.58)
    }
    return 0.9
  }

  NumberAnimation on sweepAngle {
    from: 0
    to: 360
    duration: 5200
    loops: Animation.Infinite
    running: root.visible
  }

  onSweepAngleChanged: radar.requestPaint()
  onContactsChanged: {
    if (selectedKey && !selectedContact) selectedKey = ""
    radar.requestPaint()
  }
  onAccentChanged: radar.requestPaint()
  onForegroundChanged: radar.requestPaint()
  onUrgentChanged: radar.requestPaint()

  Canvas {
    id: radar
    anchors.fill: parent
    antialiasing: true

    function strokeCircle(ctx, cx, cy, radius, alpha, width) {
      ctx.beginPath()
      ctx.arc(cx, cy, radius, 0, Math.PI * 2)
      ctx.strokeStyle = Qt.rgba(root.accent.r, root.accent.g, root.accent.b, alpha)
      ctx.lineWidth = width
      ctx.stroke()
    }

    onPaint: {
      var ctx = getContext("2d")
      ctx.clearRect(0, 0, width, height)

      var w = width
      var h = height
      var cx = w / 2
      var cy = h / 2
      var radius = Math.min(w, h) * 0.44

      // Range rings.
      for (var ring = 1; ring <= 4; ring++)
        strokeCircle(ctx, cx, cy, radius * ring / 4, ring === 4 ? 0.34 : 0.18, ring === 4 ? 1.4 : 1)

      // Axes and sector lines.
      ctx.lineWidth = 1
      for (var deg = 0; deg < 360; deg += 30) {
        var rad = (deg - 90) * Math.PI / 180
        ctx.beginPath()
        ctx.moveTo(cx, cy)
        ctx.lineTo(cx + Math.cos(rad) * radius, cy + Math.sin(rad) * radius)
        ctx.strokeStyle = Qt.rgba(root.accent.r, root.accent.g, root.accent.b, deg % 90 === 0 ? 0.20 : 0.08)
        ctx.stroke()
      }

      // Outer tick marks.
      for (var tick = 0; tick < 72; tick++) {
        var tickDeg = tick * 5
        var tickRad = (tickDeg - 90) * Math.PI / 180
        var inner = radius - (tick % 6 === 0 ? 10 : 5)
        ctx.beginPath()
        ctx.moveTo(cx + Math.cos(tickRad) * inner, cy + Math.sin(tickRad) * inner)
        ctx.lineTo(cx + Math.cos(tickRad) * radius, cy + Math.sin(tickRad) * radius)
        ctx.strokeStyle = Qt.rgba(root.accent.r, root.accent.g, root.accent.b, tick % 6 === 0 ? 0.52 : 0.22)
        ctx.stroke()
      }

      // Sweep trail.
      for (var trail = 0; trail < 18; trail++) {
        var trailDeg = root.sweepAngle - trail * 2.3
        var trailRad = (trailDeg - 90) * Math.PI / 180
        ctx.beginPath()
        ctx.moveTo(cx, cy)
        ctx.lineTo(cx + Math.cos(trailRad) * radius, cy + Math.sin(trailRad) * radius)
        ctx.strokeStyle = Qt.rgba(root.accent.r, root.accent.g, root.accent.b, Math.max(0.01, 0.30 - trail * 0.016))
        ctx.lineWidth = trail === 0 ? 2 : 1
        ctx.stroke()
      }

      // Center emitter.
      ctx.beginPath()
      ctx.arc(cx, cy, 5, 0, Math.PI * 2)
      ctx.fillStyle = root.accent
      ctx.fill()
      strokeCircle(ctx, cx, cy, 13, 0.35, 1)

      // Contacts.
      for (var i = 0; i < root.contacts.length; i++) {
        var contact = root.contacts[i]
        var point = root.pointFor(contact, w, h)
        var alpha = root.contactOpacity(contact)
        var selected = String(contact.key) === root.selectedKey
        var isNew = Number(contact.ageMs || 99999) < 1800 && contact.closed !== true
        var activity = root.clamp(contact.activity || 0, 0, 1)
        var size = 3.5 + activity * 4 + (selected ? 2 : 0)
        var kind = String(contact.kind || "outbound")
        var signalColor = kind === "inbound" ? root.urgent : root.accent

        if (isNew) {
          var pulseAge = Number(contact.ageMs || 0) / 1800
          ctx.beginPath()
          ctx.arc(point.x, point.y, 7 + pulseAge * 18, 0, Math.PI * 2)
          ctx.strokeStyle = Qt.rgba(signalColor.r, signalColor.g, signalColor.b, (1 - pulseAge) * 0.55)
          ctx.lineWidth = 1.5
          ctx.stroke()
        }

        ctx.globalAlpha = alpha
        ctx.fillStyle = signalColor
        ctx.strokeStyle = signalColor
        ctx.lineWidth = selected ? 2 : 1

        if (kind === "listen") {
          ctx.beginPath()
          ctx.moveTo(point.x, point.y - size - 2)
          ctx.lineTo(point.x + size + 2, point.y + size + 1)
          ctx.lineTo(point.x - size - 2, point.y + size + 1)
          ctx.closePath()
          contact.closed === true ? ctx.stroke() : ctx.fill()
        } else if (kind === "loopback") {
          ctx.strokeRect(point.x - size, point.y - size, size * 2, size * 2)
        } else {
          ctx.beginPath()
          ctx.arc(point.x, point.y, size, 0, Math.PI * 2)
          contact.closed === true ? ctx.stroke() : ctx.fill()
        }

        if (selected) {
          ctx.globalAlpha = 0.86
          ctx.beginPath()
          ctx.arc(point.x, point.y, size + 8, 0, Math.PI * 2)
          ctx.strokeStyle = root.foreground
          ctx.lineWidth = 1
          ctx.stroke()
        }

        ctx.globalAlpha = 1
      }
    }

    onWidthChanged: requestPaint()
    onHeightChanged: requestPaint()
  }

  MouseArea {
    anchors.fill: parent
    acceptedButtons: Qt.LeftButton
    cursorShape: Qt.CrossCursor

    onClicked: function(mouse) {
      var best = null
      var bestDistance = 26
      for (var i = 0; i < root.contacts.length; i++) {
        var point = root.pointFor(root.contacts[i], width, height)
        var dx = mouse.x - point.x
        var dy = mouse.y - point.y
        var distance = Math.sqrt(dx * dx + dy * dy)
        if (distance < bestDistance) {
          best = root.contacts[i]
          bestDistance = distance
        }
      }
      root.selectedKey = best ? String(best.key) : ""
      radar.requestPaint()
    }
  }

  Column {
    anchors.left: parent.left
    anchors.verticalCenter: parent.verticalCenter
    width: Math.min(250, parent.width * 0.22)
    spacing: 8

    Repeater {
      model: [
        { label: "LISTEN", kind: "listen", ring: "R1" },
        { label: "LOOPBACK", kind: "loopback", ring: "R2" },
        { label: "INBOUND", kind: "inbound", ring: "R3" },
        { label: "OUTBOUND", kind: "outbound", ring: "R4" }
      ]

      delegate: Row {
        required property var modelData
        spacing: 8
        Text {
          text: modelData.ring
          color: root.accent
          opacity: 0.52
          font.pixelSize: 10
          font.family: "monospace"
        }
        Text {
          text: modelData.label + "  " + root.contacts.filter(function(c) { return c.kind === modelData.kind && c.closed !== true }).length
          color: root.foreground
          opacity: 0.72
          font.pixelSize: 11
          font.family: "monospace"
          font.letterSpacing: 1
        }
      }
    }
  }

  Rectangle {
    id: detailCard
    visible: root.selectedContact !== null
    anchors.right: parent.right
    anchors.verticalCenter: parent.verticalCenter
    width: Math.min(360, parent.width * 0.31)
    height: detailColumn.implicitHeight + 34
    color: Qt.rgba(0, 0, 0, 0.34)
    border.color: Qt.rgba(root.accent.r, root.accent.g, root.accent.b, 0.36)
    border.width: 1
    radius: 3

    Column {
      id: detailColumn
      anchors.left: parent.left
      anchors.right: parent.right
      anchors.top: parent.top
      anchors.margins: 17
      spacing: 7

      Text {
        text: root.selectedContact ? String(root.selectedContact.process || "UNKNOWN PROCESS").toUpperCase() : ""
        color: root.foreground
        font.pixelSize: 15
        font.weight: Font.DemiBold
        font.letterSpacing: 1.3
      }
      Text {
        text: root.selectedContact ? String(root.selectedContact.proto || "").toUpperCase() + " / " + String(root.selectedContact.state || "UNKNOWN") : ""
        color: root.accent
        opacity: 0.86
        font.pixelSize: 11
        font.family: "monospace"
      }
      Text {
        text: root.selectedContact ? "LOCAL   " + String(root.selectedContact.local || "-") : ""
        color: root.foreground
        opacity: 0.68
        font.pixelSize: 11
        font.family: "monospace"
        elide: Text.ElideMiddle
        width: detailColumn.width
      }
      Text {
        text: root.selectedContact ? "REMOTE  " + String(root.selectedContact.remote || "-") : ""
        color: root.foreground
        opacity: 0.68
        font.pixelSize: 11
        font.family: "monospace"
        elide: Text.ElideMiddle
        width: detailColumn.width
      }
      Text {
        text: root.selectedContact ? "PID     " + String(root.selectedContact.pid || "-") + "    QUEUE " + String(root.selectedContact.queueBytes || 0) + " B" : ""
        color: root.foreground
        opacity: 0.52
        font.pixelSize: 10
        font.family: "monospace"
      }
    }
  }

  Row {
    anchors.horizontalCenter: parent.horizontalCenter
    anchors.bottom: parent.bottom
    anchors.bottomMargin: 8
    spacing: 26

    Text {
      text: "RX " + formatRate(root.system.netRxBps || 0)
      color: root.foreground
      opacity: 0.60
      font.pixelSize: 11
      font.family: "monospace"
    }
    Text {
      text: "TX " + formatRate(root.system.netTxBps || 0)
      color: root.foreground
      opacity: 0.60
      font.pixelSize: 11
      font.family: "monospace"
    }
  }

  function formatRate(value) {
    var n = Number(value || 0)
    if (n >= 1024 * 1024 * 1024) return (n / (1024 * 1024 * 1024)).toFixed(1) + " GiB/s"
    if (n >= 1024 * 1024) return (n / (1024 * 1024)).toFixed(1) + " MiB/s"
    if (n >= 1024) return (n / 1024).toFixed(1) + " KiB/s"
    return Math.round(n) + " B/s"
  }
}
