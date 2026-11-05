import QtQuick
import Quickshell
import Quickshell.Io
import Quickshell.Wayland
import qs.Commons

Item {
  id: root

  property var shell: null
  property var manifest: null

  property string currentMode: "laptop"
  readonly property bool isTablet: currentMode === "tablet"
  property bool isOskVisible: false

  FileView {
    id: modeWatcher
    path: (Quickshell.env("XDG_RUNTIME_DIR") || ("/run/user/" + Quickshell.env("UID"))) + "/omarchy-mode"
    watchChanges: true
    printErrors: false
    onLoaded: {
      var val = String(text() || "").trim()
      if (val.length > 0) root.currentMode = val
    }
    onFileChanged: reload()
  }

  FileView {
    id: oskWatcher
    path: (Quickshell.env("XDG_RUNTIME_DIR") || ("/run/user/" + Quickshell.env("UID"))) + "/surface-osk.state"
    watchChanges: true
    printErrors: false
    onLoaded: {
      var val = String(text() || "").trim()
      root.isOskVisible = (val === "visible")
    }
    onFileChanged: reload()
  }

  Component.onCompleted: {
    modeWatcher.reload()
    oskWatcher.reload()
  }

  function triggerApps() {
    if (!appsProc.running) {
      appsProc.running = true
    }
  }

  function toggleQconsole() {
    if (!qconsoleProc.running) {
      qconsoleProc.running = true
    }
  }

  function toggleOsk() {
    if (!oskProc.running) {
      oskProc.running = true
    }
  }

  Process {
    id: appsProc
    command: ["omarchy-shell", "omarchy.dock", "apps"]
  }

  Process {
    id: qconsoleProc
    command: ["hyprctl", "dispatch", "hl.dsp.workspace.toggle_special('qconsole')"]
  }

  Process {
    id: oskProc
    command: ["surface-osk", "toggle"]
  }

  // Bottom Home Bar (strictly height 28 at bottom of screen)
  Variants {
    id: bottomBars
    model: Quickshell.screens

    delegate: Component {
      HomeBarWindow {
        required property var modelData

        screen: modelData
        pluginRoot: root
      }
    }
  }

  // Top Pull Handle (strictly height 24 at top center of screen)
  Variants {
    id: topHandles
    model: Quickshell.screens

    delegate: Component {
      TopHandleWindow {
        required property var modelData

        screen: modelData
        pluginRoot: root
      }
    }
  }
}
