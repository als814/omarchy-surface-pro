#!/usr/bin/env python3
"""
Surface Tablet Mode Daemon & CLI for Omarchy
Monitors Surface Type Cover attachment and fold-back state (SW_TABLET_MODE).
Manages /run/user/<UID>/omarchy-mode, triggers desktop notifications,
and executes user hooks in ~/.config/omarchy/hooks/mode-set.d/.
"""

import os
import sys
import time
import glob
import array
import fcntl
import signal
import struct
import select
import ctypes
import argparse
import subprocess

# Kernel switch ioctl: EVIOCGSW(8)
EVIOCGSW = 2 << 30 | ord('E') << 8 | 0x1b | 8 << 16

UID = os.getuid()
RUN_DIR = f"/run/user/{UID}"
STATE_FILE = os.path.join(RUN_DIR, "omarchy-mode")
HOOKS_DIR = os.path.expanduser("~/.config/omarchy/hooks/mode-set.d")
LOG_FILE = os.path.expanduser("~/.local/state/omarchy-tablet-mode.log")

def log(msg):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    formatted = f"[{ts}] {msg}"
    try:
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
        with open(LOG_FILE, "a") as f:
            f.write(formatted + "\n")
    except Exception:
        pass
    print(formatted)

def is_typecover_connected():
    """Check if Microsoft Surface Type Cover (045e:09c0) is attached on USB."""
    for p in glob.glob("/sys/bus/usb/devices/*"):
        v_path = os.path.join(p, "idVendor")
        p_path = os.path.join(p, "idProduct")
        if os.path.exists(v_path) and os.path.exists(p_path):
            try:
                with open(v_path) as fv, open(p_path) as fp:
                    if fv.read().strip() == "045e" and fp.read().strip() == "09c0":
                        return True
            except Exception:
                pass
    return False

def get_switch_node():
    """Find the event node exposing the Surface Tablet Mode Switch."""
    for p in glob.glob("/sys/class/input/event*"):
        n_path = os.path.join(p, "device/name")
        if os.path.exists(n_path):
            try:
                with open(n_path) as fn:
                    if "Tablet Mode Switch" in fn.read():
                        sw_path = os.path.join(p, "device/capabilities/sw")
                        if os.path.exists(sw_path):
                            with open(sw_path) as fsw:
                                if fsw.read().strip() == "2":
                                    return "/dev/input/" + os.path.basename(p)
            except Exception:
                pass
    return None

def query_switch_state(dev_node):
    """Query SW_TABLET_MODE (bit 1 of switch bitmap). 1 = folded back, 0 = laptop."""
    if not dev_node or not os.path.exists(dev_node):
        return None
    try:
        with open(dev_node, "rb") as fd:
            buf = array.array("B", [0] * 8)
            fcntl.ioctl(fd, EVIOCGSW, buf)
            return (buf[0] >> 1) & 1
    except Exception:
        return None

def detect_mode():
    """Determine current physical mode and reason."""
    if not is_typecover_connected():
        return "tablet", "Type Cover detached"
    node = get_switch_node()
    sw = query_switch_state(node)
    if sw == 1:
        return "tablet", "Type Cover folded back"
    return "laptop", "Type Cover attached"

