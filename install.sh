#!/usr/bin/env bash
# ==============================================================================
# Omarchy Linux 2-in-1 Hybrid Tablet Suite for Microsoft Surface Pro 5
# Installer & Deployment Script
# ==============================================================================

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_DIR="$HOME/bin"
LOCAL_BIN="$HOME/.local/bin"
OMARCHY_HOOKS="$HOME/.config/omarchy/hooks/mode-set.d"
OMARCHY_PLUGINS="$HOME/.config/omarchy/plugins"
SYSTEMD_USER_DIR="$HOME/.config/systemd/user"
HYPR_DIR="$HOME/.config/hypr"

COLOR_GREEN="\033[1;32m"
COLOR_BLUE="\033[1;34m"
COLOR_YELLOW="\033[1;33m"
COLOR_RED="\033[1;31m"
COLOR_RESET="\033[0m"

log_info() { echo -e "${COLOR_BLUE}[INFO]${COLOR_RESET} $*"; }
log_ok()   { echo -e "${COLOR_GREEN}[OK]${COLOR_RESET} $*"; }
log_warn() { echo -e "${COLOR_YELLOW}[WARN]${COLOR_RESET} $*"; }
log_err()  { echo -e "${COLOR_RED}[ERROR]${COLOR_RESET} $*"; }

echo -e "${COLOR_BLUE}==================================================================${COLOR_RESET}"
echo -e "${COLOR_GREEN}  Omarchy Surface Pro 5 - Tablet Mode & Gesture Suite Installer   ${COLOR_RESET}"
echo -e "${COLOR_BLUE}==================================================================${COLOR_RESET}"

# 1. Check prerequisites
log_info "Checking prerequisites..."

missing_pkgs=()
command -v python3 >/dev/null 2>&1 || missing_pkgs+=("python")
command -v hyprctl >/dev/null 2>&1 || missing_pkgs+=("hyprland")
command -v quickshell >/dev/null 2>&1 || missing_pkgs+=("quickshell")

