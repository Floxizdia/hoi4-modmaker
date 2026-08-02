"""Read-only loader for an existing (downloaded) HOI4 mod: finds focus tree
files, parses focus nodes out of them, resolves GFX icon names to actual
texture files, loads english localisation, and makes a best-effort guess at
a leader portrait per country tag.

This never writes to the source mod's files. New content added through the
mod browser is exported to a brand new file instead (see mod_browser.py).
"""

import os
import re
import glob

from app import pds_scan as scan


def list_workshop_mods(workshop_root):
    """Scan a Steam Workshop content folder (.../workshop/content/394360)
    and read each subfolder's descriptor.mod to get the real mod name, so
    the UI can show 'Kaiserreich' instead of a numeric id like 3365515312."""
    out = []
    if not workshop_root or not os.path.isdir(workshop_root):
        return out
    for entry in sorted(os.listdir(workshop_root)):
        mod_path = os.path.join(workshop_root, entry)
        descriptor = os.path.join(mod_path, "descriptor.mod")
        if not os.path.isfile(descriptor):
            continue
        name = entry
        supported = ""
        try:
            with open(descriptor, "r", encoding="utf-8-sig", errors="ignore") as f:
                text = f.read()
            m = re.search(r'\bname\s*=\s*"([^"]+)"', text)
            if m:
                name = m.group(1)
            m = re.search(r'\bsupported_version\s*=\s*"([^"]+)"', text)
            if m:
                supported = m.group(1)
        except OSError:
            pass
        out.append({"workshop_id": entry, "name": name, "path": mod_path,
                    "supported_version": supported})
    return out


def find_focus_tree_files(mod_root):
    """Return paths under common/national_focus that actually define at
    least one focus_tree block."""
    folder = os.path.join(mod_root, "common", "national_focus")
    if not os.path.isdir(folder):
        return []
    out = []
    for path in glob.glob(os.path.join(folder, "*.txt")):
        try:
            with open(path, "r", encoding="utf-8-sig", errors="ignore") as f:
                text = f.read()
        except OSError:
            continue
        if re.search(r"\bfocus_tree\s*=\s*\{", text):
            out.append(path)
    return out


def _extract_focus(inner):
    # In HOI4, options inside ONE prerequisite block are OR'd together, and
    # separate prerequisite blocks are AND'd. Keep the groups so the
    # progression simulator can evaluate them correctly, plus a flat list
    # for drawing connector lines.
    prereq_groups = []
    prereq = []
    for _, _, block in scan.iter_blocks(inner, "prerequisite"):
        options = scan.all_scalars(block, "focus")
        if options:
            prereq_groups.append(options)
            prereq.extend(options)

    mutex = []
    for _, _, block in scan.iter_blocks(inner, "mutually_exclusive"):
        mutex.extend(scan.all_scalars(block, "focus"))

    def num(key, default):
        raw = scan.scalar(inner, key, str(default))
        try:
            return float(raw) if "." in raw else int(raw)
        except (TypeError, ValueError):
            return default

    return {
        "id": scan.scalar(inner, "id", ""),
        "icon": scan.scalar(inner, "icon", ""),
        "x": num("x", 0),
        "y": num("y", 0),
        "cost": num("cost", 10),
        "relative_position_id": scan.scalar(inner, "relative_position_id"),
        "prerequisite": prereq,
        "prerequisite_groups": prereq_groups,
        "mutually_exclusive": mutex,
        "available_raw": scan.first_block(inner, "available") or "",
        "bypass_raw": scan.first_block(inner, "bypass") or "",
        "completion_reward_raw": scan.first_block(inner, "completion_reward") or "",
        "select_effect_raw": scan.first_block(inner, "select_effect") or "",
        "ai_will_do_raw": scan.first_block(inner, "ai_will_do") or "",
    }


