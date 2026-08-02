"""Which trait ids exist for which leader role, read straight out of the
game's own trait definitions rather than hand-typed - a curated list would
drift the moment a mod adds its own traits, which is exactly the case this
app has to handle well.
"""

import os
import re

from app import pds_scan as scan
from app.map_data import BASE_GAME

_TYPE_RE = re.compile(r"\btype\s*=\s*(\w+)")

# land covers both corps_commander and field_marshal - the game doesn't
# distinguish between the two army roles at the trait level
ROLE_TRAIT_TYPES = {
    "corps_commander": {"land", "all"},
    "field_marshal": {"land", "all"},
    "navy_leader": {"navy", "all"},
}


def _land_navy_traits(mod_root):
    """{name: type} from every common/unit_leader/*.txt across base game +
    mod, mod's own traits winning on a name collision (matches in-game
    override behaviour)."""
    out = {}
    for root in (BASE_GAME, mod_root):
        folder = os.path.join(root, "common", "unit_leader")
        if not os.path.isdir(folder):
            continue
        for name in sorted(os.listdir(folder)):
            if not name.endswith(".txt"):
                continue
            try:
                with open(os.path.join(folder, name), "r", encoding="utf-8-sig", errors="ignore") as f:
                    text = scan.strip_comments(f.read())
            except OSError:
                continue
            wrapper = scan.first_block(text, "leader_traits")
            if not wrapper:
                continue
            for trait_id, inner in scan.iter_named_blocks(wrapper):
                m = _TYPE_RE.search(inner)
                out[trait_id] = m.group(1) if m else "all"
    return out


def _scientist_traits(mod_root):
    names = []
    for root in (BASE_GAME, mod_root):
        folder = os.path.join(root, "common", "scientist_traits")
        if not os.path.isdir(folder):
            continue
        for name in sorted(os.listdir(folder)):
            if not name.endswith(".txt"):
                continue
            try:
                with open(os.path.join(folder, name), "r", encoding="utf-8-sig", errors="ignore") as f:
                    text = scan.strip_comments(f.read())
            except OSError:
                continue
            for trait_id, _ in scan.iter_named_blocks(text):
                if trait_id not in names:
                    names.append(trait_id)
    return names


def _political_traits(mod_root):
    """{name: source} for every common/country_leader/*.txt trait, across
    base game + mod - the political (head of state/government) trait pool,
    which uses the same `leader_traits = { id = {...} }` wrapper as
    common/unit_leader but lives in its own folder."""
    out = {}
    for root, source in ((BASE_GAME, "vanilla"), (mod_root, "mod")):
        folder = os.path.join(root, "common", "country_leader")
        if not os.path.isdir(folder):
            continue
        for name in sorted(os.listdir(folder)):
            if not name.endswith(".txt"):
                continue
            try:
                with open(os.path.join(folder, name), "r", encoding="utf-8-sig", errors="ignore") as f:
                    text = scan.strip_comments(f.read())
            except OSError:
                continue
            wrapper = scan.first_block(text, "leader_traits")
            if not wrapper:
                continue
            for trait_id, _ in scan.iter_named_blocks(wrapper):
                out[trait_id] = source
    return out


def traits_for_role(mod_root, role_key):
    """Sorted list of trait ids usable on this role. Empty for roles with no
    well-known trait pool (advisor's traits are ideas, handled separately)."""
    if role_key == "country_leader":
        return sorted(_political_traits(mod_root))
    if role_key in ROLE_TRAIT_TYPES:
        wanted = ROLE_TRAIT_TYPES[role_key]
        traits = _land_navy_traits(mod_root)
        return sorted(name for name, kind in traits.items() if kind in wanted)
    if role_key == "scientist":
        return sorted(_scientist_traits(mod_root))
    return []


def all_traits_by_category(mod_root):
    """{category: {trait_id: source}} across political/land/navy/scientist,
    for a browsing/reference view - source is 'vanilla' or 'mod'."""
    land_navy = _land_navy_traits(mod_root)
    land_navy_source = {}
    for root, source in ((BASE_GAME, "vanilla"), (mod_root, "mod")):
        folder = os.path.join(root, "common", "unit_leader")
        if not os.path.isdir(folder):
            continue
        for name in sorted(os.listdir(folder)):
            if not name.endswith(".txt"):
                continue
            try:
                with open(os.path.join(folder, name), "r", encoding="utf-8-sig", errors="ignore") as f:
                    text = scan.strip_comments(f.read())
            except OSError:
                continue
            wrapper = scan.first_block(text, "leader_traits")
            if not wrapper:
                continue
            for trait_id, _ in scan.iter_named_blocks(wrapper):
                land_navy_source[trait_id] = source

    scientist_source = {}
    for root, source in ((BASE_GAME, "vanilla"), (mod_root, "mod")):
        folder = os.path.join(root, "common", "scientist_traits")
        if not os.path.isdir(folder):
            continue
        for name in sorted(os.listdir(folder)):
            if not name.endswith(".txt"):
                continue
            try:
                with open(os.path.join(folder, name), "r", encoding="utf-8-sig", errors="ignore") as f:
                    text = scan.strip_comments(f.read())
            except OSError:
                continue
            for trait_id, _ in scan.iter_named_blocks(text):
                scientist_source[trait_id] = source

    return {
        "political": _political_traits(mod_root),
        "land": {n: s for n, s in land_navy_source.items() if land_navy.get(n) in ("land", "all")},
        "navy": {n: s for n, s in land_navy_source.items() if land_navy.get(n) in ("navy", "all")},
        "scientist": scientist_source,
    }
