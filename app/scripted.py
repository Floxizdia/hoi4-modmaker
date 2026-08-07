"""Scripted effects, scripted triggers and dynamic modifiers.

These three are the reusable building blocks of HOI4 script - a named
block you write once and then call from focuses, events and decisions by
name. Every other screen in this app can *reference* them, but until now
nothing could *define* one, so anybody wanting a shared condition had to
drop out to a text editor.

They differ from on_actions in one way that matters a lot here: these are
NOT additive. Two files defining the same name means the last one loaded
wins and the other is silently discarded - so redefining a name the base
game already uses quietly replaces vanilla behaviour, and this module's
job is to notice that and say so rather than let it happen unremarked.
"""

import os

from app import pds_scan as scan
from app import safe_io
from app.map_data import BASE_GAME

#: kind -> (folder under common/, file this app writes into)
KINDS = {
    "effect": (os.path.join("common", "scripted_effects"), "zzz_custom_scripted_effects.txt"),
    "trigger": (os.path.join("common", "scripted_triggers"), "zzz_custom_scripted_triggers.txt"),
    "modifier": (os.path.join("common", "dynamic_modifiers"), "zzz_custom_dynamic_modifiers.txt"),
}

KIND_LABELS = {
    "effect": "Scripted effect",
    "trigger": "Scripted trigger",
    "modifier": "Dynamic modifier",
}


def folder_for(root, kind):
    return os.path.join(root, KINDS[kind][0])


def list_defined(mod_root, kind):
    """{name: [(source, filename)]} for every definition of this kind.

    A name appearing under both "vanilla" and "mod" is the case worth
    seeing: the mod's copy replaces the base game's outright.
    """
    out = {}
    for root, source in ((BASE_GAME, "vanilla"), (mod_root, "mod")):
        folder = folder_for(root, kind) if root else ""
        if not folder or not os.path.isdir(folder):
            continue
        for name in sorted(os.listdir(folder)):
            if not name.endswith(".txt"):
                continue
            path = os.path.join(folder, name)
            try:
                with open(path, "r", encoding="utf-8-sig", errors="ignore") as handle:
                    text = scan.strip_comments(handle.read())
            except OSError:
                continue
            for key, _body in scan.iter_named_blocks(text):
                out.setdefault(key, []).append((source, name))
    return out


def overrides_vanilla(defined, name):
    """True when adding `name` would shadow a base-game definition."""
    return any(source == "vanilla" for source, _file in defined.get(name, ()))


def _indent(raw, depth=1):
    pad = "\t" * depth
    lines = []
    for line in raw.strip().splitlines():
        stripped = line.strip()
        lines.append(pad + stripped if stripped else "")
    return "\n".join(lines)


def format_definition(kind, name, body, *, icon="", enable="", remove_trigger=""):
    """The text for one definition.

    A dynamic modifier is the odd one out: `icon`, `enable` and
    `remove_trigger` are its own fields rather than part of the body, and
    the body is a plain list of `modifier = value` lines.
    """
    parts = []
    if kind == "modifier":
        if icon:
            parts.append(f'\ticon = "{icon}"')
        if enable.strip():
            parts.append("\tenable = {\n" + _indent(enable, 2) + "\n\t}")
        if remove_trigger.strip():
            parts.append("\tremove_trigger = {\n" + _indent(remove_trigger, 2) + "\n\t}")
    if body.strip():
        parts.append(_indent(body, 1))
    inner = "\n".join(parts)
    return f"{name} = {{\n{inner}\n}}\n"


def target_file(mod_root, kind):
    folder, filename = KINDS[kind]
    return os.path.join(mod_root, folder, filename)


def create(mod_root, kind, name, body, *, icon="", enable="", remove_trigger="",
           parent=None):
    """Append a definition to this app's file for `kind`.

    Returns the path written, or None when the user declined the overwrite
    prompt. Appending rather than replacing keeps definitions the user
    added earlier in the same session.
    """
    path = target_file(mod_root, kind)
    entry = format_definition(kind, name, body, icon=icon, enable=enable,
                              remove_trigger=remove_trigger)

    existing = ""
    if os.path.isfile(path):
        with open(path, "r", encoding="utf-8-sig", errors="ignore") as handle:
            existing = handle.read().rstrip("\n")

    if existing:
        content = existing + "\n\n" + entry
    else:
        content = entry

    os.makedirs(os.path.dirname(path), exist_ok=True)
    if not safe_io.write_text(path, content, parent=parent,
                              describe=os.path.basename(path)):
        return None
    return path


def read_definition(mod_root, kind, name):
    """The raw text of one definition in the mod, or "" if it isn't there -
    used to show what's already written before adding another."""
    folder = folder_for(mod_root, kind)
    if not os.path.isdir(folder):
        return ""
    for filename in sorted(os.listdir(folder)):
        if not filename.endswith(".txt"):
            continue
        try:
            with open(os.path.join(folder, filename), "r",
                      encoding="utf-8-sig", errors="ignore") as handle:
                text = scan.strip_comments(handle.read())
        except OSError:
            continue
        for key, body in scan.iter_named_blocks(text):
            if key == name:
                return body
    return ""