def parse_focus_trees(path):
    """A single file can contain more than one focus_tree block (shared
    branch files sometimes do). Returns a list of tree dicts."""
    with open(path, "r", encoding="utf-8-sig", errors="ignore") as f:
        text = scan.strip_comments(f.read())

    trees = []
    for _, _, inner in scan.iter_blocks(text, "focus_tree"):
        tags = []
        for _, _, country_block in scan.iter_blocks(inner, "country"):
            for _, _, modifier_block in scan.iter_blocks(country_block, "modifier"):
                tag = scan.scalar(modifier_block, "tag")
                if tag:
                    tags.append(tag.upper())

        focuses = [_extract_focus(f_inner) for _, _, f_inner in scan.iter_blocks(inner, "focus")]
        focuses = [f for f in focuses if f["id"]]

        trees.append({
            "id": scan.scalar(inner, "id", os.path.basename(path)),
            "default": scan.scalar(inner, "default", "yes"),
            "country_tags": tags,
            "source_file": path,
            "focuses": focuses,
        })
    return trees


_GFX_PAIR_RE = re.compile(
    r'name\s*=\s*"([^"]+)"[^{}]*?texturefile\s*=\s*"([^"]+)"', re.IGNORECASE
)


def build_gfx_index(mod_roots):
    """Scan *.gfx files under each root's interface/ and gfx/ folders and
    return {sprite_name: absolute_texture_path}. Later roots override
    earlier ones, so pass the base game root first and the mod root last."""
    index = {}
    for root in mod_roots:
        if not root or not os.path.isdir(root):
            continue
        search_dirs = [os.path.join(root, "interface"), os.path.join(root, "gfx")]
        for search_dir in search_dirs:
            if not os.path.isdir(search_dir):
                continue
            for gfx_path in glob.glob(os.path.join(search_dir, "**", "*.gfx"), recursive=True):
                try:
                    with open(gfx_path, "r", encoding="utf-8-sig", errors="ignore") as f:
                        text = f.read()
                except OSError:
                    continue
                for name, texture_rel in _GFX_PAIR_RE.findall(text):
                    index[name] = os.path.normpath(os.path.join(root, texture_rel))
    return index


_LOC_LINE_RE = re.compile(r'^\s*([A-Za-z0-9_.\-]+)\s*:\s*\d*\s*"(.*)"\s*$')


def load_localisation(mod_root, language="english"):
    """Returns {key: text} from every localisation/<language>/**/*.yml."""
    out = {}
    loc_dir = os.path.join(mod_root, "localisation", language)
    if not os.path.isdir(loc_dir):
        return out
    for path in glob.glob(os.path.join(loc_dir, "**", "*.yml"), recursive=True):
        try:
            with open(path, "r", encoding="utf-8-sig", errors="ignore") as f:
                for line in f:
                    m = _LOC_LINE_RE.match(line)
                    if m:
                        key, text = m.groups()
                        out[key] = text.replace('\\"', '"')
        except OSError:
            continue
    return out


_LARGE_PORTRAIT_RE = re.compile(r'\blarge\s*=\s*(?:"([^"]+)"|(\S+))')


def load_leader_portraits(mod_root):
    """Best-effort: one representative portrait per country tag, taken from
    the first character listed in common/characters/<TAG>.txt (or
    common/characters/<TAG>/*.txt). This is NOT necessarily the currently
    ruling leader — determining that requires simulating game start date and
    election/succession events, which is out of scope here."""
    out = {}
    char_dir = os.path.join(mod_root, "common", "characters")
    if not os.path.isdir(char_dir):
        return out
    for path in glob.glob(os.path.join(char_dir, "**", "*.txt"), recursive=True):
        tag = os.path.splitext(os.path.basename(path))[0].upper()
        if tag in out:
            continue
        try:
            with open(path, "r", encoding="utf-8-sig", errors="ignore") as f:
                text = f.read()
        except OSError:
            continue
        m = _LARGE_PORTRAIT_RE.search(text)
        if m:
            out[tag] = m.group(1) or m.group(2)
    return out


_EVENT_TYPES = ("country_event", "news_event", "state_event", "unit_leader_event", "operative_leader_event")


def find_event_files(mod_root):
    folder = os.path.join(mod_root, "events")
    if not os.path.isdir(folder):
        return []
    out = []
    for path in glob.glob(os.path.join(folder, "**", "*.txt"), recursive=True):
        try:
            with open(path, "r", encoding="utf-8-sig", errors="ignore") as f:
                head = f.read()
        except OSError:
            continue
        if re.search(r"\badd_namespace\s*=", head):
            out.append(path)
    return out


