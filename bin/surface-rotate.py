#!/usr/bin/env python3
"""
Surface Auto-Rotate Daemon for Hyprland
Handles automatic and manual rotation for display, touchscreen, and stylus.
"""

import sys
import os
import json
import signal
import argparse
import subprocess
import dbus
from dbus.mainloop.glib import DBusGMainLoop
from gi.repository import GLib

LOCK_FILE = os.path.expanduser("~/.cache/surface-rotate-lock")
LOG_FILE = os.path.expanduser("~/auto-rotate.log")

ORIENTATION_TRANSFORMS = {
    "normal": 0,
    "bottom-up": 2,
    "right-up": 3,
    "left-up": 1,
}

TOUCH_DEVICES = [
    "iptsd-virtual-touchscreen-045e:001f",
    "ipts-045e:001f-touchscreen",
    "iptsd-virtual-stylus-045e:001f",
]

def log(msg):
    try:
        with open(LOG_FILE, "a") as f:
            f.write(f"{msg}\n")
    except Exception:
        pass
    print(msg)

def get_current_monitor_info(output_name="eDP-1"):
    try:
        res = subprocess.run(["hyprctl", "monitors", "-j"], capture_output=True, text=True, check=True)
        monitors = json.loads(res.stdout)
        for m in monitors:
            if m.get("name") == output_name:
                return m
    except Exception as e:
        log(f"Error querying monitor info: {e}")
    return {"scale": 2, "transform": 0, "x": 0, "y": 0}

def apply_rotation(transform, output_name="eDP-1"):
    m_info = get_current_monitor_info(output_name)
    scale = m_info.get("scale", 2)
    pos_x = m_info.get("x", 0)
    pos_y = m_info.get("y", 0)
    pos_str = f"{pos_x}x{pos_y}"

    device_calls = []
    for dev in TOUCH_DEVICES:
        device_calls.append(f'hl.device({{ name = "{dev}", output = "{output_name}", transform = t }})')
    device_calls_str = "\n".join(device_calls)

    lua_code = f"""
local t = {transform}
hl.monitor({{ output = "{output_name}", mode = "preferred", position = "{pos_str}", scale = {scale}, transform = t }})
hl.config({{
  input = {{
    touchdevice = {{ output = "{output_name}", transform = t }},
    tablet = {{ output = "{output_name}", transform = t }}
  }}
}})
{device_calls_str}
"""
    try:
        res = subprocess.run(["hyprctl", "eval", lua_code], capture_output=True, text=True, check=True)
        log(f"Applied rotation transform {transform} to {output_name} and touch/tablet devices: {res.stdout.strip()}")
        return True
    except subprocess.CalledProcessError as e:
        log(f"Failed to apply rotation: {e.stderr or e.stdout}")
        return False

def notify(summary, body=""):
    try:
        subprocess.run(["notify-send", "-a", "Surface Rotate", summary, body, "-t", "2000"], check=False)
    except Exception:
        pass

