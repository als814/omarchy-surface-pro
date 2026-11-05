#!/bin/bash
# Mode hook: Ensure OSK is hidden when returning to Laptop Mode
MODE="$1"

if [ "$MODE" = "laptop" ]; then
  if command -v surface-osk >/dev/null 2>&1; then
    surface-osk hide >/dev/null 2>&1 || true
  elif [ -x "$HOME/bin/surface-osk" ]; then
    "$HOME/bin/surface-osk" hide >/dev/null 2>&1 || true
  fi
fi
