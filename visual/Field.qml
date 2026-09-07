pragma ComponentBehavior: Bound
import QtQuick
import "Layout.js" as Layout
import "Draw.js" as Draw

Item {
    id: root
    required property var view
    required property var theme
    property string focusKey: ""
    property string labelDensity: "balanced"
    property string animation: "normal"
    property bool active: true
    property var scene: ({nodes:[],edges:[],labels:[],positions:{},omittedNodes:0,omittedEdges:0,width:1,height:1,instrument:"connection"})
    property var caches: ({})
    property bool disposing: false
    property double layoutDurationMs: 0
    signal picked(string key)
    signal focused(string key)
    signal hovered(string key)
    readonly property int hiddenCount: scene.omittedNodes || 0
    clip: true

    FontMetrics { id: metrics; font.family: root.theme.fontFamily; font.pixelSize: root.theme.bodySize }
    ListModel { id: nodeItems; dynamicRoles: true }
    ListModel { id: labelItems; dynamicRoles: true }

    function sync(model, records) {
        var target = {}
        for (var i=0;i<records.length;i++) target[records[i].idKey] = true
        for (var k=model.count-1;k>=0;k--) if (!target[model.get(k).idKey]) model.remove(k)
        for (var index=0;index<records.length;index++) {
            var at = -1
            for (var j=index;j<model.count;j++) if (model.get(j).idKey === records[index].idKey) { at = j; break }
            if (at < 0) model.insert(index,records[index])
            else {
                if (at !== index) model.move(at,index,1)
                var r=records[index]
                Object.keys(r).forEach(function(key){ if (model.get(index)[key] !== r[key]) model.setProperty(index,key,r[key]) })
            }
        }
    }
    function relayout() {
        if (disposing || !active || !view || width < 240 || height < 180) return
        var start=Date.now()
        var mode=view.instrument
        var output=Layout.layout(view,width,height,{labels:labelDensity,fontSize:theme.bodySize,smallSize:theme.smallSize,focusKey:focusKey},caches[mode] || {},function(t){return metrics.advanceWidth(t)})
        var updated=Object.assign({},caches)
        updated[mode]=output.positions
        caches=updated
        scene=output
        sync(nodeItems,output.nodes.map(function(n){return {idKey:n.key,px:n.x,py:n.y,nodeName:n.name,subtitle:n.subtitle,
            emphasized:n.selected||n.focused,nodeOpacity:n.opacity,acquired:n.event === "opened",eventAge:Number(n.raw.eventAgeMs||0)};}))
        sync(labelItems,output.labels.map(function(l){return {idKey:l.key,px:l.x,py:l.y,boxWidth:l.w,boxHeight:l.h,caption:l.text,secondary:l.secondary,
            emphasized:l.selected,labelOpacity:l.opacity};}))
        layoutDurationMs=Date.now()-start
        fieldCanvas.requestPaint()
    }
    function schedule() { if (!disposing && active) updateTimer.restart() }
    onViewChanged: schedule()
    onWidthChanged: schedule()
    onHeightChanged: schedule()
    onFocusKeyChanged: schedule()
    onLabelDensityChanged: schedule()
    onThemeChanged: schedule()
    onActiveChanged: { if (active) schedule(); else updateTimer.stop() }
    Timer { id: updateTimer; interval: 0; onTriggered: root.relayout() }
    Connections { target: root.theme; function onColorsChanged() { fieldCanvas.requestPaint() }
        function onFontFamilyChanged() { root.schedule() }
        function onBodySizeChanged() { root.schedule() }
        function onSmallSizeChanged() { root.schedule() } }

    Canvas {
        id: fieldCanvas
        anchors.fill: parent
        antialiasing: true
        onPaint: {
            if (!root.active || root.disposing || !root.scene.width) return
            var colors=Object.assign({},root.theme.colors)
            colors.fontFamily=root.theme.fontFamily
            Draw.draw(getContext("2d"),root.scene,colors)
        }
    }
    MouseArea {
        anchors.fill: parent
        onClicked: mouse => {
            var best=null,dist=10
            for(var i=0;i<root.scene.edges.length;i++) {
                var e=root.scene.edges[i],curve=Draw.curve(e,root.scene.instrument)
                for(var step=1;step<24;step++) {
                    var p=Draw.bezier(curve,step/24),dx=mouse.x-p[0],dy=mouse.y-p[1],d=Math.sqrt(dx*dx+dy*dy)
                    if(d<dist){dist=d;best=e.key;}
                }
            }
            if(best)root.picked(best)
        }
    }
    Repeater {
        model: nodeItems
        delegate: Item {
            id: hit
            required property string idKey
            required property real px
            required property real py
            required property string nodeName
            required property string subtitle
            required property bool emphasized
            required property real nodeOpacity
            required property bool acquired
            required property real eventAge
            x: px-20; y: py-20; width: 40; height: 40
            Accessible.role: Accessible.Button
            Accessible.name: nodeName
            Accessible.description: subtitle
            Accessible.onPressAction: root.picked(hit.idKey)
            Rectangle {
                anchors.centerIn: parent
                width: 31; height: 31; radius: 16
                color: "transparent"
                border.color: root.theme.colors.newly
                border.width: 1
                opacity: hit.acquired ? Math.max(0,0.7-hit.eventAge/4000) * hit.nodeOpacity : 0
                Behavior on opacity { NumberAnimation { duration: root.animation === "reduced" ? 0 : 380 } }
            }
            MouseArea {
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onEntered: root.hovered(hit.idKey)
                onExited: root.hovered("")
                onClicked: root.picked(hit.idKey)
                onDoubleClicked: root.focused(hit.idKey)
            }
        }
    }
    Repeater {
        model: labelItems
        delegate: Rectangle {
            id: label
            required property string idKey
            required property real px
            required property real py
            required property real boxWidth
            required property real boxHeight
            required property string caption
            required property string secondary
            required property bool emphasized
            required property real labelOpacity
            x: px; y: py; width: boxWidth; height: boxHeight
            opacity: labelOpacity
            color: root.theme.colors.background
            radius: 3
            border.width: emphasized ? 1 : 0
            border.color: root.theme.colors.accent
            Column {
                x: 7; y: 4; width: label.width-14; spacing: 3
                Text { width: parent.width; text: label.caption; textFormat: Text.PlainText; color: root.theme.colors.foreground; font.family: root.theme.fontFamily; font.pixelSize: root.theme.bodySize; font.weight: label.emphasized ? Font.DemiBold : Font.Normal; elide: Text.ElideRight }
                Text { width: parent.width; visible: label.secondary.length > 0; text: label.secondary; textFormat: Text.PlainText; color: root.theme.colors.subdued; font.family: root.theme.fontFamily; font.pixelSize: root.theme.smallSize; elide: Text.ElideRight }
            }
            MouseArea {
                anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor
                onEntered: root.hovered(label.idKey)
                onExited: root.hovered("")
                onClicked: root.picked(label.idKey)
                onDoubleClicked: root.focused(label.idKey)
            }
        }
    }
    Component.onCompleted: schedule()
    Component.onDestruction: { disposing = true; updateTimer.stop(); caches = ({}) }
}
