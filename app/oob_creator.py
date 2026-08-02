"""Starting forces (order of battle): the divisions/fleets/air wings a
country begins the game with, written the same way the base game's own
history/units/<TAG>_1936*.txt files are. A country only picks these up
through `oob = "..."` / `set_naval_oob = "..."` / `set_air_oob = "..."` in
its history/countries file, which this deliberately does NOT edit
automatically - that file already exists with real content for a loaded
mod's country, and guessing where to splice a reference into arbitrary
existing script is exactly the kind of edit that corrupts a file quietly.
Instead the tab hands back the exact line to paste in.
"""

import os

from app import pds_scan as scan
from app.map_data import BASE_GAME

UNITS_DIR = os.path.join("history", "units")


def list_division_templates(mod_root):
    """{template_name: source} - the display name IS the reference key the
    game uses (division_template = "Exact Name"), there's no separate id."""
    out = {}
    for root, source in ((BASE_GAME, "vanilla"), (mod_root, "mod")):
        folder = os.path.join(root, UNITS_DIR)
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
            for start, end, inner in scan.iter_blocks(text, "division_template"):
                tmpl_name = scan.scalar(inner, "name", "")
                if tmpl_name:
                    out[tmpl_name.strip('"')] = source
    return out


def list_regiment_types(mod_root):
    """Every sub_unit key across common/units (base game + mod) - land
    regiment types, ship hull types and air wing equipment groups all share
    this one pool, which is why they aren't split into separate lists."""
    out = []
    for root in (BASE_GAME, mod_root):
        folder = os.path.join(root, "common", "units")
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
            wrapper = scan.first_block(text, "sub_units")
            if not wrapper:
                continue
            for sub_name, _ in scan.iter_named_blocks(wrapper):
                if sub_name not in out:
                    out.append(sub_name)
    return sorted(out)


def list_equipment_ids(mod_root):
    """Every equipment id across common/units/equipment (base game + mod),
    used for ship/air-wing loadouts."""
    out = []
    for root in (BASE_GAME, mod_root):
        folder = os.path.join(root, "common", "units", "equipment")
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
            wrapper = scan.first_block(text, "equipments")
            if not wrapper:
                continue
            for eq_id, _ in scan.iter_named_blocks(wrapper):
                if eq_id not in out:
                    out.append(eq_id)
    return sorted(out)


def _write(mod_root, filename, content):
    folder = os.path.join(mod_root, UNITS_DIR)
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return path


def create_land_oob(mod_root, *, tag, oob_name, template_name, regiments, support,
                     divisions, start_experience=0.2, start_equipment=0.8):
    """`regiments`/`support` are [(type, x, y), ...]. `divisions` is
    [{"name":.., "location":.., "count":..}] - `count` identical divisions
    are written per row, each with its own `division = {...}` block since
    the game has no "repeat N times" shorthand."""
    reg_lines = "\n".join(f"\t\t{t} = {{ x = {x} y = {y} }}" for t, x, y in regiments)
    sup_lines = "\n".join(f"\t\t{t} = {{ x = {x} y = {y} }}" for t, x, y in support)

    template_block = (
        "division_template = {\n"
        f'\tname = "{template_name}"\n'
        "\tregiments = {\n" + (reg_lines + "\n" if reg_lines else "") + "\t}\n"
        + ("\tsupport = {\n" + sup_lines + "\n\t}\n" if sup_lines else "")
        + "}\n"
    )

    division_blocks = []
    for row in divisions:
        for i in range(max(1, int(row.get("count", 1)))):
            division_blocks.append(
                "\tdivision = {\n"
                f'\t\tname = "{row["name"]}"\n'
                f"\t\tlocation = {row['location']}\n"
                f'\t\tdivision_template = "{template_name}"\n'
                f"\t\tstart_experience_factor = {start_experience}\n"
                f"\t\tstart_equipment_factor = {start_equipment}\n"
                "\t}\n"
            )
    units_block = "units = {\n" + "".join(division_blocks) + "}\n"

    content = template_block + "\n" + units_block
    path = _write(mod_root, f"{tag}_{oob_name}.txt", content)
    return path, f'oob = "{tag}_{oob_name}"'


def create_air_oob(mod_root, *, tag, oob_name, wings):
    """`wings` is [{"location":.., "equipment":.., "amount":..}, ...] -
    entries sharing a location are grouped under one air_wings province key,
    matching how the base game writes multiple squadrons at one airbase."""
    by_location = {}
    for w in wings:
        by_location.setdefault(w["location"], []).append((w["equipment"], w["amount"]))

    body = []
    for location, entries in by_location.items():
        lines = "\n".join(f'\t\t{eq} = {{ owner = "{tag}" amount = {amount} }}' for eq, amount in entries)
        body.append(f"\t{location} = {{\n{lines}\n\t}}\n")

    content = "air_wings = {\n" + "".join(body) + "}\n"
    path = _write(mod_root, f"{tag}_{oob_name}_air.txt", content)
    return path, f'set_air_oob = "{tag}_{oob_name}_air"'


def create_naval_oob(mod_root, *, tag, oob_name, fleet_name, naval_base, ships):
    """`ships` is [{"name":.., "hull":.., "equipment":.., "amount":..}]."""
    ship_lines = "\n".join(
        f'\t\t\tship = {{ name = "{s["name"]}" definition = {s["hull"]} '
        f'equipment = {{ {s["equipment"]} = {{ amount = {s["amount"]} owner = {tag} }} }} }}'
        for s in ships
    )
    content = (
        "units = {\n"
        "\tfleet = {\n"
        f'\t\tname = "{fleet_name}"\n'
        f"\t\tnaval_base = {naval_base}\n"
        "\t\ttask_force = {\n"
        f'\t\t\tname = "{fleet_name}"\n'
        f"\t\t\tlocation = {naval_base}\n"
        f"{ship_lines}\n"
        "\t\t}\n"
        "\t}\n"
        "}\n"
    )
    path = _write(mod_root, f"{tag}_{oob_name}_naval.txt", content)
    return path, f'set_naval_oob = "{tag}_{oob_name}_naval"'
