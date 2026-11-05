import QtQuick
import Quickshell
import Quickshell.Wayland
import qs.Commons

PanelWindow {
  id: topWindow

  property var pluginRoot: null

  WlrLayershell.layer: WlrLayer.Overlay
  WlrLayershell.namespace: "surface-top-handle"
  exclusionMode: ExclusionMode.Ignore
  color: "transparent"

  anchors {
    top: true
    left: true
    right: true
  }

  implicitHeight: 24

  mask: Region {
    item: pluginRoot && pluginRoot.isTablet ? topTrigger : null
  }

  Item {
    id: topTrigger
    anchors.top: parent.top
    anchors.horizontalCenter: parent.horizontalCenter
    width: 140
    height: 24
    visible: pluginRoot ? pluginRoot.isTablet : false

    Rectangle {
      id: topPill
      anchors.top: parent.top
      anchors.topMargin: 4
      anchors.horizontalCenter: parent.horizontalCenter
      width: 60
      height: 4
      radius: 2
      color: topTap.pressed ? Qt.rgba(1, 1, 1, 0.85) : Qt.rgba(1, 1, 1, 0.25)
      scale: topTap.pressed ? 1.1 : 1.0

      Behavior on scale { NumberAnimation { duration: 100 } }
      Behavior on color { ColorAnimation { duration: 100 } }
    }

    TapHandler {
      id: topTap
      onTapped: {
        if (pluginRoot) pluginRoot.toggleQconsole()
      }
    }

    DragHandler {
      id: topDrag
      target: null
      xAxis.enabled: false
      yAxis.enabled: true
      onActiveChanged: {
        if (active && pluginRoot) {
          pluginRoot.toggleQconsole()
        }
      }
    }
  }
}
