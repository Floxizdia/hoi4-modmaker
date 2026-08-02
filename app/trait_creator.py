"""Trait creator: write a brand-new political leader / military commander /
scientist trait into the open mod. Each role uses a different file location
and wrapper - see the game's own common/country_leader, common/unit_leader
and common/scientist_traits for the exact shapes this mirrors.
"""

import os

from app import loc_surgery

ROLE_FOLDERS = {
    "political": os.path.join("common", "country_leader"),
    "land": os.path.join("common", "unit_leader"),
    "navy": os.path.join("common", "unit_leader"),
    "scientist": os.path.join("common", "scientist_traits"),
}
FILENAME = "zzz_custom_traits.txt"


def create_trait(mod_root, *, role, trait_id, display_name, random=False,
                  unit_type="all", ai_factor=1, modifiers_raw=""):
    """`role` is political/land/navy/scientist. `unit_type` only matters for
    land/navy (written as `type = land/navy/all`). Returns the files written."""
    modifiers_raw = modifiers_raw.strip()
    modifier_lines = "\n".join("\t\t" + line.strip() for line in modifiers_raw.splitlines() if line.strip())

    if role == "scientist":
        entry = (
            f"\t{trait_id} = {{\n"
            "\t\tmodifier = {\n"
            + (modifier_lines if modifier_lines else "\t\t\t# add special_project modifiers here")
            + "\n\t\t}\n"
            "\t}\n"
        )
    else:
        type_line = f"\t\ttype = {unit_type}\n" if role in ("land", "navy") else ""
        entry = (
            f"\t{trait_id} = {{\n"
            f"{type_line}"
            f"\t\trandom = {'yes' if random else 'no'}\n"
            + (f"{modifier_lines}\n" if modifier_lines else "")
            + "\t\tai_will_do = {\n"
            f"\t\t\tfactor = {ai_factor}\n"
            "\t\t}\n"
            "\t}\n"
        )

    folder = os.path.join(mod_root, ROLE_FOLDERS[role])
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, FILENAME)
    created = []
    # scientist traits are flat top-level blocks; the other two roles share
    # one leader_traits = { ... } wrapper per file
    wrapper = None if role == "scientist" else "leader_traits"
    if os.path.isfile(path):
        with open(path, "r", encoding="utf-8-sig", errors="ignore") as f:
            existing = f.read().rstrip()
        if wrapper is None:
            content = existing + "\n\n" + entry
        elif existing.endswith("}") :
            content = existing[:-1].rstrip("\n") + "\n" + entry + "}\n"
        else:
            content = existing + "\n" + f"{wrapper} = {{\n{entry}}}\n"
    else:
        content = entry if wrapper is None else f"{wrapper} = {{\n{entry}}}\n"
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    created.append(path)

    loc_path = loc_surgery.set_key(mod_root, trait_id, display_name)
    created.append(loc_path)
    return created
