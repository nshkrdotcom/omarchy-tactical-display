import QtQuick
import QtTest
import "../../core"
import "../../model/Settings.js" as Settings

TestCase {
    id: suite
    name: "OperatorController"
    when: windowShown
    width: 640
    height: 480
    QtObject {
        id: fake
        property bool ready: true
        property string backendError: ""
        property double clock: 1000000
        property double lastSampleAt: 1000000
        signal received(var frame)
        signal detailReceived(var frame)
        signal scopeReceived(var frame)
        signal freezeReceived(var frame)
        function setInstanceGroups(groups, frozen) {}
        function inspect(key, offset, frozen) {}
        function freeze(value) { return 7 }
    }
    NavigationController { id: controller; telemetry: fake }
    function sample(at) {
        return {schemaVersion:3,sequence:at,monotonic:at,wallTime:1700000000+at,
            system:{cpuPercent:25},processes:[{key:"process:42:100",name:"Operator test",pid:42,groupKey:"application:test"}],groups:[],
            capabilities:{machine:{status:"available",sampledAt:at,intervalSeconds:1}},
            events:[{key:"event:"+at,entityKey:"process:42:100",domain:"process",kind:"opened",at:at}],trend:[]}
    }
    function init() { controller.close(); controller.open(Settings.payload('{"instrument":"machine"}')); controller.setFlag("showPicker",false); controller.setFlag("showIntro",false) }
    function test_briefing_shortcut_respects_editor_and_modifiers() {
        var e={key:Qt.Key_A,modifiers:Qt.NoModifier,accepted:false}
        controller.handleKey(e,true,false); verify(!controller.navState.showOperator)
        e.modifiers=Qt.ControlModifier; controller.handleKey(e,false,false); verify(!controller.navState.showOperator)
        e.modifiers=Qt.NoModifier; controller.handleKey(e,false,false); verify(controller.navState.showOperator); verify(e.accepted)
        controller.back(); verify(!controller.navState.showOperator)
    }
    function test_baseline_and_pins_clear_on_close() {
        fake.received(sample(1000)); controller.captureBaseline(); verify(controller.comparisonBaseline !== null)
        controller.pick({key:"process:42:100",name:"Operator test",kind:"process"})
        controller.togglePinSelection(); compare(controller.pins.length,1)
        controller.close(); compare(controller.pins.length,0); compare(controller.comparisonBaseline,null); compare(controller.operatorSession.events.length,0)
    }
    function test_frozen_timeline_is_stable_while_live_history_advances() {
        fake.received(sample(1000)); controller.toggleFreeze()
        fake.freezeReceived({requestId:7,frozen:true,snapshot:sample(1000)})
        compare(controller.displaySession.events.length,1)
        fake.received(sample(1001)); compare(controller.operatorSession.events.length,2); compare(controller.displaySession.events.length,1)
        controller.toggleFreeze(); fake.freezeReceived({requestId:7,frozen:false})
        compare(controller.displaySession.events.length,2)
    }
    function test_briefing_jump_clears_lenses_and_keeps_exact_identity() {
        fake.received(sample(1000)); controller.setFlag("query","unrelated"); controller.setFlag("showOperator",true)
        controller.jumpOperator({instrument:"processes",entityKey:"process:42:100"})
        compare(controller.navState.instrument,"processes"); compare(controller.navState.query,""); verify(!controller.navState.showOperator)
        tryVerify(function() { return controller.navState.selectedKey === "process:42:100" })
    }
}
