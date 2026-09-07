pragma Singleton
import QtQuick

// Deliberately distinct popup/general colors expose an incorrect host profile.
QtObject {
    property color background: "#232323"
    property color foreground: "#eeeeee"
    property color accent: "#8fcaff"
    property color urgent: "#ffaaaa"
    property var popups: ({background:"#07101a",text:"#ffffff",border:"#8fcaff"})
}
