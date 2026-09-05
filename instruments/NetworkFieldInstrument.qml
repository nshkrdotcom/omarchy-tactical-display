pragma ComponentBehavior: Bound

import QtQuick

Item {
  id: root

  property var network: ({ processes: [], remotes: [], links: [], listeners: [], summary: ({}) })
  property var system: ({})
  property color accent: "#7fffd4"
  property color foreground: "#f4f4f4"
  property color urgent: "#ff4d5a"

  property real phase: 0
  property string selectedType: ""
  property string selectedKey: ""
  property string hoverType: ""
  property string hoverKey: ""
  property var layout: ({ processes: ({}), remotes: ({}) })

  readonly property var summary: network && network.summary ? network.summary : ({})
  readonly property var processes: network && Array.isArray(network.processes) ? network.processes : []
  readonly property var remotes: network && Array.isArray(network.remotes) ? network.remotes : []
  readonly property var links: network && Array.isArray(network.links) ? network.links : []
  readonly property var listeners: network && Array.isArray(network.listeners) ? network.listeners : []

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

  function colorWithAlpha(color, alpha) {
    return Qt.rgba(color.r, color.g, color.b, alpha)
  }

  function shortAddress(address) {
    var text = String(address || "-")
    if (text.length <= 23) return text
    if (text.indexOf(":") >= 0) return text.slice(0, 10) + "…" + text.slice(-9)
    return text
  }

  function processLabel(process) {
    var name = String(process && process.name ? process.name : "unattributed")
    return name.length > 15 ? name.slice(0, 14) + "…" : name
  }

  function roleForRemote(remote) {
    if (String(remote.scope || "") === "loopback") return "loopback"
    var inbound = Number(remote.inboundCount || 0)
    var outbound = Number(remote.outboundCount || 0)
    if (inbound > 0 && outbound > 0 && Math.abs(inbound - outbound) <= Math.max(1, Math.min(inbound, outbound))) return "mixed"
    return inbound > outbound ? "inbound" : "outbound"
  }

  function activeProcesses() {
    return processes.filter(function(item) { return item.active === true && Number(item.socketCount || 0) > 0 })
      .slice(0, 18)
  }

  function activeRemotes() {
    return remotes.filter(function(item) { return item.active === true })
      .slice(0, 36)
  }

  function findByKey(items, key) {
    for (var i = 0; i < items.length; i++)
      if (String(items[i].key) === String(key)) return items[i]
    return null
  }

  function selectedObject() {
    if (selectedType === "process") return findByKey(processes, selectedKey)
    if (selectedType === "remote") return findByKey(remotes, selectedKey)
    return null
  }

  function selectedPoint() {
    if (selectedType === "process") return pointForProcess(selectedKey)
    if (selectedType === "remote") return pointForRemote(selectedKey)
    return null
  }

  function detailPanelOnLeft() {
    var point = selectedPoint()
    return point !== null && Number(point.x || 0) > width * 0.58
  }

  function linkedToSelection(link) {
    if (!selectedKey) return false
    if (selectedType === "process") return String(link.processKey) === selectedKey
    if (selectedType === "remote") return String(link.remoteKey) === selectedKey
    return false
  }

  function linkedToHover(link) {
    if (!hoverKey) return false
    if (hoverType === "process") return String(link.processKey) === hoverKey
    if (hoverType === "remote") return String(link.remoteKey) === hoverKey
    return false
  }

  function remoteServiceSummary(remote) {
    if (!remote) return ""
    var rows = []
    for (var i = 0; i < links.length; i++) {
      var link = links[i]
      if (link.active !== true || String(link.remoteKey) !== String(remote.key)) continue
      var label = link.service ? String(link.service).toUpperCase() : String(link.servicePort || "")
      if (label && rows.indexOf(label) < 0) rows.push(label)
      if (rows.length >= 3) break
    }
    return rows.join(" · ")
  }

  function detailLines() {
    var selected = selectedObject()
    if (!selected) return []
    var rows = []
    if (selectedType === "process") {
      for (var i = 0; i < links.length; i++) {
        var link = links[i]
        if (link.active !== true || String(link.processKey) !== String(selected.key)) continue
        var arrow = String(link.direction) === "in" ? "←" : (String(link.direction) === "local" ? "↔" : "→")
        var service = link.service ? " " + String(link.service) : ""
        rows.push(arrow + " " + shortAddress(link.address) + ":" + String(link.servicePort || "-") + service + "  ×" + String(link.socketCount || 1))
        if (rows.length >= 6) break
      }
    } else {
      for (var j = 0; j < links.length; j++) {
        var remoteLink = links[j]
        if (remoteLink.active !== true || String(remoteLink.remoteKey) !== String(selected.key)) continue
        var remoteArrow = String(remoteLink.direction) === "in" ? "→" : (String(remoteLink.direction) === "local" ? "↔" : "←")
        var remoteService = remoteLink.service ? " " + String(remoteLink.service) : ""
        rows.push(remoteArrow + " " + String(remoteLink.process || "unattributed") + "  " + String(remoteLink.proto || "").toUpperCase() + "/" + String(remoteLink.servicePort || "-") + remoteService)
        if (rows.length >= 6) break
      }
    }
    return rows
  }

  function placeRemoteGroup(group, startDeg, endDeg, output, cx, cy, radius) {
    if (group.length === 0) return
    var entries = []
    var span = endDeg - startDeg
    for (var i = 0; i < group.length; i++) {
      var seed = hashText(group[i].key)
      entries.push({
        node: group[i],
        angle: startDeg + ((seed % 10000) / 10000) * span,
        radial: 0.91 + (((seed >>> 9) % 1000) / 1000) * 0.075
      })
    }
    entries.sort(function(a, b) { return a.angle - b.angle })
    var minimum = Math.min(13, Math.max(4.5, Math.abs(span) / Math.max(2, group.length + 1) * 0.7))
    for (var j = 1; j < entries.length; j++)
      entries[j].angle = Math.max(entries[j].angle, entries[j - 1].angle + minimum)
    if (entries[entries.length - 1].angle > endDeg) {
      var shift = entries[entries.length - 1].angle - endDeg
      for (var k = 0; k < entries.length; k++) entries[k].angle -= shift
    }
    if (entries[0].angle < startDeg) {
      var forward = startDeg - entries[0].angle
      for (var m = 0; m < entries.length; m++) entries[m].angle += forward
    }

    for (var n = 0; n < entries.length; n++) {
      var radians = entries[n].angle * Math.PI / 180
      output[String(entries[n].node.key)] = {
        x: cx + Math.cos(radians) * radius * entries[n].radial,
        y: cy + Math.sin(radians) * radius * entries[n].radial,
        angle: entries[n].angle,
        role: roleForRemote(entries[n].node)
      }
    }
  }

  function rebuildLayout() {
    if (width < 10 || height < 10) return
    var cx = width * 0.50
    var cy = height * 0.53
    var minDim = Math.min(width, height)
    var machineRadius = minDim * 0.205
    var processOuter = machineRadius * 0.73
    var externalRadius = minDim * 0.445
    var ppoints = ({})
    var rpoints = ({})
    var plist = activeProcesses()

    for (var i = 0; i < plist.length; i++) {
      var count = Math.max(1, plist.length)
      var ring = count > 10 && i % 2 === 1 ? 0.72 : 1.0
      var slot = count > 10 ? Math.floor(i / 2) : i
      var slotCount = count > 10 ? Math.ceil(count / 2) : count
      var angle = -90 + slot * (360 / Math.max(1, slotCount)) + ((hashText(plist[i].key) % 17) - 8) * 0.35
      if (count > 10 && i % 2 === 1) angle += 360 / Math.max(2, slotCount) * 0.48
      var rad = angle * Math.PI / 180
      ppoints[String(plist[i].key)] = {
        x: cx + Math.cos(rad) * processOuter * ring,
        y: cy + Math.sin(rad) * processOuter * ring,
        angle: angle,
        radius: processOuter * ring
      }
    }

    var outbound = []
    var inbound = []
    var mixed = []
    var loopback = []
    var rlist = activeRemotes()
    for (var j = 0; j < rlist.length; j++) {
      var role = roleForRemote(rlist[j])
      if (role === "inbound") inbound.push(rlist[j])
      else if (role === "mixed") mixed.push(rlist[j])
      else if (role === "loopback") loopback.push(rlist[j])
      else outbound.push(rlist[j])
    }
    placeRemoteGroup(outbound, -58, 58, rpoints, cx, cy, externalRadius)
    placeRemoteGroup(inbound, 122, 238, rpoints, cx, cy, externalRadius)
    placeRemoteGroup(mixed, -112, -68, rpoints, cx, cy, externalRadius * 0.99)

    for (var q = 0; q < loopback.length; q++) {
      var loopAngle = 72 + q * (36 / Math.max(1, loopback.length))
      var loopRad = loopAngle * Math.PI / 180
      rpoints[String(loopback[q].key)] = {
        x: cx + Math.cos(loopRad) * machineRadius * 0.34,
        y: cy + Math.sin(loopRad) * machineRadius * 0.34,
        angle: loopAngle,
        role: "loopback"
      }
    }

    layout = { processes: ppoints, remotes: rpoints, cx: cx, cy: cy, machineRadius: machineRadius, externalRadius: externalRadius }
    field.requestPaint()
  }

  function pointForProcess(key) {
    return layout.processes ? layout.processes[String(key)] : null
  }

  function pointForRemote(key) {
    return layout.remotes ? layout.remotes[String(key)] : null
  }

  function formatRate(value) {
    var n = Number(value || 0)
    if (n >= 1024 * 1024 * 1024) return (n / (1024 * 1024 * 1024)).toFixed(1) + " GiB/s"
    if (n >= 1024 * 1024) return (n / (1024 * 1024)).toFixed(1) + " MiB/s"
    if (n >= 1024) return (n / 1024).toFixed(1) + " KiB/s"
    return Math.round(n) + " B/s"
  }

  function selectionStillExists() {
    if (!selectedKey) return true
    return selectedObject() !== null
  }

  onNetworkChanged: {
    if (!selectionStillExists()) {
      selectedType = ""
      selectedKey = ""
    }
    rebuildLayout()
  }
  onWidthChanged: rebuildLayout()
  onHeightChanged: rebuildLayout()
  onAccentChanged: field.requestPaint()
  onForegroundChanged: field.requestPaint()
  onUrgentChanged: field.requestPaint()

  NumberAnimation on phase {
    from: 0
    to: 1
    duration: 2200
    loops: Animation.Infinite
    running: root.visible
  }
  onPhaseChanged: field.requestPaint()

  Canvas {
    id: field
    anchors.fill: parent
    antialiasing: true

    function lineColorFor(link) {
      if (String(link.kind) === "inbound") return root.urgent
      if (String(link.kind) === "loopback") return root.foreground
      return root.accent
    }

    function drawArrow(ctx, from, to, t, color, alpha, size) {
      var x = from.x + (to.x - from.x) * t
      var y = from.y + (to.y - from.y) * t
      var angle = Math.atan2(to.y - from.y, to.x - from.x)
      ctx.save()
      ctx.translate(x, y)
      ctx.rotate(angle)
      ctx.globalAlpha = alpha
      ctx.fillStyle = color
      ctx.beginPath()
      ctx.moveTo(size, 0)
      ctx.lineTo(-size * 0.72, size * 0.62)
      ctx.lineTo(-size * 0.72, -size * 0.62)
      ctx.closePath()
      ctx.fill()
      ctx.restore()
    }

    function drawNodeLabel(ctx, text, x, y, align, color, alpha, bold) {
      ctx.save()
      ctx.globalAlpha = alpha
      ctx.fillStyle = color
      ctx.textAlign = align
      ctx.textBaseline = "middle"
      ctx.font = (bold ? "600 " : "") + "11px monospace"
      ctx.fillText(text, x, y)
      ctx.restore()
    }

    onPaint: {
      var ctx = getContext("2d")
      ctx.clearRect(0, 0, width, height)
      if (!root.layout || !root.layout.cx) return

      var cx = root.layout.cx
      var cy = root.layout.cy
      var machineRadius = root.layout.machineRadius
      var externalRadius = root.layout.externalRadius
      var minDim = Math.min(width, height)

      // Spatial reference field: center is this machine; the perimeter is the outside world.
      ctx.save()
      ctx.lineWidth = 1
      ctx.strokeStyle = root.colorWithAlpha(root.accent, 0.075)
      ctx.setLineDash([2, 11])
      ctx.beginPath()
      ctx.arc(cx, cy, externalRadius, 0, Math.PI * 2)
      ctx.stroke()
      ctx.setLineDash([])

      ctx.strokeStyle = root.colorWithAlpha(root.accent, 0.18)
      ctx.beginPath()
      ctx.arc(cx, cy, machineRadius, 0, Math.PI * 2)
      ctx.stroke()

      ctx.strokeStyle = root.colorWithAlpha(root.accent, 0.055)
      ctx.beginPath()
      ctx.arc(cx, cy, machineRadius * 0.48, 0, Math.PI * 2)
      ctx.stroke()

      // Direction sectors are meaningful: inbound left, outbound right, bidirectional top.
      ctx.font = "10px monospace"
      ctx.textBaseline = "middle"
      ctx.fillStyle = root.colorWithAlpha(root.foreground, 0.28)
      ctx.textAlign = "left"
      ctx.fillText("INBOUND", cx - externalRadius + 2, cy - externalRadius * 0.60)
      ctx.textAlign = "right"
      ctx.fillText("OUTBOUND", cx + externalRadius - 2, cy - externalRadius * 0.60)
      ctx.textAlign = "center"
      ctx.fillText("BIDIRECTIONAL", cx, cy - externalRadius - 12)
      ctx.restore()

      // Relationship links first so nodes sit crisply above them.
      for (var i = 0; i < root.links.length; i++) {
        var link = root.links[i]
        var from = root.pointForProcess(link.processKey)
        var remote = root.pointForRemote(link.remoteKey)
        if (!from || !remote) continue

        var color = lineColorFor(link)
        var selected = root.linkedToSelection(link)
        var hovered = root.linkedToHover(link)
        var hasSelection = root.selectedKey.length > 0
        var active = link.active === true
        var closedFade = active ? 1 : root.clamp(1 - Number(link.closedAgeMs || 2600) / 2600, 0.05, 0.44)
        var alpha = active ? (selected ? 0.90 : (hovered ? 0.66 : (hasSelection ? 0.055 : 0.20))) : 0.12 * closedFade
        var multiplicity = Math.max(1, Number(link.socketCount || 0))
        var pressure = root.clamp(Number(link.queuePressure || 0), 0, 1)
        var widthBoost = Math.min(2.4, Math.log(multiplicity + 1) / Math.LN2 * 0.42) + pressure * 2.4

        ctx.save()
        ctx.globalAlpha = alpha
        ctx.strokeStyle = color
        ctx.lineWidth = 0.8 + widthBoost
        if (!active) ctx.setLineDash([5, 8])
        ctx.beginPath()
        ctx.moveTo(from.x, from.y)
        ctx.lineTo(remote.x, remote.y)
        ctx.stroke()
        ctx.setLineDash([])
        ctx.restore()

        if (active) {
          // This tracer encodes relationship direction, not measured per-link bandwidth.
          var direction = String(link.direction || "out")
          var t = root.phase
          var arrowFrom = direction === "in" ? remote : from
          var arrowTo = direction === "in" ? from : remote
          var tracerAlpha = selected ? 1.0 : (hovered ? 0.88 : (hasSelection ? 0.10 : 0.62))
          drawArrow(ctx, arrowFrom, arrowTo, 0.08 + t * 0.84, color, tracerAlpha, selected ? 5.2 : 3.8)
          if (multiplicity >= 3)
            drawArrow(ctx, arrowFrom, arrowTo, 0.08 + ((t + 0.46) % 1) * 0.84, color, tracerAlpha * 0.58, 3.1)

          if (Number(link.newCount || 0) > 0 && Number(link.ageMs !== undefined && link.ageMs !== null ? link.ageMs : 99999) < 1800) {
            var target = direction === "in" ? from : remote
            var pulse = root.clamp(Number(link.ageMs !== undefined && link.ageMs !== null ? link.ageMs : 0) / 1800, 0, 1)
            ctx.save()
            ctx.globalAlpha = (1 - pulse) * 0.72
            ctx.strokeStyle = color
            ctx.lineWidth = 1.4
            ctx.beginPath()
            ctx.arc(target.x, target.y, 11 + pulse * 24, 0, Math.PI * 2)
            ctx.stroke()
            ctx.restore()
          }
        }
      }

      // Listener apertures live on the machine boundary and point to their owning process.
      var listenerIndexByProcess = ({})
      for (var l = 0; l < root.listeners.length; l++) {
        var listener = root.listeners[l]
        if (listener.active !== true) continue
        var processPoint = root.pointForProcess(listener.processKey)
        if (!processPoint) continue
        var countForProcess = listenerIndexByProcess[String(listener.processKey)] || 0
        listenerIndexByProcess[String(listener.processKey)] = countForProcess + 1
        var angle = Math.atan2(processPoint.y - cy, processPoint.x - cx) + (countForProcess - 1) * 0.055
        var apertureX = cx + Math.cos(angle) * machineRadius
        var apertureY = cy + Math.sin(angle) * machineRadius
        ctx.save()
        ctx.translate(apertureX, apertureY)
        ctx.rotate(angle)
        ctx.strokeStyle = root.colorWithAlpha(root.accent, 0.76)
        ctx.lineWidth = 2
        ctx.beginPath()
        ctx.moveTo(-7, -4)
        ctx.lineTo(0, -4)
        ctx.lineTo(5, 0)
        ctx.lineTo(0, 4)
        ctx.lineTo(-7, 4)
        ctx.stroke()
        ctx.restore()
      }

      // Process hubs: these are the local actors actually owning sockets.
      var plist = root.activeProcesses()
      for (var p = 0; p < plist.length; p++) {
        var process = plist[p]
        var point = root.pointForProcess(process.key)
        if (!point) continue
        var selectedProcess = root.selectedType === "process" && root.selectedKey === String(process.key)
        var hoveredProcess = root.hoverType === "process" && root.hoverKey === String(process.key)
        var related = !root.selectedKey || selectedProcess
        if (!related && root.selectedType === "remote") {
          for (var rp = 0; rp < root.links.length; rp++) {
            if (root.links[rp].active === true && String(root.links[rp].remoteKey) === root.selectedKey && String(root.links[rp].processKey) === String(process.key)) {
              related = true
              break
            }
          }
        }
        var nodeAlpha = related ? 0.94 : 0.18
        var nodeRadius = 5.4 + Math.min(5, Math.log(Number(process.socketCount || 1) + 1) / Math.LN2)

        ctx.save()
        ctx.globalAlpha = nodeAlpha
        ctx.fillStyle = root.accent
        ctx.strokeStyle = selectedProcess || hoveredProcess ? root.foreground : root.colorWithAlpha(root.accent, 0.72)
        ctx.lineWidth = selectedProcess ? 2.2 : 1.1
        ctx.beginPath()
        ctx.arc(point.x, point.y, nodeRadius, 0, Math.PI * 2)
        ctx.fill()
        ctx.stroke()
        if (selectedProcess || hoveredProcess) {
          ctx.globalAlpha = 0.72
          ctx.beginPath()
          ctx.arc(point.x, point.y, nodeRadius + 8, 0, Math.PI * 2)
          ctx.stroke()
        }
        ctx.restore()

        var align = point.x < cx ? "right" : "left"
        var labelX = point.x + (align === "left" ? nodeRadius + 8 : -nodeRadius - 8)
        drawNodeLabel(ctx, root.processLabel(process), labelX, point.y - 2, align, root.foreground, nodeAlpha * 0.86, selectedProcess)
        drawNodeLabel(ctx, String(process.socketCount || 0) + " SOCKET" + (Number(process.socketCount || 0) === 1 ? "" : "S"), labelX, point.y + 11, align, root.accent, nodeAlpha * 0.42, false)
      }

      // Remote systems: address is the outer-world identity; geometry shows direction class.
      var rlist = root.activeRemotes()
      for (var r = 0; r < rlist.length; r++) {
        var remoteNode = rlist[r]
        var remotePoint = root.pointForRemote(remoteNode.key)
        if (!remotePoint) continue
        var role = root.roleForRemote(remoteNode)
        var selectedRemote = root.selectedType === "remote" && root.selectedKey === String(remoteNode.key)
        var hoveredRemote = root.hoverType === "remote" && root.hoverKey === String(remoteNode.key)
        var remoteRelated = !root.selectedKey || selectedRemote
        if (!remoteRelated && root.selectedType === "process") {
          for (var pr = 0; pr < root.links.length; pr++) {
            if (root.links[pr].active === true && String(root.links[pr].processKey) === root.selectedKey && String(root.links[pr].remoteKey) === String(remoteNode.key)) {
              remoteRelated = true
              break
            }
          }
        }
        var remoteAlpha = remoteRelated ? 0.92 : 0.14
        var remoteColor = role === "inbound" ? root.urgent : (role === "loopback" ? root.foreground : root.accent)
        var remoteSize = 5.2 + Math.min(4.5, Math.log(Number(remoteNode.socketCount || 1) + 1) / Math.LN2)

        ctx.save()
        ctx.globalAlpha = remoteAlpha
        ctx.translate(remotePoint.x, remotePoint.y)
        ctx.rotate(Math.PI / 4)
        ctx.strokeStyle = remoteColor
        ctx.fillStyle = root.colorWithAlpha(remoteColor, role === "loopback" ? 0.18 : 0.08)
        ctx.lineWidth = selectedRemote ? 2.2 : 1.25
        ctx.beginPath()
        ctx.rect(-remoteSize, -remoteSize, remoteSize * 2, remoteSize * 2)
        ctx.fill()
        ctx.stroke()
        if (selectedRemote || hoveredRemote) {
          ctx.globalAlpha = 0.72
          ctx.beginPath()
          ctx.rect(-remoteSize - 6, -remoteSize - 6, remoteSize * 2 + 12, remoteSize * 2 + 12)
          ctx.stroke()
        }
        ctx.restore()

        var remoteAlign = remotePoint.x < cx ? "right" : "left"
        var remoteLabelX = remotePoint.x + (remoteAlign === "left" ? remoteSize + 9 : -remoteSize - 9)
        drawNodeLabel(ctx, root.shortAddress(remoteNode.address), remoteLabelX, remotePoint.y - 3, remoteAlign, root.foreground, remoteAlpha * 0.88, selectedRemote)
        var serviceSummary = root.remoteServiceSummary(remoteNode)
        if (serviceSummary)
          drawNodeLabel(ctx, serviceSummary, remoteLabelX, remotePoint.y + 10, remoteAlign, remoteColor, remoteAlpha * 0.48, false)
      }

      // Machine core: conceptual anchor, deliberately not another metric gauge.
      ctx.save()
      ctx.textAlign = "center"
      ctx.textBaseline = "middle"
      ctx.fillStyle = root.colorWithAlpha(root.foreground, 0.90)
      ctx.font = "600 15px monospace"
      ctx.fillText("THIS MACHINE", cx, cy - 5)
      ctx.fillStyle = root.colorWithAlpha(root.accent, 0.58)
      ctx.font = "10px monospace"
      ctx.fillText(String(root.summary.processes || 0) + " NETWORKED PROCESSES", cx, cy + 13)
      ctx.restore()

      if (Number(root.summary.connections || 0) === 0) {
        ctx.save()
        ctx.textAlign = "center"
        ctx.textBaseline = "middle"
        ctx.fillStyle = root.colorWithAlpha(root.foreground, 0.36)
        ctx.font = "11px monospace"
        ctx.fillText("NO ACTIVE CONNECTIONS OBSERVED", cx, cy + machineRadius + 36)
        ctx.restore()
      }
    }
  }

  MouseArea {
    id: hitArea
    anchors.fill: parent
    acceptedButtons: Qt.LeftButton
    hoverEnabled: true
    cursorShape: root.hoverKey ? Qt.PointingHandCursor : Qt.CrossCursor

    function nearestNode(x, y, maxDistance) {
      var best = null
      var bestDistance = maxDistance
      var plist = root.activeProcesses()
      for (var i = 0; i < plist.length; i++) {
        var pp = root.pointForProcess(plist[i].key)
        if (!pp) continue
        var pdx = x - pp.x
        var pdy = y - pp.y
        var pd = Math.sqrt(pdx * pdx + pdy * pdy)
        if (pd < bestDistance) {
          bestDistance = pd
          best = { type: "process", key: String(plist[i].key) }
        }
      }
      var rlist = root.activeRemotes()
      for (var j = 0; j < rlist.length; j++) {
        var rp = root.pointForRemote(rlist[j].key)
        if (!rp) continue
        var rdx = x - rp.x
        var rdy = y - rp.y
        var rd = Math.sqrt(rdx * rdx + rdy * rdy)
        if (rd < bestDistance) {
          bestDistance = rd
          best = { type: "remote", key: String(rlist[j].key) }
        }
      }
      return best
    }

    onPositionChanged: function(mouse) {
      var node = nearestNode(mouse.x, mouse.y, 24)
      root.hoverType = node ? node.type : ""
      root.hoverKey = node ? node.key : ""
      field.requestPaint()
    }

    onExited: {
      root.hoverType = ""
      root.hoverKey = ""
      field.requestPaint()
    }

    onClicked: function(mouse) {
      var node = nearestNode(mouse.x, mouse.y, 28)
      if (!node) {
        root.selectedType = ""
        root.selectedKey = ""
      } else if (root.selectedType === node.type && root.selectedKey === node.key) {
        root.selectedType = ""
        root.selectedKey = ""
      } else {
        root.selectedType = node.type
        root.selectedKey = node.key
      }
      field.requestPaint()
    }
  }

  Row {
    anchors.horizontalCenter: parent.horizontalCenter
    anchors.top: parent.top
    anchors.topMargin: 8
    spacing: Math.max(18, root.width * 0.018)

    Repeater {
      model: [
        { label: "CONNECTIONS", value: String(root.summary.connections || 0) },
        { label: "PROCESSES", value: String(root.summary.processes || 0) },
        { label: "REMOTE SYSTEMS", value: String(root.summary.remoteSystems || 0) },
        { label: "LISTENERS", value: String(root.summary.listeners || 0) },
        { label: "NEW", value: String(root.summary.newConnections || 0) }
      ]

      delegate: Column {
        required property var modelData
        spacing: 0
        Text {
          anchors.horizontalCenter: parent.horizontalCenter
          text: parent.modelData.value
          color: root.foreground
          font.family: "monospace"
          font.pixelSize: 16
          font.weight: Font.DemiBold
        }
        Text {
          anchors.horizontalCenter: parent.horizontalCenter
          text: parent.modelData.label
          color: root.accent
          opacity: 0.50
          font.family: "monospace"
          font.pixelSize: 8
          font.letterSpacing: 1.1
        }
      }
    }
  }

  Row {
    anchors.horizontalCenter: parent.horizontalCenter
    anchors.bottom: parent.bottom
    anchors.bottomMargin: 6
    spacing: 28

    Text {
      text: "← INBOUND  " + String(root.summary.inbound || 0)
      color: root.urgent
      opacity: 0.68
      font.family: "monospace"
      font.pixelSize: 10
    }
    Text {
      text: "OUTBOUND →  " + String(root.summary.outbound || 0)
      color: root.accent
      opacity: 0.68
      font.family: "monospace"
      font.pixelSize: 10
    }
    Text {
      text: "LOCAL ↔  " + String(root.summary.loopback || 0)
      color: root.foreground
      opacity: 0.48
      font.family: "monospace"
      font.pixelSize: 10
    }
    Text {
      text: "RX " + root.formatRate(root.system.netRxBps || 0) + "   TX " + root.formatRate(root.system.netTxBps || 0)
      color: root.foreground
      opacity: 0.56
      font.family: "monospace"
      font.pixelSize: 10
    }
  }

  Rectangle {
    id: details
    visible: root.selectedObject() !== null
    anchors.verticalCenter: parent.verticalCenter
    x: root.detailPanelOnLeft() ? 0 : parent.width - width
    width: Math.min(390, parent.width * 0.30)
    height: detailColumn.implicitHeight + 34
    color: Qt.rgba(0, 0, 0, 0.72)
    border.color: root.colorWithAlpha(root.accent, 0.28)
    border.width: 1
    radius: 2

    Column {
      id: detailColumn
      anchors.left: parent.left
      anchors.right: parent.right
      anchors.top: parent.top
      anchors.margins: 17
      spacing: 7

      Text {
        readonly property var selected: root.selectedObject()
        text: root.selectedType === "process"
          ? root.processLabel(selected).toUpperCase()
          : root.shortAddress(selected ? selected.address : "").toUpperCase()
        color: root.foreground
        font.pixelSize: 15
        font.weight: Font.DemiBold
        font.letterSpacing: 1.5
      }

      Text {
        readonly property var selected: root.selectedObject()
        text: root.selectedType === "process"
          ? (selected && selected.pid ? "LOCAL PROCESS / PID " + selected.pid : "LOCAL PROCESS / UNATTRIBUTED")
          : "REMOTE SYSTEM / " + (selected ? String(root.roleForRemote(selected)).toUpperCase() : "")
        color: root.accent
        opacity: 0.82
        font.family: "monospace"
        font.pixelSize: 10
        font.letterSpacing: 1.1
      }

      Text {
        readonly property var selected: root.selectedObject()
        visible: root.selectedType === "process" && selected && String(selected.command || "").length > 0
        width: detailColumn.width
        text: selected ? String(selected.command || "") : ""
        color: root.foreground
        opacity: 0.48
        wrapMode: Text.WrapAnywhere
        maximumLineCount: 3
        elide: Text.ElideRight
        font.family: "monospace"
        font.pixelSize: 10
      }

      Text {
        readonly property var selected: root.selectedObject()
        text: {
          if (!selected) return ""
          if (root.selectedType === "process")
            return String(selected.socketCount || 0) + " SOCKETS   " + String(selected.listenerCount || 0) + " LISTENERS"
          return String(selected.socketCount || 0) + " SOCKETS   " + String(selected.processCount || 0) + " LOCAL PROCESSES"
        }
        color: root.foreground
        opacity: 0.62
        font.family: "monospace"
        font.pixelSize: 10
      }

      Rectangle {
        width: detailColumn.width
        height: 1
        color: root.colorWithAlpha(root.accent, 0.18)
      }

      Repeater {
        model: root.detailLines()
        delegate: Text {
          required property var modelData
          width: detailColumn.width
          text: String(modelData)
          color: root.foreground
          opacity: 0.72
          elide: Text.ElideMiddle
          font.family: "monospace"
          font.pixelSize: 10
        }
      }

      Text {
        visible: root.detailLines().length === 0
        text: "NO ACTIVE RELATIONSHIPS"
        color: root.foreground
        opacity: 0.34
        font.family: "monospace"
        font.pixelSize: 10
      }

      Text {
        visible: root.selectedType === "remote"
        text: "Address identity only. No DNS or GeoIP lookup is performed."
        color: root.foreground
        opacity: 0.28
        font.family: "monospace"
        font.pixelSize: 9
        wrapMode: Text.WordWrap
        width: detailColumn.width
      }
    }
  }

  Text {
    anchors.left: parent.left
    anchors.bottom: parent.bottom
    anchors.bottomMargin: Number(root.summary.unattributed || 0) > 0 ? 20 : 6
    visible: root.activeProcesses().length < Number(root.summary.processes || 0) || root.activeRemotes().length < (root.remotes.filter(function(item) { return item.active === true }).length)
    text: "FIELD " + String(root.activeProcesses().length) + "/" + String(root.summary.processes || 0) + " PROCESSES   " + String(root.activeRemotes().length) + "/" + String(root.remotes.filter(function(item) { return item.active === true }).length) + " REMOTES"
    color: root.foreground
    opacity: 0.24
    font.family: "monospace"
    font.pixelSize: 9
  }

  Text {
    anchors.left: parent.left
    anchors.bottom: parent.bottom
    anchors.bottomMargin: 6
    visible: Number(root.summary.unattributed || 0) > 0
    text: String(root.summary.unattributed || 0) + " SOCKET" + (Number(root.summary.unattributed || 0) === 1 ? "" : "S") + " UNATTRIBUTED"
    color: root.foreground
    opacity: 0.28
    font.family: "monospace"
    font.pixelSize: 9
  }
}
