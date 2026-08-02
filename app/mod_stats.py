"""One summary pass over an open mod: how much content it has, its biggest
files, and which single focus branches out the most - the kind of "what am
I even looking at" overview that's otherwise only visible by clicking
through every tab one at a time.
"""

import os
from collections import Counter

from app import mod_loader as ml
from app import tech_graph
from app import mod_files


def collect(mod_root):
    focus_trees = []
    for path in ml.find_focus_tree_files(mod_root):
        focus_trees.extend(ml.parse_focus_trees(path))
    focuses = [f for tree in focus_trees for f in tree["focuses"]]

    events = []
    for path in ml.find_event_files(mod_root):
        _, evs = ml.parse_events(path)
        events.extend(evs)

    decisions = []
    for path in ml.find_decision_files(mod_root):
        for category in ml.parse_decisions(path):
            decisions.extend(category["decisions"])

    ideas = []
    for path in ml.find_idea_files(mod_root):
        for category in ml.parse_ideas(path):
            ideas.extend(category["ideas"])

    techs = [tid for tid, info in tech_graph.build_graph(mod_root).items() if not info.get("is_vanilla")]
    characters = ml.load_country_characters(mod_root)
    character_count = sum(len(v) for v in characters.values())

    branch_counts = Counter()
    for tree in focus_trees:
        for f in tree["focuses"]:
            for group in (f.get("prerequisite_groups") or [[p] for p in f.get("prerequisite", [])]):
                for parent in group:
                    branch_counts[parent] += 1
    busiest_focus = branch_counts.most_common(1)[0] if branch_counts else None

    country_focus_counts = Counter()
    for f in focuses:
        prefix = f["id"].split("_")[0]
        if len(prefix) == 3 and prefix.isupper() and prefix.isalpha():
            country_focus_counts[prefix] += 1
    richest_country = country_focus_counts.most_common(1)[0] if country_focus_counts else None

    biggest_files = []
    for path in mod_files.iter_script_files(mod_root):
        try:
            size = os.path.getsize(path)
        except OSError:
            continue
        biggest_files.append((os.path.relpath(path, mod_root), size))
    biggest_files.sort(key=lambda t: -t[1])

    return {
        "focus_trees": len(focus_trees),
        "focuses": len(focuses),
        "events": len(events),
        "decisions": len(decisions),
        "ideas": len(ideas),
        "techs_added": len(techs),
        "characters": character_count,
        "countries_with_focuses": len(country_focus_counts),
        "busiest_focus": busiest_focus,
        "richest_country": richest_country,
        "biggest_files": biggest_files[:8],
        "total_files": len(biggest_files),
        "total_size": sum(s for _, s in biggest_files),
    }


def format_size(num_bytes):
    for unit in ("B", "KB", "MB", "GB"):
        if num_bytes < 1024:
            return f"{num_bytes:.0f} {unit}"
        num_bytes /= 1024
    return f"{num_bytes:.1f} TB"
