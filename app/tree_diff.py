"""Compare the current focus trees against a snapshot's - what got added,
removed, or changed since that point in time. The visual sibling to the
What Changed? tab, which diffs raw file text; this diffs at the focus
level, so moving a focus 40 pixels shows up as "changed", not as a wall of
text lines that happened to shift.
"""

import os
import shutil
import tempfile
import zipfile

from app import mod_loader as ml

COMPARE_FIELDS = ("title", "icon", "x", "y", "cost")


def extract_snapshot(zip_path):
    """Unzip into a scratch temp dir for read-only comparison. Caller must
    clean it up (e.g. via cleanup())."""
    tmp = tempfile.mkdtemp(prefix="hoi4_snap_diff_")
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(tmp)
    return tmp


def cleanup(tmp_dir):
    shutil.rmtree(tmp_dir, ignore_errors=True)


def _load_focuses(root):
    out = {}
    for path in ml.find_focus_tree_files(root):
        for tree in ml.parse_focus_trees(path):
            for f in tree["focuses"]:
                out[f["id"]] = f
    return out


def _fields_differ(old, new):
    changed = []
    for key in COMPARE_FIELDS:
        if old.get(key) != new.get(key):
            changed.append(key)
    old_pre = sorted(old.get("prerequisite", []))
    new_pre = sorted(new.get("prerequisite", []))
    if old_pre != new_pre:
        changed.append("prerequisite")
    return changed


def compare(old_root, new_root):
    """{'added': [...], 'removed': [...], 'changed': {id: [fields]},
    'unchanged': [...], 'old': {id: focus}, 'new': {id: focus}}"""
    old = _load_focuses(old_root)
    new = _load_focuses(new_root)

    added = sorted(set(new) - set(old))
    removed = sorted(set(old) - set(new))
    changed = {}
    unchanged = []
    for fid in sorted(set(old) & set(new)):
        diff_fields = _fields_differ(old[fid], new[fid])
        if diff_fields:
            changed[fid] = diff_fields
        else:
            unchanged.append(fid)

    return {"added": added, "removed": removed, "changed": changed,
            "unchanged": unchanged, "old": old, "new": new}
