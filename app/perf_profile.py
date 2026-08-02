"""Time the same scans the app already runs on a mod (focus trees, events,
decisions, ideas, gfx index, full validation) so a modder with a huge mod
(1000+ files) can see which step is actually slow instead of just "the tool
feels sluggish" - the numbers point at a folder, not a vibe.
"""

import time

from app import mod_loader as ml
from app import validator
from app import mod_files


def _time_it(fn):
    start = time.perf_counter()
    result = fn()
    return result, time.perf_counter() - start


def profile(mod_root, progress=None):
    """[(label, seconds, detail), ...] in the order steps actually run."""
    steps = []

    def report(label):
        if progress:
            progress(f"Timing: {label}...")

    report("counting script files")
    files, t = _time_it(lambda: list(mod_files.iter_script_files(mod_root)))
    steps.append(("Walk script files", t, f"{len(files)} file(s)"))

    report("focus trees")
    tree_paths, t1 = _time_it(lambda: ml.find_focus_tree_files(mod_root))

    def parse_all_trees():
        out = []
        for p in tree_paths:
            out.extend(ml.parse_focus_trees(p))
        return out
    trees, t2 = _time_it(parse_all_trees)
    n_focuses = sum(len(tr["focuses"]) for tr in trees)
    steps.append(("Parse focus trees", t1 + t2, f"{len(tree_paths)} file(s), {n_focuses} focus(es)"))

    report("events")
    event_paths, t1 = _time_it(lambda: ml.find_event_files(mod_root))

    def parse_all_events():
        total = 0
        for p in event_paths:
            _, evs = ml.parse_events(p)
            total += len(evs)
        return total
    n_events, t2 = _time_it(parse_all_events)
    steps.append(("Parse events", t1 + t2, f"{len(event_paths)} file(s), {n_events} event(s)"))

    report("decisions")
    dec_paths, t1 = _time_it(lambda: ml.find_decision_files(mod_root))

    def parse_all_decisions():
        total = 0
        for p in dec_paths:
            for cat in ml.parse_decisions(p):
                total += len(cat["decisions"])
        return total
    n_decisions, t2 = _time_it(parse_all_decisions)
    steps.append(("Parse decisions", t1 + t2, f"{len(dec_paths)} file(s), {n_decisions} decision(s)"))

    report("ideas")
    idea_paths, t1 = _time_it(lambda: ml.find_idea_files(mod_root))

    def parse_all_ideas():
        total = 0
        for p in idea_paths:
            for cat in ml.parse_ideas(p):
                total += len(cat["ideas"])
        return total
    n_ideas, t2 = _time_it(parse_all_ideas)
    steps.append(("Parse ideas", t1 + t2, f"{len(idea_paths)} file(s), {n_ideas} idea(s)"))

    report("gfx index")
    gfx_index, t = _time_it(lambda: ml.build_gfx_index([mod_root]))
    steps.append(("Build gfx index", t, f"{len(gfx_index)} sprite(s)"))

    report("localisation")
    loc, t = _time_it(lambda: ml.load_localisation(mod_root))
    steps.append(("Load localisation", t, f"{len(loc)} key(s)"))

    report("full validation")
    issues, t = _time_it(lambda: validator.validate(mod_root, loc, gfx_index))
    steps.append(("Full validate()", t, f"{len(issues)} issue(s) found"))

    return steps
