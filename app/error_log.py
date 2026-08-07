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


def _classify(message, mod_root):
    """(mod_relevant, mod_file) for a message that may name a script file."""
    match = _MOD_PATH_RE.search(message)
    if not match or not mod_root:
        return False, None
    rel = match.group(1).replace("/", os.sep)
    if not os.path.isfile(os.path.join(mod_root, rel)):
        return False, None
    return True, rel + (f":{match.group(2)}" if match.group(2) else "")


def _read_lines(path, start_offset):
    # binary, because a byte offset isn't a valid seek target for a text
    # stream - only values that came back from tell() are
    with open(path, "rb") as handle:
        if start_offset and start_offset < os.path.getsize(path):
            handle.seek(start_offset)
        return handle.read().decode("utf-8", "ignore").splitlines()


def parse_errors(path, mod_root=None, limit=2000, start_offset=0):
    """[(timestamp, source, message, mod_relevant, mod_file, count)] in the
    order the game first reported each distinct message. `mod_relevant` is
    True when the message references a script path inside `mod_root`.

    Identical messages are collapsed into one row carrying how many times
    they occurred. A real log is overwhelmingly repetition - one install
    here had 34,098 entries but only 738 distinct messages, a single one of
    them repeated 21,099 times - so listing them raw buried everything else.

    The whole file is read, not the tail. Script errors are reported while
    the game loads, which is the very beginning of the log; reading only
    the last N lines meant a mod's own errors were never once visible.

    `start_offset` is a byte position recorded before a test run, so the
    caller can ask for only what the game appended during it. The game
    truncates the log on startup, so an offset past the current end means
    a fresh log and is treated as 0 rather than hiding everything."""
    try:
        lines = _read_lines(path, start_offset)
    except OSError:
        return []

    # message -> index into `out`, so repeats bump a count instead of
    # appending another identical row
    seen = {}
    out = []
    last = None   # index of the row a continuation line belongs to; not
                  # out[-1], which goes stale as soon as a repeat is folded
                  # into an earlier row instead of appending a new one
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        match = _LINE_RE.match(stripped)
        if not match:
            # a continuation of the previous message: the game breaks long
            # quoted errors across lines, and the tail - '" in file:
            # "music/got_songs.txt"' - is the half naming the file, so
            # dropping it threw away the only useful part
            if last is not None:
                ts, source, message, _relevant, _file, count = out[last]
                seen.pop(message, None)
                message = f"{message} {stripped}"
                relevant, mod_file = _classify(message, mod_root)
                out[last] = (ts, source, message, relevant, mod_file, count)
                seen[message] = last
            continue

        ts, _date, source, message = match.groups()
        if any(noise in message for noise in NOISE_PATTERNS):
            last = None
            continue

        index = seen.get(message)
        if index is not None:
            row = out[index]
            out[index] = row[:5] + (row[5] + 1,)
            last = index
            continue

        relevant, mod_file = _classify(message, mod_root)
        last = len(out)
        seen[message] = last
        out.append((ts, source, message, relevant, mod_file, 1))

    if len(out) > limit:
        # a cap still has to keep the rows this tool exists to show, so the
        # mod's own errors survive it and only base-game noise is dropped
        mine = [row for row in out if row[3]]
        others = [row for row in out if not row[3]]
        out = mine + others[:max(0, limit - len(mine))]
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
