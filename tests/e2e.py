#!/usr/bin/env python3
"""End-to-end test of dux-menu through real key presses (virtual keyboard).

Needs write access to /dev/uinput (member of the `input` group) and the menu
installed. Don't touch the keyboard or mouse while it runs (about 3 minutes):
menus, settings pages and terminals open and close by themselves.

Plain Enter/Esc/Down/letters are only sent while dux-menu's own picker is
open; Super+... combos are consumed by Hyprland binds, so they are safe in
any focus. Screenshots go to tests/out/.
"""
import fcntl, json, os, struct, subprocess as sp, sys, time

UI_SET_EVBIT, UI_SET_KEYBIT = 0x40045564, 0x40045565
UI_DEV_SETUP, UI_DEV_CREATE, UI_DEV_DESTROY = 0x405c5503, 0x5501, 0x5502
K = {"esc": 1, "enter": 28, "down": 108, "space": 57, "k": 37,
     "super": 125, "alt": 56, "ctrl": 29, "shift": 42,
     # letters whose position is the same on QWERTY and QWERTZ layouts
     "q": 16, "w": 17, "e": 18, "r": 19, "t": 20, "u": 22, "i": 23, "o": 24, "p": 25,
     "a": 30, "s": 31, "d": 32, "f": 33, "l": 38, "x": 45, "v": 47, "m": 50}
STATE = os.path.join(os.environ["XDG_RUNTIME_DIR"], "dux-menu")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
RESULTS = []
PRE_PAVU = set()


class Abort(Exception):
    pass


def sh(*a):
    return sp.run(a, capture_output=True, text=True).stdout.strip()


def shot(name):
    """Screenshot of the focused monitor into tests/out/."""
    os.makedirs(OUT, exist_ok=True)
    mon = next((m["name"] for m in json.loads(sh("hyprctl", "monitors", "-j")) if m["focused"]), None)
    sh("grim", *(["-o", mon] if mon else []), os.path.join(OUT, name))


def layers():
    data = json.loads(sh("hyprctl", "layers", "-j"))
    out = set()
    for mon in data.values():
        for lvl in mon["levels"].values():
            for l in lvl:
                ns = l["namespace"]
                if not any(x in ns for x in ("desktop-widget", "precache")) and ns not in ("quickshell", "dms:bar"):
                    out.add(ns)
    return out


def clients():
    return json.loads(sh("hyprctl", "clients", "-j"))


def read(name):
    try:
        return open(os.path.join(STATE, name)).read().strip()
    except OSError:
        return ""


def alive(pid):
    return pid.isdigit() and os.path.exists(f"/proc/{pid}")


def menu_prompt():
    """Prompt of dux-menu's live picker, or None."""
    d = read("dmenu")
    if not alive(d):
        return None
    args = open(f"/proc/{d}/cmdline").read().split("\0")
    return args[args.index("-p") + 1] if "-p" in args else "?"


def strays():
    return sh("pgrep", "-f", "^dms dmenu ").split()


def owners():
    # Only the installed script run by bash, not shells whose text mentions it
    return sh("pgrep", "-f", r"^(/usr/bin/)?bash [^ ]*\.local/bin/dux-menu").split()


class Kbd:
    def __init__(self):
        self.fd = os.open("/dev/uinput", os.O_WRONLY | os.O_NONBLOCK)
        fcntl.ioctl(self.fd, UI_SET_EVBIT, 1)
        for c in K.values():
            fcntl.ioctl(self.fd, UI_SET_KEYBIT, c)
        fcntl.ioctl(self.fd, UI_DEV_SETUP, struct.pack("HHHH80sI", 3, 0x1234, 0x5679, 1, b"dux-menu-e2e-kbd", 0))
        fcntl.ioctl(self.fd, UI_DEV_CREATE)
        time.sleep(1.0)

    def _ev(self, code, val):
        os.write(self.fd, struct.pack("qqHHi", 0, 0, 1, code, val))
        os.write(self.fd, struct.pack("qqHHi", 0, 0, 0, 0, 0))
        time.sleep(0.02)

    def combo(self, *keys):
        """Super+... combos: Hyprland binds consume them, safe in any focus."""
        assert keys[0] == "super"
        for k in keys:
            self._ev(K[k], 1)
        for k in reversed(keys):
            self._ev(K[k], 0)

    def key(self, k):
        if menu_prompt() is None or "dms:spotlight" not in layers():
            raise Abort(f"refused {k}: dux-menu picker not open")
        self._ev(K[k], 1)
        self._ev(K[k], 0)

    def type(self, text):
        for ch in text:
            self.key(ch)
            time.sleep(0.04)

    def close(self):
        fcntl.ioctl(self.fd, UI_DEV_DESTROY)
        os.close(self.fd)


