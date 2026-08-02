"""Focus tree progression rules, mirroring how HOI4 gates a tree at runtime.

Kept separate from the UI so the logic can be reasoned about (and tested)
on its own. This models tree structure only - it deliberately does NOT
evaluate `available` triggers, since those depend on live game state
(politics, wars, dates) that a static file viewer cannot know.
"""


def _prereq_groups(focus):
    """Options within one prerequisite block are OR'd; separate blocks are
    AND'd. Older parses only kept a flat list, so fall back to treating it
    as a single OR group."""
    groups = focus.get("prerequisite_groups")
    if groups:
        return groups
    flat = focus.get("prerequisite") or []
    return [flat] if flat else []


def compute_states(focuses, completed):
    """Return (hidden, available) id sets for the given completed set.

    A focus is hidden when it is mutually exclusive with something already
    completed, or when every option of one of its prerequisite groups is
    itself hidden - which is how picking one branch makes the rival branch
    and everything behind it disappear in game.
    """
    by_id = {f["id"]: f for f in focuses}
    completed = {c for c in completed if c in by_id}

    hidden = set()
    for _ in range(len(focuses) + 1):
        changed = False

        for f in focuses:
            fid = f["id"]
            if fid in completed or fid in hidden:
                continue

            # mutual exclusivity, in both directions
            excluded = any(m in completed for m in f.get("mutually_exclusive", []))
            if not excluded:
                for cid in completed:
                    if fid in by_id[cid].get("mutually_exclusive", []):
                        excluded = True
                        break
            if excluded:
                hidden.add(fid)
                changed = True
                continue

            # a prerequisite group with no reachable option left
            for group in _prereq_groups(f):
                reachable = [o for o in group if o in by_id and o not in hidden]
                if group and not reachable:
                    hidden.add(fid)
                    changed = True
                    break

        if not changed:
            break

    available = set()
    for f in focuses:
        fid = f["id"]
        if fid in completed or fid in hidden:
            continue
        if all(any(o in completed for o in group) for group in _prereq_groups(f)):
            available.add(fid)

    return hidden, available


def state_of(focus_id, completed, hidden, available):
    if focus_id in completed:
        return "completed"
    if focus_id in hidden:
        return "hidden"
    if focus_id in available:
        return "available"
    return "locked"
