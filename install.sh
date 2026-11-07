#!/usr/bin/env bash
# Install dux-menu from the repo onto this machine.
#
#   ./install.sh                       install the script and keybinds
#   ./install.sh --wallpapers DIR      also point the wallpaper carousel at DIR
#
# Existing files that differ are kept as *.bak. hyprland.lua only gets one
# line appended (require("custom.binds")), after the file it loads exists.

set -euo pipefail

REPO=$(cd "$(dirname "$(readlink -f "$0")")" && pwd)
HYPR="$HOME/.config/hypr"
WALLPAPERS=""

while [ $# -gt 0 ]; do
	case $1 in
	--wallpapers)
		WALLPAPERS=$(readlink -f "${2:?--wallpapers needs a folder}")
		shift 2
		;;
	-h | --help)
		sed -n '2,8p' "$0"
		exit 0
		;;
	*)
		echo "unknown option: $1" >&2
		exit 64
		;;
	esac
done

# put SRC DEST: copy, keeping a differing existing DEST as DEST.bak
put() {
	mkdir -p "$(dirname "$2")"
	if [ -f "$2" ] && ! cmp -s "$1" "$2"; then
		cp -p "$2" "$2.bak"
		echo "backed up: $2.bak"
	fi
	cp "$1" "$2"
	echo "installed: $2"
}

for t in dms hyprctl jq; do
	command -v "$t" >/dev/null || { echo "missing dependency: $t" >&2; exit 1; }
done

put "$REPO/bin/dux-menu" "$HOME/.local/bin/dux-menu"
chmod +x "$HOME/.local/bin/dux-menu"

# The binds file must exist before hyprland.lua requires it: a failing
# require stops the rest of hyprland.lua.
put "$REPO/hypr/binds.lua" "$HYPR/custom/binds.lua"

if [ -f "$HYPR/hyprland.lua" ]; then
	if grep -qE '^[[:space:]]*require\(["'"'"']custom\.binds["'"'"']\)' "$HYPR/hyprland.lua"; then
		echo "unchanged: hyprland.lua already loads custom.binds"
	else
		cp -p "$HYPR/hyprland.lua" "$HYPR/hyprland.lua.backup-before-dux-menu"
		printf '\nrequire("custom.binds")\n' >>"$HYPR/hyprland.lua"
		echo "updated:   hyprland.lua (backup: hyprland.lua.backup-before-dux-menu)"
	fi
else
	echo "no $HYPR/hyprland.lua found: add require(\"custom.binds\") to your Lua config yourself" >&2
fi

if [ -n "$WALLPAPERS" ]; then
	[ -d "$WALLPAPERS" ] || { echo "not a folder: $WALLPAPERS" >&2; exit 1; }
	settings="$HOME/.config/dms/plugin_settings.json"
	cp -p "$settings" "$settings.bak"
	jq --arg d "$WALLPAPERS" '.wallpaperCarousel.wallpaperDirectory = $d' "$settings" >"$settings.tmp"
	mv "$settings.tmp" "$settings"
	echo "updated:   wallpaper carousel folder -> $WALLPAPERS (backup: $settings.bak)"
	# Dux only reads plugin settings at startup
	dms restart >/dev/null 2>&1 && echo "restarted: Dux Shell"
fi

sleep 1
if command -v hyprctl >/dev/null && [ -n "${HYPRLAND_INSTANCE_SIGNATURE:-}" ]; then
	errors=$(hyprctl configerrors)
	if [ -n "${errors//[[:space:]]/}" ]; then
		echo "Hyprland reports config errors:" >&2
		echo "$errors" >&2
		exit 1
	fi
	echo "Hyprland config: no errors"
fi
