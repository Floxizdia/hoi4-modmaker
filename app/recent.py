"""Remembers which mods were opened, so the home screen can offer to pick
up where the last session stopped instead of making you hunt the list again.

Kept in the user's app-data folder rather than next to the code: the exe
may sit in a read-only place, and this is preference data, not mod data.
"""

import json
import os
import time

CONFIG_DIR = os.path.join(
    os.environ.get("APPDATA") or os.path.expanduser("~"), "HOI4ModMaker")
RECENT_FILE = os.path.join(CONFIG_DIR, "recent_mods.json")
MAX_RECENT = 8


def load():
    """[{path, name, opened}] newest first, with vanished folders dropped."""
    try:
        with open(RECENT_FILE, "r", encoding="utf-8") as f:
            entries = json.load(f)
    except (OSError, ValueError):
        return []
    if not isinstance(entries, list):
        return []
    return [e for e in entries
            if isinstance(e, dict) and e.get("path") and os.path.isdir(e["path"])]


def remember(path, name):
    entries = [e for e in load() if os.path.normcase(e["path"]) != os.path.normcase(path)]
    entries.insert(0, {"path": path, "name": name, "opened": time.time()})
    del entries[MAX_RECENT:]
    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(RECENT_FILE, "w", encoding="utf-8") as f:
            json.dump(entries, f, indent=1)
    except OSError:
        pass          # a missing recent list is never worth an error dialog
    return entries


def last():
    entries = load()
    return entries[0] if entries else None


def ago(timestamp):
    """'3 minutes ago' - short enough to sit on a button."""
    secs = max(0, int(time.time() - timestamp))
    for limit, div, unit in ((60, 1, "second"), (3600, 60, "minute"),
                             (86400, 3600, "hour"), (604800, 86400, "day")):
        if secs < limit:
            n = max(1, secs // div)
            return f"{n} {unit}{'s' if n != 1 else ''} ago"
    n = max(1, secs // 604800)
    return f"{n} week{'s' if n != 1 else ''} ago"
