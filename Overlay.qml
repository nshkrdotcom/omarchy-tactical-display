pragma ComponentBehavior: Bound

import QtQuick
import Quickshell
import Quickshell.Hyprland
import Quickshell.Wayland
import qs.Commons
import "core"
import "instruments"

Item {
  id: root

  // Injected by the Omarchy Quattro shell.
  property string omarchyPath: Quickshell.env("OMARCHY_PATH")
  property var shell: null
  property var manifest: ({})
  property var pluginRegistry: null

  property bool opened: false
  property string screenFilter: ""
  property bool showHelp: false
  property string lastPayloadError: ""

  readonly property string pluginDir: manifest && manifest.__sourceDir ? String(manifest.__sourceDir) : ""
  readonly property bool telemetryNeeded: opened

  function open(payloadJson) {
    var args = {}
    lastPayloadError = ""

    if (payloadJson) {
      try {
        args = JSON.parse(payloadJson) || {}
      } catch (error) {
        lastPayloadError = String(error)
        args = {}
      }
    }

    // v0.2 is one focused instrument. Legacy radar/reactor payloads still
    // summon the connection field so existing development bindings keep working.
    screenFilter = String(args.screen || "")
    showHelp = args.help === true || args.help === "true"
    opened = true
    telemetry.start()
  }

  function close() {
    opened = false
    showHelp = false
    telemetry.stop()
  }

  function requestHide() {
    if (shell && manifest && manifest.id && typeof shell.hide === "function") {
      shell.hide(String(manifest.id))
    } else {
      close()
    }
  }

  Telemetry {
    id: telemetry
    pluginDir: root.pluginDir
    active: root.telemetryNeeded
  }

  Variants {
    model: Quickshell.screens

    PanelWindow {
      id: tacticalWindow
      required property var modelData

      readonly property bool selectedScreen: !root.screenFilter || String(modelData.name) === root.screenFilter
      readonly property bool focusedScreen: !Hyprland.focusedMonitor || String(Hyprland.focusedMonitor.name) === String(modelData.name)

      screen: modelData
      visible: root.opened && selectedScreen
      color: "transparent"
      anchors { top: true; bottom: true; left: true; right: true }
      exclusionMode: ExclusionMode.Ignore

      WlrLayershell.namespace: "nshkr-tactical-display"
      WlrLayershell.layer: WlrLayer.Overlay
      WlrLayershell.keyboardFocus: visible && focusedScreen ? WlrKeyboardFocus.Exclusive : WlrKeyboardFocus.None

      HudSurface {
        id: hud
        anchors.fill: parent
        active: tacticalWindow.visible
        title: "NETWORK / LIVE"
        subtitle: "THIS MACHINE  ⇄  THE WORLD"
        footerText: "CLICK NODE INSPECT   H HELP   ESC CLOSE"
        statusText: telemetry.statusText
        accent: Color.accent
        foreground: Color.foreground
        background: Color.background
        urgent: Color.urgent

        focus: tacticalWindow.focusedScreen && tacticalWindow.visible
        Keys.priority: Keys.BeforeItem
        Keys.onPressed: function(event) {
          if (event.key === Qt.Key_Escape) {
            root.requestHide()
            event.accepted = true
          } else if (event.key === Qt.Key_H || event.key === Qt.Key_Question) {
            root.showHelp = !root.showHelp
            event.accepted = true
          }
        }

        Component.onCompleted: if (focus) forceActiveFocus()
        onFocusChanged: if (focus) forceActiveFocus()

        NetworkFieldInstrument {
          anchors.fill: parent
          network: telemetry.network
          system: telemetry.system
          accent: hud.accent
          foreground: hud.foreground
          urgent: hud.urgent
        }

        Rectangle {
          anchors.fill: parent
          visible: root.showHelp
          color: Qt.rgba(0, 0, 0, 0.88)
          z: 100

          Column {
            anchors.centerIn: parent
            width: Math.min(parent.width * 0.72, 760)
            spacing: 13

            Text {
              anchors.horizontalCenter: parent.horizontalCenter
              text: "CONNECTION FIELD"
              color: hud.foreground
              font.pixelSize: 28
              font.weight: Font.DemiBold
              font.letterSpacing: 4
            }
            Text {
              width: parent.width
              horizontalAlignment: Text.AlignHCenter
              text: "LOCAL PROCESSES LIVE INSIDE THE MACHINE BOUNDARY. REMOTE SYSTEMS LIVE AT THE PERIMETER."
              color: hud.accent
              opacity: 0.78
              wrapMode: Text.WordWrap
              font.pixelSize: 12
              font.family: "monospace"
              font.letterSpacing: 1.0
            }
            Text {
              width: parent.width
              horizontalAlignment: Text.AlignHCenter
              text: "LINKS ARE REAL SOCKET RELATIONSHIPS. MOVING TRACERS SHOW DIRECTION, NOT PER-CONNECTION BANDWIDTH. NEW RELATIONSHIPS PULSE; CLOSED RELATIONSHIPS DECAY."
              color: hud.foreground
              opacity: 0.62
              wrapMode: Text.WordWrap
              font.pixelSize: 11
              font.family: "monospace"
            }
            Text {
              width: parent.width
              horizontalAlignment: Text.AlignHCenter
              text: "LEFT = LIKELY INBOUND    RIGHT = OUTBOUND    TOP = BIDIRECTIONAL    INNER = LOOPBACK"
              color: hud.foreground
              opacity: 0.52
              wrapMode: Text.WordWrap
              font.pixelSize: 10
              font.family: "monospace"
            }
            Text {
              anchors.horizontalCenter: parent.horizontalCenter
              text: "CLICK A PROCESS OR REMOTE SYSTEM TO ISOLATE ITS RELATIONSHIPS.   H / ? HELP   ESC CLOSE"
              color: hud.accent
              opacity: 0.72
              font.pixelSize: 10
              font.family: "monospace"
            }
            Text {
              anchors.horizontalCenter: parent.horizontalCenter
              visible: root.lastPayloadError.length > 0
              text: "Payload warning: " + root.lastPayloadError
              color: hud.urgent
              font.pixelSize: 10
              font.family: "monospace"
            }
          }
        }
      }
    }
  }
}
