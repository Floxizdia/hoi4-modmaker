"""Byte-preserving edits to one role inside one character block, the same
pattern as `focus_surgery.py` and `tech_tab.py`'s raw editor: locate the
span, rewrite only what changed, leave the rest of the (possibly huge,
possibly someone else's) characters file untouched.

Characters are the deepest nesting this app edits surgically: a role like
`corps_commander` sits inside a character which sits inside the file's
`characters = { ... }` wrapper, so finding it is a three-step walk rather
than the single `iter_blocks` call a tech or focus needs.
"""

import os
import re
import shutil

from app import pds_scan as scan
from app import undo

SKILL_KEYS = ("skill", "attack_skill", "defense_skill", "planning_skill",
             "logistics_skill", "maneuvering_skill", "coordination_skill")


def find_character_span(text, char_id):
    """(start, end) of `CHAR_ID = { ... }` inside this file's `characters`
    wrapper, or None if the file has no such character."""
    if scan.first_block(text, "characters") is None:
        return None
    m = re.search(r"\b" + re.escape(char_id) + r"\s*=\s*\{", text)
    if not m:
        return None
    open_idx = m.end() - 1
    close_idx = scan.find_matching_brace(text, open_idx)
    if close_idx == -1:
        return None
    return m.start(), close_idx + 1


def find_role_span(char_block, role_key):
    """(start, end) of `role_key = { ... }` relative to `char_block`'s own
    text, or None if this character doesn't have that role."""
    m = re.search(r"\b" + re.escape(role_key) + r"\s*=\s*\{", char_block)
    if not m:
        return None
    open_idx = m.end() - 1
    close_idx = scan.find_matching_brace(char_block, open_idx)
    if close_idx == -1:
        return None
    return m.start(), close_idx + 1


def _set_scalar(block, key, value):
    pattern = re.compile(r"(\b" + re.escape(key) + r"\s*=\s*)(?!\{)(\"[^\"]*\"|\S+)")
    if pattern.search(block):
        return pattern.sub(lambda m: m.group(1) + str(value), block, count=1)
    return re.sub(r"^(.*?\{)", lambda m: m.group(1) + f"\n\t\t\t{key} = {value}", block, count=1, flags=re.DOTALL)


def _set_traits(block, traits):
    """Replace `traits = { ... }` entirely with the new space-separated list,
    or insert one if the role had none."""
    joined = " ".join(traits)
    m = re.search(r"\btraits\s*=\s*\{", block)
    if m:
        open_idx = m.end() - 1
        close_idx = scan.find_matching_brace(block, open_idx)
        if close_idx != -1:
            return block[:open_idx + 1] + " " + joined + " " + block[close_idx:]
    return re.sub(r"^(.*?\{)", lambda m: m.group(1) + f"\n\t\t\ttraits = {{ {joined} }}",
                  block, count=1, flags=re.DOTALL)


def apply_role_edits(path, char_id, role_key, *, scalars=None, traits=None, raw_body=None):
    """Edit one role of one character in place, `.bak`-backed. If the role
    doesn't exist yet, it's created (from `raw_body` if given, else empty)
    right before the character's closing brace. Returns True on success."""
    with open(path, "r", encoding="utf-8-sig", errors="ignore") as f:
        text = f.read()

    span = find_character_span(text, char_id)
    if not span:
        return False
    cstart, cend = span
    char_block = text[cstart:cend]

    role_span = find_role_span(char_block, role_key)
    if role_span is None:
        if raw_body is not None:
            body = raw_body
        else:
            lines = [f"{key} = {value}" for key, value in (scalars or {}).items()
                    if key in SKILL_KEYS and value not in (None, "")]
            if traits:
                lines.append("traits = { " + " ".join(traits) + " }")
            body = "\n".join(lines)
        indented = "\n".join("\t\t\t" + line for line in body.strip().splitlines()) if body.strip() else ""
        new_role = f"\t\t{role_key} = {{\n{indented}\n\t\t}}\n" if indented else f"\t\t{role_key} = {{\n\t\t}}\n"
        tail = char_block.rstrip()
        assert tail.endswith("}")
        new_char_block = tail[:-1].rstrip() + "\n" + new_role + "\t}"
    else:
        rstart, rend = role_span
        role_block = char_block[rstart:rend]
        if raw_body is not None:
            indented = "\n".join("\t\t\t" + line for line in raw_body.strip().splitlines())
            role_block = re.sub(
                r"\{.*\}", "{\n" + indented + "\n\t\t}", role_block, count=1, flags=re.DOTALL)
        else:
            for key, value in (scalars or {}).items():
                if key in SKILL_KEYS and value not in (None, ""):
                    role_block = _set_scalar(role_block, key, value)
            if traits is not None:
                role_block = _set_traits(role_block, traits)
        new_char_block = char_block[:rstart] + role_block + char_block[rend:]

    backup = path + ".bak"
    if not os.path.exists(backup):
        shutil.copy2(path, backup)
    undo.record(path, f"{role_key} of {char_id}")
    with open(path, "w", encoding="utf-8") as f:
        f.write(text[:cstart] + new_char_block + text[cend:])
    return True
