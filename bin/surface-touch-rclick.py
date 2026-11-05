#!/usr/bin/env python3
"""
Surface Touch Two-Finger Tap Right-Click Emulator
Listens to multitouch events on Microsoft Surface touchscreen digitizer
and injects a native right-click when a 2-finger tap is performed.
Uses Linux /dev/uinput and /dev/input/ standard interfaces (zero external dependencies).
"""

import os
import sys
import glob
import time
import struct
import fcntl
import signal
import select

# Input event constants
EV_SYN = 0x00
EV_KEY = 0x01
EV_REL = 0x02
EV_ABS = 0x03

SYN_REPORT = 0x00
BTN_LEFT = 0x110
BTN_RIGHT = 0x111

ABS_MT_SLOT = 0x2f         # 47
ABS_MT_POSITION_X = 0x35   # 53
ABS_MT_POSITION_Y = 0x36   # 54
ABS_MT_TRACKING_ID = 0x39  # 57

# uinput ioctl numbers (Linux 64-bit)
UI_SET_EVBIT = 0x40045564
UI_SET_KEYBIT = 0x40045565
UI_DEV_SETUP = 0x405c5503
UI_DEV_CREATE = 0x5501
UI_DEV_DESTROY = 0x5502

# Configuration
TAP_MAX_DURATION = 0.35    # Max seconds from first touch to all fingers up
MAX_TAP_MOVE_DELTA = 80    # Max movement allowed in coordinates before tap is invalidated
POLL_TIMEOUT = 1.0

# 64-bit input_event struct format: timeval (2 * long), uint16, uint16, int32
EVENT_FORMAT = "qqHHi"
EVENT_SIZE = struct.calcsize(EVENT_FORMAT)


def find_touchscreen_device():
    """Finds the IPTS or IPTSD touchscreen event node."""
    candidates = []
    for sys_dev in glob.glob("/sys/class/input/input*"):
        name_path = os.path.join(sys_dev, "name")
        if os.path.exists(name_path):
            try:
                with open(name_path, "r") as f:
                    name = f.read().strip()
                if "IPTS" in name and "Touchscreen" in name:
                    for entry in os.listdir(sys_dev):
                        if entry.startswith("event"):
                            ev_path = f"/dev/input/{entry}"
                            # Prefer IPTSD Virtual Touchscreen if available
                            if "IPTSD" in name:
                                candidates.insert(0, ev_path)
                            else:
                                candidates.append(ev_path)
            except Exception:
                pass
    return candidates[0] if candidates else None


class UInputMouse:
    def __init__(self):
        self.fd = None

    def open(self):
        try:
            self.fd = os.open("/dev/uinput", os.O_WRONLY | os.O_NONBLOCK)
            fcntl.ioctl(self.fd, UI_SET_EVBIT, EV_KEY)
            fcntl.ioctl(self.fd, UI_SET_KEYBIT, BTN_LEFT)
            fcntl.ioctl(self.fd, UI_SET_KEYBIT, BTN_RIGHT)

            setup = struct.pack("HHHH80sI", 0x03, 0x1234, 0x5678, 1, b"Surface Touchscreen Virtual Mouse", 0)
            fcntl.ioctl(self.fd, UI_DEV_SETUP, setup)
            fcntl.ioctl(self.fd, UI_DEV_CREATE)
            return True
        except Exception as e:
            print(f"Failed to open /dev/uinput: {e}", file=sys.stderr)
            if self.fd:
                try:
                    os.close(self.fd)
                except Exception:
                    pass
                self.fd = None
            return False

    def emit_right_click(self):
        if not self.fd:
            return
        now = time.time()
        sec = int(now)
        usec = int((now - sec) * 1_000_000)

        # Button down
        ev_down = struct.pack(EVENT_FORMAT, sec, usec, EV_KEY, BTN_RIGHT, 1)
        ev_syn = struct.pack(EVENT_FORMAT, sec, usec, EV_SYN, SYN_REPORT, 0)
        os.write(self.fd, ev_down + ev_syn)

        time.sleep(0.02)

        # Button up
        now = time.time()
        sec = int(now)
        usec = int((now - sec) * 1_000_000)
        ev_up = struct.pack(EVENT_FORMAT, sec, usec, EV_KEY, BTN_RIGHT, 0)
        ev_syn = struct.pack(EVENT_FORMAT, sec, usec, EV_SYN, SYN_REPORT, 0)
        os.write(self.fd, ev_up + ev_syn)

    def close(self):
        if self.fd:
            try:
                fcntl.ioctl(self.fd, UI_DEV_DESTROY)
                os.close(self.fd)
            except Exception:
                pass
            self.fd = None


