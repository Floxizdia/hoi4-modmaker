"""New equipment: a further tier/variant of an existing archetype (infantry
weapons, tank chassis, plane airframes, ship hulls...). Defining a brand
new archetype needs 3D models/sprites the game engine expects, which is out
of scope for a script-only tool - what's genuinely useful here, and what
every "add a late-war upgrade" mod actually does, is adding a new
`archetype = X` tier with `parent = <previous tier>` and upgraded stats.
Written to common/units/equipment/.

Hooking it up so a technology unlocks it means adding this equipment's id
to that technology's `enable_equipments = { ... }` - technologies files are
hand-authored, so this hands back the exact line to paste rather than
touching them automatically.
"""

import os

from app import pds_scan as scan
from app.map_data import BASE_GAME

EQUIPMENT_DIR = os.path.join("common", "units", "equipment")
FILENAME = "zzz_custom_equipment.txt"

STAT_FIELDS = [
    "reliability", "maximum_speed", "defense", "breakthrough", "hardness",
    "armor_value", "soft_attack", "hard_attack", "ap_attack", "air_attack",
    "build_cost_ic",
]

ARCHETYPES = [
    "infantry_equipment", "motorized_equipment", "motorbike_equipment", "artillery_equipment",
    "rocket_artillery_equipment", "anti_air_equipment", "anti_tank_equipment",
    "light_tank_chassis", "medium_tank_chassis", "heavy_tank_chassis", "super_heavy_tank_chassis",
    "modern_tank_chassis", "amphibious_tank_chassis", "land_cruiser_chassis",
    "mechanized_equipment", "amphibious_mechanized_equipment", "armored_car_equipment",
    "small_plane_airframe", "medium_plane_airframe", "large_plane_airframe", "cv_small_plane_airframe",
    "transport_plane_equipment", "helicopter_equipment",
    "ship_hull_light", "ship_hull_cruiser", "ship_hull_heavy", "ship_hull_carrier",
    "ship_hull_submarine", "convoy",
]


def list_equipment(mod_root, archetype=None):
    """{equipment_id: (source, archetype, parent, year)} across base game +
    mod, optionally filtered to one archetype."""
    out = {}
    for root, source in ((BASE_GAME, "vanilla"), (mod_root, "mod")):
        folder = os.path.join(root, EQUIPMENT_DIR)
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
            outer = scan.first_block(text, "equipments")
            if outer is None:
                continue
            for eq_id, inner in scan.iter_named_blocks(outer):
                arch = scan.scalar(inner, "archetype") or (eq_id if scan.scalar(inner, "is_archetype") == "yes" else "")
                if archetype and arch != archetype:
                    continue
                out[eq_id] = (source, arch, scan.scalar(inner, "parent") or "", scan.scalar(inner, "year") or "")
    return out


def create_equipment(mod_root, *, equipment_id, archetype, parent, year, priority,
                      visual_level, stats, resources):
    """`stats` maps a subset of STAT_FIELDS to values; `resources` maps
    resource token -> amount. Only non-empty stats/resources are written -
    anything omitted inherits from `parent` like vanilla tiers do."""
    lines = [f"\t{equipment_id} = {{", f"\t\tyear = {year}", f"\t\tarchetype = {archetype}"]
    if parent:
        lines.append(f"\t\tparent = {parent}")
    if priority:
        lines.append(f"\t\tpriority = {priority}")
    if visual_level:
        lines.append(f"\t\tvisual_level = {visual_level}")
    lines.append("\t\tactive = yes")
    for key in STAT_FIELDS:
        if stats.get(key):
            lines.append(f"\t\t{key} = {stats[key]}")
    if resources:
        lines.append("\t\tresources = {")
        for tok, amt in resources.items():
            lines.append(f"\t\t\t{tok} = {amt}")
        lines.append("\t\t}")
    lines.append("\t}\n")
    entry = "\n".join(lines)

    folder = os.path.join(mod_root, EQUIPMENT_DIR)
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, FILENAME)
    if os.path.isfile(path):
        with open(path, "r", encoding="utf-8-sig", errors="ignore") as f:
            existing = f.read().rstrip()
        if existing.endswith("}"):
            content = existing[:-1].rstrip("\n") + "\n" + entry + "}\n"
        else:
            content = existing + "\n\n" + f"equipments = {{\n{entry}}}\n"
    else:
        content = f"equipments = {{\n{entry}}}\n"

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return path
