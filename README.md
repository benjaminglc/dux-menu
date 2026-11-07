# dux-menu

An Omarchy-style menu and keybinds for [Dux Shell](https://duxlabs.dev) (formerly DankMaterialShell) on Hyprland. It uses Dux's own picker (`dms dmenu`), Spotlight and panels, so there's no second launcher or shell to install.

## Keys

| Key | Action |
|---|---|
| Super+Space | Menu |
| Super+Alt+Space | Apps (Spotlight) |
| Super+Ctrl+Space | Wallpaper carousel |
| Super+Ctrl+Shift+Space | Style menu |
| Super+K | Keybind cheatsheet |
| Super+Escape | Power menu |

They replace Dux's defaults for Super+Space (Spotlight) and Super+K (focus up). All six show up in the Dux keybind cheatsheet.

## Menu

| Entry | Contents |
|---|---|
| Apps | Spotlight |
| Style | Wallpaper (carousel), Light / Dark, Theme, Fonts, Bar |
| Setup | Displays, Audio, Volume Control, Network, Keyboard, Mouse & Touchpad, Keybinds, Default Apps, Autostart, Power & Sleep, Window Rules |
| Install | Package (`paru` with `fzf`), Flatpak |
| Remove | Package, Flatpak |
| Update | System (`arch-update`, or `paru -Syu`), Dux Plugins, Firmware (`fwupdmgr`), Mirrors (`cachyos-rate-mirrors`) |
| About | `fastfetch` |
| System | Dux power menu |

Entries whose tool isn't installed are hidden. Install, Remove and Update run in a floating terminal and ask for your password themselves.

**Search:** start typing right after Super+Space. Text that matches a menu entry picks it. Anything else leaves only Apps visible, and Enter opens Spotlight with your text, which searches apps, settings, files and commands.

**Navigation:** Esc in a submenu goes back to the main menu. A click outside, Super+Space again, or opening another Dux panel closes the menu.

## Requirements

- Hyprland 0.55+ with the Lua config (`~/.config/hypr/hyprland.lua`)
- Dux Shell 2.x (the `dms` CLI), plus `jq`
- `ghostty` for the terminal entries
- Optional: `paru`, `flatpak`, `fzf`, `arch-update`, `fwupdmgr`, `cachyos-rate-mirrors`, `fastfetch`, `pavucontrol`
- Optional: the [wallpaperCarousel](https://github.com/motor-dev/wallpaperCarousel) Dux plugin for Style → Wallpaper and Super+Ctrl+Space

Tested on CachyOS with Hyprland 0.57.1 and Dux Shell 2.1.0.

## Install

```bash
./install.sh
```

This installs `~/.local/bin/dux-menu` and `~/.config/hypr/custom/binds.lua`, then appends `require("custom.binds")` to `hyprland.lua` if it's missing. Hyprland reloads on its own. Existing files that differ are kept as `*.bak`.

To also point the wallpaper carousel at a folder (this restarts Dux once, because it only reads plugin settings at startup):

```bash
./install.sh --wallpapers ~/Pictures/wallpapers
```

If `dms setup` ever rewrites `hyprland.lua` and the keys stop working, run `./install.sh` again.

## Updating the repo

After changing the installed files, copy them back into the repo:

```bash
./sync.sh
```

It only copies and shows `git status`; committing and pushing is up to you.

| Installed file | In the repo |
|---|---|
| `~/.local/bin/dux-menu` | `bin/dux-menu` |
| `~/.config/hypr/custom/binds.lua` | `hypr/binds.lua` |

## Testing

`tests/e2e.py` drives the real menu with a temporary virtual keyboard: 55 checks covering every key, menu entry, the search hand-off and the edge cases below. It needs write access to `/dev/uinput` (the `input` group). Don't touch the keyboard or mouse for about three minutes while it runs.

```bash
python3 tests/e2e.py
```

Plain keys like Enter and Esc are only sent while the menu's own picker is open. Screenshots land in `tests/out/`.

## Icons

Menu rows use standard icon names (for example `preferences-system`), so they follow your icon theme. Change it in Dux Settings → Theme → Icons. Material Symbols names don't work for picker rows, only for the prompt badge.

## How it handles `dms dmenu` quirks

Found by testing with Dux Shell 2.0/2.1:

- A second `dms dmenu` queues behind an open one, so pressing the key again closes the open picker over IPC.
- `spotlight open` while a picker is up strands its client, and every later picker then waits with nothing on screen. Apps closes the menu first, and a stranded menu is detected and cleared.
- Esc, a click outside, and other panels all end the picker with the same exit code. Esc is bound as a custom key (exit code 10) so only Esc goes back.
- Hyprland's `PATH` doesn't always include `~/.local/bin`, so the binds use `$HOME/.local/bin/dux-menu`.

## Uninstall

```bash
rm ~/.local/bin/dux-menu ~/.config/hypr/custom/binds.lua
```

Then remove the `require("custom.binds")` line from `hyprland.lua`, or restore `hyprland.lua.backup-before-dux-menu`.
