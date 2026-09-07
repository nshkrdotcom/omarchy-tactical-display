import QtQuick
import QtTest
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
    Component { id: sheetComponent; OperatorSheet { controller: suite.subject; theme: testTheme } }
    Component { id: trendComponent; Trend { theme: testTheme } }
    Component { id: buttonComponent; InstrumentButton { paletteColors: testTheme.colors; chosen: true; text: "Selected choice" } }
    Component { id: shellComponent; TacticalDisplayShell { controller: suite.subject; theme: testTheme } }
    readonly property var subject: controller
    function init() {
        controller.close()
        controller.open(Settings.payload('{"instrument":"machine"}'))
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
