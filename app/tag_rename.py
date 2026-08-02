"""Rename a country tag across a whole mod - TUR -> OTT and everything that
implies.

This is deliberately not "Find & Replace with three letters", because a bare
three-letter string is far too common to replace blindly: "TUR" appears
inside `TURN`, inside filenames like `naTURal.dds`, inside localisation
prose. Every match here has to look like a *tag reference*, which in Paradox
script means it stands alone as a token - bounded by whitespace, braces,
equals signs, quotes or the start/end of a line.

Filenames matter too, and Find & Replace can't touch those at all: the game
finds a country's history file by the `TAG - Name.txt` convention and its
flags by `gfx/flags/TAG.tga`, so a rename that only edits file *contents*
leaves a mod that loads but has no flag and no starting history.

Nothing is written until the caller has seen the plan; every touched file
keeps a one-time .bak, same as every other edit in this app.
"""

import os
import re
import shutil

SCRIPT_EXT = {".txt", ".yml", ".gfx", ".gui", ".lua"}
SKIP_DIRS = {".hoi4modmaker_snapshots", ".git", "__pycache__"}


def _token_re(tag):
    """A tag reference is either the bare tag (`tag = TUR`) or the leading
    part of a tag-derived identifier (`TUR_1936`, `TUR_focus_name`), both of
    which a rename must follow.

    The lookbehind rejects anything already inside an identifier, so
    `SOV_TUR_pact` - a different id that merely contains the letters - is
    left alone. The lookahead allows a following `_` (that's the prefix
    case) but not a letter or digit, so `TURN` and `naTURal` don't match.
    Plain `\\b` would get all three of those wrong.
    """
    return re.compile(rf"(?<![A-Za-z0-9_]){re.escape(tag)}(?![A-Za-z0-9])")


def _iter_files(mod_root):
    for dirpath, dirnames, filenames in os.walk(mod_root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            yield os.path.join(dirpath, name)


def plan(mod_root, old_tag, new_tag):
    """What a rename would do, without doing any of it.

    Returns {"edits": [(path, hit_count)], "renames": [(old_path, new_path)],
    "conflicts": [str]} - conflicts are renames whose target already exists,
    which must be resolved by hand rather than silently overwritten."""
    old_tag = old_tag.strip().upper()
    new_tag = new_tag.strip().upper()
    pattern = _token_re(old_tag)

    edits = []
    renames = []
    conflicts = []

    for path in _iter_files(mod_root):
        ext = os.path.splitext(path)[1].lower()

        if ext in SCRIPT_EXT:
            try:
                with open(path, "r", encoding="utf-8-sig", errors="ignore") as f:
                    text = f.read()
            except OSError:
                continue
            hits = len(pattern.findall(text))
            if hits:
                edits.append((path, hits))

        # filenames: only when the tag is a standalone token there too, so
        # `TUR - Turkey.txt` and `TUR.tga` rename but `naTURal.dds` doesn't
        name = os.path.basename(path)
        if pattern.search(name):
            new_name = pattern.sub(new_tag, name)
            if new_name != name:
                new_path = os.path.join(os.path.dirname(path), new_name)
                if os.path.exists(new_path):
                    conflicts.append(f"{name} -> {new_name} (target already exists)")
                else:
                    renames.append((path, new_path))

    return {"edits": edits, "renames": renames, "conflicts": conflicts}


def apply(mod_root, old_tag, new_tag, plan_result=None, record=None):
    """Carry out the plan. Returns (files_edited, total_replacements,
    files_renamed). Content is rewritten before anything is renamed, so a
    failure part-way leaves files findable under their original names."""
    old_tag = old_tag.strip().upper()
    new_tag = new_tag.strip().upper()
    pattern = _token_re(old_tag)
    result = plan_result or plan(mod_root, old_tag, new_tag)

    edited = 0
    total = 0
    for path, _hits in result["edits"]:
        try:
            with open(path, "r", encoding="utf-8-sig", errors="ignore") as f:
                text = f.read()
        except OSError:
            continue
        new_text, n = pattern.subn(new_tag, text)
        if not n:
            continue
        backup = path + ".bak"
        if not os.path.exists(backup):
            try:
                shutil.copy2(path, backup)
            except OSError:
                pass
        try:
            with open(path, "w", encoding="utf-8-sig") as f:
                f.write(new_text)
        except OSError:
            continue
        edited += 1
        total += n

    renamed = 0
    touched_paths = []
    for old_path, new_path in result["renames"]:
        if not os.path.exists(old_path) or os.path.exists(new_path):
            continue
        try:
            os.rename(old_path, new_path)
        except OSError:
            continue
        renamed += 1
        touched_paths.append(new_path)

    if record and touched_paths:
        record(touched_paths)
    return edited, total, renamed
