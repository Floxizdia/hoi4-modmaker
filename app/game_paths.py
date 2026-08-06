"""Where Hearts of Iron IV and its user folder live on this machine.

Every screen used to carry its own hardcoded
`C:\\Program Files (x86)\\Steam\\...` string, which is wrong for anyone whose
Steam library sits on another drive and impossible on Linux or macOS. The
paths are searched here instead, once, in the order Steam actually uses:

* the location the user pinned in this app's settings, if any;
* Steam's own `libraryfolders.vdf`, which lists every library drive - this
  is what finds a game installed to D:\\SteamLibrary;
* the default install location for the running platform.

Nothing here creates directories or falls over when the game is missing; a
caller that gets "" is expected to say so rather than crash.
"""

import json
import os
import re
import sys

APP_ID = "394360"
GAME_DIR_NAME = "Hearts of Iron IV"
WORKSHOP_REL = os.path.join("steamapps", "workshop", "content", APP_ID)

CONFIG_DIR = os.path.join(
    os.environ.get("APPDATA") or os.path.join(os.path.expanduser("~"), ".config"),
    "HOI4ModMaker")
PATHS_FILE = os.path.join(CONFIG_DIR, "game_paths.json")

_LIBRARY_PATH_RE = re.compile(r'"path"\s*"([^"]+)"')


def _steam_roots():
    """Candidate Steam installation roots for the running platform."""
    home = os.path.expanduser("~")
    if sys.platform == "win32":
        program_files = [os.environ.get("ProgramFiles(x86)"),
                         os.environ.get("ProgramFiles"),
                         r"C:\Program Files (x86)", r"C:\Program Files"]
        roots = [os.path.join(p, "Steam") for p in program_files if p]
        roots += [f"{letter}:\\Steam" for letter in "CDEFG"]
        return roots
    if sys.platform == "darwin":
        return [os.path.join(home, "Library", "Application Support", "Steam")]
    return [
        os.path.join(home, ".steam", "steam"),
        os.path.join(home, ".steam", "root"),
        os.path.join(home, ".local", "share", "Steam"),
        os.path.join(home, ".var", "app", "com.valvesoftware.Steam",
                     "data", "Steam"),          # Flatpak
    ]


def _library_roots():
    """Every Steam library on this machine, read from libraryfolders.vdf so
    a game installed to a second drive is still found."""
    roots = []
    for steam_root in _steam_roots():
        if not os.path.isdir(steam_root):
            continue
        roots.append(steam_root)
        # Steam has kept this file in both places over the years
        for vdf in (os.path.join(steam_root, "steamapps", "libraryfolders.vdf"),
                    os.path.join(steam_root, "config", "libraryfolders.vdf")):
            try:
                with open(vdf, "r", encoding="utf-8", errors="ignore") as handle:
                    text = handle.read()
            except OSError:
                continue
            for path in _LIBRARY_PATH_RE.findall(text):
                roots.append(path.replace("\\\\", "\\"))
    return roots


def _pinned():
    try:
        with open(PATHS_FILE, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def save_pinned(base_game=None, workshop=None):
    """Remember paths the user picked by hand, for installs the search
    can't reach (a game moved outside Steam, a network drive).

    None leaves a setting alone; an empty string clears it, which is how
    "detect again" drops a pin and falls back to the search."""
    data = _pinned()
    for key, value in (("base_game", base_game), ("workshop", workshop)):
        if value is None:
            continue
        if value:
            data[key] = value
        else:
            data.pop(key, None)
    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(PATHS_FILE, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2)
    except OSError:
        pass


def find_base_game():
    """The game's install folder, or "" when it isn't on this machine."""
    pinned = _pinned().get("base_game")
    if pinned and os.path.isdir(pinned):
        return pinned
    for root in _library_roots():
        candidate = os.path.join(root, "steamapps", "common", GAME_DIR_NAME)
        if os.path.isdir(candidate):
            return candidate
    return ""


def find_workshop():
    """The Workshop download folder for HOI4, or "" if there isn't one."""
    pinned = _pinned().get("workshop")
    if pinned and os.path.isdir(pinned):
        return pinned
    for root in _library_roots():
        candidate = os.path.join(root, WORKSHOP_REL)
        if os.path.isdir(candidate):
            return candidate
    return ""


def user_dir_candidates():
    """Where the launcher keeps mod/, settings and saves. Windows puts this
    under Documents (and OneDrive redirects it, in whatever language the
    user's Windows is in); Linux and macOS use their own conventions."""
    home = os.path.expanduser("~")
    if sys.platform == "win32":
        docs = ["Documents", "OneDrive/Documents", "OneDrive/Belgeler", "Belgeler",
                "Dokumente", "Documenti", "Documentos"]
        return [os.path.join(home, *part.split("/"), "Paradox Interactive", GAME_DIR_NAME)
                for part in docs]
    if sys.platform == "darwin":
        return [os.path.join(home, "Documents", "Paradox Interactive", GAME_DIR_NAME)]
    return [
        os.path.join(home, ".local", "share", "Paradox Interactive", GAME_DIR_NAME),
        os.path.join(home, "Documents", "Paradox Interactive", GAME_DIR_NAME),
        # Proton keeps a Windows-shaped Documents tree inside the prefix
        os.path.join(home, ".steam", "steam", "steamapps", "compatdata", APP_ID,
                     "pfx", "drive_c", "users", "steamuser", "Documents",
                     "Paradox Interactive", GAME_DIR_NAME),
    ]


def open_folder(path):
    """Show a folder in the platform's file manager."""
    import subprocess
    if not path or not os.path.isdir(path):
        return False
    try:
        if sys.platform == "win32":
            os.startfile(path)                                   # noqa: S606
        elif sys.platform == "darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])
    except (OSError, AttributeError):
        return False
    return True
