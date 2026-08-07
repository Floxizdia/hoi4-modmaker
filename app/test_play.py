"""Launch Hearts of Iron IV with the open mod enabled, then hand back
whatever the game wrote to its error log while it was running.

Testing a mod has always meant leaving this app: alt-tab to the launcher,
tick the mod in a playset, start the game, play until something breaks,
quit, then come back and read the log by hand. This closes that loop.

How the mod actually gets enabled: the game reads `dlc_load.json` in the
user folder at startup - a flat list of mod descriptors relative to that
folder, e.g. "mod/my_mod.mod". The launcher generates that file from its
own sqlite playset database, but the game itself only ever looks at the
json, so writing it and starting hoi4 directly is enough. The user's own
selection is put back the moment the game exits, so a test run never
quietly changes which mods they play with.
"""

import json
import os
import re
import subprocess
import sys

from app import game_paths
from app.mod_export import find_user_dir

DLC_LOAD = "dlc_load.json"

#: the selection to put back, written to disk before the game starts. In
#: memory alone it would be lost if Mod Maker is closed (or crashes) while
#: the game is still running, leaving the user with only the test mod
#: enabled and no idea why - so it's a file, replayed on the next start.
PENDING_RESTORE = os.path.join(game_paths.CONFIG_DIR, "dlc_load_restore.json")

_PATH_RE = re.compile(r'^\s*path\s*=\s*"([^"]*)"', re.MULTILINE)
_NAME_RE = re.compile(r'^\s*name\s*=\s*"([^"]*)"', re.MULTILINE)


# ---- dlc_load.json ----

def dlc_load_path(user_dir=None):
    user_dir = user_dir or find_user_dir()
    return os.path.join(user_dir, DLC_LOAD) if user_dir else None


def read_dlc_load(user_dir=None):
    """The launcher's current selection, or a usable empty shape. Other keys
    (disabled_dlcs above all) are preserved so we only ever touch mods."""
    path = dlc_load_path(user_dir)
    if path and os.path.isfile(path):
        try:
            with open(path, "r", encoding="utf-8-sig") as handle:
                data = json.load(handle)
            if isinstance(data, dict):
                data.setdefault("enabled_mods", [])
                data.setdefault("disabled_dlcs", [])
                return data
        except (OSError, ValueError):
            pass
    return {"enabled_mods": [], "disabled_dlcs": []}


def write_dlc_load(data, user_dir=None):
    path = dlc_load_path(user_dir)
    if not path:
        return False
    try:
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=4)
    except OSError:
        return False
    return True


# ---- crash-safe restore ----

def _remember_restore(data, user_dir):
    try:
        os.makedirs(game_paths.CONFIG_DIR, exist_ok=True)
        with open(PENDING_RESTORE, "w", encoding="utf-8") as handle:
            json.dump({"user_dir": user_dir, "dlc_load": data}, handle, indent=2)
    except OSError:
        pass


def _clear_restore():
    try:
        os.remove(PENDING_RESTORE)
    except OSError:
        pass


def restore_pending():
    """Put back a selection left behind by a test run that never finished
    cleanly. Called once at startup; returns True when it actually restored
    something, so the caller can say so."""
    try:
        with open(PENDING_RESTORE, "r", encoding="utf-8") as handle:
            saved = json.load(handle)
    except (OSError, ValueError):
        return False
    _clear_restore()
    if not isinstance(saved, dict) or not isinstance(saved.get("dlc_load"), dict):
        return False
    return write_dlc_load(saved["dlc_load"], saved.get("user_dir"))


# ---- finding the mod's descriptor ----

def descriptor_entries(user_dir=None):
    """[(entry, name, path)] for every .mod file in the user mod folder,
    where `entry` is the "mod/foo.mod" string dlc_load.json wants."""
    user_dir = user_dir or find_user_dir()
    if not user_dir:
        return []
    mod_dir = os.path.join(user_dir, "mod")
    if not os.path.isdir(mod_dir):
        return []

    out = []
    for filename in sorted(os.listdir(mod_dir)):
        if not filename.lower().endswith(".mod"):
            continue
        full = os.path.join(mod_dir, filename)
        try:
            with open(full, "r", encoding="utf-8-sig", errors="ignore") as handle:
                text = handle.read()
        except OSError:
            continue
        name_match = _NAME_RE.search(text)
        path_match = _PATH_RE.search(text)
        out.append((f"mod/{filename}",
                    name_match.group(1) if name_match else filename[:-4],
                    (path_match.group(1) if path_match else "").replace("/", os.sep)))
    return out