def parse_events(path):
    """Pull events out of an events file. Option effects and triggers are
    kept as raw text - they can contain arbitrary scripting we neither need
    to understand nor want to mangle on the way back out."""
    with open(path, "r", encoding="utf-8-sig", errors="ignore") as f:
        text = scan.strip_comments(f.read())

    namespaces = scan.all_scalars(text, "add_namespace")
    events = []
    seen = set()

    # Only top-level blocks define events. The same keywords appear inside
    # effects to *fire* an event (`country_event = { id = x days = 3 }`),
    # and treating those as definitions produces phantom duplicates.
    for block_name, inner in scan.iter_named_blocks(text):
        if block_name not in _EVENT_TYPES:
            continue
        event_type = block_name
        full_id = scan.scalar(inner, "id", "")
        if not full_id or full_id in seen:
            continue
        seen.add(full_id)
        namespace, _, number = full_id.rpartition(".")

        options = []
        for _, _, opt in scan.iter_blocks(inner, "option"):
            ai_block = scan.first_block(opt, "ai_chance") or ""
            options.append({
                "name_key": scan.scalar(opt, "name", ""),
                "ai_factor": scan.scalar(ai_block, "factor", ""),
                "effect": _strip_known_keys(opt, ("name",), ("ai_chance",)),
            })

        events.append({
            "namespace": namespace,
            "number": int(number) if number.isdigit() else number,
            "type": event_type,
            "title_key": _loc_key(inner, "title"),
            "desc_key": _loc_key(inner, "desc"),
            "picture": scan.scalar(inner, "picture", ""),
            "is_triggered_only": scan.scalar(inner, "is_triggered_only", "no") == "yes",
            "trigger": scan.first_block(inner, "trigger") or "",
            "immediate": scan.first_block(inner, "immediate") or "",
            "options": options,
            "source_file": path,
        })

    return namespaces, events


def _loc_key(inner, key):
    """`title`/`desc` are usually `key = some.loc.key`, but may instead be a
    block of conditional variants: `desc = { text = X trigger = {...} }`.
    Take the scalar when there is one, otherwise the first variant's text."""
    direct = scan.scalar(inner, key)
    if direct:
        return direct
    block = scan.first_block(inner, key)
    if block:
        return scan.scalar(block, "text", "")
    return ""


def _strip_known_keys(text, scalar_keys, block_keys):
    """Return `text` minus the given scalar assignments and blocks, so what
    remains is the raw effect body."""
    out = text
    for key in block_keys:
        for start, end, _ in reversed(list(scan.iter_blocks(out, key))):
            out = out[:start] + out[end:]
    for key in scalar_keys:
        out = re.sub(r"\b" + re.escape(key) + r"\s*=\s*(?!\{)(\"[^\"]*\"|\S+)", "", out)
    return "\n".join(line.rstrip() for line in out.splitlines() if line.strip()).strip()


def find_decision_files(mod_root):
    folder = os.path.join(mod_root, "common", "decisions")
    if not os.path.isdir(folder):
        return []
    return sorted(glob.glob(os.path.join(folder, "*.txt")))


def parse_decisions(path):
    """Return [{category, decisions:[...]}] for one decisions file."""
    with open(path, "r", encoding="utf-8-sig", errors="ignore") as f:
        text = scan.strip_comments(f.read())

    categories = []
    for category, inner in scan.iter_named_blocks(text):
        decisions_inner = scan.first_block(inner, "decisions")
        # some files list decisions directly under the category
        body = decisions_inner if decisions_inner is not None else inner

        entries = []
        for did, d_inner in scan.iter_named_blocks(body):
            if did in ("decisions",):
                continue
            ai_block = scan.first_block(d_inner, "ai_will_do") or ""
            entries.append({
                "id": did,
                "icon": scan.scalar(d_inner, "icon", ""),
                "cost": scan.scalar(d_inner, "cost", ""),
                "days_re_enable": scan.scalar(d_inner, "days_re_enable", ""),
                "allowed": scan.first_block(d_inner, "allowed") or "",
                "visible": scan.first_block(d_inner, "visible") or "",
                "available": scan.first_block(d_inner, "available") or "",
                "effect": scan.first_block(d_inner, "complete_effect")
                          or scan.first_block(d_inner, "effect")
                          or scan.first_block(d_inner, "remove_effect") or "",
                "ai_factor": scan.scalar(ai_block, "factor", ""),
                "ai_will_do_raw": ai_block,
            })

        if entries:
            categories.append({"category": category, "decisions": entries, "source_file": path})

    return categories


