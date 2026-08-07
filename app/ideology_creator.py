"""Ideology creator: define a brand-new ideology group (with its own
sub-ideologies, the ones that show up as ruling parties in-game) and write
everything HOI4 needs to recognise it.

  common/ideologies/zzz_<id>.txt              the group + its sub-ideology types
  gfx/interface/ideologies/<id>.dds (or .png)  the icon shown in the politics UI
  interface/zz_custom_ideologies.gfx           GFX_ideology_<id> sprite registration
  localisation/english/zzz_<id>_ideology_l_english.yml   group + sub-ideology names

This covers what a group needs to exist and be selectable as a country's
ruling ideology (also usable from the Country tab's ideology dropdown once
the mod is reloaded). Advanced things real total-conversion mods add on top
- faction unlock conditions, AI strategy plans, ideology-specific ideas -
aren't generated here; the wiki page for `common/ideologies` covers those
once this scaffold is in place.
"""

import os

from PIL import Image

from app import pds_scan as scan

VANILLA_GROUPS = {"neutrality", "democratic", "fascism", "communism"}


def existing_group_ids(mod_root):
    """Custom group ids already defined in this mod's common/ideologies/."""
    found = set()
    folder = os.path.join(mod_root, "common", "ideologies")
    if not os.path.isdir(folder):
        return found
    # sorted: both of these take the first file that matches, and
    # os.listdir has no defined order - the answer would differ
    # between Windows and Linux for the same mod
    for fname in sorted(os.listdir(folder)):
        if not fname.endswith(".txt"):
            continue
        try:
            with open(os.path.join(folder, fname), "r", encoding="utf-8-sig", errors="ignore") as f:
                text = scan.strip_comments(f.read())
        except OSError:
            continue
        block = scan.first_block(text, "ideologies")
        if block is None:
            continue
        for group_id, _ in scan.iter_named_blocks(block):
            found.add(group_id)
    return found


def first_sub_ideology(mod_root, group_id):
    """The first sub-ideology id defined for a custom group, or None."""
    folder = os.path.join(mod_root, "common", "ideologies")
    if not os.path.isdir(folder):
        return None
    # sorted: both of these take the first file that matches, and
    # os.listdir has no defined order - the answer would differ
    # between Windows and Linux for the same mod
    for fname in sorted(os.listdir(folder)):
        if not fname.endswith(".txt"):
            continue
        try:
            with open(os.path.join(folder, fname), "r", encoding="utf-8-sig", errors="ignore") as f:
                text = scan.strip_comments(f.read())
        except OSError:
            continue
        outer = scan.first_block(text, "ideologies")
        if outer is None:
            continue
        group_block = scan.first_block(outer, group_id)
        if group_block is None:
            continue
        types_block = scan.first_block(group_block, "types")
        if types_block is None:
            continue
        for sub_id, _ in scan.iter_named_blocks(types_block):
            return sub_id
    return None


def create_group(mod_root, *, group_id, display_name, color, can_be_boosted,
                  sub_ideologies, icon_path=None):
    """`sub_ideologies` is [(id, display_name), ...], at least one entry.
    Returns the list of files written."""
    created = []

    types_block = "".join(f"\t\t\t{sid} = {{\n\t\t\t}}\n" for sid, _ in sub_ideologies)
    r, g, b = color
    script = (
        "ideologies = {\n"
        f"\t{group_id} = {{\n"
        "\t\ttypes = {\n"
        f"{types_block}"
        "\t\t}\n\n"
        f"\t\tcolor = {{ {r} {g} {b} }}\n\n"
        f"\t\tcan_be_boosted = {'yes' if can_be_boosted else 'no'}\n"
        "\t}\n"
        "}\n"
    )
    ideo_dir = os.path.join(mod_root, "common", "ideologies")
    os.makedirs(ideo_dir, exist_ok=True)
    script_path = os.path.join(ideo_dir, f"zzz_{group_id}.txt")
    with open(script_path, "w", encoding="utf-8") as f:
        f.write(script)
    created.append(script_path)

    if icon_path:
        icon_dir = os.path.join(mod_root, "gfx", "interface", "ideologies")
        os.makedirs(icon_dir, exist_ok=True)
        im = Image.open(icon_path).convert("RGBA").resize((48, 48), Image.LANCZOS)
        dds_path = os.path.join(icon_dir, f"{group_id}.dds")
        try:
            im.save(dds_path, "DDS")
            texture_path = dds_path
        except Exception:
            texture_path = os.path.join(icon_dir, f"{group_id}.png")
            im.save(texture_path, "PNG")
        created.append(texture_path)

        rel = os.path.relpath(texture_path, mod_root).replace("\\", "/")
        gfx_path = _register_ideology_sprite(mod_root, group_id, rel)
        created.append(gfx_path)

    loc_dir = os.path.join(mod_root, "localisation", "english")
    os.makedirs(loc_dir, exist_ok=True)
    loc_path = os.path.join(loc_dir, f"zzz_{group_id}_ideology_l_english.yml")
    lines = ["l_english:",
             f' {group_id}:0 "{display_name}"',
             f' {group_id}_desc:0 "{display_name} is a custom ideology added by this mod."']
    for sid, sname in sub_ideologies:
        lines.append(f' {sid}:0 "{sname}"')
    with open(loc_path, "w", encoding="utf-8-sig") as f:
        f.write("\n".join(lines) + "\n")
    created.append(loc_path)

    return created


def _register_ideology_sprite(mod_root, group_id, texture_rel):
    gfx_dir = os.path.join(mod_root, "interface")
    os.makedirs(gfx_dir, exist_ok=True)
    gfx_path = os.path.join(gfx_dir, "zz_custom_ideologies.gfx")
    sprite = f"GFX_ideology_{group_id}"

    entry = f'\tSpriteType = {{\n\t\tname = "{sprite}"\n\t\ttexturefile = "{texture_rel}"\n\t}}\n'
    if os.path.isfile(gfx_path):
        with open(gfx_path, "r", encoding="utf-8-sig", errors="ignore") as f:
            existing = f.read().rstrip()
        if sprite not in existing:
            if existing.endswith("}"):
                existing = existing[:-1].rstrip("\n")
            content = existing + "\n" + entry + "}\n"
        else:
            content = existing + "\n"
    else:
        content = "spriteTypes = {\n" + entry + "}\n"

    with open(gfx_path, "w", encoding="utf-8") as f:
        f.write(content)
    return gfx_path
