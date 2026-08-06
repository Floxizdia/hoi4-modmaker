"""Which DLC the user switched off on the Tech screen.

Stored as the *disabled* set rather than the enabled one so a DLC installed
later still shows up on by default, and kept next to the other preference
files in the user's app-data folder for the same reason recent.py is: the
exe may sit somewhere read-only.
"""

import json
import os

from app.recent import CONFIG_DIR

PREFS_FILE = os.path.join(CONFIG_DIR, "dlc_prefs.json")


def load_disabled():
    try:
        with open(PREFS_FILE, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError):
        return []
    disabled = data.get("disabled") if isinstance(data, dict) else None
    return [name for name in disabled if isinstance(name, str)] if isinstance(disabled, list) else []


def save_disabled(names):
    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(PREFS_FILE, "w", encoding="utf-8") as handle:
            json.dump({"disabled": sorted(names)}, handle, indent=2)
    except OSError:
        pass   # a preference that won't persist must not break the screen
