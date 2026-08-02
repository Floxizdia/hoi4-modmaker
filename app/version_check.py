"""What a HOI4 patch broke: mod content that points at a vanilla id which
no longer exists in the installed game.

This is the single most common way a working mod silently breaks. Paradox
renames or removes ideas, technologies and focus ids between versions; a
mod referencing the old name keeps loading, but the effect that mentions it
just does nothing, or the focus that requires it can never unlock - with no
error message anywhere, because from the game's point of view the mod asked
for something that isn't there and it moved on.

Deliberately limited to three reference kinds with an unambiguous vanilla
namespace (ideas, technologies, focus prerequisites). Effects and triggers
name hundreds of engine tokens that aren't ids at all, and guessing at
those would produce noise instead of findings.
"""

import os
import re

from app import mod_loader as ml
from app import pds_scan as scan
from app import mod_files
from app.map_data import BASE_GAME


def _vanilla_idea_ids():
    out = set()
    for path in ml.find_idea_files(BASE_GAME):
        try:
            for cat in ml.parse_ideas(path):
                for idea in cat["ideas"]:
                    out.add(idea["id"])
        except OSError:
            continue
    return out


def _vanilla_tech_ids():
    out = set()
    folder = os.path.join(BASE_GAME, "common", "technologies")
    if not os.path.isdir(folder):
        return out
    for name in sorted(os.listdir(folder)):
        if not name.endswith(".txt"):
            continue
        try:
            with open(os.path.join(folder, name), "r", encoding="utf-8-sig", errors="ignore") as f:
                text = scan.strip_comments(f.read())
        except OSError:
            continue
        wrapper = scan.first_block(text, "technologies")
        if wrapper is None:
            continue
        for tech_id, _inner in scan.iter_named_blocks(wrapper):
            out.add(tech_id)
    return out


def _vanilla_focus_ids():
    out = set()
    for path in ml.find_focus_tree_files(BASE_GAME):
        try:
            for tree in ml.parse_focus_trees(path):
                for f in tree["focuses"]:
                    out.add(f["id"])
        except OSError:
            continue
    return out


_ADD_IDEA_RE = re.compile(r"\badd_idea(?:s)?\s*=\s*\{([^{}]*)\}")
_ADD_IDEA_SINGLE_RE = re.compile(r"\badd_idea(?:s)?\s*=\s*([A-Za-z0-9_]+)")
_ADD_TECH_RE = re.compile(r"\bset_technology\s*=\s*\{([^{}]*)\}")
_TECH_LINE_RE = re.compile(r"([A-Za-z0-9_]+)\s*=\s*1\b")


def check(mod_root, progress=None):
    """[{severity, kind, id, where, message}] - references to vanilla ids
    the installed game no longer defines."""
    if progress:
        progress("Reading the installed game's ideas...")
    vanilla_ideas = _vanilla_idea_ids()
    if progress:
        progress("Reading the installed game's technologies...")
    vanilla_techs = _vanilla_tech_ids()
    if progress:
        progress("Reading the installed game's focus trees...")
    vanilla_focuses = _vanilla_focus_ids()

    # anything the mod itself defines is fine no matter what vanilla does
    mod_ideas = set()
    for path in ml.find_idea_files(mod_root):
        try:
            for cat in ml.parse_ideas(path):
                for idea in cat["ideas"]:
                    mod_ideas.add(idea["id"])
        except OSError:
            continue
    mod_focuses = set()
    for path in ml.find_focus_tree_files(mod_root):
        try:
            for tree in ml.parse_focus_trees(path):
                for f in tree["focuses"]:
                    mod_focuses.add(f["id"])
        except OSError:
            continue
    mod_techs = set()
    folder = os.path.join(mod_root, "common", "technologies")
    if os.path.isdir(folder):
        for name in sorted(os.listdir(folder)):
            if not name.endswith(".txt"):
                continue
            try:
                with open(os.path.join(folder, name), "r", encoding="utf-8-sig", errors="ignore") as f:
                    text = scan.strip_comments(f.read())
            except OSError:
                continue
            wrapper = scan.first_block(text, "technologies")
            if wrapper is None:
                continue
            for tech_id, _inner in scan.iter_named_blocks(wrapper):
                mod_techs.add(tech_id)

    findings = []
    seen = set()

    def report(kind, ref, where, hint):
        key = (kind, ref)
        if key in seen:
            return
        seen.add(key)
        findings.append({
            "kind": kind, "id": ref, "where": where,
            "message": f"{kind} '{ref}' is referenced by {where} but exists in neither this mod "
                       f"nor the installed game — {hint}",
        })

    if progress:
        progress("Checking the mod's references...")

    # focus prerequisites pointing at vanilla focus ids
    for path in ml.find_focus_tree_files(mod_root):
        rel = os.path.relpath(path, mod_root)
        try:
            trees = ml.parse_focus_trees(path)
        except OSError:
            continue
        for tree in trees:
            for f in tree["focuses"]:
                for pre in f.get("prerequisite", []):
                    if pre in mod_focuses or pre in vanilla_focuses:
                        continue
                    report("focus", pre, f"focus '{f['id']}' in {rel}",
                           "that focus can never unlock")

    # add_idea / set_technology inside any script file
    for path in mod_files.iter_script_files(mod_root):
        rel = os.path.relpath(path, mod_root)
        try:
            with open(path, "r", encoding="utf-8-sig", errors="ignore") as f:
                text = scan.strip_comments(f.read())
        except OSError:
            continue

        for block in _ADD_IDEA_RE.findall(text):
            for ref in re.findall(r"[A-Za-z0-9_]+", block):
                if ref in mod_ideas or ref in vanilla_ideas:
                    continue
                report("idea", ref, rel, "adding it does nothing at runtime")
        for ref in _ADD_IDEA_SINGLE_RE.findall(text):
            if ref in mod_ideas or ref in vanilla_ideas:
                continue
            report("idea", ref, rel, "adding it does nothing at runtime")

        for block in _ADD_TECH_RE.findall(text):
            for ref in _TECH_LINE_RE.findall(block):
                if ref in mod_techs or ref in vanilla_techs:
                    continue
                report("technology", ref, rel, "granting it does nothing at runtime")

    return findings
