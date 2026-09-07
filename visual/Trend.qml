pragma ComponentBehavior: Bound
import QtQuick
import qs.Commons
import "../model/InstrumentModel.js" as Instruments

Item {
    id: root
    required property var theme
    property var samples: []
    property string selectedKey: "subsystem:cpu"
    readonly property var series: selectedKey === "subsystem:memory" ? [{key:"memoryUsedBytes",name:"Used memory",role:"accent"}] : selectedKey === "subsystem:storage" ? [{key:"readBps",name:"Read",role:"read"},{key:"writeBps",name:"Write",role:"write"}] : selectedKey === "subsystem:network" ? [{key:"netRxBps",name:"Receive",role:"inbound"},{key:"netTxBps",name:"Transmit",role:"outbound"}] : [{key:"cpuPercent",name:"CPU",role:"accent"}]
    readonly property bool rate: selectedKey === "subsystem:storage" || selectedKey === "subsystem:network"
    readonly property bool percent: series[0].key === "cpuPercent"
    readonly property real ceiling: {
        var maxValue = percent ? 100 : 0
        for (var i=0;i<samples.length;i++) for (var j=0;j<series.length;j++) {
            var v=samples[i][series[j].key]
            if (typeof v === "number" && isFinite(v)) maxValue=Math.max(maxValue,v)
        }
        return maxValue || 1
    }
    Rectangle { anchors.fill: parent; color: root.theme.colors.panel; radius: Style.cornerRadius }
    Row {
        id: legend
        x: Style.spacing.xxl; y: Style.spacing.lg; spacing: Style.spacing.huge
        Repeater {
            model: root.series
            delegate: Text {
                required property var modelData
                text: modelData.name + (root.samples.length ? ": " + (root.percent ? Instruments.percent(root.samples[root.samples.length-1][modelData.key]) : Instruments.bytes(root.samples[root.samples.length-1][modelData.key],root.rate)) : ": awaiting samples")
                textFormat: Text.PlainText
                color: root.theme.colors[modelData.role]
                font.family: root.theme.fontFamily
                font.pixelSize: root.theme.smallSize
            }
        }
    }
    Text { anchors.right: parent.right; anchors.top: parent.top; anchors.margins: Style.spacing.lg; text: "Last 60 seconds"; textFormat: Text.PlainText; color: root.theme.colors.subdued; font.family: root.theme.fontFamily; font.pixelSize: root.theme.smallSize; visible: root.width > Style.space(570) }
    Canvas {
        id: trace
        anchors.fill: parent
        anchors.leftMargin: Style.spacing.xxl; anchors.rightMargin: Style.spacing.xxl; anchors.topMargin: legend.height+Style.spacing.huge; anchors.bottomMargin: Style.spacing.xl
        antialiasing: true
        onPaint: {
            var c=getContext("2d")
            c.clearRect(0,0,width,height)
            c.strokeStyle=root.theme.colors.line; c.lineWidth=Style.spacing.hairline
            c.beginPath();c.moveTo(0,height-1);c.lineTo(width,height-1);c.stroke()
            if (!root.samples.length) return
            var end=root.samples[root.samples.length-1].at
            for (var j=0;j<root.series.length;j++) {
                c.strokeStyle=root.theme.colors[root.series[j].role];c.lineWidth=j===0?Style.space(2):Style.spacing.hairline
                c.beginPath();var started=false
                for (var i=0;i<root.samples.length;i++) {
                    var s=root.samples[i],v=s[root.series[j].key]
                    if (typeof v!=="number" || !isFinite(v) || end-s.at>60) {started=false;continue}
                    var x=width*(1-(end-s.at)/60),y=height-3-Math.max(0,v)/root.ceiling*(height-6)
                    if (!started) c.moveTo(x,y); else c.lineTo(x,y)
                    started=true
                }
                c.stroke()
            }
        }
        onWidthChanged: requestPaint()
        onHeightChanged: requestPaint()
    }
    onSamplesChanged: trace.requestPaint()
    onSeriesChanged: trace.requestPaint()
    Connections { target: root.theme; function onColorsChanged() { trace.requestPaint() } }
}