"""Intelligence agency upgrades: the tree every country's spy agency spends
its upgrade points in, grouped into branches (intelligence, defense,
operation, operative, crypto). common/intelligence_agency_upgrades/.

Note on scope: the actual La Resistance `common/operatives/*.txt` (spy
archetype definitions) aren't present in this install - operative-type
data is gated DLC content this tool has no verified real file to check
syntax against, so guessing at it risked shipping a schema nobody could
confirm. The agency upgrade tree, by contrast, ships as free base-game
content (added alongside La Resistance) and is fully present and verified
here, so that's what this creator targets - still squarely in the spy/
operative gameplay area the feature request was going for.
"""

import os

from app import pds_scan as scan
from app.map_data import BASE_GAME

UPGRADE_DIR = os.path.join("common", "intelligence_agency_upgrades")
FILENAME = "zzz_custom_agency_upgrades.txt"

BRANCHES = ["branch_intelligence", "branch_defense", "branch_operation", "branch_operative", "branch_crypto"]


def list_upgrades(mod_root):
    """{upgrade_id: (source, branch, num_levels)} across base game + mod."""
    out = {}
    for root, source in ((BASE_GAME, "vanilla"), (mod_root, "mod")):
        folder = os.path.join(root, UPGRADE_DIR)
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
            for branch_id, branch_inner in scan.iter_named_blocks(text):
                for up_id, up_inner in scan.iter_named_blocks(branch_inner):
                    levels = len(list(scan.iter_blocks(up_inner, "level")))
                    out[up_id] = (source, branch_id, levels)
    return out


def create_upgrade(mod_root, *, upgrade_id, branch, picture, ai_factor, progress_modifier_raw, level_modifiers):
    """`level_modifiers` is a list of raw modifier-block-inner strings, one
    per level (in order) - each becomes its own `level = { modifier = {...} }`."""
    def indent(raw, depth):
        pad = "\t" * depth
        return "\n".join(pad + line.strip() for line in raw.strip().splitlines() if line.strip())

    lines = [f"\t{upgrade_id} = {{", f"\t\tpicture = {picture}"]
    lines.append("\t\tai_will_do = {")
    lines.append(f"\t\t\tfactor = {ai_factor}")
    lines.append("\t\t}")
    if progress_modifier_raw.strip():
        lines.append("\t\tmodifiers_during_progress = {")
        lines.append(indent(progress_modifier_raw, 3))
        lines.append("\t\t}")
    for mod_raw in level_modifiers:
        lines.append("\t\tlevel = {")
        lines.append("\t\t\tmodifier = {")
        lines.append(indent(mod_raw, 4))
        lines.append("\t\t\t}")
        lines.append("\t\t}")
    lines.append("\t}\n")
    entry = "\n".join(lines)

    folder = os.path.join(mod_root, UPGRADE_DIR)
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, FILENAME)
    if os.path.isfile(path):
        with open(path, "r", encoding="utf-8-sig", errors="ignore") as f:
            existing = f.read().rstrip()
        # find the matching branch wrapper if it's already in this file, else append a new one
        branch_start = existing.find(f"{branch} = {{")
        if branch_start != -1:
            open_idx = existing.index("{", branch_start)
            close_idx = scan.find_matching_brace(existing, open_idx)
            content = existing[:close_idx] + entry + existing[close_idx:]
        else:
            content = existing + "\n\n" + f"{branch} = {{\n{entry}}}\n"
    else:
        content = f"{branch} = {{\n{entry}}}\n"

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return path
