pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import qs.Commons
import "../core"
import "../model/Operator.js" as Operator
import "TrendModel.js" as TrendModel

FocusScope {
    id: root
    required property var theme
    property var samples: []
    property string selectedKey: "subsystem:cpu"
    property real intervalSeconds: 1
    property int windowSeconds: 60
    property string metric: "usage"
    property var cursorAt: null
    property bool cursorLocked: false
    readonly property bool pressureAvailable: ["subsystem:cpu","subsystem:memory","subsystem:storage"].indexOf(selectedKey)>=0
    readonly property var plot: TrendModel.build(samples,selectedKey,{seconds:windowSeconds,metric:metric,interval:intervalSeconds,width:trace.width,height:trace.height})
    readonly property var inspection: TrendModel.inspect(plot,cursorAt)
    readonly property string summary: {
        return plot.traces.map(function(t,index) { return root.describeTrace(t,index) }).join("    ")
    }
    function describeTrace(t,index) {
        var value = root.inspection ? root.inspection.values[index].value : t.stats.current
        return (t.dashed ? "┄ " : "━ ")+t.name+": "+Operator.format(value,root.plot.unit)+
            "  ["+Operator.format(t.stats.min,root.plot.unit)+"–"+Operator.format(t.stats.max,root.plot.unit)+"]"
    }
    activeFocusOnTab: visible
    Accessible.role: Accessible.Chart
    Accessible.name: (metric === "pressure" ? "Stall pressure trend. " : "Resource trend. ")+summary
    Accessible.description: "Left and Right inspect measured samples. Home and End jump to first and last. Space returns to live. Brackets show measured minimum and maximum."
    function resume() { cursorAt=null; cursorLocked=false }
    Keys.onPressed: event => {
        if (event.modifiers & (Qt.ControlModifier | Qt.AltModifier | Qt.MetaModifier)) return
        if (event.key === Qt.Key_Left || event.key === Qt.Key_Right) {
            cursorAt=TrendModel.step(plot,cursorAt,event.key === Qt.Key_Left ? -1 : 1)
            cursorLocked=true
        } else if (event.key === Qt.Key_Home || event.key === Qt.Key_End) {
            cursorAt=plot.samples.length ? plot.samples[event.key === Qt.Key_Home ? 0 : plot.samples.length-1].at : null
            cursorLocked=true
        } else if (event.key === Qt.Key_Space) resume()
        else return
        event.accepted=true
    }
    Rectangle { anchors.fill: parent; color: root.theme.colors.panel; radius: Style.cornerRadius; border.color: root.activeFocus ? root.theme.colors.accent : root.theme.colors.line; border.width: Style.spacing.hairline }
    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Style.spacing.lg
        spacing: Style.spacing.sm
        RowLayout {
            Layout.fillWidth: true
            spacing: Style.spacing.sm
            Repeater {
                model: [15,30,60]
                delegate: InstrumentButton {
                    required property int modelData
                    text: modelData+"s"
                    chosen: root.windowSeconds === modelData
                    paletteColors: root.theme.colors; fontFamily: root.theme.fontFamily; textSize: root.theme.smallSize
                    onClicked: { root.windowSeconds=modelData; root.resume() }
                }
            }
            InstrumentButton {
                visible: root.pressureAvailable
                text: root.metric === "pressure" ? "PSI avg10" : "Usage"
                hint: "Toggle usage and measured stall pressure. Some / all non-idle tasks use separate traces."
                chosen: root.metric === "pressure"
                paletteColors: root.theme.colors; fontFamily: root.theme.fontFamily; textSize: root.theme.smallSize
                onClicked: { root.metric=root.metric === "pressure" ? "usage" : "pressure"; root.resume() }
            }
            Item { Layout.fillWidth: true }
            InstrumentButton {
                text: root.cursorLocked ? "Return to live" : "Inspect ← →"
                hint: "Click to focus chart; Left/Right, Home/End inspect samples; Space returns to live"
                paletteColors: root.theme.colors; fontFamily: root.theme.fontFamily; textSize: root.theme.smallSize
                onClicked: { root.resume(); root.forceActiveFocus() }
            }
        }
        ColumnLayout {
            Layout.fillWidth: true
            spacing: 0
            Repeater {
                model: root.plot.traces
                delegate: Text {
                    required property var modelData
                    required property int index
                    objectName: "trendSummary"+index
                    Layout.fillWidth: true
                    text: root.describeTrace(modelData,index)
                    textFormat: Text.PlainText
                    wrapMode: Text.Wrap
                    color: root.theme.colors.foreground
                    font.family: root.theme.fontFamily; font.pixelSize: root.theme.smallSize
                }
            }
        }
        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: Style.spacing.md
            ColumnLayout {
                Layout.fillHeight: true
                Text { text: Operator.format(root.plot.ceiling,root.plot.unit); textFormat: Text.PlainText; color: root.theme.colors.subdued; font.family: root.theme.fontFamily; font.pixelSize: root.theme.smallSize }
                Item { Layout.fillHeight: true }
                Text { text: "0"; textFormat: Text.PlainText; color: root.theme.colors.subdued; font.family: root.theme.fontFamily; font.pixelSize: root.theme.smallSize }
            }
            Canvas {
                id: trace
                Layout.fillWidth: true
                Layout.fillHeight: true
                antialiasing: true
                onPaint: {
                    var c=getContext("2d"), plot=root.plot
                    c.clearRect(0,0,width,height)
                    c.lineWidth=1; c.strokeStyle=root.theme.colors.line; c.setLineDash([])
                    for (var level=0;level<=2;level++) {
                        var y=Math.max(1,Math.min(height-1,height*level/2))
                        c.beginPath(); c.moveTo(0,y); c.lineTo(width,y); c.stroke()
                    }
                    for (var j=0;j<plot.traces.length;j++) {
                        var t=plot.traces[j]
                        c.strokeStyle=root.theme.colors[t.role]; c.fillStyle=root.theme.colors[t.role]; c.lineWidth=2
                        c.setLineDash(t.dashed ? [5,4] : [])
                        for (var k=0;k<t.paths.length;k++) {
                            var path=t.paths[k]
                            c.beginPath()
                            for (var i=0;i<path.length;i++) {
                                var p=path[i], py=Math.max(1,Math.min(height-1,p.y))
                                if (i===0) c.moveTo(p.x,py); else c.lineTo(p.x,py)
                            }
                            c.stroke()
                            if (path.length===1) {c.beginPath();c.arc(path[0].x,Math.max(2,Math.min(height-2,path[0].y)),2,0,Math.PI*2);c.fill()}
                        }
                    }
                    c.setLineDash([])
                    if (root.inspection) {
                        c.strokeStyle=root.theme.colors.foreground; c.lineWidth=1
                        c.beginPath(); c.moveTo(root.inspection.x,0); c.lineTo(root.inspection.x,height); c.stroke()
                    }
                }
                MouseArea {
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.CrossCursor
                    onPositionChanged: mouse => { if (!root.cursorLocked || pressed) root.cursorAt=root.plot.start+mouse.x/Math.max(1,width)*root.plot.seconds }
                    onClicked: mouse => { root.cursorAt=root.plot.start+mouse.x/Math.max(1,width)*root.plot.seconds; root.cursorLocked=true; root.forceActiveFocus() }
                    onExited: if (!root.cursorLocked) root.cursorAt=null
                }
            }
        }
        Text {
            Layout.fillWidth: true
            text: root.cursorAt !== null ? root.inspection ? "Measured "+Math.max(0,root.plot.end-root.inspection.at).toFixed(1)+"s ago · "+(root.cursorLocked ? "cursor held" : "hover") : "No observed sample at cursor · acquisition gap or expired window" : "−"+root.windowSeconds+"s → latest · hover or click to inspect · gaps mean no observation"
            textFormat: Text.PlainText; elide: Text.ElideRight
            color: root.theme.colors.subdued; font.family: root.theme.fontFamily; font.pixelSize: root.theme.smallSize
        }
    }
    onPlotChanged: trace.requestPaint()
    onInspectionChanged: trace.requestPaint()
    onSelectedKeyChanged: { if (!pressureAvailable) metric="usage"; resume() }
    Connections { target: root.theme; function onColorsChanged() { trace.requestPaint() } }
}