class TwoFingerTapDaemon:
    def __init__(self):
        self.running = True
        self.mouse = UInputMouse()
        self.touch_fd = None
        self.device_path = None

    def cleanup(self, *args):
        self.running = False
        if self.touch_fd:
            try:
                os.close(self.touch_fd)
            except Exception:
                pass
        self.mouse.close()

    def start(self):
        signal.signal(signal.SIGINT, self.cleanup)
        signal.signal(signal.SIGTERM, self.cleanup)

        if not self.mouse.open():
            print("Failed to initialize virtual mouse device.", file=sys.stderr)
            sys.exit(1)

        self.device_path = find_touchscreen_device()
        if not self.device_path:
            print("No IPTS touchscreen device found.", file=sys.stderr)
            sys.exit(1)

        print(f"Monitoring {self.device_path} for two-finger tap right-click...")

        while self.running:
            try:
                self.touch_fd = os.open(self.device_path, os.O_RDONLY | os.O_NONBLOCK)
            except Exception as e:
                print(f"Error opening {self.device_path}: {e}. Retrying in 2s...", file=sys.stderr)
                time.sleep(2)
                continue

            current_slot = 0
            active_slots = {}
            gesture_start_time = 0.0
            max_fingers_seen = 0
            slot_positions = {}
            slot_start_positions = {}

            epoll = select.epoll()
            epoll.register(self.touch_fd, select.EPOLLIN)

            try:
                while self.running:
                    events = epoll.poll(POLL_TIMEOUT)
                    if not events:
                        continue

                    try:
                        data = os.read(self.touch_fd, EVENT_SIZE * 64)
                    except BlockingIOError:
                        continue
                    except Exception:
                        break

                    if not data:
                        break

                    num_events = len(data) // EVENT_SIZE
                    for i in range(num_events):
                        sec, usec, ev_type, ev_code, ev_val = struct.unpack_from(EVENT_FORMAT, data, i * EVENT_SIZE)
                        t_now = sec + usec / 1_000_000.0

                        if ev_type == EV_ABS:
                            if ev_code == ABS_MT_SLOT:
                                current_slot = ev_val
                            elif ev_code == ABS_MT_TRACKING_ID:
                                if ev_val != -1 and ev_val != 0xFFFFFFFF:
                                    # Finger down
                                    active_slots[current_slot] = t_now
                                    if len(active_slots) == 1:
                                        gesture_start_time = t_now
                                        max_fingers_seen = 1
                                    else:
                                        max_fingers_seen = max(max_fingers_seen, len(active_slots))
                                    if current_slot in slot_positions:
                                        slot_start_positions[current_slot] = slot_positions[current_slot]
                                else:
                                    # Finger up
                                    active_slots.pop(current_slot, None)
                            elif ev_code == ABS_MT_POSITION_X:
                                slot_positions.setdefault(current_slot, [0, 0])[0] = ev_val
                            elif ev_code == ABS_MT_POSITION_Y:
                                slot_positions.setdefault(current_slot, [0, 0])[1] = ev_val

                        elif ev_type == EV_SYN and ev_code == SYN_REPORT:
                            # If all fingers lifted
                            if len(active_slots) == 0 and max_fingers_seen > 0:
                                elapsed = t_now - gesture_start_time

                                # Check for clean 2-finger tap
                                if max_fingers_seen == 2 and elapsed <= TAP_MAX_DURATION:
                                    # Verify distance wasn't a long drag / swipe
                                    moved_too_much = False
                                    for s, start_pos in slot_start_positions.items():
                                        end_pos = slot_positions.get(s, start_pos)
                                        dx = abs(end_pos[0] - start_pos[0])
                                        dy = abs(end_pos[1] - start_pos[1])
                                        if dx > MAX_TAP_MOVE_DELTA or dy > MAX_TAP_MOVE_DELTA:
                                            moved_too_much = True
                                            break

                                    if not moved_too_much:
                                        self.mouse.emit_right_click()

                                # Reset tracking
                                max_fingers_seen = 0
                                slot_start_positions.clear()

            except Exception as e:
                print(f"Touch read loop error: {e}", file=sys.stderr)
            finally:
                try:
                    epoll.unregister(self.touch_fd)
                    epoll.close()
                    os.close(self.touch_fd)
                except Exception:
                    pass
                time.sleep(1)


def main():
    daemon = TwoFingerTapDaemon()
    daemon.start()


if __name__ == "__main__":
    main()
