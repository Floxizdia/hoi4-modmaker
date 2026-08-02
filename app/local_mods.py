"""Manually pinned local mod folders - mods that live outside the Steam
Workshop folder (e.g. developed straight in Documents/Paradox Interactive)
that the user has told Mod Maker about via "Add mod folder...".

Separate from recent.py: recent is an automatic MRU of whatever's been
*opened*; this is a small, user-curated list of folders to always show in
the Installed mods table, opened or not.
"""

import json
import os

from app.recent import CONFIG_DIR

LOCAL_FILE = os.path.join(CONFIG_DIR, "local_mods.json")


def load():
    """[path, ...] for folders that still exist."""
    try:
        with open(LOCAL_FILE, "r", encoding="utf-8") as f:
            paths = json.load(f)
    except (OSError, ValueError):
        return []
    if not isinstance(paths, list):
        return []
    return [p for p in paths if isinstance(p, str) and os.path.isdir(p)]


def add(path):
    paths = [p for p in load() if os.path.normcase(p) != os.path.normcase(path)]
    paths.insert(0, path)
    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(LOCAL_FILE, "w", encoding="utf-8") as f:
            json.dump(paths, f, indent=1)
    except OSError:
        pass
    return paths
