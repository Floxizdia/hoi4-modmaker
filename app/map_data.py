"""HOI4 map plumbing: turn provinces.bmp + definition.csv + history/states
into a clickable political map, and write ownership changes back.

How the game stores the map:
  map/provinces.bmp    every province painted in a unique RGB colour
  map/definition.csv   province id <-> that RGB colour (+ land/sea type)
  history/states/*.txt state = { id, provinces={...}, history={ owner=TAG } }

So a "state at this pixel" lookup is colour -> province -> state, which we
vectorise with numpy over a nearest-neighbour-downscaled image (nearest
keeps the exact palette, so no colours are invented by scaling).
"""

import os
import re
import glob

import numpy as np
from PIL import Image

from app import pds_scan as scan
from app import undo

from app.game_paths import find_base_game

#: resolved once at import; empty when HOI4 isn't installed here
BASE_GAME = find_base_game()

SEA_COLOR = (22, 36, 52)
UNOWNED_COLOR = (110, 105, 95)
NO_STATE_COLOR = (72, 66, 54)   # land whose province isn't claimed by any state file
BORDER_DARKEN = 0.55

# core/claim overlay: owned-and-cored reads as solid, cored-but-not-owned as
# the interesting case (irredentism), claimed as a weaker want
CORE_OWNED_COLOR = (86, 132, 84)
CORE_FOREIGN_COLOR = (196, 148, 62)
CLAIM_COLOR = (128, 96, 148)
INACTIVE_COLOR = (58, 56, 52)

_STATE_ID_RE = re.compile(r"\bid\s*=\s*(\d+)")
_OWNER_RE = re.compile(r"\bowner\s*=\s*([A-Z][A-Z0-9]{2})")
_NAME_RE = re.compile(r'\bname\s*=\s*"([^"]+)"')
_CORE_RE = re.compile(r"\badd_core_of\s*=\s*([A-Z][A-Z0-9]{2})")
_CLAIM_RE = re.compile(r"\badd_claim_by\s*=\s*([A-Z][A-Z0-9]{2})")
_COLOR_BLOCK_RE = re.compile(
    r"^([A-Z][A-Z0-9]{2})\s*=\s*\{[^{}]*?color\s*=\s*rgb\s*\{\s*(\d+)\s+(\d+)\s+(\d+)",
    re.MULTILINE | re.DOTALL,
)


def _map_dir(mod_root):
    for root in (mod_root, BASE_GAME):
        if os.path.isfile(os.path.join(root, "map", "provinces.bmp")):
            return os.path.join(root, "map")
    raise FileNotFoundError("provinces.bmp not found in the mod or the base game")


def _states_dir(mod_root):
    mod_states = os.path.join(mod_root, "history", "states")
    if os.path.isdir(mod_states) and glob.glob(os.path.join(mod_states, "*.txt")):
        return mod_states
    return os.path.join(BASE_GAME, "history", "states")


def load_definition(map_dir):
    """{packed_rgb: province_id} for land provinces; sea/lakes left out so
    they fall through to the sea colour."""
    out = {}
    with open(os.path.join(map_dir, "definition.csv"), "r", encoding="utf-8-sig", errors="ignore") as f:
        for line in f:
            parts = line.split(";")
            if len(parts) < 5:
                continue
            try:
                pid = int(parts[0])
                r, g, b = int(parts[1]), int(parts[2]), int(parts[3])
            except ValueError:
                continue
            if parts[4].strip().lower() == "land":
                out[(r << 16) | (g << 8) | b] = pid
    return out


def load_states(states_dir):
    """{state_id: {name, owner, provinces, file}}"""
    states = {}
    for path in glob.glob(os.path.join(states_dir, "*.txt")):
        try:
            with open(path, "r", encoding="utf-8-sig", errors="ignore") as f:
                text = scan.strip_comments(f.read())
        except OSError:
            continue
        m = _STATE_ID_RE.search(text)
        if not m:
            continue
        sid = int(m.group(1))
        prov_block = scan.first_block(text, "provinces") or ""
        provinces = [int(p) for p in re.findall(r"\d+", prov_block)]
        history = scan.first_block(text, "history") or text
        owner_m = _OWNER_RE.search(history)
        name_m = _NAME_RE.search(text)
        states[sid] = {
            "name": name_m.group(1) if name_m else f"STATE_{sid}",
            "owner": owner_m.group(1) if owner_m else "",
            # who considers this state theirs (cores) and who is owed it
            # (claims) - both drive war goals and annexation in game, and
            # neither was readable before
            "cores": sorted(set(_CORE_RE.findall(history))),
            "claims": sorted(set(_CLAIM_RE.findall(history))),
            "provinces": provinces,
            "file": path,
        }
    return states


