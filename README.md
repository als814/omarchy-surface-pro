# Omarchy Linux 2-in-1 Hybrid Suite for Microsoft Surface Pro 5

A production-ready, native hybrid tablet experience for the **Microsoft Surface Pro 5 (2017)** running [Omarchy Linux](https://omarchy.com) (Arch Linux + Hyprland 0.56 + Quickshell).

Seamlessly transitions between a high-efficiency keyboard-driven tiling desktop (Laptop Mode) and an iPad-style touch navigation experience (Tablet Mode) when the Surface Type Cover is detached or folded back.

---

## Features

- **Hardware Mode Detection (`surface-tablet-mode`)**:
  - Real-time kernel `SW_TABLET_MODE` switch detection via `ioctl` and inotify on `/dev/input/`.
  - Fallback USB device polling for Microsoft Surface Type Cover (`045e:09c0`).
  - Broadcasts mode changes to `/run/user/$UID/omarchy-mode`, triggers desktop notifications, and executes modular hooks.
- **Fluid Wayland Touch Gestures**:
  - 1:1 finger-following horizontal workspace paging (`workspace_swipe_touch = true`).
  - Strict directional locking to prevent diagonal drift while scrolling.
- **Exclusive Wayland Overlay (`surface.homebar`)**:
  - Built natively with Quickshell `PanelWindow` on `WlrLayer.Overlay`.
  - Input masks (`Region`) guarantee zero touch bleed to underlying applications or web pages.
  - **Bottom Home Bar**: Minimalist pill (`───────`) to summon the Omarchy App Grid or dismiss the Quake console, plus a dedicated on-screen keyboard toggle button (`⌨`).
  - **Top Quake Handle**: Compact top-edge handle (`────`) to open or close the Omarchy drop-down Quake console without dragging the top bar.
- **Auto-Rotation (`surface-rotate`)**:
  - Real-time display and touch digitizer rotation via `iio-sensor-proxy` D-Bus accelerometer signals.
  - Automatically updates display transform and touch device coordinate mapping (`iptsd-virtual-touchscreen-045e:001f`, `iptsd-virtual-stylus-045e:001f`).
  - Supports orientation locking (`surface-rotate toggle-lock`).
- **Adaptive Quickshell Profile**:
  - **Laptop Mode**: Restores stock ultra-compact 26px bar height.
  - **Tablet Mode**: Automatically expands bar height to 34px with 12px touch tap targets and scaled font.
- **On-Screen Keyboard Integration (`wvkbd`)**:
  - Custom dark theme matching Omarchy's color palette.
  - Persistent state tracking (`surface-osk.state`).
  - Automatically hides when the hardware keyboard is reconnected.
- **Hardware Power & Sleep Protection**:
  - Monotonic clock debounce script prevents re-suspend loops on wake button press.
  - Udev rule prevents Type Cover USB autosuspend disconnects.

---

## Directory Structure

```text
omarchy-surface-pro/
├── bin/
│   ├── surface-tablet-mode.py    # Mode detection daemon & CLI (omarchy-mode)
│   ├── surface-rotate.py         # Accelerometer daemon & CLI (surface-rotate)
│   ├── surface-osk               # On-screen keyboard manager (surface-osk)
│   └── surface-power-button      # Monotonic sleep/wake button handler
├── config/
│   ├── hypr/
│   │   ├── input.lua             # Touchscreen digitizer & 1:1 swipe config
│   │   └── bindings.lua          # Power button rebind & workspace shortcuts
│   ├── omarchy/
│   │   ├── hooks/mode-set.d/     # Extensible hooks executed on mode change
│   │   │   ├── 00-mode-logger.sh     # System logger hook
│   │   │   ├── 20-qconsole-tablet.sh # Auto-dismiss Quake console on detach
│   │   │   ├── 30-adaptive-shell.sh  # Dynamic Quickshell 34px/26px profile
│   │   │   └── 40-osk-mode.sh        # Auto-hide OSK on keyboard attach
│   │   └── plugins/surface.homebar/ # Quickshell layer-shell plugin
│   │       ├── manifest.json
│   │       ├── HomeBar.qml       # State watchers & process dispatchers
│   │       ├── HomeBarWindow.qml # Bottom Home Bar (height: 28px)
│   │       └── TopHandleWindow.qml# Top pull handle (height: 24px)
│   └── systemd/user/
│       ├── surface-tablet-mode.service # User daemon for mode switching
│       └── surface-auto-rotate.service # User daemon for display rotation
├── system/
│   ├── udev/
│   │   └── 90-surface-typecover.rules  # Disables USB autosuspend for Type Cover
│   └── system-sleep/
│       └── surface-typecover-resume    # Pre/post sleep clock recorder
├── install.sh                    # Automated idempotent installation script
└── README.md
```

---

## Prerequisites

On Omarchy / Arch Linux:

```bash
# Core dependencies
sudo pacman -S python-evdev python-dbus python-gobject iio-sensor-proxy

# On-screen keyboard (AUR)
yay -S wvkbd
```

---

## Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/<your-username>/omarchy-surface-pro.git
   cd omarchy-surface-pro
   ```

2. **Install user components** (binaries, hooks, Quickshell plugin, and systemd services):
   ```bash
   ./install.sh
   ```

3. **Install system rules** (optional, recommended for Type Cover stability & power button):
   ```bash
   sudo ./install.sh --system
   ```

---

## Usage & CLI Commands

### Tablet Mode
```bash
omarchy-mode status        # Display current hardware mode (laptop / tablet)
omarchy-mode set tablet    # Manually force Tablet Mode
omarchy-mode set laptop    # Manually force Laptop Mode
omarchy-mode toggle        # Toggle between modes
omarchy-mode daemon        # Run in foreground (managed by systemd)
```

### Auto-Rotation
```bash
surface-rotate status      # Check current transform & lock status
surface-rotate toggle-lock # Lock or unlock auto-rotation
surface-rotate set normal  # Force landscape orientation (transform 0)
surface-rotate set portrait# Force portrait orientation (transform 1)
```

### On-Screen Keyboard
```bash
surface-osk toggle         # Toggle on-screen keyboard
surface-osk show           # Display keyboard
surface-osk hide           # Dismiss keyboard
surface-osk status         # Print state (visible / hidden)
```

---

## License

MIT License. Designed for the Omarchy Linux community.
