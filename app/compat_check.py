"""Compare two mods for the collisions that cause the classic "works alone,
crashes together" problem: two mods defining the same country tag, the same
focus/event/decision/idea id, or replacing the exact same file (whichever
loads last silently wins, and neither author necessarily knows).

This never needs to touch either mod - it's a read-only comparison, so it's
safe to point at two real Workshop mods without staging or backups.
"""

import os
import re

from app import mod_loader as ml
from app import tech_graph
from app import mod_files


def _ids(mod_root, finder, parser, extract):
    out = {}
    for path in finder(mod_root):
        for item in parser(path):
            for id_, source in extract(item, path):
                out.setdefault(id_, []).append(source)
    return out


def _focus_ids(mod_root):
    out = {}
    for path in ml.find_focus_tree_files(mod_root):
        for tree in ml.parse_focus_trees(path):
            for focus in tree["focuses"]:
                out.setdefault(focus["id"], []).append(path)
    return out


def _event_ids(mod_root):
    out = {}
    for path in ml.find_event_files(mod_root):
        _, events = ml.parse_events(path)
        for e in events:
            out.setdefault(f"{e['namespace']}.{e['number']}", []).append(path)
    return out


def _decision_ids(mod_root):
    out = {}
    for path in ml.find_decision_files(mod_root):
        for category in ml.parse_decisions(path):
            for d in category["decisions"]:
                out.setdefault(d["id"], []).append(path)
    return out


def _idea_ids(mod_root):
    out = {}
    for path in ml.find_idea_files(mod_root):
        for category in ml.parse_ideas(path):
            for i in category["ideas"]:
                out.setdefault(i["id"], []).append(path)
    return out


def _tech_ids(mod_root):
    out = {}
    for tid, info in tech_graph.build_graph(mod_root).items():
        out.setdefault(tid, []).append(info["file"])
    return out


def _country_tags(mod_root):
    """Tags this mod REGISTERS (common/country_tags/*.txt), not every tag it
    merely references - referencing TUR in an event doesn't collide with
    another mod that also references TUR."""
    out = set()
    folder = os.path.join(mod_root, "common", "country_tags")
    if not os.path.isdir(folder):
        return out
    tag_re = re.compile(r'^\s*([A-Z][A-Z0-9]{2})\s*=')
    for name in os.listdir(folder):
        if not name.endswith(".txt"):
            continue
        try:
            with open(os.path.join(folder, name), "r", encoding="utf-8-sig", errors="ignore") as f:
                for line in f:
                    m = tag_re.match(line)
                    if m:
                        out.add(m.group(1))
        except OSError:
            continue
    return out


CATEGORY_BUILDERS = {
    "Focus ids": _focus_ids,
    "Event ids": _event_ids,
    "Decision ids": _decision_ids,
    "Idea ids": _idea_ids,
    "Tech ids": _tech_ids,
}


def compare(mod_a, mod_b):
    """{'tags': [...], 'files': [rel paths], category: [ids]} - every entry
    here is something BOTH mods define, i.e. a real collision risk."""
    report = {}

    tags_a, tags_b = _country_tags(mod_a), _country_tags(mod_b)
    report["tags"] = sorted(tags_a & tags_b)

    for label, builder in CATEGORY_BUILDERS.items():
        ids_a, ids_b = set(builder(mod_a)), set(builder(mod_b))
        report[label] = sorted(ids_a & ids_b)

    files_a = {os.path.relpath(p, mod_a) for p in mod_files.iter_script_files(mod_a)}
    files_b = {os.path.relpath(p, mod_b) for p in mod_files.iter_script_files(mod_b)}
    report["files"] = sorted(files_a & files_b)

    return report


def summarise(report):
    total = sum(len(v) for v in report.values())
    return total, {k: len(v) for k, v in report.items()}
