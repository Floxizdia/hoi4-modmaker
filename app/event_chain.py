"""Which events fire which other events, built from the same firing-chain
detection `event_owner.py` already uses to trace country ownership - here
the graph itself is the point, not just a byproduct used to propagate tags.

Only events that actually participate in a chain (fire something, or are
fired by something) are kept; a mod's other few thousand standalone events
would just be noise on this view and are already covered by the plain
Events tab.
"""

from collections import defaultdict

from app import mod_loader as ml
from app.event_owner import _refs_in


def build_graph(mod_root):
    """{event_id: {'fires': [...], 'fired_by': [...], 'type', 'file'}} -
    only for events with at least one edge."""
    fires = defaultdict(set)
    fired_by = defaultdict(set)
    meta = {}

    for path in ml.find_event_files(mod_root):
        _, events = ml.parse_events(path)
        for e in events:
            eid = f"{e['namespace']}.{e['number']}"
            meta[eid] = {"type": e.get("type", ""), "file": path,
                        "title_key": e.get("title_key", "")}
            body = " ".join([e.get("immediate", "")] + [o.get("effect", "") for o in e["options"]])
            for ref in _refs_in(body):
                if ref != eid:
                    fires[eid].add(ref)
                    fired_by[ref].add(eid)

    graph = {}
    involved = set(fires) | set(fired_by)
    for eid in involved:
        graph[eid] = {
            "fires": sorted(fires.get(eid, ())),
            "fired_by": sorted(fired_by.get(eid, ())),
            "type": meta.get(eid, {}).get("type", ""),
            "file": meta.get(eid, {}).get("file", ""),
            "title_key": meta.get(eid, {}).get("title_key", ""),
        }
    return graph


def roots(graph):
    """Events with no known firer - where a chain starts, from this mod's
    point of view (the true trigger might be a focus/decision outside any
    event, which is exactly what event_owner.py separately infers)."""
    return sorted(eid for eid, info in graph.items() if not info["fired_by"])


def chain_from(graph, start_id, max_depth=12):
    """Every event reachable forward from `start_id`, id -> distance."""
    seen = {start_id: 0}
    frontier = [start_id]
    depth = 0
    while frontier and depth < max_depth:
        depth += 1
        nxt = []
        for eid in frontier:
            for target in graph.get(eid, {}).get("fires", []):
                if target not in seen:
                    seen[target] = depth
                    nxt.append(target)
        frontier = nxt
    return seen
