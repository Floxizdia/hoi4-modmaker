"""Turn every common/technologies/*.txt file into one graph the visual tree
can draw - the same idea as mod_loader's focus tree parsing, but techs store
their edges backwards from how focuses do.

A focus lists its own prerequisites. A tech instead lists what it UNLOCKS
(`path = { leads_to_tech = X }`), so building "what does tech X require" needs
a full pass over every tech in every file first, then a reverse lookup -
there is no shortcut that reads one tech in isolation.

Folder tabs (infantry_folder, armour_folder, ...) are the game's own
grouping and become this view's tabs; a tech's `folder.position` is the
game's own curated layout, so unlike the focus tree this doesn't need an
auto-layout fallback - the position data is basically always present and
essentially collision-free by construction.
"""

import glob
import os
import re

from app import pds_scan as scan

_LEADS_TO_RE = re.compile(r"\bleads_to_tech\s*=\s*(\S+)")
_COUNTRY_TAG_RE = re.compile(r"^([A-Z]{3})\b")
_TECH_ASSIGNMENT_RE = re.compile(r"(?m)^\s*([A-Za-z_@][\w@]*)\s*=\s*(\d+)\s*$")
_CONST_RE = re.compile(r"(?m)^\s*(@\w+)\s*=\s*(-?[\d.]+)\s*$")

#: bucket for techs that declare no folder - the game doesn't put these on
#: the research screen either, they're granted by script at gamestart
NO_FOLDER = "(no folder)"


def _constants(text):
    """{'@1936': 2.0, ...} - the scripted-variable block vanilla puts at the
    top of a technologies file and then uses for row positions
    (`position = { x = 0 y = @1936 }`). Without these the y of every
    year-gated tech reads as the literal string '@1936', collapses to 0, and
    a whole folder stacks onto one cell."""
    out = {}
    for name, value in _CONST_RE.findall(text):
        try:
            out[name] = float(value)
        except ValueError:
            continue
    return out


def _number(raw, consts, default=0.0):
    raw = (raw or "").strip()
    if raw in consts:
        return consts[raw]
    try:
        return float(raw)
    except ValueError:
        return default


def find_tech_files(mod_root):
    folder = os.path.join(mod_root, "common", "technologies")
    if not os.path.isdir(folder):
        return []
    return sorted(glob.glob(os.path.join(folder, "*.txt")))


def parse_techs(path):
    """[(tech_id, span_start, span_end)] - spans cover `id = { ... }` in the
    ORIGINAL text (comments included), so a span can be cut out and replaced
    without disturbing anything around it."""
    with open(path, "r", encoding="utf-8-sig", errors="ignore") as f:
        text = f.read()

    m = re.search(r"\btechnologies\s*=\s*\{", text)
    if not m:
        return text, []
    outer_open = m.end() - 1
    outer_close = scan.find_matching_brace(text, outer_open)
    if outer_close == -1:
        return text, []

    techs = []
    i = outer_open + 1
    pattern = re.compile(r"([A-Za-z_@][\w@]*)\s*=\s*\{")
    while i < outer_close:
        m = pattern.search(text, i, outer_close)
        if not m:
            break
        open_idx = m.end() - 1
        close_idx = scan.find_matching_brace(text, open_idx)
        if close_idx == -1 or close_idx > outer_close:
            break
        name = m.group(1)
        if not name.startswith("@"):  # @vars are constants, not techs
            techs.append((name, m.start(), close_idx + 1))
        i = close_idx + 1
    return text, techs


def _tech_fields(inner, consts=None):
    consts = consts or {}
    folder_block = scan.first_block(inner, "folder") or ""
    name = scan.scalar(folder_block, "name", "")
    pos = scan.first_block(folder_block, "position") or ""
    x = _number(scan.scalar(pos, "x", "0"), consts)
    y = _number(scan.scalar(pos, "y", "0"), consts)
    positioned = bool(folder_block and pos)

    leads_to = []
    for _, _, path_inner in scan.iter_blocks(inner, "path"):
        m = _LEADS_TO_RE.search(path_inner)
        if m:
            leads_to.append(m.group(1))

    return {
        "folder": name,
        "x": x,
        "y": y,
        "positioned": positioned,
        "doctrine": scan.scalar(inner, "doctrine", "") == "yes",
        "xp_cost": scan.scalar(inner, "xp_unlock_cost", ""),
        "xp_type": scan.scalar(inner, "xp_research_type", ""),
        "leads_to": leads_to,
        "research_cost": scan.scalar(inner, "research_cost", ""),
        "start_year": scan.scalar(inner, "start_year", ""),
    }


