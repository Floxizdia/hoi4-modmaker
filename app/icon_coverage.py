"""Icon coverage report: every icon/picture reference a mod's focuses,
ideas, decisions and events make, checked against the sprites actually
registered in .gfx files (base game + mod) - state.gfx_index, built once
at mod-load time. A reference with no matching sprite name is exactly the
kind of thing that renders as a blank/red-X icon in-game, and the game's
own error log rarely points at which file caused it.
"""

import glob
import os
import re

from app import pds_scan as scan

_ICON_TOKEN_RE = re.compile(r"\b(icon|picture|large_picture|small_icon)\s*=\s*\"?([A-Za-z0-9_]+)\"?")


def _scan_file_for_icons(path, source_label):
    """[(icon_token, field, context_id, source_label)] - context_id is
    whatever named block the reference sits inside, best-effort."""
    try:
        with open(path, "r", encoding="utf-8-sig", errors="ignore") as f:
            text = scan.strip_comments(f.read())
    except OSError:
        return []

    out = []
    for m in _ICON_TOKEN_RE.finditer(text):
        field, token = m.group(1), m.group(2)
        if token.upper() == token and len(token) <= 4:
            continue  # bare country tags etc slipping through, not real gfx tokens
        # find the nearest enclosing "id = xxx" or block name before this match, best-effort
        preceding = text[:m.start()]
        id_m = list(re.finditer(r"\b(?:id|name)\s*=\s*\"?([A-Za-z0-9_.]+)\"?", preceding))
        context = id_m[-1].group(1) if id_m else os.path.basename(path)
        out.append((token, field, context, source_label))
    return out


def scan_icon_references(mod_root):
    """[(token, field, context_id, file)] across the areas that most
    commonly cause visible icon breakage: focuses, ideas, decisions,
    events."""
    areas = [
        os.path.join("common", "national_focus"),
        os.path.join("common", "ideas"),
        os.path.join("common", "decisions"),
        os.path.join("events"),
    ]
    out = []
    for area in areas:
        folder = os.path.join(mod_root, area)
        if not os.path.isdir(folder):
            continue
        for path in glob.glob(os.path.join(folder, "**", "*.txt"), recursive=True):
            rel = os.path.relpath(path, mod_root)
            out.extend((tok, field, ctx, rel) for tok, field, ctx, _ in _scan_file_for_icons(path, rel))
    return out


def missing_icons(mod_root, gfx_index):
    """{token: [(field, context_id, file), ...]} for every icon reference
    whose token isn't a key in gfx_index (i.e. no .gfx spriteType registers
    it anywhere base game or mod scanned)."""
    missing = {}
    for token, field, context, rel in scan_icon_references(mod_root):
        if token in gfx_index:
            continue
        missing.setdefault(token, []).append((field, context, rel))
    return missing