def unclaimed_land_provinces(mod_root):
    """Land province ids from definition.csv that no state file claims -
    the raw material for building a brand new state from scratch."""
    map_dir = _map_dir(mod_root)
    land_ids = set(load_definition(map_dir).values())
    states = load_states(_states_dir(mod_root))
    claimed = {pid for st in states.values() for pid in st["provinces"]}
    # a mod's own states dir may only contain a handful of files (edited via
    # this app) while still inheriting all the untouched base-game ones, so
    # also fold in whichever base-game states aren't shadowed by the mod
    if os.path.abspath(_states_dir(mod_root)) != os.path.abspath(os.path.join(BASE_GAME, "history", "states")):
        base_states = load_states(os.path.join(BASE_GAME, "history", "states"))
        mod_files = {os.path.basename(st["file"]) for st in states.values()}
        for name, st in base_states.items():
            if os.path.basename(st["file"]) not in mod_files:
                claimed.update(st["provinces"])
    return sorted(land_ids - claimed - {0})


def next_free_state_id(mod_root):
    states = load_states(_states_dir(mod_root))
    base_states = load_states(os.path.join(BASE_GAME, "history", "states"))
    all_ids = set(states) | set(base_states)
    return (max(all_ids) if all_ids else 0) + 1


def load_country_colors(mod_root):
    """{TAG: (r, g, b)} from the mod's colors.txt, else the base game's."""
    for root in (mod_root, BASE_GAME):
        path = os.path.join(root, "common", "countries", "colors.txt")
        if os.path.isfile(path):
            with open(path, "r", encoding="utf-8-sig", errors="ignore") as f:
                text = scan.strip_comments(f.read())
            return {tag: (int(r), int(g), int(b))
                    for tag, r, g, b in _COLOR_BLOCK_RE.findall(text)}
    return {}


