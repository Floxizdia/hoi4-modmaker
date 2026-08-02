"""War goal (casus belli) types: what a war is fought to achieve - take
states, puppet, liberate, topple a government, annex outright - and what it
costs in war support to justify. Written to common/wargoals/, wrapped in
the game's single `wargoal_types = { ... }` block. ROOT is the goal's
owner, PREV the original target.
"""

import os

from app import pds_scan as scan
from app import loc_surgery
from app.map_data import BASE_GAME

WARGOALS_DIR = "common/wargoals".replace("/", os.sep)
FILENAME = "zzz_custom_wargoals.txt"

GOAL_KINDS = ["take_states", "puppet", "liberate", "force_government", "annex"]


def list_wargoals(mod_root):
    """{wargoal_id: source} across base game + mod."""
    out = {}
    for root, source in ((BASE_GAME, "vanilla"), (mod_root, "mod")):
        folder = os.path.join(root, WARGOALS_DIR)
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
            outer = scan.first_block(text, "wargoal_types")
            if outer is None:
                continue
            for goal_id, _ in scan.iter_named_blocks(outer):
                out[goal_id] = source
    return out


def create_wargoal(mod_root, *, wargoal_id, goal_kind, war_name_key, allowed_raw,
                    base_cost, per_state_cost, threat, expire_days=None, war_name_text=""):
    """`goal_kind` picks the effect block (take_states/puppet/liberate/
    force_government all take an `always = yes` sub-trigger; annex needs
    none - it's expressed purely through take_states with no restriction
    plus a very high threat/cost, matching vanilla's `annex_everything`)."""
    def indent(raw, depth=2):
        pad = "\t" * depth
        return "\n".join(pad + line.strip() for line in raw.strip().splitlines() if line.strip())

    lines = [f"\t{wargoal_id} = {{"]
    if war_name_key:
        lines.append(f"\t\twar_name = {war_name_key}")
    lines.append("\t\tallowed = {")
    if allowed_raw.strip():
        lines.append(indent(allowed_raw, 3))
    lines.append("\t\t}")

    if goal_kind == "take_states":
        lines.append("\t\ttake_states = {\n\t\t}")
    elif goal_kind == "puppet":
        lines.append("\t\tpuppet = {\n\t\t\talways = yes\n\t\t}")
    elif goal_kind == "liberate":
        lines.append("\t\tliberate = {\n\t\t\talways = yes\n\t\t}")
    elif goal_kind == "force_government":
        lines.append("\t\tforce_government = {\n\t\t\talways = yes\n\t\t}")
    elif goal_kind == "annex":
        lines.append("\t\ttake_states = {\n\t\t}")

    lines.append(f"\t\tgenerate_base_cost = {base_cost}")
    lines.append(f"\t\tgenerate_per_state_cost = {per_state_cost}")
    if expire_days:
        lines.append(f"\t\texpire = {expire_days}")
    lines.append(f"\t\tthreat = {threat}")
    lines.append("\t}\n")
    entry = "\n".join(lines)

    folder = os.path.join(mod_root, WARGOALS_DIR)
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, FILENAME)
    if os.path.isfile(path):
        with open(path, "r", encoding="utf-8-sig", errors="ignore") as f:
            existing = f.read().rstrip()
        if existing.endswith("}"):
            content = existing[:-1].rstrip("\n") + "\n" + entry + "}\n"
        else:
            content = existing + "\n\n" + f"wargoal_types = {{\n{entry}}}\n"
    else:
        content = f"wargoal_types = {{\n{entry}}}\n"

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

    if war_name_key and war_name_text:
        loc_surgery.set_key(mod_root, war_name_key, war_name_text)

    return path
