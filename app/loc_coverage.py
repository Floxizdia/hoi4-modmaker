"""Which localisation keys exist in English but are missing everywhere
else - the gap that shows up in game as a raw key like `TUR_focus_x` on
the screen of anyone not playing in English.

English is the always-written language in this tool (every generator writes
english first), so it's treated as the source of truth: a key present in
English but absent from a language's own .yml files is "missing" for that
language. A key that's genuinely English-only content (author's choice) has
no way to be distinguished from an oversight, so this only ever offers to
fill gaps, never to delete extra keys - the worst it can do is give a
non-English player readable placeholder text instead of a raw key.
"""

import os
import re

from app.localisation import HOI4_LANGUAGES

_KEY_RE = re.compile(r'^\s*([\w.]+)\s*:\s*\d*\s*"((?:[^"\\]|\\.)*)"', re.MULTILINE)

FILL_SUFFIX = "_coverage_fill"


def _lang_dir(mod_root, lang):
    return os.path.join(mod_root, "localisation", lang)


def scan_language(mod_root, lang):
    """{key: text} merged over every .yml under localisation/<lang>."""
    out = {}
    folder = _lang_dir(mod_root, lang)
    if not os.path.isdir(folder):
        return out
    for name in os.listdir(folder):
        if not name.lower().endswith(".yml"):
            continue
        path = os.path.join(folder, name)
        try:
            with open(path, "r", encoding="utf-8-sig", errors="ignore") as f:
                text = f.read()
        except OSError:
            continue
        for key, value in _KEY_RE.findall(text):
            out[key] = value.replace('\\"', '"')
    return out


def coverage_report(mod_root):
    """{lang: {'missing': {key: english_text}, 'total': n}} for every
    language except English itself."""
    english = scan_language(mod_root, "english")
    report = {}
    for lang in HOI4_LANGUAGES:
        if lang == "english":
            continue
        theirs = scan_language(mod_root, lang)
        missing = {k: v for k, v in english.items() if k not in theirs}
        report[lang] = {"missing": missing, "total": len(english)}
    return english, report


def write_fill(mod_root, mod_name, lang, missing):
    """A separate '<mod>_coverage_fill_l_<lang>.yml' carrying the English
    text for every key that language is missing - kept apart from any real
    translation file so a later human translation pass isn't clobbered."""
    safe = re.sub(r"[^a-z0-9_]+", "_", mod_name.lower()).strip("_") or "my_mod"
    out_dir = os.path.join(mod_root, "localisation", lang)
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"{safe}{FILL_SUFFIX}_l_{lang}.yml")

    lines = [f"l_{lang}:"]
    for key, text in sorted(missing.items()):
        safe_text = text.replace('"', '\\"')
        lines.append(f' {key}:0 "{safe_text}"')
    with open(out_path, "w", encoding="utf-8-sig") as f:
        f.write("\n".join(lines) + "\n")
    return out_path


# ---- keys the mod's own content references but nobody ever wrote ----
#
# coverage_report() above answers "english exists, other languages don't".
# This answers the more severe question: the content references a key that
# no language defines at all, so it shows as a raw id for *everyone*,
# english players included.

ENGLISH_FILL_SUFFIX = "_missing_keys"


def _prettify(key):
    """Turn a script id into readable placeholder text. 'GER_four_year_plan'
    -> 'Four Year Plan'; the tag prefix is dropped because it reads as noise
    in a title, and suffixes like '.t'/'.d' are structural, not words."""
    base = key.split(".")[0]
    parts = base.split("_")
    if parts and len(parts[0]) == 3 and parts[0].isupper():
        parts = parts[1:]
    words = [w for w in parts if w]
    return " ".join(w.capitalize() for w in words) or key


def referenced_keys(mod_root):
    """{key: what_references_it} for every loc key the mod's focuses,
    events, decisions and ideas point at."""
    from app import mod_loader as ml

    refs = {}

    def note(key, owner):
        if key and not key.startswith("["):
            refs.setdefault(key, owner)

    for path in ml.find_focus_tree_files(mod_root):
        for tree in ml.parse_focus_trees(path):
            for f in tree["focuses"]:
                note(f["id"], f"focus '{f['id']}'")
                note(f["id"] + "_desc", f"focus '{f['id']}' description")

    for path in ml.find_event_files(mod_root):
        try:
            _, events = ml.parse_events(path)
        except OSError:
            continue
        for e in events:
            eid = f"{e['namespace']}.{e['number']}"
            note(e.get("title_key"), f"event '{eid}' title")
            note(e.get("desc_key"), f"event '{eid}' description")
            for o in e["options"]:
                note(o.get("name_key"), f"event '{eid}' option")

    for path in ml.find_decision_files(mod_root):
        try:
            categories = ml.parse_decisions(path)
        except OSError:
            continue
        for cat in categories:
            for d in cat["decisions"]:
                note(d["id"], f"decision '{d['id']}'")

    for path in ml.find_idea_files(mod_root):
        try:
            categories = ml.parse_ideas(path)
        except OSError:
            continue
        for cat in categories:
            for idea in cat["ideas"]:
                note(idea["id"], f"idea '{idea['id']}'")

    return refs


def missing_english_keys(mod_root):
    """{key: (owner, suggested_text)} for referenced keys no .yml defines.

    Descriptions are deliberately left blank rather than filled with a
    prettified id - an empty description looks intentional in game, while
    'Four Year Plan' repeated as its own description reads as a bug."""
    english = scan_language(mod_root, "english")
    out = {}
    for key, owner in referenced_keys(mod_root).items():
        if key in english:
            continue
        is_desc = key.endswith(".d") or key.endswith("_desc")
        out[key] = (owner, "" if is_desc else _prettify(key))
    return out


def write_english_fill(mod_root, mod_name, missing):
    """Write placeholders into their own file so a later real pass over the
    mod's normal loc files can't be clobbered by this."""
    safe = re.sub(r"[^a-z0-9_]+", "_", mod_name.lower()).strip("_") or "my_mod"
    out_dir = os.path.join(mod_root, "localisation", "english")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"{safe}{ENGLISH_FILL_SUFFIX}_l_english.yml")

    lines = ["l_english:"]
    for key, (_owner, text) in sorted(missing.items()):
        safe_text = text.replace('"', '\\"')
        lines.append(f' {key}:0 "{safe_text}"')
    with open(out_path, "w", encoding="utf-8-sig") as f:
        f.write("\n".join(lines) + "\n")
    return out_path