def entry_for_mod(mod_root, mod_name=None, user_dir=None):
    """The dlc_load entry that points at this mod, or None when the mod has
    never been exported - matching on the folder it points at first, since
    two mods sharing a display name is far more likely than sharing a path."""
    if not mod_root:
        return None
    target = os.path.normcase(os.path.normpath(mod_root))
    entries = descriptor_entries(user_dir)
    for entry, _name, path in entries:
        if path and os.path.normcase(os.path.normpath(path)) == target:
            return entry
    if mod_name:
        for entry, name, _path in entries:
            if name == mod_name:
                return entry
    return None


# ---- getting the mod somewhere the game will look ----

def export_for_test(mod_root, mod_name, progress=None):
    """Publish the mod's own files as a submod so the game can load it.

    Test Play used to stop at "export it first, then come back", which put
    the slowest part of the edit-test loop back in the user's hands. This
    is deliberately the submod path only: a full copy duplicates the entire
    mod, runs to gigabytes, and is not something to start behind a button
    that says Test Play.

    Returns the dlc_load entry for the exported mod. Raises RuntimeError
    when there's nothing of the user's own to export.
    """
    from app import mod_export

    own_files = mod_export.recorded_files(mod_root)
    if not own_files:
        raise RuntimeError(
            "This mod has no files created by Mod Maker yet, so there's nothing to export "
            "as a submod. Add something first, or use Export on the Home screen and pick "
            "'Full copy' to test the whole mod as it is.")

    # the entry comes from the .mod file export just wrote: a submod lives
    # in the launcher's folder, not at mod_root, so looking it back up by
    # path would miss and fall through to matching on display name - which
    # picks the wrong mod as soon as two of them share one
    _dest, mod_file, _copied = mod_export.export(
        mod_root, mod_name, mode="submod", own_files=own_files, progress=progress)
    return f"mod/{os.path.basename(mod_file)}"


# ---- the game itself ----

def game_executable(base_game=None):
    """Path to the hoi4 binary, or "" when the game isn't installed here."""
    base_game = base_game or game_paths.find_base_game()
    if not base_game:
        return ""
    names = ["hoi4.exe"] if sys.platform == "win32" else ["hoi4", "hoi4.sh"]
    for name in names:
        candidate = os.path.join(base_game, name)
        if os.path.isfile(candidate):
            return candidate
    return ""


def log_size():
    """Bytes in error.log right now, so a test run can report only what the
    game appends from here on instead of the whole history."""
    from app import error_log
    path = error_log.log_path()
    if not path:
        return 0
    try:
        return os.path.getsize(path)
    except OSError:
        return 0


def launch(mod_root, mod_name=None, debug=True, user_dir=None, base_game=None, entry=None):
    """Start the game with only this mod enabled.

    Returns (process, restore) where `restore` is a zero-argument callable
    that puts the user's previous mod selection back - call it once the
    process has exited. Raises RuntimeError with something a user can act
    on when the game or the mod's descriptor can't be found.
    """
    user_dir = user_dir or find_user_dir()
    if not user_dir:
        raise RuntimeError(
            "Could not find the Hearts of Iron IV user folder "
            "(Documents/Paradox Interactive/Hearts of Iron IV). Run the game "
            "once first, or set the path in Settings.")

    executable = game_executable(base_game)
    if not executable:
        raise RuntimeError(
            "Could not find hoi4 in the game folder. Set it in "
            "Settings -> Game folders and try again.")

    # `entry` is passed in when the caller has just exported and already
    # knows which descriptor it wrote
    entry = entry or entry_for_mod(mod_root, mod_name, user_dir)
    if not entry:
        raise RuntimeError(
            "This mod isn't in the launcher's mod folder yet, so the game "
            "can't load it. Export it first (Settings -> Export), then test.")

    previous = read_dlc_load(user_dir)
    # on disk before anything is overwritten, so the user's selection is
    # recoverable even if this process never gets to put it back
    _remember_restore(previous, user_dir)

    testing = dict(previous)
    testing["enabled_mods"] = [entry]
    if not write_dlc_load(testing, user_dir):
        _clear_restore()
        raise RuntimeError(f"Couldn't write {DLC_LOAD} in {user_dir}.")

    def restore():
        write_dlc_load(previous, user_dir)
        _clear_restore()

    command = [executable]
    if debug:
        # -debug turns on the script error reporting that makes error.log
        # worth reading; without it most script problems never get logged
        command.append("-debug")
    try:
        process = subprocess.Popen(command, cwd=os.path.dirname(executable))
    except OSError as exc:
        restore()
        raise RuntimeError(f"Couldn't start the game: {exc}") from exc

    return process, restore
