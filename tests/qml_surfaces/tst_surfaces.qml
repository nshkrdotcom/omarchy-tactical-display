import QtQuick
import QtTest
import qs.Commons
import "../../core"
import "../../visual"
import "../../model/Settings.js" as Settings

TestCase {
    id: suite
    name: "OperatorSurfaces"
    when: windowShown
    visible: true
    width: 900; height: 640
    QtObject {
        id: testTheme
        property var colors: ({background:"#07101a",panel:"#122333",plane:"#183348",foreground:"#ffffff",subdued:"#bdcddd",accent:"#8fcaff",warning:"#ffe0a0",critical:"#ffaaaa",line:"#567890",newly:"#8fcaff",read:"#aaffdd",write:"#ffdddd",inbound:"#aaffdd",outbound:"#ffdddd"})
        property string fontFamily: "monospace"
        property int smallSize: 13
        property int bodySize: 16
        property int titleSize: 22
    }
    NavigationController { id: controller }
    ThemeAdapter { id: hostTheme }
    Component { id: sheetComponent; OperatorSheet { controller: suite.subject; theme: testTheme } }
    Component { id: trendComponent; Trend { theme: testTheme } }
    Component { id: buttonComponent; InstrumentButton { paletteColors: testTheme.colors; chosen: true; text: "Selected choice" } }
    Component { id: shellComponent; TacticalDisplayShell { controller: suite.subject; theme: testTheme } }
    Component {
        id: fieldComponent
        Field {
            theme: hostTheme
            view: ({instrument:"machine",visibleNodes:[{key:"subsystem:cpu",kind:"subsystem",zone:"compute",name:"COMPUTE",subtitle:"CPU stall pressure",priority:1,related:true,match:true,raw:{}}],edges:[]})
        }
    }
    readonly property var subject: controller
    function descendants(item) {
        var result=[]
        for(var i=0;i<item.children.length;i++) {
            result.push(item.children[i])
            result=result.concat(descendants(item.children[i]))
        }
        return result
    }
    function textItem(item,text) {
        return descendants(item).filter(function(child){return child.text===text})[0]
    }
    function init() {
        controller.close()
        controller.open(Settings.payload('{"instrument":"machine"}'))
    }
    function test_shared_theme_uses_native_popup_tokens_and_tracks_changes() {
        var oldFont=Style.font,oldPopups=Color.popups
        try {
            compare(hostTheme.baseBackground,Color.popups.background)
            compare(hostTheme.baseForeground,Color.popups.text)
            compare(hostTheme.fontFamily,Style.font.family)
            compare(hostTheme.smallSize,Style.font.caption)
            compare(hostTheme.bodySize,Style.font.body)
            compare(hostTheme.titleSize,Style.font.title)
            Style.font={family:"serif",caption:16,body:20,subtitle:22,title:28}
            Color.popups={background:"#ffffff",text:"#111111",border:"#334488"}
            compare(hostTheme.fontFamily,"serif")
            compare(hostTheme.smallSize,16)
            compare(hostTheme.bodySize,20)
            compare(hostTheme.titleSize,28)
            compare(hostTheme.baseBackground,"#ffffff")
            verify(hostTheme.colors.light,"A live popup-theme change must update both surfaces")
        } finally { Style.font=oldFont;Color.popups=oldPopups }
    }
    function test_shared_header_preserves_native_geometry_data() {
        return [{tag:"compact",surfaceWidth:900,surfaceHeight:640},
            {tag:"wide",surfaceWidth:1260,surfaceHeight:740},
            {tag:"large-monitor",surfaceWidth:1900,surfaceHeight:1040},
            {tag:"native-small-type",surfaceWidth:1260,surfaceHeight:740,font:{family:"monospace",caption:10,body:12,subtitle:13,title:15}},
            {tag:"larger-host-type",surfaceWidth:1260,surfaceHeight:740,font:{family:"monospace",caption:20,body:24,subtitle:26,title:30}}]
    }
    function test_caption_token_change_relayouts_unchanged_field() {
        var oldFont=Style.font
        try {
            var f=createTemporaryObject(fieldComponent,suite,{width:900,height:520})
            verify(f)
            tryVerify(function(){return f.scene.labels.length===1})
            var originalView=f.view,oldHeight=f.scene.labels[0].h,position=f.scene.nodes[0]
            Style.font=Object.assign({},Style.font,{caption:Style.font.caption+12})
            tryVerify(function(){return f.scene.labels[0].h===oldHeight+12},1000,
                "Frozen/unchanged data must still reflow labels when the host caption token changes")
            compare(f.view,originalView,"A theme change must not mutate observation data")
            compare(f.scene.labels[0].key,"subsystem:cpu")
            compare(f.scene.nodes[0].x,position.x)
            compare(f.scene.nodes[0].y,position.y)
            f.active=false
            Style.font=oldFont
            wait(20)
            compare(f.scene.labels[0].h,oldHeight+12,"Inactive fields must not schedule rendering work")
            f.active=true
            tryVerify(function(){return f.scene.labels[0].h===oldHeight})
        } finally { Style.font=oldFont }
    }
    function test_shared_header_preserves_native_geometry(data) {
        var oldFont=Style.font
        try {
            if(data.font)Style.font=data.font
            checkSharedHeader(data)
        } finally { Style.font=oldFont }
    }
    function checkSharedHeader(data) {
        controller.setFlag("showIntro",false)
        controller.setFlag("showPicker",false)
        var s=createTemporaryObject(shellComponent,suite,{width:data.surfaceWidth,height:data.surfaceHeight,theme:hostTheme})
        verify(s)
        wait(0)
        var title=textItem(s,"TACTICAL DISPLAY"),search=textItem(s,"/ Search"),close=textItem(s,"Close")
        verify(title && search && close)
        compare(title.font.pixelSize,Style.font.subtitle,"Both hosts must retain the clicked panel's main title size")
        compare(title.font.family,Style.font.family)
        fuzzyCompare(title.font.letterSpacing,0.4,1/64) // Qt quantizes font metrics.
        compare(title.mapToItem(s,0,0).x,0,"Host containers own outer padding; shared content must not add a second inset")
        compare(title.mapToItem(s,0,0).y,0)
        var status=findChild(s,"providerStatus")
        compare(status.font.pixelSize,Style.font.caption)
        var rail=search.parent,header=rail.parent
        compare(header.spacing,Style.spacing.huge)
        compare(rail.spacing,Style.spacing.sm)
        compare(rail.mapToItem(s,rail.width,0).x,s.width,"Action rail keeps its native right edge")
        fuzzyCompare(rail.mapToItem(s,0,rail.height/2).y,header.height/2,0.5)
        var actions=rail.children.filter(function(item){return item.visible && item.text!==undefined})
        compare(actions.map(function(item){return item.text}).join("|"),data.surfaceWidth<1050?"/ Search|Freeze|Close":"/ Search|Freeze|Legend|Settings|Close")
        actions.forEach(function(action){
            compare(action.textSize,Style.font.caption)
            compare(action.leftPadding,Style.spacing.controlPaddingX)
            compare(action.topPadding,Style.spacing.controlPaddingY)
            verify(action.mapToItem(s,0,0).x>=title.width,"Title and actions must not overlap")
        })
        var selector=textItem(s,"A Briefing").parent
        compare(selector.mapToItem(s,0,0).y,header.height+Style.spacing.xxl,"No overlay-only purpose row or spacing before navigation")
    }
    function test_chosen_control_keeps_visible_keyboard_focus() {
        var b=createTemporaryObject(buttonComponent,suite,{width:180,height:40})
        b.forceActiveFocus(); tryVerify(function(){return b.activeFocus})
        verify(b.background.border.width>0,"A selected button must still show a focus outline")
    }
    function test_status_is_keyboard_operable() {
        controller.setFlag("showIntro",false)
        controller.setFlag("showPicker",false)
        var s=createTemporaryObject(shellComponent,suite,{width:900,height:640})
        verify(s)
        wait(0)
        var status=findChild(s,"providerStatus")
        verify(status,"Provider status is a discoverable native control")
        verify(status.activeFocusOnTab,"Provider status participates in control navigation")
        status.forceActiveFocus(); tryCompare(status,"activeFocus",true)
        keyClick(Qt.Key_Return,Qt.ControlModifier)
        verify(!controller.navState.showCapabilities,"Command-modified keys belong to the focused control")
        keyClick(Qt.Key_Return)
        tryVerify(function(){return controller.navState.showCapabilities})
    }
    function test_trend_keyboard_cursor_and_live_return() {
        var t=createTemporaryObject(trendComponent,suite,{width:850,height:200})
        verify(t)
        // Production frames arrive via JSON.parse, not a QVariantMap initializer.
        t.samples=JSON.parse('[{"at":1,"cpuPercent":10},{"at":2,"cpuPercent":20},{"at":3,"cpuPercent":30}]')
        compare(t.plot.samples.length,3)
        t.forceActiveFocus(); tryCompare(t,"activeFocus",true)
        keyClick(Qt.Key_Left); compare(t.cursorAt,3)
        keyClick(Qt.Key_Left); compare(t.cursorAt,2); compare(t.inspection.values[0].value,20)
        keyClick(Qt.Key_Home); compare(t.cursorAt,1)
        keyClick(Qt.Key_End); compare(t.cursorAt,3)
        keyClick(Qt.Key_Space); compare(t.cursorAt,null); verify(!t.cursorLocked)
    }
    function test_paired_trend_labels_stay_readable_at_compact_width() {
        var t=createTemporaryObject(trendComponent,suite,{width:440,height:200,selectedKey:"subsystem:storage"})
        t.samples=JSON.parse('[{"at":1,"readBps":16384,"writeBps":8192},{"at":2,"readBps":32768,"writeBps":4096}]')
        tryVerify(function(){
            var read=findChild(t,"trendSummary0"),write=findChild(t,"trendSummary1")
            return read && write && read.width>0 && write.width>0 &&
                read.text.indexOf("Read:")>=0 && write.text.indexOf("Write:")>=0 &&
                !read.truncated && !write.truncated &&
                read.mapToItem(t,0,0).y+read.height<=write.mapToItem(t,0,0).y
        },1000,"Both paired legends fit at compact width without clipping or overlap")
    }
    function test_briefing_scroll_focus_and_narrow_geometry() {
        var s=createTemporaryObject(sheetComponent,suite,{width:480,height:430})
        verify(s)
        var scroll=findChild(s,"briefingScroll")
        verify(scroll,"Briefing exposes its scroll surface for interaction tests")
        s.section="activity"
        var events=[]
        for(var i=0;i<120;i++)events.push({key:"event:"+i,entityKey:"process:"+i,kind:"opened",domain:"process",instrument:"processes",entityKind:"process",name:"Observed process "+i,at:1000-i})
        controller.operatorSession={at:1000,sequence:1,events:events,seen:[]}
        tryVerify(function(){return scroll.contentHeight>scroll.height})
        var last=findChild(s,"activityRow119")
        verify(last)
        compare(last.contentItem.horizontalAlignment,Text.AlignLeft,"Timeline labels have a consistent reading edge")
        last.forceActiveFocus()
        tryVerify(function(){return scroll.contentItem.contentY>0})
        var top=last.mapToItem(scroll,0,0).y
        verify(top>=0 && top+last.height<=scroll.height+2,"Keyboard focus must reveal the event")
        var header=findChild(s,"briefingHeader")
        verify(header.width<=s.width-20,"Narrow briefing must not clip its header")
    }
    function test_activity_focus_survives_live_refresh() {
        var s=createTemporaryObject(sheetComponent,suite,{width:850,height:540})
        s.section="activity"
        controller.operatorSession={at:1000,sequence:1,events:[{key:"event:first",entityKey:"process:1",kind:"opened",domain:"process",instrument:"processes",entityKind:"process",name:"First process",at:999}],seen:[]}
        var row=findChild(s,"activityRow0")
        verify(row); row.forceActiveFocus(); tryCompare(row,"activeFocus",true)
        controller.operatorSession={at:1001,sequence:2,events:[{key:"event:first",entityKey:"process:1",kind:"opened",domain:"process",instrument:"processes",entityKind:"process",name:"First process",at:999}],seen:[]}
        compare(findChild(s,"activityRow0"),row,"Refresh must update the existing delegate")
        verify(row.activeFocus,"Live sample must preserve operator keyboard focus")
    }
    function test_briefing_large_type_preserves_header_actions() {
        var small=testTheme.smallSize,body=testTheme.bodySize
        try {
            testTheme.smallSize=20; testTheme.bodySize=24
            var s=createTemporaryObject(sheetComponent,suite,{width:480,height:430})
            tryVerify(function(){
                var title=findChild(s,"briefingTitle")
                return title.paintedWidth<=title.width+0.5 && ["briefingFreeze","briefingCopy","briefingBack"].every(function(name){
                    var item=findChild(s,name),p=item.mapToItem(s,0,0)
                    return p.x>=12 && p.x+item.width<=s.width-12
                })
            },1000,"Large native typography must not push actions past the sheet edge")
        } finally { testTheme.smallSize=small;testTheme.bodySize=body }
    }
}
