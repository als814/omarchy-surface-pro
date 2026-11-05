#!/bin/bash
# Mode hook: Suppress screen locking in Tablet Mode while preserving display screensaver
MODE="$1"
SHELL_JSON="$HOME/.config/omarchy/shell.json"

if [ ! -f "$SHELL_JSON" ]; then
  exit 0
fi

if [ "$MODE" = "tablet" ]; then
  # Disable idle screen lock (screensaver display sleep remains active)
  python3 -c "
import json
try:
    with open('$SHELL_JSON', 'r') as f:
        d = json.load(f)
    if 'idle' not in d:
        d['idle'] = {}
    if d['idle'].get('lock') != 0:
        d['idle']['lock'] = 0
        with open('$SHELL_JSON', 'w') as f:
            json.dump(d, f, indent=2)
except Exception:
    pass
"
elif [ "$MODE" = "laptop" ]; then
  # Restore normal screen lock (matches screensaver timeout, power-idle-adjust manages AC/battery)
  python3 -c "
import json
try:
    with open('$SHELL_JSON', 'r') as f:
        d = json.load(f)
    if 'idle' not in d:
        d['idle'] = {}
    target = d['idle'].get('screensaver', 900)
    if target == 0:
        target = 900
    if d['idle'].get('lock') != target:
        d['idle']['lock'] = target
        with open('$SHELL_JSON', 'w') as f:
            json.dump(d, f, indent=2)
except Exception:
    pass
"
fi
