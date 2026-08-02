"""Build a brand new state from scratch, for provinces that exist on the
map but no state file claims yet (typically a custom map extension — the
vanilla map is already 100% covered by vanilla states). Unlike
state_surgery.py, which edits an existing state file byte-for-byte, this
only ever writes a new file, so there's nothing hand-authored to disturb.
"""

import os

MANDATORY_CATEGORY = "rural"


def create_state(mod_root, *, state_id, name, owner, province_ids, category=MANDATORY_CATEGORY,
                  manpower=0, local_supplies=1.0, resources=None, buildings=None, victory_points=None,
                  is_core=True):
    """Writes history/states/<id>-<name>.txt. Returns the path."""
    lines = [
        "state={",
        f"\tid={state_id}",
        f'\tname="STATE_{state_id}"',
        f"\tmanpower = {manpower}",
    ]
    if resources:
        lines.append("\tresources = {")
        for tok, amt in resources.items():
            lines.append(f"\t\t{tok} = {amt}")
        lines.append("\t}")
    lines.append(f"\tstate_category = {category}")
    lines.append("\thistory={")
    if owner:
        lines.append(f"\t\towner = {owner}")
    for prov, val in (victory_points or []):
        lines.append("\t\tvictory_points = {")
        lines.append(f"\t\t\t{prov} {val}")
        lines.append("\t\t}")
    if buildings:
        lines.append("\t\tbuildings = {")
        for tok, lvl in buildings.items():
            lines.append(f"\t\t\t{tok} = {lvl}")
        lines.append("\t\t}")
    if owner and is_core:
        lines.append(f"\t\tadd_core_of = {owner}")
    lines.append("\t}")
    lines.append("\tprovinces={")
    lines.append("\t\t" + " ".join(str(p) for p in province_ids))
    lines.append("\t}")
    lines.append(f"\tlocal_supplies={local_supplies}")
    lines.append("}\n")
    content = "\n".join(lines)

    safe_name = "".join(c if c.isalnum() else "_" for c in name).strip("_") or f"state_{state_id}"
    folder = os.path.join(mod_root, "history", "states")
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, f"{state_id}-{safe_name}.txt")
    if os.path.exists(path):
        raise FileExistsError(f"{path} already exists")

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return path
