"""Division templates: the regiment/support grid a country actually fields.

The Units tab can already edit a sub-unit and add up a handful of ticked
battalions, but it can't produce a `division_template` block - the thing
that goes into history/units/<TAG>_1936.txt and decides what the country
starts the war with. That had to be typed out by hand, coordinates and all.

Layout rules the game imposes, and the reason the grid here is not a free
canvas:

* regiments sit at (x, y) with x a column (0-4) and y a row (0-4), so 25
  battalions at most;
* a column has to fill from y=0 with no gaps - a hole makes the game drop
  everything below it;
* support companies are their own 5-slot list, and crucially they do NOT
  count towards combat width, which is the number templates are usually
  built around.
"""

import glob
import os
import re

from app import pds_scan as scan
from app.game_paths import find_base_game

COLUMNS = 5
ROWS = 5
SUPPORT_SLOTS = 5

UNITS_DIR = os.path.join("common", "units")
OOB_DIR = os.path.join("history", "units")

# Only the stats a sub-unit file states as a real, absolute number are
# totalled. Attack, defence, breakthrough and armour are deliberately left
# out: on a line battalion they come from its equipment, not the template,
# and on a support company the value in the file is a multiplier - engineer
# declares `soft_attack = -0.5`, meaning -50%, so adding it to a regiment's
# number produces a division with negative attack. Showing four numbers
# that are right beats showing ten where six are fiction.
SUM_KEYS = ["manpower", "max_strength"]

#: organisation is the division's average across its battalions, not the
#: total - nine 60-org infantry make a 60-org division, not a 540-org one
AVG_KEYS = ["max_organisation"]

#: the slowest piece would set the pace - but no vanilla sub-unit declares
#: max_speed at all (it comes from equipment), so there is nothing to take a
#: minimum of and a speed row would sit permanently empty
MIN_KEYS = []

STAT_KEYS = ["combat_width"] + SUM_KEYS + AVG_KEYS + MIN_KEYS

#: read off the sub-unit blocks, whether or not they get totalled
READ_KEYS = STAT_KEYS + ["defense", "soft_attack", "hard_attack",
                         "breakthrough", "armor_value", "max_speed"]


def _unit_files(root):
    folder = os.path.join(root, UNITS_DIR)
    if not os.path.isdir(folder):
        return []
    return sorted(glob.glob(os.path.join(folder, "*.txt")))


def load_sub_units(mod_root):
    """{name: {stat: value, "support": bool}} from the mod and base game.

    The mod's own definition of a name wins, matching how the game loads
    these: last file loaded replaces an earlier one of the same name.
    """
    out = {}
    for root in (find_base_game(), mod_root):
        if not root:
            continue
        for path in _unit_files(root):
            try:
                with open(path, "r", encoding="utf-8-sig", errors="ignore") as handle:
                    text = scan.strip_comments(handle.read())
            except OSError:
                continue
            block = scan.first_block(text, "sub_units")
            if block is None:
                continue
            for name, body in scan.iter_named_blocks(block):
                stats = {}
                for key in READ_KEYS:
                    found = re.search(r"\b" + key + r"\s*=\s*(-?[\d.]+)", body)
                    if found:
                        try:
                            stats[key] = float(found.group(1))
                        except ValueError:
                            pass
                # a support company declares itself by the group it's in
                stats["support"] = bool(re.search(r"\bgroup\s*=\s*support\b", body))
                out[name] = stats
    return out


def division_stats(regiments, support, catalogue):
    """Totals for a template.

    `regiments` is {(x, y): name}, `support` a list of names. Combat width
    counts regiments only - support companies add none, which is the whole
    reason a 40-width template can still carry five of them.
    """
    totals = {}
    regiment_names = list(regiments.values())
    all_names = regiment_names + list(support)

    def values_for(key, names):
        return [catalogue[n][key] for n in names
                if n in catalogue and key in catalogue[n]]

    width = values_for("combat_width", regiment_names)
    if width:
        totals["combat_width"] = sum(width)

    for key in SUM_KEYS:
        found = values_for(key, all_names)
        if found:
            totals[key] = sum(found)

    for key in AVG_KEYS:
        found = values_for(key, all_names)
        if found:
            totals[key] = sum(found) / len(found)

    for key in MIN_KEYS:
        found = values_for(key, all_names)
        if found:
            totals[key] = min(found)
    return totals


def problems(regiments, support, catalogue=None):
    """What the game would mishandle, as a list of plain sentences."""
    found = []
    if not regiments:
        found.append("A division needs at least one regiment.")

    for x in range(COLUMNS):
        column = sorted(y for (cx, y) in regiments if cx == x)
        if column and column != list(range(len(column))):
            found.append(f"Column {x + 1} has a gap — a column must fill from the top, "
                         "or the game drops everything below the hole.")

    if len(support) > SUPPORT_SLOTS:
        found.append(f"{len(support)} support companies, but only {SUPPORT_SLOTS} fit.")

    if catalogue:
        for name in set(regiments.values()):
            if name in catalogue and catalogue[name].get("support"):
                found.append(f"'{name}' is a support company — it belongs in the support "
                             "slots, not the regiment grid.")
        for name in support:
            if name in catalogue and not catalogue[name].get("support"):
                found.append(f"'{name}' is a line battalion, not a support company.")
        unknown = [n for n in set(list(regiments.values()) + list(support))
                   if n not in catalogue]
        if unknown:
            found.append("Not defined in any units file: " + ", ".join(sorted(unknown)[:4]))
    return found


def format_template(name, regiments, support, *, names_group=""):
    """The `division_template = { ... }` block, ready to paste into an OOB.

    Entries are emitted column by column so the text reads the way the grid
    looks, rather than in whatever order the dictionary happens to hold.
    """
    lines = ["division_template = {", f'\tname = "{name}"', ""]
    if names_group:
        lines.append(f"\tdivision_names_group = {names_group}")
        lines.append("")

    lines.append("\tregiments = {")
    for x in range(COLUMNS):
        for y in range(ROWS):
            unit = regiments.get((x, y))
            if unit:
                lines.append(f"\t\t{unit} = {{ x = {x} y = {y} }}")
    lines.append("\t}")

    if support:
        lines.append("")
        lines.append("\tsupport = {")
        for i, unit in enumerate(support[:SUPPORT_SLOTS]):
            lines.append(f"\t\t{unit} = {{ x = 0 y = {i} }}")
        lines.append("\t}")

    lines.append("}")
    return "\n".join(lines) + "\n"


def oob_files(mod_root):
    """The mod's own OOB files - where a template can be appended."""
    folder = os.path.join(mod_root, OOB_DIR)
    if not os.path.isdir(folder):
        return []
    return sorted(glob.glob(os.path.join(folder, "*.txt")))


def append_to_oob(path, block):
    """Put a template at the top of an OOB file, where templates live.

    Appending at the end would place it after the `units = { ... }` block
    that references it; the game reads the file in order, so a template
    defined below its first use is not found.
    """
    existing = ""
    if os.path.isfile(path):
        with open(path, "r", encoding="utf-8-sig", errors="ignore") as handle:
            existing = handle.read()
    return block + "\n" + existing
