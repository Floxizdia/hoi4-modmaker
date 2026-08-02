"""Opinion modifiers: the named blocks (`guarantee`, `non_aggression_pact`,
`at_war`, ...) that decisions, events, focuses and diplomatic actions grant
via `add_opinion_modifier`. Several other tabs in this app (Diplomatic
Actions, the Non-Aggression Pact focus template) already reference
modifier ids like `temporary_nap_signed` without anywhere to define them -
this closes that gap.
"""

import os

from app import pds_scan as scan
from app import loc_surgery
from app.map_data import BASE_GAME

MODIFIER_DIR = os.path.join("common", "opinion_modifiers")
FILENAME = "zzz_custom_opinion_modifiers.txt"


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
            outer = scan.first_block(text, "opinion_modifiers")
            if outer is None:
                continue
            for mod_id, _ in scan.iter_named_blocks(outer):
                out[mod_id] = source
    return out


def create_modifier(mod_root, *, modifier_id, display_name, value, duration_unit="",
                     duration_amount="", decay=None, min_trust=None, max_trust=None,
                     is_trade=False, target_only=False):
    """`duration_unit` is "days"/"months"/"years"/"" (permanent until removed).
    `target_only` writes `target = yes` (only visible to the target country,
    like vanilla's targeted `guarantee` entry)."""
    lines = [f"\tvalue = {value}"]
    if target_only:
        lines.append("\ttarget = yes")
    if is_trade:
        lines.append("\ttrade = yes")
    if duration_unit and duration_amount:
        lines.append(f"\t{duration_unit} = {duration_amount}")
    if decay is not None:
        lines.append(f"\tdecay = {decay}")
    if min_trust is not None:
        lines.append(f"\tmin_trust = {min_trust}")
    if max_trust is not None:
        lines.append(f"\tmax_trust = {max_trust}")

    entry = f"\t{modifier_id} = {{\n" + "\n".join(lines) + "\n\t}\n"

    folder = os.path.join(mod_root, MODIFIER_DIR)
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, FILENAME)
    if os.path.isfile(path):
        with open(path, "r", encoding="utf-8-sig", errors="ignore") as f:
            existing = f.read().rstrip()
        if existing.endswith("}"):
            content = existing[:-1].rstrip("\n") + "\n" + entry + "}\n"
        else:
            content = existing + "\n\n" + f"opinion_modifiers = {{\n{entry}}}\n"
    else:
        content = f"opinion_modifiers = {{\n{entry}}}\n"

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

    created = [path]
    if display_name:
        created.append(loc_surgery.set_key(mod_root, modifier_id, display_name))
    return created