def build_graph(mod_root):
    """{tech_id: {folder, x, y, leads_to, requires, research_cost,
    start_year, file, start, end, is_vanilla}} across the base game's own
    technologies plus whatever the mod adds or overrides on top - the same
    merge HOI4 itself does. A brand new mod with no common/technologies of
    its own still gets the full vanilla tree this way, instead of an empty
    view; an established mod's own techs simply layer over vanilla, so a
    modded tech's `leads_to_tech` pointing back at a vanilla one still
    resolves into a real `requires` edge.
    """
    from app.map_data import BASE_GAME

    techs = {}
    for root, is_vanilla in ((BASE_GAME, True), (mod_root, False)):
        for path in find_tech_files(root):
            text, spans = parse_techs(path)
            consts = _constants(text)
            for tech_id, start, end in spans:
                inner = text[start:end]
                fields = _tech_fields(inner, consts)
                fields.update({"file": path, "start": start, "end": end,
                              "requires": [], "is_vanilla": is_vanilla})
                techs[tech_id] = fields   # the mod's own definition wins on id collision

    for tech_id, info in techs.items():
        for target in info["leads_to"]:
            if target in techs:
                techs[target]["requires"].append(tech_id)

    return techs


def is_doctrine_folder(graph, folder):
    """Whether a folder holds doctrines rather than ordinary research.

    Decided from the `doctrine = yes` marker the techs themselves carry -
    every tech in vanilla's four doctrine folders has it - rather than from
    the folder's name, so a mod that calls its own doctrine folder
    something else is still classified correctly."""
    techs = [info for info in graph.values()
             if (info["folder"] or NO_FOLDER) == folder]
    if not techs:
        return False
    return sum(1 for info in techs if info.get("doctrine")) > len(techs) / 2


def folders(graph):
    """Folder names in a stable order: first-seen across the (sorted) tech
    ids, so the tab order doesn't reshuffle between scans."""
    seen = []
    for tech_id in sorted(graph):
        name = graph[tech_id]["folder"] or NO_FOLDER
        if name not in seen:
            seen.append(name)
    return seen


def resolve_icon(mod_root, tech_id, gfx_index=None, tag=None):
    """The texture the game itself would draw for this tech.

    The game reaches a tech's art through a sprite name, not a filename:
    interface/*.gfx defines `GFX_<id>_medium` pointing at whatever texture
    it likes (`GFX_early_ship_hull_light_medium` -> early_destroyer.dds),
    and country-flavoured techs only exist as `GFX_<TAG>_<id>_medium` with
    no generic variant at all. Guessing `technologies/<id>.dds` therefore
    misses roughly 40% of the base game's techs, so the sprite index is
    tried first and the filename convention kept only as a fallback for
    mods that ship loose art without registering a sprite."""
    from app.map_data import BASE_GAME

    if gfx_index:
        names = []
        if tag:
            names += [f"GFX_{tag}_{tech_id}_medium", f"GFX_{tag}_{tech_id}"]
        names += [f"GFX_{tech_id}_medium", f"GFX_{tech_id}"]
        for name in names:
            path = gfx_index.get(name)
            if path and os.path.isfile(path):
                return path

    for root in (mod_root, BASE_GAME):
        for ext in (".dds", ".png", ".tga"):
            path = os.path.join(root, "gfx", "interface", "technologies", tech_id + ext)
            if os.path.isfile(path):
                return path
    return None


def country_tags(mod_root):
    """Country tags with history files in the base game or current mod."""
    from app.map_data import BASE_GAME
    tags = set()
    for root in (BASE_GAME, mod_root):
        folder = os.path.join(root, "history", "countries")
        if not os.path.isdir(folder):
            continue
        for path in glob.glob(os.path.join(folder, "*.txt")):
            match = _COUNTRY_TAG_RE.match(os.path.basename(path))
            if match:
                tags.add(match.group(1))
    return sorted(tags)


def starting_techs(mod_root, tag):
    """Best-effort set of technologies granted by country history at start."""
    from app.map_data import BASE_GAME
    tag = (tag or "").upper()
    known = set()
    for root in (BASE_GAME, mod_root):
        folder = os.path.join(root, "history", "countries")
        if not os.path.isdir(folder):
            continue
        for path in glob.glob(os.path.join(folder, f"{tag}*.txt")):
            try:
                with open(path, "r", encoding="utf-8-sig", errors="ignore") as handle:
                    text = scan.strip_comments(handle.read())
            except OSError:
                continue
            for _, _, block in scan.iter_blocks(text, "set_technology"):
                for tech_id, level in _TECH_ASSIGNMENT_RE.findall(block):
                    if int(level) > 0:
                        known.add(tech_id)
    return known
