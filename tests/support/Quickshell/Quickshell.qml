pragma Singleton
import QtQuick

// No desktop clipboard writes in component tests.
QtObject { property string clipboardText: "" }