class SensorDaemon:
    def __init__(self):
        self.bus = None
        self.sensor_proxy = None
        self.sensor_iface = None
        self.loop = None
        self.current_orientation = None

    def start(self):
        DBusGMainLoop(set_as_default=True)
        self.bus = dbus.SystemBus()
        self.loop = GLib.MainLoop()

        try:
            self.sensor_proxy = self.bus.get_object("net.hadess.SensorProxy", "/net/hadess/SensorProxy")
            self.sensor_iface = dbus.Interface(self.sensor_proxy, "net.hadess.SensorProxy")
            props_iface = dbus.Interface(self.sensor_proxy, "org.freedesktop.DBus.Properties")

            self.sensor_iface.ClaimAccelerometer()
            log("Claimed accelerometer successfully.")

            initial = str(props_iface.Get("net.hadess.SensorProxy", "AccelerometerOrientation"))
            log(f"Initial accelerometer orientation: {initial}")
            self.on_orientation_changed(initial)

            self.bus.add_signal_receiver(
                self.properties_changed_handler,
                signal_name="PropertiesChanged",
                dbus_interface="org.freedesktop.DBus.Properties",
                path="/net/hadess/SensorProxy",
            )
        except dbus.DBusException as e:
            log(f"DBus error initializing SensorProxy: {e}")
            sys.exit(1)

        signal.signal(signal.SIGINT, self.cleanup)
        signal.signal(signal.SIGTERM, self.cleanup)

        try:
            self.loop.run()
        except KeyboardInterrupt:
            self.cleanup()

    def properties_changed_handler(self, interface, changed_properties, invalidated_properties):
        if interface == "net.hadess.SensorProxy" and "AccelerometerOrientation" in changed_properties:
            orientation = str(changed_properties["AccelerometerOrientation"])
            self.on_orientation_changed(orientation)

    def on_orientation_changed(self, orientation):
        if os.path.exists(LOCK_FILE):
            log(f"Orientation changed to {orientation}, but rotation is locked.")
            return

        if orientation == self.current_orientation:
            return

        transform = ORIENTATION_TRANSFORMS.get(orientation)
        if transform is not None:
            log(f"Orientation changed: {orientation} -> transform {transform}")
            apply_rotation(transform)
            self.current_orientation = orientation

    def cleanup(self, *args):
        log("Stopping SensorDaemon and releasing accelerometer...")
        if self.sensor_iface:
            try:
                self.sensor_iface.ReleaseAccelerometer()
            except Exception:
                pass
        if self.loop and self.loop.is_running():
            self.loop.quit()
        sys.exit(0)

def main():
    parser = argparse.ArgumentParser(description="Surface Auto-Rotate for Hyprland")
    parser.add_argument("action", nargs="?", default="daemon",
                        choices=["daemon", "set", "toggle", "lock", "unlock", "toggle-lock", "status"])
    parser.add_argument("value", nargs="?", default=None,
                        help="Value for set action: normal, portrait, inverted, portrait-inverted, 0, 1, 2, 3")

    args = parser.parse_args()

    if args.action == "daemon":
        log("Starting surface auto-rotate daemon...")
        daemon = SensorDaemon()
        daemon.start()

    elif args.action == "lock":
        with open(LOCK_FILE, "w") as f:
            f.write("locked\n")
        notify("Rotation Locked", "Auto-rotation is paused")
        log("Rotation locked.")

    elif args.action == "unlock":
        if os.path.exists(LOCK_FILE):
            os.remove(LOCK_FILE)
        notify("Rotation Unlocked", "Auto-rotation is active")
        log("Rotation unlocked.")

    elif args.action == "toggle-lock":
        if os.path.exists(LOCK_FILE):
            os.remove(LOCK_FILE)
            notify("Rotation Unlocked", "Auto-rotation is active")
            log("Rotation unlocked.")
        else:
            with open(LOCK_FILE, "w") as f:
                f.write("locked\n")
            notify("Rotation Locked", "Auto-rotation is paused")
            log("Rotation locked.")

    elif args.action == "status":
        info = get_current_monitor_info("eDP-1")
        is_locked = os.path.exists(LOCK_FILE)
        print(f"Current transform: {info.get('transform', 0)}")
        print(f"Rotation locked: {is_locked}")

    elif args.action == "set":
        target = args.value
        mapping = {
            "normal": 0, "0": 0, "landscape": 0,
            "portrait": 1, "1": 1, "left-up": 1,
            "inverted": 2, "2": 2, "bottom-up": 2,
            "portrait-inverted": 3, "3": 3, "right-up": 3,
        }
        if target not in mapping:
            print(f"Unknown value '{target}'. Options: {', '.join(mapping.keys())}")
            sys.exit(1)
        transform = mapping[target]
        apply_rotation(transform)

    elif args.action == "toggle":
        info = get_current_monitor_info("eDP-1")
        cur_t = info.get("transform", 0)
        new_t = 1 if cur_t in (0, 2) else 0
        apply_rotation(new_t)

if __name__ == "__main__":
    main()
