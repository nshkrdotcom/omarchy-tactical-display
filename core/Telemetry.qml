import QtQuick
import Quickshell.Io

Item {
  id: root

  property string pluginDir: ""
  property bool active: false
  property var system: ({
    netRxBps: 0,
    netTxBps: 0,
    uptimeSeconds: 0
  })
  property var contacts: []
  property var network: ({
    processes: [],
    remotes: [],
    links: [],
    listeners: [],
    summary: ({})
  })
  property string backendError: ""
  property double lastSampleAt: 0
  property int sampleCount: 0
  property bool manuallyStopped: false

  readonly property bool fresh: lastSampleAt > 0 && (Date.now() - lastSampleAt) < 3500
  readonly property string statusText: backendError.length > 0
    ? "TELEMETRY DEGRADED"
    : (fresh ? "LIVE" : (active ? "ACQUIRING" : "STANDBY"))

  function start() {
    manuallyStopped = false
    if (active && pluginDir.length > 0 && !telemetryProcess.running)
      telemetryProcess.running = true
  }

  function stop() {
    manuallyStopped = true
    telemetryProcess.running = false
  }

  onActiveChanged: {
    if (active) start()
    else stop()
  }

  onPluginDirChanged: if (active) start()

  Process {
    id: telemetryProcess
    command: ["python3", root.pluginDir + "/scripts/telemetry.py", "--interval", "0.75"]
    running: false

    stdout: SplitParser {
      onRead: function(line) {
        var raw = String(line || "").trim()
        if (!raw) return
        try {
          var sample = JSON.parse(raw)
          if (sample.system) root.system = sample.system
          if (Array.isArray(sample.contacts)) root.contacts = sample.contacts
          if (sample.network) root.network = sample.network
          root.lastSampleAt = Date.now()
          root.sampleCount += 1
          root.backendError = ""
        } catch (error) {
          root.backendError = "Invalid telemetry frame: " + error
        }
      }
    }

    stderr: SplitParser {
      onRead: function(line) {
        var text = String(line || "").trim()
        if (text) root.backendError = text
      }
    }

    onExited: function(exitCode) {
      if (!root.manuallyStopped && root.active) {
        root.backendError = "Telemetry process exited (" + exitCode + ")"
        restartTimer.restart()
      }
    }
  }

  Timer {
    id: restartTimer
    interval: 1200
    repeat: false
    onTriggered: if (root.active && !root.manuallyStopped && !telemetryProcess.running) telemetryProcess.running = true
  }
}
