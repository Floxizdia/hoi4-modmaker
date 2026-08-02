"""Peace conference cost modifiers: how expensive a peace action (taking
states, puppeting, liberating, forcing a government) is under conditions
the mod defines - written to common/peace_conference/cost_modifiers/.

New peace action TYPES aren't something script can add (take_states/
puppet/force_government/liberate are the engine's fixed set per the game's
own documentation) - what mods actually tune here is the cost multiplier,
which is exactly what this wraps.
"""

import os

from app import pds_scan as scan
from app.map_data import BASE_GAME

MODIFIER_DIR = os.path.join("common", "peace_conference", "cost_modifiers")
FILENAME = "zzz_custom_peace_modifiers.txt"

PEACE_ACTION_TYPES = ["take_states", "puppet", "force_government", "liberate"]

CATEGORIES = [
    "other", "occupation", "ideology", "is_core", "core_of_ally", "has_claim",
    "defensive_war", "treaties_or_conferences", "belonged_to_someone_else",
    "events_or_focuses", "continuous_political_action",
]


def list_modifiers(mod_root):
    """{modifier_id: source} across base game + mod."""
    out = {}
    for root, source in ((BASE_GAME, "vanilla"), (mod_root, "mod")):
        folder = os.path.join(root, MODIFIER_DIR)
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
            outer = scan.first_block(text, "peace_action_modifiers")
            if outer is None:
                continue
            for mod_id, _ in scan.iter_named_blocks(outer):
                out[mod_id] = source
    return out


def create_modifier(mod_root, *, modifier_id, category, peace_action_types,
                     enable_raw, cost_multiplier):
    """`peace_action_types` is a list of one or more of PEACE_ACTION_TYPES."""
    def indent(raw, depth=3):
        pad = "\t" * depth
        return "\n".join(pad + line.strip() for line in raw.strip().splitlines() if line.strip())

    if len(peace_action_types) == 1:
        type_line = f"\t\tpeace_action_type = {peace_action_types[0]}"
    else:
        type_line = "\t\tpeace_action_type = { " + " ".join(peace_action_types) + " }"

    entry = (
        f"\t{modifier_id} = {{\n"
        f"\t\tcategory = {category}\n"
        f"{type_line}\n"
        "\t\tenable = {\n" + indent(enable_raw) + "\n\t\t}\n"
        f"\t\tcost_multiplier = {cost_multiplier}\n"
        "\t}\n"
    )

    folder = os.path.join(mod_root, MODIFIER_DIR)
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, FILENAME)
    if os.path.isfile(path):
        with open(path, "r", encoding="utf-8-sig", errors="ignore") as f:
            existing = f.read().rstrip()
        if existing.endswith("}"):
            content = existing[:-1].rstrip("\n") + "\n" + entry + "}\n"
        else:
            content = existing + "\n\n" + f"peace_action_modifiers = {{\n{entry}}}\n"
    else:
        content = f"peace_action_modifiers = {{\n{entry}}}\n"

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return path
