#!/usr/bin/env python3
"""
Watch the system power source and update ~/.config/omarchy/shell.json
so idle.screensaver is 600 (10min) on battery and 900 (15min) on AC.
Backs up the original shell.json once before the first change.
Runs as a user service; polls every 10 seconds (lightweight).
"""
import json
import os
import re
import time
import datetime

HOME = os.path.expanduser("~")
CONFIG_PATH = os.path.join(HOME, ".config/omarchy/shell.json")
HYPRIDLE_PATH = os.path.join(HOME, ".config/hypr/hypridle.conf")
BACKUP_DIR = os.path.join(HOME, ".config/omarchy/backups")
POLL_INTERVAL = 10
BATTERY_SECONDS = 300   # 5 minutes
AC_SECONDS = 900        # 15 minutes
HYPRIDLE_MARGIN = 2     # allow the screensaver listener to run first


def get_power_state():
    """
    Prefer powerprofilesctl when available (returns 'ac' or 'battery').
    Fall back to sysfs; also treat a battery whose status is 'Charging' as AC.
    """
    try:
        import subprocess
        p = subprocess.run(["powerprofilesctl", "get"], capture_output=True, text=True, timeout=1)
        out = (p.stdout or "").strip().lower()
        if out:
            if "ac" in out or out == "ac":
                return "ac"
            if "battery" in out:
                return "battery"
    except Exception:
        pass

    sysbase = "/sys/class/power_supply"
    try:
        for name in os.listdir(sysbase):
            path = os.path.join(sysbase, name)
            type_path = os.path.join(path, "type")
            online_path = os.path.join(path, "online")
            status_path = os.path.join(path, "status")
            try:
                t = open(type_path, "r").read().strip().lower() if os.path.isfile(type_path) else ""
            except Exception:
                t = ""

            # If mains/adapter and online==1, treat as AC
            if t in ("mains", "ac", "line_power") and os.path.isfile(online_path):
                try:
                    v = open(online_path, "r").read().strip()
                except Exception:
                    v = "0"
                if v == "1" or v.lower() == "true":
                    return "ac"

            # If battery reports 'Charging', treat as AC
            if t in ("battery",) and os.path.isfile(status_path):
                try:
                    s = open(status_path, "r").read().strip().lower()
                except Exception:
                    s = ""
                if "charging" in s or "full" in s:
                    return "ac"

        # Default to battery if no AC indicators found
        return "battery"
    except Exception:
        # conservative fallback: assume AC to avoid aggressive screensaver on false negatives
        return "ac"


def backup_once(orig_path):
    try:
        os.makedirs(BACKUP_DIR, exist_ok=True)
        ts = datetime.datetime.now().strftime("%Y%m%dT%H%M%S")
        dest = os.path.join(BACKUP_DIR, f"shell.json.bak.{ts}")
        if not os.path.exists(dest) and os.path.exists(orig_path):
            with open(orig_path, "rb") as fr, open(dest, "wb") as fw:
                fw.write(fr.read())
            return dest
    except Exception:
        pass
    return None


def load_config(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def write_config_atomic(path, data):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")
    os.replace(tmp, path)


def update_hypridle(path, screensaver_seconds, lock_seconds):
    """Update the two idle listeners while preserving the rest of the config."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
        text = re.sub(
            r"(listener \{\n\s+timeout = )\d+(\n\s+on-timeout = pidof hyprlock \|\| omarchy-launch-screensaver)",
            rf"\g<1>{screensaver_seconds}\g<2>",
            text,
            count=1,
        )
        text = re.sub(
            r"(listener \{\n\s+timeout = )\d+(\n\s+on-timeout = omarchy-system-lock)",
            rf"\g<1>{lock_seconds}\g<2>",
            text,
            count=1,
        )
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(text)
        os.replace(tmp, path)
        if os.environ.get("HYPRLAND_INSTANCE_SIGNATURE"):
            import subprocess
            subprocess.run(["hyprctl", "reload"], check=False, timeout=5)
    except FileNotFoundError:
        print(f"{path} not found, skipping Hypridle update")


def is_tablet_mode():
    try:
        mode_file = f"/run/user/{os.getuid()}/omarchy-mode"
        if os.path.exists(mode_file):
            with open(mode_file, "r") as f:
                return f.read().strip() == "tablet"
    except Exception:
        pass
    return False


if __name__ == "__main__":
    prev_combo = None
    backed_up = False
    # Ensure config exists; exit if it doesn't (nothing to edit)
    if not os.path.isfile(CONFIG_PATH):
        # nothing to do
        print(f"{CONFIG_PATH} not found, exiting")
        raise SystemExit(0)

    while True:
        try:
            state = get_power_state()
            tablet = is_tablet_mode()
            combo = (state, tablet)
            if combo != prev_combo:
                cfg = load_config(CONFIG_PATH)
                if cfg is None:
                    # wait and retry
                    prev_combo = combo
                    time.sleep(POLL_INTERVAL)
                    continue

                # backup once
                if not backed_up:
                    backup_once(CONFIG_PATH)
                    backed_up = True

                idle = cfg.get("idle") if isinstance(cfg.get("idle"), dict) else {}
                current_screensaver = idle.get("screensaver")
                current_lock = idle.get("lock")

                target_screensaver = AC_SECONDS if state == "ac" else BATTERY_SECONDS
                target_lock = 0 if tablet else target_screensaver

                if current_screensaver != target_screensaver or current_lock != target_lock:
                    # set without touching other fields
                    if not isinstance(cfg.get("idle"), dict):
                        cfg["idle"] = {}
                    cfg["idle"]["screensaver"] = target_screensaver
                    cfg["idle"]["lock"] = target_lock
                    # persist
                    write_config_atomic(CONFIG_PATH, cfg)
                    print(f"[{datetime.datetime.now().isoformat()}] updated idle: screensaver={target_screensaver}, lock={target_lock} (state={state}, tablet={tablet})")
                update_hypridle(HYPRIDLE_PATH, target_screensaver, (target_screensaver + HYPRIDLE_MARGIN) if not tablet else 0)
                prev_combo = combo
        except Exception as e:
            # swallow and retry
            print("error in power-idle-adjust:", e)
        time.sleep(POLL_INTERVAL)
