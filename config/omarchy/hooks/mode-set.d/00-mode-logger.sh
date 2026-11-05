#!/bin/bash
# Hook executed on mode change
# Arguments: $1 = mode (laptop|tablet), $2 = reason
MODE="$1"
REASON="$2"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Mode switched to: $MODE ($REASON)" >> "${XDG_STATE_HOME:-$HOME/.local/state}/omarchy-mode-events.log"
