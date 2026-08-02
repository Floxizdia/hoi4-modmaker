"""Reads the game's own logs/error.log - what actually happens when a mod
loads or crashes has never been checked by anything in this app before now;
the Validator only ever looked at the mod's files in isolation, never at
what HOI4 itself said about them after actually trying to run.

Format confirmed straight from a real error.log on this machine:
    [HH:MM:SS][in-game-date][source_file.cpp:line]: message
Script errors frequently embed a mod-relative path + line right in the
message, e.g. "events/WW1_Latvia.txt:100: create_ship equipment_variant
does not exist for the creator country" - that's the part worth surfacing.
"""

import os
import re

from app.mod_export import find_user_dir

_LINE_RE = re.compile(r"^\[(\d{2}:\d{2}:\d{2})\]\[([^\]]*)\]\[([^\]]*)\]:\s*(.*)$")
_MOD_PATH_RE = re.compile(r"([\w./\\-]+\.(?:txt|gui|yml))(?::(\d+))?")

# substrings that mean "this is background noise from base-game 3D assets,
# not a script problem" - march_move/attachment-node spam is the single
# largest category in every install's error.log and drowns out anything
# a modder actually needs to see
NOISE_PATTERNS = (
    "Setting animation failed", "has no attachment node named",
    "Could not find animation", "texture not found for gfx",
)


def log_path():
    user_dir = find_user_dir()
    if not user_dir:
        return None
    path = os.path.join(user_dir, "logs", "error.log")
    return path if os.path.isfile(path) else None


def parse_errors(path, mod_root=None, limit=500):
    """[(timestamp, source, message, mod_relevant, mod_file)] - most recent
    last, matching file order. `mod_relevant` is True when the message
    references a script path that exists inside `mod_root`."""
    out = []
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
    except OSError:
        return out

    for line in lines[-limit:]:
        m = _LINE_RE.match(line.strip())
        if not m:
            continue
        ts, _date, source, message = m.groups()
        if any(noise in message for noise in NOISE_PATTERNS):
            continue

        mod_file = None
        mod_relevant = False
        pm = _MOD_PATH_RE.search(message)
        if pm and mod_root:
            rel = pm.group(1).replace("/", os.sep)
            candidate = os.path.join(mod_root, rel)
            if os.path.isfile(candidate):
                mod_relevant = True
                mod_file = rel + (f":{pm.group(2)}" if pm.group(2) else "")

        out.append((ts, source, message, mod_relevant, mod_file))
    return out


# plain-language hints for the error patterns that show up most often when
# a hand-written focus/event/decision has a real bug, keyed by a substring
# match against the raw message
HINTS = [
    ("No valid option for event", "Every option on this event has a trigger that's false for the country "
     "it fired on - the event has nothing to show, so it silently fails instead of popping up. "
     "Give at least one option an always-true (or blank) trigger."),
    ("does not exist for the creator country", "An effect referenced something (equipment variant, unit, "
     "state...) that this specific country doesn't actually have. Common cause: a template/variant id "
     "typo, or the effect firing before the thing it references was created."),
    ("AI tried to post an invalid command", "Usually harmless AI noise, but if it's constant it can mean "
     "an ai_strategy entry is pointing at something (a focus, a wargoal type) that doesn't exist."),
    ("duplicate", "Two files define the same id - the game keeps whichever loaded last, silently "
     "discarding the other. Search all common/ and history/ files for this id."),
    ("Unknown token", "A field or effect name the parser doesn't recognise - almost always a typo, or "
     "an effect that needs a DLC this install doesn't have flagged with a has_dlc check."),
    ("Failed to load", "The engine couldn't parse this file at all, usually from an unbalanced brace or "
     "a stray quote earlier in the file - run Validate first, it catches most of these."),
]


def hint_for(message):
    for needle, text in HINTS:
        if needle in message:
            return text
    return None
