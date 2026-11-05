-- Keep only your personal keybinding overrides here. Add new bindings or
-- unbind defaults before replacing them.

-- See current bindings and descriptions:
--   omarchy menu keybindings --print

-- To disable every Omarchy default binding, set this in
-- ~/.config/hypr/hyprland.lua before require("default.hypr.omarchy"), then add
-- only the bindings you want below:
--   omarchy_default_bindings = false

-- To disable all preinstalled app/webapp bindings, set:
--   omarchy_preinstalled_bindings = false

-- Add a new binding.
-- o.bind("SUPER + SHIFT + R", "SSH", "alacritty -e ssh your-server")

-- Change an existing binding by unbinding it first, then binding the key again.
-- This example changes SUPER+SPACE from the launcher to the Omarchy root menu.
-- hl.unbind("SUPER + SPACE")
-- o.bind("SUPER + SPACE", "Omarchy menu", "omarchy-menu toggle root")

-- Disable a default binding without replacing it.
-- hl.unbind("SUPER + SHIFT + B")

-- Logitech MX Keys examples:
-- o.bind("SUPER + SHIFT + S", nil, "omarchy-capture-screenshot")
-- o.bind("SUPER + H", nil, "voxtype record toggle")
-- o.bind("SUPER + PERIOD", nil, "omarchy-shell shell toggle omarchy.emojis")
dofile(os.getenv("HOME") .. "/.config/omarchy/plugins/vbrosseau.alttab/omarchy-plugin/alttab-bindings.lua")

hl.unbind("SUPER + TAB")
o.bind("SUPER + TAB", "Former workspace", hl.dsp.focus({ workspace = "previous" }))

-- Rebind power button to instant suspend with resume-debounce protection
o.rebind("XF86PowerOff", "Suspend", "/usr/local/bin/surface-power-button", { locked = true })

-- Rebind volume buttons: Smart terminal navigation in Tablet Mode, native volume in Laptop Mode
o.rebind("XF86AudioRaiseVolume", "Volume / Menu Up", os.getenv("HOME") .. "/bin/surface-volume-nav up", { locked = true, repeating = true })
o.rebind("XF86AudioLowerVolume", "Volume / Menu Down", os.getenv("HOME") .. "/bin/surface-volume-nav down", { locked = true, repeating = true })

