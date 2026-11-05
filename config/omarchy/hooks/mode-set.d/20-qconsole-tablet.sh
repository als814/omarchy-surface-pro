#!/bin/bash
# Mode hook: Auto-dismiss Quake console when entering Tablet mode
MODE="$1"

if [ "$MODE" = "tablet" ]; then
  if hyprctl monitors -j | grep -q '"special:qconsole"'; then
    hyprctl dispatch "hl.dsp.workspace.toggle_special('qconsole')"
  fi
fi