class WorldMap:
    """Holds the rendered map plus the per-pixel state ids for hit-testing."""

    def __init__(self, mod_root, downscale=4, progress=None):
        self.mod_root = mod_root
        self.downscale = downscale

        if progress:
            progress("Reading definition.csv...")
        map_dir = _map_dir(mod_root)
        definition = load_definition(map_dir)

        if progress:
            progress("Reading state files...")
        self.states = load_states(_states_dir(mod_root))
        self.colors = load_country_colors(mod_root)

        prov_to_state = {}
        for sid, st in self.states.items():
            for pid in st["provinces"]:
                prov_to_state[pid] = sid

        if progress:
            progress("Loading provinces.bmp...")
        im = Image.open(os.path.join(map_dir, "provinces.bmp")).convert("RGB")
        w, h = im.size
        im = im.resize((w // downscale, h // downscale), Image.NEAREST)
        arr = np.asarray(im, dtype=np.int32)

        if progress:
            progress("Mapping pixels to states...")
        # a province can be real land with simply no state file claiming it -
        # a custom or partially-built map, not a bug - and that must render
        # differently from actual sea, or huge tracts of unfinished land
        # silently vanish into the ocean colour
        self.no_state_id = (max(self.states) if self.states else 0) + 1
        packed = (arr[:, :, 0] << 16) | (arr[:, :, 1] << 8) | arr[:, :, 2]
        unique, inverse = np.unique(packed, return_inverse=True)
        state_of_unique = np.zeros(len(unique), dtype=np.int32)
        # kept alongside the state lookup - picking a starting location for a
        # division/fleet/air wing needs the actual province id, not just
        # which state it's part of
        province_of_unique = np.zeros(len(unique), dtype=np.int32)
        for i, colour in enumerate(unique):
            pid = definition.get(int(colour))
            if pid is not None:
                state_of_unique[i] = prov_to_state.get(pid, self.no_state_id)
                province_of_unique[i] = pid
        self.state_arr = state_of_unique[inverse].reshape(packed.shape)
        self.province_arr = province_of_unique[inverse].reshape(packed.shape)

        if progress:
            progress("Colouring by owner...")
        self._build_luts()
        self._borders = self._compute_borders()

    # ---- rendering ----

    def _build_luts(self):
        max_id = int(self.state_arr.max()) + 1
        lut = np.full((max_id, 3), NO_STATE_COLOR, dtype=np.uint8)
        lut[0] = SEA_COLOR
        for sid, st in self.states.items():
            if sid >= max_id:
                continue
            lut[sid] = self.colors.get(st["owner"], UNOWNED_COLOR) if st["owner"] else UNOWNED_COLOR
        self._lut = lut

    def _compute_borders(self):
        s = self.state_arr
        border = np.zeros(s.shape, dtype=bool)
        border[1:, :] |= s[1:, :] != s[:-1, :]
        border[:, 1:] |= s[:, 1:] != s[:, :-1]
        return border

    def claim_lut(self, tag, kind="core"):
        """Colour table for the core/claim overlay of one country, so the
        map can answer "what does Hungary think is theirs?" at a glance
        instead of making the user open states one at a time."""
        max_id = int(self.state_arr.max()) + 1
        lut = np.full((max_id, 3), INACTIVE_COLOR, dtype=np.uint8)
        lut[0] = SEA_COLOR
        field = "cores" if kind == "core" else "claims"
        for sid, st in self.states.items():
            if sid >= max_id:
                continue
            if tag not in st.get(field, ()):
                continue
            lut[sid] = CORE_OWNED_COLOR if st["owner"] == tag else (
                CORE_FOREIGN_COLOR if kind == "core" else CLAIM_COLOR)
        return lut

    def render(self, selected=(), lut=None):
        """RGB numpy image; selected states are lifted towards white.

        `lut` swaps the colour table for an overlay (see `claim_lut`) while
        keeping the same borders and selection highlight."""
        img = (self._lut if lut is None else lut)[self.state_arr].astype(np.float32)
        if selected:
            mask = np.isin(self.state_arr, list(selected))
            img[mask] = img[mask] * 0.35 + 255 * 0.65
        img[self._borders] *= BORDER_DARKEN
        return Image.fromarray(img.astype(np.uint8), "RGB")

    # ---- queries ----

    def state_at(self, x, y):
        if 0 <= y < self.state_arr.shape[0] and 0 <= x < self.state_arr.shape[1]:
            return int(self.state_arr[y, x])
        return 0

    def province_at(self, x, y):
        if 0 <= y < self.province_arr.shape[0] and 0 <= x < self.province_arr.shape[1]:
            return int(self.province_arr[y, x])
        return 0

    def states_owned_by(self, tag):
        return {sid for sid, st in self.states.items() if st["owner"] == tag}

    def bbox_for_states(self, state_ids, pad=20):
        """Pixel bounding box (x0, y0, x1, y1) covering the given states, or
        None if none of them are on the map - used to crop/zoom the world
        render down to just one country's own territory."""
        if not state_ids:
            return None
        mask = np.isin(self.state_arr, list(state_ids))
        if not mask.any():
            return None
        ys, xs = np.where(mask)
        h, w = self.state_arr.shape
        x0, x1 = max(0, int(xs.min()) - pad), min(w, int(xs.max()) + pad)
        y0, y1 = max(0, int(ys.min()) - pad), min(h, int(ys.max()) + pad)
        return x0, y0, x1, y1

    def refresh_owner_colors(self):
        self._build_luts()

    def province_centroids(self):
        """{province id: (x, y)} in rendered-image pixels.

        Railways are stored as a list of province ids with no coordinates
        anywhere, so drawing the network at all means working out where
        each province sits. Averaging every pixel of every province at once
        with bincount keeps that to a single pass over the map rather than
        one masked scan per province.
        """
        flat = self.province_arr.ravel()
        height, width = self.province_arr.shape
        ys, xs = np.divmod(np.arange(flat.size), width)
        counts = np.bincount(flat)
        counts[counts == 0] = 1     # avoid dividing by zero for absent ids
        sum_x = np.bincount(flat, weights=xs, minlength=len(counts))
        sum_y = np.bincount(flat, weights=ys, minlength=len(counts))
        centres = {}
        for pid in np.nonzero(np.bincount(flat))[0]:
            if pid == 0:
                continue
            centres[int(pid)] = (float(sum_x[pid] / counts[pid]),
                                 float(sum_y[pid] / counts[pid]))
        return centres


BUILDING_KEYS = ("infrastructure", "arms_factory", "industrial_complex",
                 "dockyard", "air_base", "synthetic_refinery", "fuel_silo",
                 "rocket_site", "nuclear_reactor", "radar_station",
                 "anti_air_building", "supply_node")

#: buildings the game stores against a single province rather than the
#: whole state, written inside `buildings` as `1234 = { naval_base = 3 }`.
#: A naval base is the one that decides whether a state has a working port
#: at all, so leaving these unreachable made harbour edits impossible.
PROVINCE_BUILDING_KEYS = ("naval_base", "bunker", "coastal_bunker", "floating_harbour")

RESOURCE_KEYS = ("oil", "aluminium", "rubber", "tungsten", "steel", "chromium")

STATE_CATEGORIES = ["wasteland", "small_island", "pastoral", "rural", "town",
                    "large_town", "city", "large_city", "metropolis", "megalopolis"]


def _without_province_blocks(buildings_block):
    """The buildings block with its `1234 = { ... }` province entries cut
    out, so reading a state-wide level can't accidentally pick up a number
    that belongs to one province."""
    out = []
    index = 0
    for match in re.finditer(r"\b\d+\s*=\s*\{", buildings_block):
        if match.start() < index:
            continue
        close = scan.find_matching_brace(buildings_block, match.end() - 1)
        if close == -1:
            continue
        out.append(buildings_block[index:match.start()])
        index = close + 1
    out.append(buildings_block[index:])
    return "".join(out)


def read_province_buildings(buildings_block):
    """{province_id: {building: level}} for the `1234 = { naval_base = 3 }`
    entries nested inside a state's `buildings` block."""
    out = {}
    for match in re.finditer(r"\b(\d+)\s*=\s*\{", buildings_block):
        close = scan.find_matching_brace(buildings_block, match.end() - 1)
        if close == -1:
            continue
        inner = buildings_block[match.end():close]
        levels = {}
        for key in PROVINCE_BUILDING_KEYS:
            found = re.search(r"\b" + key + r"\s*=\s*(\d+(?:\.\d+)?)", inner)
            if found:
                levels[key] = found.group(1)
        if levels:
            out[int(match.group(1))] = levels
    return out


def read_state_details(path):
    """Everything the state editor can change, pulled out of one state file.

    Per-province buildings (`1234 = { naval_base = 3 }`) are read back as
    well as the state-wide ones - a state's port lives there, so without
    them there was no way to give a coastal state a harbour.
    """
    with open(path, "r", encoding="utf-8-sig", errors="ignore") as f:
        raw = f.read()
    text = scan.strip_comments(raw)

    history = scan.first_block(text, "history") or ""
    buildings = scan.first_block(history, "buildings") or ""
    resources = scan.first_block(text, "resources") or ""

    def num(block, key):
        m = re.search(r"\b" + key + r"\s*=\s*(\d+(?:\.\d+)?)", block)
        return m.group(1) if m else ""

    vps = []
    for m in re.finditer(r"\bvictory_points\s*=\s*\{\s*(\d+)\s+(\d+)\s*\}", history):
        vps.append((int(m.group(1)), int(m.group(2))))

    cat = re.search(r"\bstate_category\s*=\s*(\w+)", text)
    return {
        "manpower": num(text, "manpower"),
        "state_category": cat.group(1) if cat else "",
        "buildings": {k: num(_without_province_blocks(buildings), k) for k in BUILDING_KEYS},
        "province_buildings": read_province_buildings(buildings),
        "resources": {k: num(resources, k) for k in RESOURCE_KEYS},
        "victory_points": vps,
        "raw": raw,
    }


def _set_or_add(text, key, value, anchor_re, indent):
    """Set `key = value`, or insert it right after `anchor_re` if absent."""
    pattern = re.compile(r"(\b" + key + r"\s*=\s*)(?!\{)\S+")
    if pattern.search(text):
        return pattern.sub(lambda m: m.group(1) + str(value), text, count=1)
    m = re.search(anchor_re, text)
    if not m:
        return text
    return text[:m.end()] + f"\n{indent}{key} = {value}" + text[m.end():]


def _edit_sub_block(text, key, edits, parent_anchor, indent):
    """Update numeric keys inside `key = { ... }`, creating the block if the
    state never had one. Unknown lines inside it are preserved."""
    edits = {k: v for k, v in edits.items() if str(v).strip() != ""}
    if not edits:
        return text
    m = re.search(r"\b" + key + r"\s*=\s*\{", text)
    if m:
        open_idx = m.end() - 1
        close_idx = scan.find_matching_brace(text, open_idx)
        if close_idx != -1:
            inner = text[open_idx + 1:close_idx]
            for k, v in edits.items():
                inner = _set_or_add(inner, k, v, r"\A", indent + "\t")
            return text[:open_idx + 1] + inner + text[close_idx:]
    body = "".join(f"\n{indent}\t{k} = {v}" for k, v in edits.items())
    anchor = re.search(parent_anchor, text)
    if not anchor:
        return text
    return text[:anchor.end()] + f"\n{indent}{key} = {{{body}\n{indent}}}" + text[anchor.end():]


def _edit_province_buildings(buildings_inner, province_buildings):
    """Apply {province_id: {building: level}} inside a `buildings` block.

    A level of 0 removes that building rather than writing `naval_base = 0`,
    and a province left with nothing loses its block entirely - the game
    treats a zero as "no port" either way, but a file full of empty blocks
    is noise for whoever reads it next.
    """
    for province, levels in province_buildings.items():
        wanted = {k: str(v).strip() for k, v in levels.items() if str(v).strip() != ""}
        wanted = {k: v for k, v in wanted.items() if v not in ("0", "0.0")}
        match = re.search(r"\b" + str(province) + r"\s*=\s*\{", buildings_inner)

        if match:
            close = scan.find_matching_brace(buildings_inner, match.end() - 1)
            if close == -1:
                continue
            if not wanted:
                # drop the whole block, and the blank line it leaves behind
                start = buildings_inner.rfind("\n", 0, match.start())
                start = start if start != -1 else match.start()
                buildings_inner = buildings_inner[:start] + buildings_inner[close + 1:]
                continue
            inner = buildings_inner[match.end():close]
            for key, value in wanted.items():
                inner = _set_or_add(inner, key, value, r"\A", "\t\t\t\t")
            buildings_inner = buildings_inner[:match.end()] + inner + buildings_inner[close:]
        elif wanted:
            body = "".join(f"\n\t\t\t\t{k} = {v}" for k, v in wanted.items())
            block = f"\n\t\t\t{province} = {{{body}\n\t\t\t}}"
            # insert ahead of the block's own trailing newline+indent, so the
            # closing brace stays on its own line instead of being pushed
            # onto the end of what we just wrote
            tail = re.search(r"\s*$", buildings_inner).group(0)
            buildings_inner = buildings_inner[:len(buildings_inner) - len(tail)] + block + tail
    return buildings_inner


def apply_state_edits(path, *, manpower=None, state_category=None,
                      buildings=None, resources=None, victory_points=None,
                      province_buildings=None):
    """Rewrite only the fields that changed in one state file, keeping a
    one-time .bak. Returns True if anything was written."""
    import shutil

    with open(path, "r", encoding="utf-8-sig", errors="ignore") as f:
        text = f.read()
    original = text

    if manpower not in (None, ""):
        text = _set_or_add(text, "manpower", int(manpower), r"\bid\s*=\s*\d+", "\t")
    if state_category:
        text = _set_or_add(text, "state_category", state_category, r"\bid\s*=\s*\d+", "\t")
    if resources:
        text = _edit_sub_block(text, "resources", resources, r"\bid\s*=\s*\d+", "\t")

    if buildings or province_buildings:
        m = re.search(r"\bhistory\s*=\s*\{", text)
        if m:
            open_idx = m.end() - 1
            close_idx = scan.find_matching_brace(text, open_idx)
            if close_idx != -1:
                inner = text[open_idx + 1:close_idx]
                if buildings:
                    inner = _edit_sub_block(inner, "buildings", buildings, r"\A", "\t\t")
                if province_buildings:
                    # after the state-wide pass, so a state that had no
                    # buildings block at all has one by now to write into
                    b = re.search(r"\bbuildings\s*=\s*\{", inner)
                    if not b:
                        inner = f"\n\t\tbuildings = {{\n\t\t}}" + inner
                        b = re.search(r"\bbuildings\s*=\s*\{", inner)
                    b_open = b.end() - 1
                    b_close = scan.find_matching_brace(inner, b_open)
                    if b_close != -1:
                        edited = _edit_province_buildings(
                            inner[b_open + 1:b_close], province_buildings)
                        inner = inner[:b_open + 1] + edited + inner[b_close:]
                text = text[:open_idx + 1] + inner + text[close_idx:]

    if victory_points is not None:
        text = re.sub(r"[ \t]*\bvictory_points\s*=\s*\{\s*\d+\s+\d+\s*\}\n?", "", text)
        if victory_points:
            block = "".join(f"\n\t\tvictory_points = {{ {p} {v} }}" for p, v in victory_points)
            text = re.sub(r"(\bhistory\s*=\s*\{)", lambda m: m.group(1) + block, text, count=1)

    if text == original:
        return False
    backup = path + ".bak"
    if not os.path.exists(backup):
        shutil.copy2(path, backup)
    undo.record(path, os.path.basename(path))
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return True


CORE_KEYS = {"core": "add_core_of", "claim": "add_claim_by"}


def apply_state_claims(path, *, add=(), remove=(), kind="core"):
    """Add or remove `add_core_of` / `add_claim_by` lines in one state.

    Cores used to appear only as a side effect of handing a state to a
    country, and claims not at all - so "these three provinces are claimed
    by Hungary" had to be typed into the files by hand.

    Returns True if the file changed.
    """
    import shutil

    key = CORE_KEYS[kind]
    with open(path, "r", encoding="utf-8-sig", errors="ignore") as handle:
        text = handle.read()
    original = text

    for tag in remove:
        text = re.sub(r"[ \t]*\b" + key + r"\s*=\s*" + tag + r"\b[ \t]*\n?", "", text)

    present = set(re.findall(r"\b" + key + r"\s*=\s*([A-Z][A-Z0-9]{2})", text))
    for tag in add:
        if tag in present:
            continue
        # after the owner line where one exists, otherwise straight into
        # history - a state nobody owns can still be claimed
        text, count = re.subn(r"(\bowner\s*=\s*[A-Z][A-Z0-9]{2})",
                              rf"\1\n\t\t{key} = {tag}", text, count=1)
        if count == 0:
            text, count = re.subn(r"(\bhistory\s*=\s*\{)",
                                  rf"\1\n\t\t{key} = {tag}", text, count=1)
        if count == 0:
            continue
        present.add(tag)

    if text == original:
        return False
    backup = path + ".bak"
    if not os.path.exists(backup):
        shutil.copy2(path, backup)
    undo.record(path, os.path.basename(path))
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)
    return True


def localise_state(mod_root, state_ids, states, record=None):
    """Bring a base-game state file into the mod so it can be edited without
    touching the installation. Returns the new paths."""
    import shutil

    moved = []
    for sid in state_ids:
        st = states.get(sid)
        if not st:
            continue
        path = st["file"]
        if os.path.abspath(path).startswith(os.path.abspath(mod_root)):
            continue
        dest = os.path.join(mod_root, "history", "states", os.path.basename(path))
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        if not os.path.isfile(dest):
            shutil.copy2(path, dest)
        st["file"] = dest
        moved.append(dest)
    if record and moved:
        record(moved)
    return moved


def give_states(mod_root, state_ids, tag, states, record=None):
    """Set `tag` as owner (and core) of each state, editing the state files
    in place with a one-time .bak backup. Files living in the base game are
    first copied into the mod, never touched at the source.

    Returns (changed_files, errors)."""
    import shutil

    changed = []
    errors = []
    tag = tag.upper()

    for sid in state_ids:
        st = states.get(sid)
        if not st:
            errors.append(f"state {sid}: not found")
            continue
        path = st["file"]

        # never write into the base game - bring the file into the mod
        if not os.path.abspath(path).startswith(os.path.abspath(mod_root)):
            dest = os.path.join(mod_root, "history", "states", os.path.basename(path))
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            if not os.path.isfile(dest):
                shutil.copy2(path, dest)
            path = dest
            st["file"] = dest

        try:
            with open(path, "r", encoding="utf-8-sig", errors="ignore") as f:
                text = f.read()
        except OSError as exc:
            errors.append(f"state {sid}: {exc}")
            continue

        backup = path + ".bak"
        if not os.path.exists(backup):
            shutil.copy2(path, backup)

        new_text, n = _OWNER_RE.subn(f"owner = {tag}", text, count=1)
        if n == 0:
            # no owner line (uncolonised state) - inject one into history
            new_text = re.sub(r"(history\s*=\s*\{)", rf"\1\n\t\towner = {tag}", text, count=1)
            if new_text == text:
                errors.append(f"state {sid}: couldn't find a place to set the owner")
                continue
        if f"add_core_of = {tag}" not in new_text and f"add_core_of={tag}" not in new_text:
            new_text = re.sub(r"(owner\s*=\s*[A-Z][A-Z0-9]{2})", rf"\1\n\t\tadd_core_of = {tag}",
                              new_text, count=1)

        undo.record(path, f"state {sid} ownership")
        with open(path, "w", encoding="utf-8") as f:
            f.write(new_text)
        st["owner"] = tag
        changed.append(path)

    if record and changed:
        record(changed)
    return changed, errors