def wait(cond, timeout=3.0):
    t0 = time.time()
    while time.time() - t0 < timeout:
        v = cond()
        if v:
            return v
        time.sleep(0.05)
    return None


def check(name, ok, info=""):
    RESULTS.append((name, bool(ok)))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name} {info}")


def settle():
    """Close everything and wait until nothing of ours is left."""
    for t in ("spotlight", "wallpaperCarousel", "keybinds", "powermenu", "settings"):
        sh("dms", "ipc", "call", t, "close")
    for pid in sh("pgrep", "-x", "pavucontrol").split():
        if pid not in PRE_PAVU:  # only windows this test opened
            sp.run(["kill", pid])
    sp.run(["pkill", "-f", "dux-menu __task"])
    wait(lambda: not owners() and not strays() and "dms:spotlight" not in layers(), 3)
    time.sleep(0.4)


def open_menu(kb, *combo):
    kb.combo(*combo)
    return wait(lambda: menu_prompt() if "dms:spotlight" in layers() else None)


def choose(kb, index, expect_prompt=None):
    time.sleep(0.25)
    for _ in range(index):
        kb.key("down")
        time.sleep(0.05)
    kb.key("enter")
    if expect_prompt:
        return wait(lambda: menu_prompt() == expect_prompt and "dms:spotlight" in layers())


def gone():
    return not owners() and not strays()


def settings_open():
    return [c for c in clients() if "duxlabs" in c["class"] or "danklinux" in c["class"]]


def term():
    return wait(lambda: [c for c in clients() if c["class"] == "dux.menu.float"], 5)


def spotlight_only():
    return "dms:spotlight" in layers() and gone() and menu_prompt() is None


