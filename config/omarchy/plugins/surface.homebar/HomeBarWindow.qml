import QtQuick
import Quickshell
import Quickshell.Wayland
import Quickshell.Hyprland
import qs.Commons

PanelWindow {
  id: window

  property var pluginRoot: null

  readonly property var monitor: Hyprland.monitorFor(screen)
  readonly property bool isQconsoleOpen: {
    if (!monitor || !monitor.lastIpcObject || !monitor.lastIpcObject.specialWorkspace) return false
    return monitor.lastIpcObject.specialWorkspace.name === "special:qconsole"
  }

  WlrLayershell.layer: WlrLayer.Overlay
  WlrLayershell.namespace: "surface-home-bar"
  exclusionMode: ExclusionMode.Ignore
  color: "transparent"

  anchors {
    bottom: true
    left: true
    right: true
  }

  implicitHeight: 28

  mask: Region {
    item: pluginRoot && pluginRoot.isTablet ? bottomTrigger : null
  }

  // Bottom Home Bar (App Grid launcher, Quake Console closer, and OSK summoner)
  Item {
    id: bottomTrigger
    anchors.bottom: parent.bottom
    anchors.horizontalCenter: parent.horizontalCenter
    width: Math.min(340, window.width * 0.45)
    height: 28
    visible: pluginRoot ? pluginRoot.isTablet : false

    // Center Home Pill
    Item {
      id: pillArea
      anchors.centerIn: parent
      width: isQconsoleOpen ? 180 : 140
      height: parent.height

      Rectangle {
        id: bottomPill
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 6
        anchors.horizontalCenter: parent.horizontalCenter
        width: parent.width
        height: 5
        radius: 3
        color: bottomTap.pressed
          ? Qt.rgba(1, 1, 1, 0.95)
          : (isQconsoleOpen ? Qt.rgba(0.9, 0.6, 0.2, 0.85) : Qt.rgba(1, 1, 1, 0.45))
        scale: bottomTap.pressed ? 1.08 : 1.0

        Behavior on width { NumberAnimation { duration: 150 } }
        Behavior on scale { NumberAnimation { duration: 100 } }
        Behavior on color { ColorAnimation { duration: 100 } }
      }

      TapHandler {
        id: bottomTap
        onTapped: {
          if (!pluginRoot) return
          if (isQconsoleOpen) {
            pluginRoot.toggleQconsole()
          } else {
            pluginRoot.triggerApps()
          }
        }
      }

      DragHandler {
        id: bottomDrag
        target: null
        xAxis.enabled: false
        yAxis.enabled: true
        onActiveChanged: {
          if (active && pluginRoot) {
            if (isQconsoleOpen) {
              pluginRoot.toggleQconsole()
            } else {
              pluginRoot.triggerApps()
            }
          }
        }
      }
    }

    // Keyboard Toggle Button (Summons / Hides on-screen keyboard)
    Item {
      id: oskBtn
      anchors.right: parent.right
      anchors.rightMargin: 6
      anchors.verticalCenter: parent.verticalCenter
      width: 32
      height: 22

      Rectangle {
        anchors.fill: parent
        radius: 5
        color: oskTap.pressed
          ? Qt.rgba(1, 1, 1, 0.35)
          : (pluginRoot && pluginRoot.isOskVisible ? Qt.rgba(1, 1, 1, 0.25) : Qt.rgba(1, 1, 1, 0.08))
        border.color: pluginRoot && pluginRoot.isOskVisible ? Qt.rgba(1, 1, 1, 0.6) : Qt.rgba(1, 1, 1, 0.2)
        border.width: 1

        Text {
          anchors.centerIn: parent
          text: "⌨"
          font.pixelSize: 13
          color: Qt.rgba(1, 1, 1, 0.85)
        }

        scale: oskTap.pressed ? 1.08 : 1.0
        Behavior on scale { NumberAnimation { duration: 80 } }
        Behavior on color { ColorAnimation { duration: 100 } }
      }

      TapHandler {
        id: oskTap
        onTapped: {
          if (pluginRoot) pluginRoot.toggleOsk()
        }
      }
    }
  }
}
