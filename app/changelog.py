"""Turn "what changed since a snapshot" into readable release notes -
the paragraph a modder actually has to write by hand for every Workshop
update, built from the same comparison tree_diff.py already does for
focuses, extended to events/decisions/ideas.
"""

from app import mod_loader as ml
from app import tree_diff


def _load_events(root):
    out = {}
    for path in ml.find_event_files(root):
        try:
            _, events = ml.parse_events(path)
        except OSError:
            continue
        for e in events:
            out[f"{e['namespace']}.{e['number']}"] = e
    return out


def _load_decisions(root):
    out = {}
    for path in ml.find_decision_files(root):
        try:
            categories = ml.parse_decisions(path)
        except OSError:
            continue
        for cat in categories:
            for d in cat["decisions"]:
                out[d["id"]] = d
    return out


def _load_ideas(root):
    out = {}
    for path in ml.find_idea_files(root):
        try:
            categories = ml.parse_ideas(path)
        except OSError:
            continue
        for cat in categories:
            for idea in cat["ideas"]:
                out[idea["id"]] = idea
    return out


def _bucket(old, new):
    added = sorted(set(new) - set(old))
    removed = sorted(set(old) - set(new))
    changed = sorted(k for k in set(old) & set(new) if old[k] != new[k])
    return added, removed, changed


def compare(old_root, new_root):
    """{"focus": (added, removed, changed), "event": ..., "decision": ..., "idea": ...}"""
    old_focus = tree_diff._load_focuses(old_root)
    new_focus = tree_diff._load_focuses(new_root)
    return {
        "focus": _bucket(old_focus, new_focus),
        "event": _bucket(_load_events(old_root), _load_events(new_root)),
        "decision": _bucket(_load_decisions(old_root), _load_decisions(new_root)),
        "idea": _bucket(_load_ideas(old_root), _load_ideas(new_root)),
    }


LABELS = {"focus": "Focuses", "event": "Events", "decision": "Decisions", "idea": "Ideas / Spirits"}


def format_changelog(result, title="Changelog"):
    lines = [title, "=" * len(title), ""]
    any_changes = False
    for key, label in LABELS.items():
        added, removed, changed = result[key]
        if not (added or removed or changed):
            continue
        any_changes = True
        lines.append(f"{label}:")
        if added:
            lines.append(f"  Added ({len(added)}): " + ", ".join(added))
        if removed:
            lines.append(f"  Removed ({len(removed)}): " + ", ".join(removed))
        if changed:
            lines.append(f"  Changed ({len(changed)}): " + ", ".join(changed))
        lines.append("")
    if not any_changes:
        lines.append("No differences found between the two versions.")
    return "\n".join(lines).rstrip() + "\n"


def build(mod_root, snapshot_zip_path, title="Changelog"):
    """Compare `mod_root`'s current state against an older snapshot zip.
    Returns the formatted changelog text."""
    tmp = tree_diff.extract_snapshot(snapshot_zip_path)
    try:
        result = compare(tmp, mod_root)
    finally:
        tree_diff.cleanup(tmp)
    return format_changelog(result, title)