def run(kb):
    print("== toggle")
    p = open_menu(kb, "super", "space")
    check("Super+Space opens Menu", p == "Menu", p)
    kb.combo("super", "space")
    check("Super+Space again closes it", wait(lambda: gone() and "dms:spotlight" not in layers()))
    settle()

    print("== mashing Super+Space x5")
    for _ in range(5):
        kb.combo("super", "space")
        time.sleep(0.12)
    time.sleep(1.5)
    n = len(strays())
    check("at most one picker afterwards", n <= 1, f"pickers={n} owners={len(owners())}")
    if n:
        kb.combo("super", "space")
    time.sleep(1)
    check("menu closable after mashing", wait(gone))
    settle()

    print("== submenu, Esc goes back, Esc closes")
    open_menu(kb, "super", "space")
    check("Style submenu opens", choose(kb, 1, "Style"))
    kb.key("esc")
    check("Esc returns to Menu", wait(lambda: menu_prompt() == "Menu" and "dms:spotlight" in layers()))
    time.sleep(0.2)
    kb.key("esc")
    check("Esc on Menu closes everything", wait(lambda: gone() and "dms:spotlight" not in layers()))
    settle()

    print("== click outside / external close inside a submenu closes everything")
    open_menu(kb, "super", "space"); choose(kb, 1, "Style")
    sh("dms", "ipc", "call", "spotlight", "close")
    time.sleep(1.2)
    check("closed, not back to Menu", gone() and "dms:spotlight" not in layers(), str(layers()))
    settle()

    print("== Esc after a filter that matches nothing")
    open_menu(kb, "super", "space"); choose(kb, 1, "Style")
    kb.type("kkk")
    time.sleep(0.3)
    kb.key("esc")
    r = wait(lambda: menu_prompt() == "Menu" and "dms:spotlight" in layers())
    check("Esc still goes back to Menu", r, f"prompt={menu_prompt()} strays={strays()}")
    settle()

    print("== Enter on a filter that matches nothing reopens the same menu")
    open_menu(kb, "super", "space"); choose(kb, 1, "Style")
    kb.type("kkk")
    time.sleep(0.3)
    kb.key("enter")
    time.sleep(1.0)
    check("Style shown again", menu_prompt() == "Style" and "dms:spotlight" in layers(), f"prompt={menu_prompt()}")
    settle()

    print("== Super+Space inside a submenu closes everything")
    open_menu(kb, "super", "space"); choose(kb, 2, "Setup")
    kb.combo("super", "space")
    time.sleep(1.2)
    check("closed, not back to Menu", gone() and "dms:spotlight" not in layers(), str(layers()))
    settle()

    for label, combo, layer in (("Super+K", ("super", "k"), "dms:keybinds"),
                                ("Super+Ctrl+Space", ("super", "ctrl", "space"), "dms:plugins:wallpaperCarousel"),
                                ("Super+Escape", ("super", "esc"), "dms:power-menu")):
        print(f"== {label} while in a submenu")
        open_menu(kb, "super", "space"); choose(kb, 1, "Style")
        kb.combo(*combo)
        time.sleep(1.5)
        L = layers()
        check(f"{label} panel shows, menu not reopened", layer in L and "dms:spotlight" not in L and gone(), str(sorted(L)))
        settle()

    print("== Super+Alt+Space while the menu is open")
    open_menu(kb, "super", "space")
    kb.combo("super", "alt", "space")
    time.sleep(1.5)
    check("Apps open, menu gone, no stranded picker", "dms:spotlight" in layers() and gone() and menu_prompt() is None, str(sorted(layers())))
    kb.combo("super", "alt", "space")
    check("Super+Alt+Space again closes Apps", wait(lambda: "dms:spotlight" not in layers()))
    settle()

    print("== Super+Space while Apps is open")
    kb.combo("super", "alt", "space"); wait(lambda: "dms:spotlight" in layers())
    time.sleep(0.4)
    kb.combo("super", "space")
    time.sleep(1.2)
    check("Menu replaces Apps", menu_prompt() == "Menu" and "dms:spotlight" in layers(), f"prompt={menu_prompt()} layers={sorted(layers())}")
    settle()

    print("== Super+Ctrl+Shift+Space: Style direct, Esc closes")
    p = open_menu(kb, "super", "ctrl", "shift", "space")
    check("Style menu opens", p == "Style", p)
    kb.key("esc")
    check("Esc closes (no parent)", wait(lambda: gone() and "dms:spotlight" not in layers()))
    settle()

    print("== Super+K / Super+Escape / Super+Ctrl+Space toggle")
    for label, combo, layer in (("Super+K", ("super", "k"), "dms:keybinds"),
                                ("Super+Escape", ("super", "esc"), "dms:power-menu"),
                                ("Super+Ctrl+Space", ("super", "ctrl", "space"), "dms:plugins:wallpaperCarousel")):
        kb.combo(*combo)
        a = wait(lambda: layer in layers())
        time.sleep(0.4)
        kb.combo(*combo)
        b = wait(lambda: layer not in layers())
        check(f"{label} opens and closes", a and b)
        settle()

    print("== menu entries")
    open_menu(kb, "super", "space"); choose(kb, 0)
    time.sleep(1.2)
    check("Apps -> Spotlight, no picker client", "dms:spotlight" in layers() and gone())
    settle()

    open_menu(kb, "super", "space"); choose(kb, 1, "Style"); choose(kb, 0)
    check("Style > Wallpaper -> carousel", wait(lambda: "dms:plugins:wallpaperCarousel" in layers()) and wait(gone))
    settle()

    for idx, name in ((2, "Theme"), (3, "Fonts"), (4, "Bar")):
        open_menu(kb, "super", "space"); choose(kb, 1, "Style"); choose(kb, idx)
        w = wait(settings_open, 4)
        check(f"Style > {name} -> Settings window", w, w[0]["title"] if w else "")
        settle()

    mode = sh("dms", "ipc", "call", "theme", "getMode")
    open_menu(kb, "super", "space"); choose(kb, 1, "Style"); choose(kb, 1)
    time.sleep(1.5)
    new = sh("dms", "ipc", "call", "theme", "getMode")
    check("Style > Light / Dark toggles", new != mode, f"{mode} -> {new}")
    sh("dms", "ipc", "call", "theme", mode.lower() if mode.lower() in ("dark", "light") else "toggle")
    check("theme restored", wait(lambda: sh("dms", "ipc", "call", "theme", "getMode") == mode, 4))
    settle()

    setup = ["Displays", "Audio", "Volume Control", "Network", "Keyboard", "Mouse & Touchpad",
             "Keybinds", "Default Apps", "Autostart", "Power & Sleep", "Window Rules"]
    for idx, name in enumerate(setup):
        open_menu(kb, "super", "space"); choose(kb, 2, "Setup"); choose(kb, idx)
        if name == "Volume Control":
            w = wait(lambda: [c for c in clients() if "pavucontrol" in c["class"]], 5)
        else:
            w = wait(settings_open, 4)
        check(f"Setup > {name}", w, w[0]["title"] if w else "")
        settle()

    for path, title in (((3, 0), "Install > Package"), ((3, 1), "Install > Flatpak"),
                        ((4, 0), "Remove > Package"), ((4, 1), "Remove > Flatpak")):
        sub = {3: "Install", 4: "Remove"}[path[0]]
        open_menu(kb, "super", "space"); choose(kb, path[0], sub); choose(kb, path[1])
        w = term()
        info = f"float={w[0]['floating']} size={w[0]['size']} title={w[0]['title']}" if w else ""
        check(f"{title} -> floating terminal", w and w[0]["floating"], info)
        settle()

    open_menu(kb, "super", "space"); choose(kb, 5, "Update")
    time.sleep(0.3)
    check("Update submenu opens", menu_prompt() == "Update")
    time.sleep(0.2); kb.key("esc")
    check("Esc from Update returns to Menu", wait(lambda: menu_prompt() == "Menu" and "dms:spotlight" in layers()))
    time.sleep(0.2); kb.key("esc")
    settle()

    open_menu(kb, "super", "space"); choose(kb, 6)
    w = term()
    check("About -> floating terminal", w and w[0]["floating"], f"size={w[0]['size']}" if w else "")
    settle()

    open_menu(kb, "super", "space"); choose(kb, 7)
    check("System -> power menu", wait(lambda: "dms:power-menu" in layers()) and wait(gone))
    settle()

    print("== type-to-search in the main menu (hand-off to Spotlight)")
    open_menu(kb, "super", "space"); time.sleep(0.6)
    shot("search_empty.png")
    kb.type("volume"); time.sleep(0.5)
    shot("search_volume.png")
    kb.key("enter"); time.sleep(1.2)
    shot("search_handoff.png")
    check("type 'volume' + Enter opens Spotlight with no picker left", spotlight_only())
    settle()

    open_menu(kb, "super", "space"); time.sleep(0.3)
    kb.type("setup"); time.sleep(0.4); kb.key("enter")
    check("type 'setup' + Enter still opens the Setup submenu", wait(lambda: menu_prompt() == "Setup" and "dms:spotlight" in layers()))
    kb.key("esc")
    check("Esc from it returns to Menu", wait(lambda: menu_prompt() == "Menu" and "dms:spotlight" in layers()))
    settle()

    open_menu(kb, "super", "space"); time.sleep(0.3)
    kb.type("set"); time.sleep(0.4); kb.key("down"); time.sleep(0.1); kb.key("enter")
    time.sleep(1.2)
    check("type 'set', Down to Apps, Enter searches instead", spotlight_only(), f"prompt={menu_prompt()}")
    settle()

    open_menu(kb, "super", "space"); time.sleep(0.3)
    kb.key("enter"); time.sleep(1.2)
    check("Enter with nothing typed opens Apps", spotlight_only())
    settle()

    print("== stranded picker recovery")
    open_menu(kb, "super", "space")
    sh("dms", "ipc", "call", "spotlight", "open")  # the known way to strand a picker
    time.sleep(0.8)
    sh("dms", "ipc", "call", "spotlight", "close")
    time.sleep(0.8)
    stranded = bool(strays()) and "dms:spotlight" not in layers()
    print(f"  (stranded state reproduced: {stranded})")
    open_menu(kb, "super", "space")
    time.sleep(0.6)
    check("Super+Space recovers and shows Menu", menu_prompt() == "Menu" and "dms:spotlight" in layers(), f"strays={strays()}")
    kb.combo("super", "space")
    check("and closes cleanly", wait(lambda: gone() and "dms:spotlight" not in layers()))
    settle()


def main():
    PRE_PAVU.update(sh("pgrep", "-x", "pavucontrol").split())
    settle()
    kb = Kbd()
    try:
        run(kb)
    except Abort as e:
        print("ABORTED:", e)
        RESULTS.append(("aborted", False))
    finally:
        settle()
        kb.close()
    bad = [n for n, ok in RESULTS if not ok]
    print(f"\n{len(RESULTS) - len(bad)}/{len(RESULTS)} passed", "FAILED:" if bad else "", bad)
    print("left over: pickers", strays(), "owners", owners(), "layers", sorted(layers()))
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    sys.stdout.reconfigure(line_buffering=True)
    main()
