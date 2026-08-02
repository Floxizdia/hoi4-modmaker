"""Whole-mod validation: catch the mistakes that make HOI4 silently drop a
file or crash on load, before the game ever starts.

Checks, in rough order of how often they bite modders:
  braces     unbalanced { } in any script file (the game skips the file)
  focus      prerequisite/mutually_exclusive/relative_position_id pointing
             at focus ids that don't exist anywhere in the mod
  duplicates the same focus or event id defined twice
  events     effects firing an event id that is never defined
  loc        content whose title/description key has no localisation entry
  icons      GFX sprite names that no .gfx file defines

Everything is heuristic-but-honest: a finding names the file and the id, so
the user can judge it. Cross-mod references (a submod extending its parent)
can produce false "missing" hits, which is why results are warnings, not
gates - saving is never blocked.
"""

import os
import glob
import re
from collections import defaultdict

from app import mod_loader as ml
from app import pds_scan as scan
from app import map_data

SCRIPT_FOLDERS = [
    ("common", "national_focus"),
    ("common", "decisions"),
    ("common", "ideas"),
    ("common", "characters"),
    ("events",),
]

EVENT_REF_RE = re.compile(r"\b(?:country_event|news_event|state_event)\s*=\s*\{[^{}]*?\bid\s*=\s*([A-Za-z_][A-Za-z0-9_]*\.\d+)")
SIMPLE_EVENT_REF_RE = re.compile(r"\b(?:country_event|news_event|state_event)\s*=\s*([A-Za-z_][A-Za-z0-9_]*\.\d+)")


def _brace_balance(text):
    """Return (depth_at_end, line_of_first_negative). Respects quotes."""
    depth = 0
    first_neg = None
    line = 1
    in_quotes = False
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        if ch == "\n":
            line += 1
        elif in_quotes:
            if ch == "\\":
                i += 2
                continue
            if ch == '"':
                in_quotes = False
        elif ch == '"':
            in_quotes = True
        elif ch == "#":
            while i < n and text[i] != "\n":
                i += 1
            continue
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth < 0 and first_neg is None:
                first_neg = line
        i += 1
    return depth, first_neg


