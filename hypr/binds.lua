-- Omarchy-style keys on Dux Shell. Loaded last from hyprland.lua, so these
-- win over dms/binds.lua and dms/binds-user.lua. Menu logic: ~/.local/bin/dux-menu

hl.unbind("SUPER + space")
hl.unbind("SUPER + K")

-- Full path: Hyprland's PATH does not always include ~/.local/bin
hl.bind("SUPER + space", hl.dsp.exec_cmd("$HOME/.local/bin/dux-menu"), { description = "Menu" })
hl.bind("SUPER + ALT + space", hl.dsp.exec_cmd("$HOME/.local/bin/dux-menu apps"), { description = "Apps" })
hl.bind("SUPER + CTRL + space", hl.dsp.exec_cmd("dms ipc call wallpaperCarousel toggle"), { description = "Wallpaper carousel" })
hl.bind("SUPER + CTRL + SHIFT + space", hl.dsp.exec_cmd("$HOME/.local/bin/dux-menu style"), { description = "Style menu" })
hl.bind("SUPER + K", hl.dsp.exec_cmd("dms ipc call keybinds toggle hyprland"), { description = "Keybind cheatsheet" })
hl.bind("SUPER + Escape", hl.dsp.exec_cmd("dms ipc call powermenu toggle"), { description = "Power menu" })

-- Terminals opened from the menu (install, update, about)
hl.window_rule({
	name = "dux-menu-terminal",
	match = { class = "^(dux\\.menu\\.float)$" },
	float = true,
	size = "1200 750",
	center = true,
})