def apply_mode(mode, reason, notify=True):
    """Update state file, notify desktop, and execute hooks."""
    log(f"Mode changed: {mode} ({reason})")

    # 1. Update state file atomically
    os.makedirs(RUN_DIR, exist_ok=True)
    tmp_file = STATE_FILE + ".tmp"
    try:
        with open(tmp_file, "w") as f:
            f.write(mode + "\n")
        os.replace(tmp_file, STATE_FILE)
    except Exception as e:
        log(f"Failed to write state file: {e}")

    # 2. Desktop notification
    if notify:
        if mode == "tablet":
            title = "Tablet Mode Activated"
            body = f"{reason} — touch interface ready"
            icon = "input-tablet"
        else:
            title = "Laptop Mode Activated"
            body = f"{reason} — physical keyboard ready"
            icon = "input-keyboard"

        try:
            subprocess.Popen([
                "notify-send",
                "-a", "Omarchy",
                "-i", icon,
                "-u", "low",
                "-t", "3000",
                title, body
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as e:
            log(f"Notification error: {e}")

    # 3. Execute hooks in ~/.config/omarchy/hooks/mode-set.d/
    if os.path.isdir(HOOKS_DIR):
        for entry in sorted(os.listdir(HOOKS_DIR)):
            hook_path = os.path.join(HOOKS_DIR, entry)
            if os.path.isfile(hook_path) and os.access(hook_path, os.X_OK):
                try:
                    log(f"Running hook: {entry} {mode}")
                    subprocess.Popen([hook_path, mode, reason])
                except Exception as e:
                    log(f"Hook error ({entry}): {e}")

def run_daemon():
    """Event-driven daemon monitoring inotify on /dev/input and switch events."""
    log("Starting Surface Tablet Mode Daemon...")

    # Setup non-blocking inotify on /dev/input
    libc = ctypes.CDLL(None)
    inotify_fd = libc.inotify_init()
    if inotify_fd < 0:
        log("Failed to initialize inotify, exiting.")
        sys.exit(1)

    flags = fcntl.fcntl(inotify_fd, fcntl.F_GETFL)
    fcntl.fcntl(inotify_fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)

    IN_CREATE = 0x00000100
    IN_DELETE = 0x00000200
    libc.inotify_add_watch(inotify_fd, b"/dev/input", IN_CREATE | IN_DELETE)

    switch_fd = None
    switch_path = None

    def refresh_switch():
        nonlocal switch_fd, switch_path
        if switch_fd is not None:
            try:
                os.close(switch_fd)
            except OSError:
                pass
            switch_fd = None
            switch_path = None

        node = get_switch_node()
        if node and os.path.exists(node):
            try:
                switch_fd = os.open(node, os.O_RDONLY | os.O_NONBLOCK)
                switch_path = node
                log(f"Monitoring switch device: {node}")
            except OSError as err:
                log(f"Failed to open switch node {node}: {err}")
        return switch_fd

    # Initial state evaluation
    refresh_switch()
    current_mode, reason = detect_mode()
    apply_mode(current_mode, reason, notify=False)

    # Signal handlers
    running = True
    def stop_handler(signum, frame):
        nonlocal running
        running = False
    signal.signal(signal.SIGINT, stop_handler)
    signal.signal(signal.SIGTERM, stop_handler)

    while running:
        read_fds = [inotify_fd]
        if switch_fd is not None:
            read_fds.append(switch_fd)

        try:
            rlist, _, _ = select.select(read_fds, [], [], 5.0)
        except (InterruptedError, select.error):
            break

        mode_check_needed = False

        # Inotify fired: device added or removed
        if inotify_fd in rlist:
            try:
                os.read(inotify_fd, 4096)
            except OSError:
                pass
            time.sleep(0.15)  # Let udev/kernel settle
            refresh_switch()
            mode_check_needed = True

        # Switch event fired: fold / unfold
        if switch_fd is not None and switch_fd in rlist:
            try:
                data = os.read(switch_fd, 24 * 16)
                for i in range(0, len(data), 24):
                    chunk = data[i:i+24]
                    if len(chunk) == 24:
                        sec, usec, ev_type, ev_code, ev_val = struct.unpack("qqHHi", chunk)
                        if ev_type == 0x05 and ev_code == 0x01:  # EV_SW, SW_TABLET_MODE
                            mode_check_needed = True
            except OSError:
                refresh_switch()
                mode_check_needed = True

        if mode_check_needed:
            new_mode, new_reason = detect_mode()
            if new_mode != current_mode:
                current_mode = new_mode
                apply_mode(current_mode, new_reason, notify=True)

    # Cleanup
    if switch_fd is not None:
        os.close(switch_fd)
    os.close(inotify_fd)
    log("Daemon stopped.")

def main():
    parser = argparse.ArgumentParser(description="Surface Tablet Mode Daemon & CLI")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("daemon", help="Run the background detection daemon")
    subparsers.add_parser("status", help="Show current mode and hardware details")
    subparsers.add_parser("get", help="Print current mode only (laptop or tablet)")
    
    set_parser = subparsers.add_parser("set", help="Manually override mode")
    set_parser.add_argument("mode", choices=["laptop", "tablet"], help="Target mode")

    args = parser.parse_args()

    if args.command == "daemon":
        run_daemon()
    elif args.command == "get":
        if os.path.exists(STATE_FILE):
            try:
                print(open(STATE_FILE).read().strip())
                return
            except Exception:
                pass
        mode, _ = detect_mode()
        print(mode)
    elif args.command == "set":
        apply_mode(args.mode, "Manual override", notify=True)
    else:  # status (default)
        mode, reason = detect_mode()
        node = get_switch_node()
        sw = query_switch_state(node)
        tc = is_typecover_connected()
        print(f"Current Mode:     {mode.upper()}")
        print(f"Reason:           {reason}")
        print(f"Type Cover USB:   {'Connected (045e:09c0)' if tc else 'Disconnected'}")
        print(f"Switch Device:    {node or 'None'}")
        print(f"SW_TABLET_MODE:   {sw if sw is not None else 'N/A'}")
        print(f"State File:       {STATE_FILE}")

if __name__ == "__main__":
    main()