def find_idea_files(mod_root):
    folder = os.path.join(mod_root, "common", "ideas")
    if not os.path.isdir(folder):
        return []
    return sorted(glob.glob(os.path.join(folder, "*.txt")))


def parse_ideas(path):
    """Return [{category, ideas:[...]}] for one common/ideas file.

    `category` is the slot the idea sits in - "country" is where national
    spirits and generic country ideas both live; the other slots
    (political_advisor, army_spirit, industrial_concern, ...) are the
    classic advisor/specialist categories."""
    with open(path, "r", encoding="utf-8-sig", errors="ignore") as f:
        text = scan.strip_comments(f.read())

    ideas_inner = scan.first_block(text, "ideas")
    if ideas_inner is None:
        return []

    categories = []
    for category, cat_inner in scan.iter_named_blocks(ideas_inner):
        entries = []
        for iid, inner in scan.iter_named_blocks(cat_inner):
            picture = scan.scalar(inner, "picture", "")
            entries.append({
                "id": iid,
                "category": category,
                "picture": picture,
                "removal_cost": scan.scalar(inner, "removal_cost", ""),
                "cost": scan.scalar(inner, "cost", ""),
                "allowed": scan.first_block(inner, "allowed") or "",
                "allowed_civil_war": scan.first_block(inner, "allowed_civil_war") or "",
                "available": scan.first_block(inner, "available") or "",
                "modifier": scan.first_block(inner, "modifier") or "",
                "research_modifier": scan.first_block(inner, "research_modifier") or "",
                "equipment_bonus": scan.first_block(inner, "equipment_bonus") or "",
                "targeted_modifier": scan.first_block(inner, "targeted_modifier") or "",
                "ai_will_do": scan.first_block(inner, "ai_will_do") or "",
            })
        if entries:
            categories.append({"category": category, "ideas": entries, "source_file": path})

    return categories


_ROLE_KEYS = (
    "country_leader",
    "corps_commander",
    "field_marshal",
    "navy_leader",
    "advisor",
    "scientist",
)


def load_country_characters(mod_root):
    """Parse common/characters/**.txt into {TAG: [character dicts]}.

    Each dict carries every portrait variant we can find so the gallery can
    show an avatar, plus which roles the character can hold. The country tag
    is taken from the character id prefix when it looks like a tag (the HOI4
    convention, e.g. TUR_mustafa_kemal), otherwise from the filename."""
    out = {}
    char_dir = os.path.join(mod_root, "common", "characters")
    if not os.path.isdir(char_dir):
        return out

    for path in glob.glob(os.path.join(char_dir, "**", "*.txt"), recursive=True):
        file_tag = os.path.splitext(os.path.basename(path))[0].upper()
        try:
            with open(path, "r", encoding="utf-8-sig", errors="ignore") as f:
                text = scan.strip_comments(f.read())
        except OSError:
            continue

        chars_inner = scan.first_block(text, "characters")
        if not chars_inner:
            continue

        for cid, inner in scan.iter_named_blocks(chars_inner):
            prefix = cid.split("_")[0]
            tag = prefix.upper() if len(prefix) == 3 and prefix.isalpha() else file_tag

            portraits_inner = scan.first_block(inner, "portraits") or ""
            portrait_values = scan.all_scalars(portraits_inner, "large")
            portrait_values += scan.all_scalars(portraits_inner, "small")

            roles = [r for r in _ROLE_KEYS if re.search(r"\b" + r + r"\s*=\s*\{", inner)]
            leader_block = scan.first_block(inner, "country_leader") or ""

            out.setdefault(tag, []).append({
                "id": cid,
                "name_key": scan.scalar(inner, "name", cid),
                "portraits": portrait_values,
                "roles": roles,
                "ideology": scan.scalar(leader_block, "ideology", ""),
                "source_file": path,
            })

    return out


def resolve_texture(value, mod_root, gfx_index):
    """`value` is either a GFX_ sprite name or a literal relative path."""
    if not value:
        return None
    if value in gfx_index:
        return gfx_index[value]
    if value.upper().startswith("GFX_") and value in gfx_index:
        return gfx_index[value]
    candidate = os.path.normpath(os.path.join(mod_root, value))
    if os.path.isfile(candidate):
        return candidate
    return None
