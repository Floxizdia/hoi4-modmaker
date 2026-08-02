"""Walking every script file in a mod - shared by the diff viewer, bulk
find/replace and global search so the three don't each reinvent "which files
count as the mod's script" slightly differently.
"""

import os

# folders that hold hand-editable Paradox script; gfx/sound/etc are binary
SCRIPT_FOLDERS = [
    "common", "events", "history", "localisation", "music", "interface",
]
TEXT_EXTENSIONS = (".txt", ".yml", ".gui", ".gfx", ".asset")

SKIP_SUFFIXES = (".bak",)
SKIP_NAMES = {".hoi4modmaker_files.txt", ".hoi4modmaker_snapshots"}


def iter_script_files(mod_root):
    """Every text file under the mod's script folders, deepest-first order
    not guaranteed - just a flat list of absolute paths."""
    for folder in SCRIPT_FOLDERS:
        base = os.path.join(mod_root, folder)
        if not os.path.isdir(base):
            continue
        for dirpath, dirnames, filenames in os.walk(base):
            if os.path.basename(dirpath) in SKIP_NAMES:
                dirnames[:] = []
                continue
            for name in filenames:
                if name in SKIP_NAMES or name.endswith(SKIP_SUFFIXES):
                    continue
                if not name.lower().endswith(TEXT_EXTENSIONS):
                    continue
                yield os.path.join(dirpath, name)


def read_text(path):
    with open(path, "r", encoding="utf-8-sig", errors="ignore") as f:
        return f.read()
