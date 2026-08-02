"""Decision categories: the tabs/folders decisions get grouped under in the
decisions panel. common/decisions/*.txt decisions reference a category by
name; if you want your own tab instead of dropping into an existing one
(political_actions, war_production, etc.) you need one of these first.
Written to common/decisions/categories/.
"""

import os

from app import pds_scan as scan
from app import loc_surgery
from app.map_data import BASE_GAME

CATEGORY_DIR = os.path.join("common", "decisions", "categories")
FILENAME = "zzz_custom_decision_categories.txt"


def list_categories(mod_root):
    """{category_id: source} across base game + mod. Every top-level block
    in these files is a category, no wrapper key."""
    out = {}
    for root, source in ((BASE_GAME, "vanilla"), (mod_root, "mod")):
        folder = os.path.join(root, CATEGORY_DIR)
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
            for cat_id, _ in scan.iter_named_blocks(text):
                out[cat_id] = source
    return out


def create_category(mod_root, *, category_id, icon, display_name, priority=None,
                     visible_raw="", allowed_raw=""):
    def indent(raw, depth=2):
        pad = "\t" * depth
        return "\n".join(pad + line.strip() for line in raw.strip().splitlines() if line.strip())

    lines = [f"{category_id} = {{"]
    if icon:
        lines.append(f"\ticon = {icon}")
    if priority is not None and priority != "":
        lines.append(f"\tpriority = {priority}")
    lines.append("\tvisible = {")
    if visible_raw.strip():
        lines.append(indent(visible_raw))
    lines.append("\t}")
    if allowed_raw.strip():
        lines.append("\tallowed = {")
        lines.append(indent(allowed_raw))
        lines.append("\t}")
    lines.append("}\n")
    entry = "\n".join(lines)

    folder = os.path.join(mod_root, CATEGORY_DIR)
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, FILENAME)
    if os.path.isfile(path):
        with open(path, "r", encoding="utf-8-sig", errors="ignore") as f:
            existing = f.read().rstrip()
        content = existing + "\n\n" + entry
    else:
        content = entry

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

    if display_name:
        loc_surgery.set_key(mod_root, category_id, display_name)

    return path
