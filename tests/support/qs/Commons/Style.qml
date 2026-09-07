pragma Singleton
import QtQuick

// Test adapter for host style inputs. Native rendering is validated separately.
QtObject {
    property int cornerRadius: 3
    property var spacing: ({hairline:1,xxs:2,xs:3,sm:4,md:6,lg:8,xl:10,xxl:12,xxxl:14,huge:16,controlPaddingX:10,controlPaddingY:6,controlHeight:30,inputPaddingY:8})
    property var font: ({caption:13,body:16,subtitle:18,title:22})
    function space(value) { return value }
}
