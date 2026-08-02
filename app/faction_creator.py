"""Factions: read the faction building blocks the game (and the mod) already
define, and write new ones into the open mod.

HOI4 splits factions across common/factions/:

  templates/   a faction itself - name, icon, manifest, starting goals, rules
  goals/       what a faction is working towards (short/medium/long term),
               plus manifests (`is_manifest = yes`), the faction's main goal
  rules/       joining/war/leader-change rules a template switches on
  icons/       the pool of GFX sprites offered when a faction is created

A template is mostly a composition of the other three, which is why the tab
built on this leans on pickers rather than free text: picking a manifest and
a handful of existing goals/rules is how vanilla itself defines the Axis.
"""

import os

from app import pds_scan as scan
from app import loc_surgery
from app.map_data import BASE_GAME

FACTION_DIR = os.path.join("common", "factions")
# the game reads these out of the per-kind subfolders, not the factions
# root - a file dropped straight into common/factions/ is silently ignored
TEMPLATE_FILE = os.path.join("templates", "zzz_custom_templates.txt")
GOAL_FILE = os.path.join("goals", "zzz_custom_goals.txt")

GOAL_CATEGORIES = ("short_term", "medium_term", "long_term")


def _scan_blocks(root, subfolder):
    """{block_id: (source, inner_text)} for every top-level named block in
    common/factions/<subfolder>/**.txt under `root`."""
    out = {}
    folder = os.path.join(root, FACTION_DIR, subfolder)
    if not os.path.isdir(folder):
        return out
    for dirpath, _, filenames in os.walk(folder):
        for name in sorted(filenames):
            if not name.endswith(".txt"):
                continue
            try:
                with open(os.path.join(dirpath, name), "r", encoding="utf-8-sig", errors="ignore") as f:
                    text = scan.strip_comments(f.read())
            except OSError:
                continue
            for block_id, inner in scan.iter_named_blocks(text):
                out[block_id] = inner
    return out


def _merged(mod_root, subfolder):
    """{block_id: (source, inner)} across base game then mod (mod wins)."""
    out = {}
    for root, source in ((BASE_GAME, "vanilla"), (mod_root, "mod")):
        if not root:
            continue
        for block_id, inner in _scan_blocks(root, subfolder).items():
            out[block_id] = (source, inner)
    return out


def list_templates(mod_root):
    """{template_id: source}."""
    return {k: v[0] for k, v in _merged(mod_root, "templates").items()}


def list_rules(mod_root):
    """{rule_id: (source, rule_type)} - type is the `type = ...` scalar that
    says which situation the rule applies to (joining_rules etc)."""
    out = {}
    for rule_id, (source, inner) in _merged(mod_root, "rules").items():
        out[rule_id] = (source, scan.scalar(inner, "type", ""))
    return out


def list_goals(mod_root):
    """{goal_id: (source, category)} where category is short_term/
    medium_term/long_term, or "manifest" for `is_manifest = yes` blocks."""
    out = {}
    for goal_id, (source, inner) in _merged(mod_root, "goals").items():
        if scan.scalar(inner, "is_manifest", "no") == "yes":
            category = "manifest"
        else:
            category = scan.scalar(inner, "category", "")
        out[goal_id] = (source, category)
    return out


def list_icons(mod_root):
    """Every GFX sprite listed in the faction icon pool files."""
    icons = []
    for root in (BASE_GAME, mod_root):
        if not root:
            continue
        folder = os.path.join(root, FACTION_DIR, "icons")
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
            for _, inner in scan.iter_named_blocks(text):
                block = scan.first_block(inner, "icons")
                if not block:
                    continue
                for token in block.split():
                    if token.startswith("GFX_") and token not in icons:
                        icons.append(token)
    return icons


def _append_block(mod_root, filename, entry):
    """Faction files are flat lists of top-level blocks, so appending is
    just that - no wrapper to merge into."""
    folder = os.path.join(mod_root, FACTION_DIR, os.path.dirname(filename) or "")
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(mod_root, FACTION_DIR, filename)
    if os.path.isfile(path):
        with open(path, "r", encoding="utf-8-sig", errors="ignore") as f:
            existing = f.read().rstrip()
        content = existing + "\n\n" + entry
    else:
        content = entry
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return path


def create_template(mod_root, *, template_id, display_name, icon="", manifest="",
                     goals=(), default_rules=(), can_leader_join_other_factions=True,
                     available_raw="", visible_raw="always = yes"):
    """Write a new faction template. `goals`/`default_rules` are lists of
    ids that already exist (or that the mod defines elsewhere). Returns the
    files written."""
    name_key = f"{template_id}_name"

    def indent_block(raw, depth=2):
        pad = "\t" * depth
        return "\n".join(pad + line.strip() for line in raw.strip().splitlines() if line.strip())

    parts = [f"{template_id} = {{", f"\tname = {name_key}"]
    if icon:
        parts.append(f"\ticon = {icon}")
    if manifest:
        parts.append(f"\tmanifest = {manifest}")
    parts.append(f"\tcan_leader_join_other_factions = "
                 f"{'yes' if can_leader_join_other_factions else 'no'}")
    if visible_raw.strip():
        parts.append("\tvisible = {\n" + indent_block(visible_raw) + "\n\t}")
    if available_raw.strip():
        parts.append("\tavailable = {\n" + indent_block(available_raw) + "\n\t}")
    if goals:
        parts.append("\tgoals = {\n" + "\n".join(f"\t\t{g}" for g in goals) + "\n\t}")
    if default_rules:
        parts.append("\tdefault_rules = {\n" + "\n".join(f"\t\t{r}" for r in default_rules) + "\n\t}")
    parts.append("}\n")

    created = [_append_block(mod_root, TEMPLATE_FILE, "\n".join(parts))]
    created.append(loc_surgery.set_key(mod_root, name_key, display_name))
    return created


def create_goal(mod_root, *, goal_id, display_name, description, category,
                 completed_raw="", complete_effect_raw="", ai_factor=100):
    """Write a new (non-manifest) faction goal. An empty `completed_raw`
    means the goal can never complete - that is the game's own behaviour,
    so it is passed through rather than silently substituted."""
    name_key = f"{goal_id}_name"
    desc_key = f"{goal_id}_desc"

    def indent_block(raw, depth=2):
        pad = "\t" * depth
        return "\n".join(pad + line.strip() for line in raw.strip().splitlines() if line.strip())

    parts = [
        f"{goal_id} = {{",
        f"\tname = {name_key}",
        f"\tdescription = {desc_key}",
        f"\tcategory = {category}",
        "\tcompleted = {\n" + (indent_block(completed_raw) if completed_raw.strip()
                                else "\t\t# empty = never completes") + "\n\t}",
    ]
    if complete_effect_raw.strip():
        parts.append("\tcomplete_effect = {\n" + indent_block(complete_effect_raw) + "\n\t}")
    parts.append("\tai_will_do = {\n\t\tfactor = " + str(ai_factor) + "\n\t}")
    parts.append("}\n")

    created = [_append_block(mod_root, GOAL_FILE, "\n".join(parts))]
    created.append(loc_surgery.set_key(mod_root, name_key, display_name))
    created.append(loc_surgery.set_key(mod_root, desc_key, description))
    return created