if [ ${#missing_pkgs[@]} -gt 0 ]; then
  log_err "Missing core packages: ${missing_pkgs[*]}"
  exit 1
fi

if ! python3 -c "import evdev" 2>/dev/null; then
  log_warn "python-evdev is missing. Install with: sudo pacman -S python-evdev"
fi

if ! python3 -c "import dbus, gi" 2>/dev/null; then
  log_warn "python-dbus or python-gobject is missing. Install with: sudo pacman -S python-dbus python-gobject"
fi

if ! command -v wvkbd-mobintl >/dev/null 2>&1 && ! command -v wvkbd >/dev/null 2>&1; then
  log_warn "wvkbd is not installed. Recommended: yay -S wvkbd"
fi

# 2. Deploy User Binaries
log_info "Installing user scripts to ~/bin and ~/.local/bin..."
mkdir -p "$BIN_DIR" "$LOCAL_BIN"

for script in surface-tablet-mode.py surface-rotate.py surface-osk surface-touch-rclick.py omarchy-system-lock surface-volume-nav; do
  if [ -f "$REPO_DIR/bin/$script" ]; then
    install -m 755 "$REPO_DIR/bin/$script" "$BIN_DIR/$script"
    ln -sf "$BIN_DIR/$script" "$LOCAL_BIN/$script"
  fi
done

# CLI convenience aliases
ln -sf "$BIN_DIR/surface-tablet-mode.py" "$LOCAL_BIN/omarchy-mode"
ln -sf "$BIN_DIR/surface-rotate.py" "$LOCAL_BIN/surface-rotate"
ln -sf "$BIN_DIR/surface-rotate.py" "$LOCAL_BIN/auto-rotate"
ln -sf "$BIN_DIR/surface-touch-rclick.py" "$LOCAL_BIN/surface-touch-rclick"

if command -v wvkbd-mobintl >/dev/null 2>&1 && ! command -v wvkbd >/dev/null 2>&1; then
  ln -sf "$(command -v wvkbd-mobintl)" "$LOCAL_BIN/wvkbd"
fi

log_ok "Binaries installed."

# 3. Deploy Omarchy Mode Hooks
log_info "Deploying Omarchy mode hooks to $OMARCHY_HOOKS..."
mkdir -p "$OMARCHY_HOOKS"

for hook in "$REPO_DIR"/config/omarchy/hooks/mode-set.d/*.sh; do
  if [ -f "$hook" ]; then
    install -m 755 "$hook" "$OMARCHY_HOOKS/"
  fi
done
log_ok "Mode hooks installed."

# 4. Deploy Quickshell Plugin
log_info "Deploying Quickshell plugin 'surface.homebar'..."
mkdir -p "$OMARCHY_PLUGINS"
rm -rf "$OMARCHY_PLUGINS/surface.homebar"
cp -r "$REPO_DIR/config/omarchy/plugins/surface.homebar" "$OMARCHY_PLUGINS/"
log_ok "Plugin deployed to $OMARCHY_PLUGINS/surface.homebar"

# 5. Deploy Systemd User Services
log_info "Configuring systemd user services..."
mkdir -p "$SYSTEMD_USER_DIR"
install -m 644 "$REPO_DIR/config/systemd/user/surface-tablet-mode.service" "$SYSTEMD_USER_DIR/"
install -m 644 "$REPO_DIR/config/systemd/user/surface-auto-rotate.service" "$SYSTEMD_USER_DIR/"
install -m 644 "$REPO_DIR/config/systemd/user/surface-touch-rclick.service" "$SYSTEMD_USER_DIR/"

systemctl --user daemon-reload
systemctl --user enable --now surface-tablet-mode.service
systemctl --user enable --now surface-auto-rotate.service
systemctl --user enable --now surface-touch-rclick.service
log_ok "Systemd services enabled and active."

# 6. Hyprland Configuration Check
log_info "Checking Hyprland gestures and input config..."
if [ -f "$HYPR_DIR/input.lua" ]; then
  if ! grep -q "workspace_swipe_touch" "$HYPR_DIR/input.lua"; then
    log_warn "workspace_swipe_touch not found in $HYPR_DIR/input.lua"
    echo "  You can add touch gestures from $REPO_DIR/config/hypr/input.lua to your config."
  else
    log_ok "Touchscreen gestures already configured in $HYPR_DIR/input.lua."
  fi
else
  mkdir -p "$HYPR_DIR"
  cp "$REPO_DIR/config/hypr/input.lua" "$HYPR_DIR/input.lua"
  log_ok "Copied input.lua to $HYPR_DIR/input.lua"
fi

# 7. System-level Tweaks (Optional / sudo)
echo ""
echo -e "${COLOR_YELLOW}[System Configuration]${COLOR_RESET}"
echo "Hardware udev rules, sleep-resume hooks, and power button handler require root permissions."

install_system=false
if [ "${1:-}" = "--system" ]; then
  install_system=true
elif [ "$EUID" -eq 0 ]; then
  install_system=true
fi

if [ "$install_system" = true ]; then
  log_info "Installing system rules..."
  sudo cp "$REPO_DIR/system/udev/90-surface-typecover.rules" /etc/udev/rules.d/
  sudo udevadm control --reload-rules && sudo udevadm trigger
  sudo cp "$REPO_DIR/system/system-sleep/surface-typecover-resume" /usr/lib/systemd/system-sleep/
  sudo chmod +x /usr/lib/systemd/system-sleep/surface-typecover-resume
  sudo cp "$REPO_DIR/bin/surface-power-button" /usr/local/bin/surface-power-button
  sudo chmod +x /usr/local/bin/surface-power-button
  log_ok "System rules and power button installed successfully."
else
  echo "To install system-level rules, run:"
  echo "  sudo ./install.sh --system"
fi

echo ""
echo -e "${COLOR_GREEN}==================================================================${COLOR_RESET}"
echo -e "${COLOR_GREEN}  Installation Complete!                                          ${COLOR_RESET}"
echo -e "${COLOR_GREEN}  Current Mode: $(cat /run/user/$(id -u)/omarchy-mode 2>/dev/null || echo 'laptop') ${COLOR_RESET}"
echo -e "${COLOR_GREEN}==================================================================${COLOR_RESET}"
