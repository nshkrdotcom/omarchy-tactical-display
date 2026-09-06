import QtQuick
import Quickshell
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
    property int invalidFrames: 0
    property int freezeSequence: 0
    property var instanceGroups: []
    property string instanceScopeKey: ""
    property bool intentionalStop: true
    property bool restartRequested: false
    property bool started: false
    property bool ready: false
    property bool disposing: false
    readonly property bool fresh: lastSampleAt > 0 && clock - lastSampleAt < Math.max(3500, Number(snapshot ? snapshot.intervalSeconds : 1) * 4000)
    readonly property string statusText: !active ? "STANDBY" : backendError ? (fresh ? "PARTIAL" : "RECONNECTING") : fresh ? "LIVE" : lastSampleAt ? "STALE" : "ACQUIRING"
    readonly property int helperPid: sampler.processId || 0
    signal received(var frame)
    signal detailReceived(var frame)
    signal freezeReceived(var frame)
    signal scopeReceived(var frame)

    function helperEnvironment() {
        var env = {
            PATH: "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
            LC_ALL: "C",
            PYTHONNOUSERSITE: "1"
        }
        var pass = ["HOME","USER","LOGNAME","XDG_RUNTIME_DIR","DBUS_SESSION_BUS_ADDRESS",
                    "WAYLAND_DISPLAY","DISPLAY","XDG_SESSION_TYPE","PIPEWIRE_REMOTE","LANG","TZ"]
        pass.forEach(function(key) {
            var value = Quickshell.env(key)
            if (value !== null && value !== undefined && String(value).length) env[key] = String(value)
        })
        return env
    }
    function terminateSampler() {
        if (!sampler.running) return
        sampler.signal(15)
        terminationWatch.restart()
    }

    function start() {
        if (disposing || !active || !pluginDir || sampler.running || restart.running) return
        intentionalStop = false
        restartRequested = false
        terminationWatch.stop()
        started = false
        ready = false
        sampler.running = true
        startupWatch.restart()
    }
    function stop() {
        intentionalStop = true
        restartRequested = false
        restart.stop()
        startupWatch.stop()
        firstFrameWatch.stop()
        ready = false
        started = false
        if (sampler.running) terminateSampler()
        snapshot = null
        detail = null
        lastSampleAt = 0
        failures = 0
        goodFrames = 0
        invalidFrames = 0
        backendError = ""
    }
    function restartBackend(message) {
        if (disposing || !active) return
        if (failures >= 6) {
            backendError = "Telemetry stopped after six retries. Run doctor or press Retry."
            ready = false
            started = false
            goodFrames = 0
            invalidFrames = 0
            firstFrameWatch.stop()
            restartRequested = false
            if (sampler.running) terminateSampler()
            return
        }
        backendError = message
        ready = false
        started = false
        goodFrames = 0
        invalidFrames = 0
        firstFrameWatch.stop()
        failures++
        restartRequested = true
        if (sampler.running) terminateSampler()
        else {
            restartRequested = false
            restart.restart()
        }
    }
    function retry() {
        failures = 0
        restart.stop()
        if (sampler.running || started) restartBackend("Telemetry restart requested")
        else start()
    }
    function send(command) {
        if (started && sampler.running && active) sampler.write(JSON.stringify(command) + "\n")
    }
    function configure() {
        var c = configuration || {}
        send({op:"configure",instrument:instrument,profile:c.refreshProfile || "balanced",naming:c.naming || "local",
              privacy:c.privacy === true,aliases:c.aliases || {},offlineDb:c.offlineDb || "",audioActions:c.audioActions === true})
    }
    function sendScope(frozen) { send({op:"scope",instanceGroups:instanceGroups,frozen:frozen === true}) }
    function setInstanceGroups(groups, frozen) {
        var clean = [], seen = {}
        if (Array.isArray(groups)) groups.slice(0,64).forEach(function(key) {
            key = String(key || "").slice(0,512)
            if (key.indexOf("application:") === 0 && !seen[key]) { seen[key] = true; clean.push(key) }
        })
        clean.sort()
        var scopeKey = JSON.stringify(clean) + ":" + (frozen === true ? "frozen" : "live")
        instanceGroups = clean
        if (scopeKey === instanceScopeKey) return
        instanceScopeKey = scopeKey
        sendScope(frozen)
    }
    function inspect(key, offset, frozen) { send({op:"inspect",key:key,offset:offset || 0,limit:24,frozen:frozen === true}) }
    function freeze(value) { var id=++freezeSequence; send({op:"freeze",state:value,requestId:id}); return id }
    function audioAction(action, key, value) {
        send({op:"audio-action",action:action,key:key,value:value,confirmed:true})
    }
    function accept(line) {
        if (!active || disposing) return
        if (line.length > 4194304) { backendError = "Oversized telemetry record rejected"; invalidFrames++; if (invalidFrames >= 3) restartBackend("Repeated oversized telemetry; restarting helper"); return }
        try {
            var frame = JSON.parse(line)
            if (!frame || typeof frame !== "object") throw new Error("Expected object")
            if (frame.type === "snapshot") {
                var problem = Protocol.validateSnapshot(frame)
                if (problem) throw new Error(problem)
                root.ready = true
                firstFrameWatch.stop()
                snapshot = frame
                clock = Date.now()
                lastSampleAt = clock
                goodFrames++
                invalidFrames = 0
                if (goodFrames >= 3) failures = 0
                backendError = ""
                received(frame)
            } else if (frame.type === "freeze-result") {
                if (typeof frame.frozen!=="boolean" || typeof frame.requestId!=="number" || frame.frozen && Protocol.validateSnapshot(frame.snapshot)) throw new Error("Invalid frozen snapshot")
                freezeReceived(frame)
            } else if (frame.type === "scope-result") {
                if (frame.frozen !== true || Protocol.validateSnapshot(frame.snapshot)) throw new Error("Invalid scope response")
                scopeReceived(frame)
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
            invalidFrames++
            backendError = "Invalid telemetry record rejected: " + String(error).slice(0,180)
            if (invalidFrames >= 3) restartBackend("Repeated invalid telemetry; restarting helper")
        }
    }
    onActiveChanged: { if (active) { clock = Date.now(); start() } else stop() }
    onPluginDirChanged: if (active) start()
    onInstrumentChanged: configure()
    onConfigurationChanged: configure()

    Process {
        id: sampler
        command: ["/usr/bin/python3", "-B", "-u", root.pluginDir + "/scripts/telemetry.py", "--instrument", root.instrument]
        workingDirectory: root.pluginDir
        clearEnvironment: true
        environment: root.helperEnvironment()
        stdinEnabled: true
        running: false
        stdout: SplitParser { onRead: line => root.accept(String(line)) }
        stderr: SplitParser {
            onRead: line => { if (root.active) root.backendError = "Helper: " + String(line).slice(0,200) }
        }
        onStarted: {
            root.started = true
            root.ready = false
            startupWatch.stop()
            firstFrameWatch.restart()
            root.configure()
            root.sendScope(false)
        }
        onExited: (exitCode, exitStatus) => {
            root.started = false
            root.ready = false
            startupWatch.stop()
            firstFrameWatch.stop()
            terminationWatch.stop()
            if (root.restartRequested) {
                root.restartRequested = false
                if (root.active && !root.disposing && root.failures <= 6) restart.restart()
                return
            }
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
        id: terminationWatch
        interval: 1200
        onTriggered: { if (sampler.running) sampler.signal(9) }
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
            if (root.active && !root.started) root.restartBackend("Helper process did not start; restarting")
        }
    }
    Timer {
        id: firstFrameWatch
        interval: 5000
        onTriggered: {
            if (root.active && root.started && !root.ready) root.restartBackend("Helper started but produced no valid telemetry; restarting")
        }
    }
    Timer {
        id: healthWatch
        interval: 1000
        repeat: true
        running: root.active && root.started
        onTriggered: {
            root.clock = Date.now()
            if (root.ready && root.lastSampleAt > 0 && root.clock - root.lastSampleAt > Math.max(7000, Number(root.snapshot ? root.snapshot.intervalSeconds : 1) * 6000))
                root.restartBackend("Telemetry stopped advancing; restarting helper")
        }
    }
    Timer { interval: 500; repeat: true; running: root.active; onTriggered: root.clock = Date.now() }
    Component.onDestruction: {
        disposing = true
        intentionalStop = true
        restart.stop(); startupWatch.stop(); firstFrameWatch.stop(); terminationWatch.stop()
        if (sampler.running) sampler.signal(9)
    }
}
