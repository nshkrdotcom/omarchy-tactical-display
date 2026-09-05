import QtQuick
import Quickshell.Io
import "../model/Protocol.js" as Protocol

Item {
    id: root
    property string pluginDir: ""
    property bool active: false
    property var configuration: ({})
    property string instrument: "connection"
    property var snapshot: null
    property var detail: null
    property string backendError: ""
    property string actionMessage: ""
    property double lastSampleAt: 0
    property double clock: 0
    property int failures: 0
    property int goodFrames: 0
    property int freezeSequence: 0
    property bool intentionalStop: true
    property bool ready: false
    property bool disposing: false
    readonly property bool fresh: lastSampleAt > 0 && clock - lastSampleAt < Math.max(3500, Number(snapshot ? snapshot.intervalSeconds : 1) * 4000)
    readonly property string statusText: !active ? "STANDBY" : backendError ? (fresh ? "PARTIAL" : "RECONNECTING") : fresh ? "LIVE" : lastSampleAt ? "STALE" : "ACQUIRING"
    readonly property int helperPid: sampler.processId || 0
    signal received(var frame)
    signal detailReceived(var frame)
    signal freezeReceived(var frame)

    function start() {
        if (disposing || !active || !pluginDir || sampler.running || restart.running) return
        intentionalStop = false
        ready = false
        sampler.running = true
        startupWatch.restart()
    }
    function stop() {
        intentionalStop = true
        restart.stop()
        startupWatch.stop()
        ready = false
        sampler.running = false
        snapshot = null
        detail = null
        lastSampleAt = 0
        failures = 0
        goodFrames = 0
        backendError = ""
    }
    function retry() {
        failures = 0
        restart.stop()
        if (!sampler.running) start()
        else configure()
    }
    function send(command) {
        if (ready && sampler.running && active) sampler.write(JSON.stringify(command) + "\n")
    }
    function configure() {
        var c = configuration || {}
        send({op:"configure",instrument:instrument,profile:c.refreshProfile || "balanced",naming:c.naming || "local",
              privacy:c.privacy === true,aliases:c.aliases || {},offlineDb:c.offlineDb || "",audioActions:c.audioActions === true})
    }
    function inspect(key, offset, frozen) { send({op:"inspect",key:key,offset:offset || 0,limit:24,frozen:frozen === true}) }
    function freeze(value) { var id=++freezeSequence; send({op:"freeze",state:value,requestId:id}); return id }
    function audioAction(action, key, value) {
        send({op:"audio-action",action:action,key:key,value:value,confirmed:true})
    }
    function accept(line) {
        if (!active || disposing) return
        if (line.length > 4194304) { backendError = "Oversized telemetry record rejected"; return }
        try {
            var frame = JSON.parse(line)
            if (!frame || typeof frame !== "object") throw new Error("Expected object")
            if (frame.type === "snapshot") {
                var problem = Protocol.validateSnapshot(frame)
                if (problem) throw new Error(problem)
                snapshot = frame
                clock = Date.now()
                lastSampleAt = clock
                goodFrames++
                if (goodFrames >= 3) failures = 0
                backendError = ""
                received(frame)
            } else if (frame.type === "freeze-result") {
                if (typeof frame.frozen!=="boolean" || typeof frame.requestId!=="number" || frame.frozen && Protocol.validateSnapshot(frame.snapshot)) throw new Error("Invalid frozen snapshot")
                freezeReceived(frame)
            } else if (frame.type === "detail") {
                var detailProblem = Protocol.validateDetail(frame)
                if (detailProblem) throw new Error(detailProblem)
                detail = frame
                detailReceived(frame)
            } else if (frame.type === "action-result") {
                actionMessage = String(frame.message || "Action completed")
            } else if (frame.type === "error") {
                backendError = String(frame.message || "Helper reported an error").slice(0,240)
            }
        } catch (error) {
            backendError = "Invalid telemetry record rejected: " + String(error).slice(0,180)
        }
    }
    onActiveChanged: { if (active) { clock = Date.now(); start() } else stop() }
    onPluginDirChanged: if (active) start()
    onInstrumentChanged: configure()
    onConfigurationChanged: configure()

    Process {
        id: sampler
        command: ["python3", "-B", "-u", root.pluginDir + "/scripts/telemetry.py", "--instrument", root.instrument]
        workingDirectory: root.pluginDir
        stdinEnabled: true
        running: false
        stdout: SplitParser { onRead: line => root.accept(String(line)) }
        stderr: SplitParser {
            onRead: line => { if (root.active) root.backendError = "Helper: " + String(line).slice(0,200) }
        }
        onStarted: {
            root.ready = true
            startupWatch.stop()
            root.configure()
        }
        onExited: (exitCode, exitStatus) => {
            root.ready = false
            startupWatch.stop()
            if (root.active && !root.intentionalStop && !root.disposing) {
                root.goodFrames = 0
                root.failures++
                root.backendError = "Telemetry exited (" + exitCode + "); retry " + root.failures + "/6"
                if (root.failures <= 6) restart.restart()
                else root.backendError = "Telemetry stopped after six retries. Run doctor or press Retry."
            }
        }
    }
    Timer {
        id: restart
        interval: Math.min(30000, 500 * Math.pow(2, root.failures))
        onTriggered: root.start()
    }
    Timer {
        id: startupWatch
        interval: 3500
        onTriggered: {
            if (root.active && !root.ready) {
                root.backendError = "Helper could not start. Check python3 and plugin path; press Retry."
                sampler.running = false
            }
        }
    }
    Timer { interval: 500; repeat: true; running: root.active; onTriggered: root.clock = Date.now() }
    Component.onDestruction: { disposing = true; stop() }
}