def validate(mod_root, loc, gfx_index, progress=None):
    """Return a list of {severity, category, file, message} dicts."""
    issues = []

    def add(severity, category, path, message):
        issues.append({
            "severity": severity, "category": category,
            "file": os.path.relpath(path, mod_root) if path else "",
            "message": message,
        })

    # ---- brace balance ------------------------------------------------
    if progress:
        progress("Checking braces...")
    for folder in SCRIPT_FOLDERS:
        base = os.path.join(mod_root, *folder)
        if not os.path.isdir(base):
            continue
        for path in glob.glob(os.path.join(base, "**", "*.txt"), recursive=True):
            try:
                with open(path, "r", encoding="utf-8-sig", errors="ignore") as f:
                    text = f.read()
            except OSError:
                continue
            depth, first_neg = _brace_balance(text)
            if first_neg is not None:
                add("error", "braces", path, f"extra '}}' around line {first_neg} — the game will misread this file")
            elif depth > 0:
                add("error", "braces", path, f"{depth} unclosed '{{' — the game will skip everything after it")

    # ---- focuses ------------------------------------------------------
    if progress:
        progress("Checking focus trees...")
    all_focus_ids = set()
    focus_defs = defaultdict(list)   # id -> [files]
    trees = []
    for path in ml.find_focus_tree_files(mod_root):
        for tree in ml.parse_focus_trees(path):
            trees.append((path, tree))
            for f in tree["focuses"]:
                all_focus_ids.add(f["id"])
                focus_defs[f["id"]].append(path)

    for fid, files in focus_defs.items():
        if len(files) > 1:
            add("warning", "duplicates", files[1],
                f"focus '{fid}' is defined in {len(files)} files — the game keeps only one")

    for path, tree in trees:
        for f in tree["focuses"]:
            for pre in f.get("prerequisite", []):
                if pre not in all_focus_ids:
                    add("error", "focus", path,
                        f"focus '{f['id']}' requires '{pre}' which is not defined in this mod")
            for mx in f.get("mutually_exclusive", []):
                if mx not in all_focus_ids:
                    add("warning", "focus", path,
                        f"focus '{f['id']}' is mutually exclusive with missing '{mx}'")
            rel = f.get("relative_position_id")
            if rel and rel not in all_focus_ids:
                add("warning", "focus", path,
                    f"focus '{f['id']}' positions itself relative to missing '{rel}'")

    # a focus that (directly or through a chain) requires itself can never
    # be completed - the game just leaves it permanently locked, with no
    # error of its own to explain why, so this is worth catching by hand
    prereq_of = {}   # focus id -> (file, [prerequisite ids])
    for path, tree in trees:
        for f in tree["focuses"]:
            prereq_of[f["id"]] = (path, f.get("prerequisite", []))

    def find_cycle(start):
        path_stack = [start]
        seen_in_path = {start}
        node = start
        while True:
            _, prereqs = prereq_of.get(node, (None, []))
            nxt = next((p for p in prereqs if p in prereq_of), None)
            if nxt is None:
                return None
            if nxt in seen_in_path:
                return path_stack[path_stack.index(nxt):] + [nxt]
            path_stack.append(nxt)
            seen_in_path.add(nxt)
            node = nxt
            if len(path_stack) > len(prereq_of) + 1:
                return None   # safety valve against a malformed graph

    reported_cycles = set()
    for fid in prereq_of:
        cycle = find_cycle(fid)
        if cycle:
            key = frozenset(cycle)
            if key in reported_cycles:
                continue
            reported_cycles.add(key)
            file_path = prereq_of[cycle[0]][0]
            add("error", "focus", file_path,
                f"prerequisite cycle: {' -> '.join(cycle)} — none of these can ever unlock")

    # ---- events -------------------------------------------------------
    if progress:
        progress("Checking events...")
    event_ids = set()
    event_defs = defaultdict(list)
    parsed_events = []
    for path in ml.find_event_files(mod_root):
        try:
            _, events = ml.parse_events(path)
        except OSError:
            continue
        for e in events:
            eid = f"{e['namespace']}.{e['number']}"
            event_ids.add(eid)
            event_defs[eid].append(path)
            parsed_events.append((path, e))

    for eid, files in event_defs.items():
        if len(files) > 1:
            add("warning", "duplicates", files[1],
                f"event '{eid}' is defined in {len(files)} files")

    def check_event_refs(path, owner, text):
        for ref in set(SIMPLE_EVENT_REF_RE.findall(text or "")) | set(EVENT_REF_RE.findall(text or "")):
            if ref not in event_ids:
                add("warning", "events", path,
                    f"{owner} fires event '{ref}' which is not defined in this mod")

    for path, tree in trees:
        for f in tree["focuses"]:
            check_event_refs(path, f"focus '{f['id']}'", f.get("completion_reward_raw", ""))
    for path, e in parsed_events:
        eid = f"{e['namespace']}.{e['number']}"
        check_event_refs(path, f"event '{eid}'", e.get("immediate", ""))
        for o in e["options"]:
            check_event_refs(path, f"event '{eid}' option", o.get("effect", ""))

    # ---- decisions & ideas: duplicate ids -----------------------------
    # same failure mode as a duplicate focus/event - the game silently
    # keeps whichever definition it parsed last, so a modder editing "the"
    # decision never notices they're actually editing a shadowed copy
    if progress:
        progress("Checking decisions and ideas...")
    decision_defs = defaultdict(list)
    for path in ml.find_decision_files(mod_root):
        try:
            categories = ml.parse_decisions(path)
        except OSError:
            continue
        for cat in categories:
            for d in cat["decisions"]:
                decision_defs[d["id"]].append(path)
    for did, files in decision_defs.items():
        if len(files) > 1:
            add("warning", "duplicates", files[1],
                f"decision '{did}' is defined in {len(files)} files — the game keeps only one")

    idea_defs = defaultdict(list)
    for path in ml.find_idea_files(mod_root):
        try:
            categories = ml.parse_ideas(path)
        except OSError:
            continue
        for cat in categories:
            for idea in cat["ideas"]:
                idea_defs[idea["id"]].append(path)
    for iid, files in idea_defs.items():
        if len(files) > 1:
            add("warning", "duplicates", files[1],
                f"idea '{iid}' is defined in {len(files)} files — the game keeps only one")

    # ---- sprites registered but whose texture file is gone -------------
    # a .gfx entry pointing at a deleted/renamed/never-committed texture
    # passes every "is this sprite defined?" check but still renders as a
    # blank or missing-texture box in game, which is why it needs its own
    # pass over the actual filesystem
    if progress:
        progress("Checking texture files exist...")
    mod_abs = os.path.abspath(mod_root)
    checked_missing = set()

    def _texture_exists(path):
        """The game is tolerant about the extension - vanilla's own .gfx
        files still say .tga for art that shipped as .dds years ago, and it
        loads fine - so an extension-swapped sibling counts as present."""
        if os.path.isfile(path):
            return True
        stem = os.path.splitext(path)[0]
        return any(os.path.isfile(stem + ext) for ext in (".dds", ".tga", ".png"))

    # Scope: only sprites this mod actually invents. A mod re-declaring a
    # vanilla sprite name (very common - overriding one .gfx file re-lists
    # everything in it) resolves its art through the base game or a DLC
    # archive, which isn't visible as a loose file here. Checking those
    # produced ~2400 false positives on a real total-conversion mod, which
    # would have made the whole category useless.
    try:
        vanilla_sprites = set(ml.build_gfx_index([map_data.BASE_GAME]))
    except Exception:
        vanilla_sprites = set()

    for sprite, texture_path in gfx_index.items():
        if sprite in vanilla_sprites:
            continue
        # only this mod's own sprites - the base game's are someone else's
        # problem and would drown the real findings
        if not os.path.abspath(texture_path).startswith(mod_abs):
            continue
        if _texture_exists(texture_path):
            continue
        rel = os.path.relpath(texture_path, mod_root)
        # the game resolves a texturefile path across the whole load order,
        # not just the mod that declared the sprite
        if _texture_exists(os.path.join(map_data.BASE_GAME, rel)):
            continue
        if rel in checked_missing:
            continue
        checked_missing.add(rel)
        add("error", "missing_files", texture_path,
            f"sprite '{sprite}' points at '{rel}' which exists in neither this mod nor the "
            "base game — it will render as a blank/missing texture in game")

    # ---- character portraits that don't exist --------------------------
    for tag, chars in ml.load_country_characters(mod_root).items():
        for c in chars:
            for value in c.get("portraits", []):
                if not value or value.upper().startswith("GFX_"):
                    continue   # a sprite reference - covered by the gfx check above
                candidate = os.path.normpath(os.path.join(mod_root, value))
                if not os.path.abspath(candidate).startswith(mod_abs):
                    continue
                if os.path.isfile(candidate):
                    continue
                add("warning", "missing_files", c.get("source_file") or mod_root,
                    f"character '{c['id']}' ({tag}) has portrait '{value}' which doesn't exist on disk")

    # ---- starting forces: province ids that don't exist ----------------
    # a division/fleet/air wing pointing at a province the map never defines
    # just silently fails to deploy - no error, the unit simply isn't there
    # when the game starts, which is very hard to notice by playing
    units_dir = os.path.join(mod_root, "history", "units")
    if os.path.isdir(units_dir):
        if progress:
            progress("Checking starting forces...")
        try:
            definition = map_data.load_definition(map_data._map_dir(mod_root))
            known_provinces = set(definition.values())
        except (FileNotFoundError, OSError):
            known_provinces = set()   # no map in this mod - it inherits the base game's, skip
        if known_provinces:
            for path in sorted(glob.glob(os.path.join(units_dir, "*.txt"))):
                try:
                    with open(path, "r", encoding="utf-8-sig", errors="ignore") as f:
                        text = f.read()
                except OSError:
                    continue
                for key in ("location", "naval_base"):
                    for match in re.finditer(rf"\b{key}\s*=\s*(\d+)", text):
                        pid = int(match.group(1))
                        if pid not in known_provinces:
                            line = text.count("\n", 0, match.start()) + 1
                            add("error", "oob", path,
                                f"line {line}: {key} = {pid} is not a province on this mod's map "
                                "— that unit will silently fail to deploy")

    # ---- localisation -------------------------------------------------
    if progress:
        progress("Checking localisation...")
    for path, tree in trees:
        for f in tree["focuses"]:
            if f["id"] not in loc:
                add("warning", "loc", path, f"focus '{f['id']}' has no localisation (name will show as the raw id)")
    for path, e in parsed_events:
        eid = f"{e['namespace']}.{e['number']}"
        for key, what in ((e.get("title_key"), "title"), (e.get("desc_key"), "description")):
            if key and not key.startswith("[") and key not in loc:
                add("warning", "loc", path, f"event '{eid}' {what} key '{key}' has no localisation")

    # ---- icons --------------------------------------------------------
    if progress:
        progress("Checking icons...")
    for path, tree in trees:
        for f in tree["focuses"]:
            icon = f.get("icon", "")
            if icon and icon.upper().startswith("GFX_") and icon not in gfx_index:
                add("warning", "icons", path,
                    f"focus '{f['id']}' uses icon '{icon}' which no .gfx file defines")

    for path in ml.find_idea_files(mod_root):
        for cat in ml.parse_ideas(path):
            for idea in cat["ideas"]:
                pic = idea.get("picture", "")
                if not pic:
                    continue
                sprite = pic if pic.upper().startswith("GFX_") else f"GFX_idea_{pic}"
                if sprite not in gfx_index:
                    add("info", "icons", path,
                        f"idea '{idea['id']}' picture '{pic}' not found as {sprite}")

    return issues


def summarise(issues):
    counts = defaultdict(int)
    for issue in issues:
        counts[issue["severity"]] += 1
    return counts
