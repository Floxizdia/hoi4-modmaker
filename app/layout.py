"""Automatic focus tree layout.

Real mods lean heavily on `relative_position_id`, often pointing at a focus
that lives in a different file (shared branches). When that anchor isn't in
the tree we're viewing, the stored x/y are meaningless offsets and every
such focus collapses onto the same spot. So instead of trusting the stored
coordinates we can derive a clean layout from the prerequisite graph:
depth decides the row, and a barycenter pass orders each row so children
sit near their parents and nothing ever overlaps.
"""

from collections import defaultdict


def _parents(focus, by_id):
    groups = focus.get("prerequisite_groups")
    if not groups:
        flat = focus.get("prerequisite") or []
        groups = [flat] if flat else []
    out = []
    for group in groups:
        for option in group:
            if option in by_id and option != focus["id"]:
                out.append(option)
    return out


def compute_depths(focuses, by_id):
    """Longest-path depth, iterated to a fixed point. The iteration cap also
    keeps malformed trees with prerequisite cycles from looping forever."""
    depth = {f["id"]: 0 for f in focuses}
    for _ in range(len(focuses) + 1):
        changed = False
        for f in focuses:
            parents = _parents(f, by_id)
            new = 0 if not parents else max(depth[p] for p in parents) + 1
            if new != depth[f["id"]]:
                depth[f["id"]] = new
                changed = True
        if not changed:
            break
    return depth


def auto_layout(focuses, barycenter_passes=4):
    """Return {focus_id: (col, row)} grid coordinates with no two focuses
    sharing a cell."""
    if not focuses:
        return {}

    by_id = {f["id"]: f for f in focuses}
    depth = compute_depths(focuses, by_id)

    rows = defaultdict(list)
    for f in focuses:
        rows[depth[f["id"]]].append(f)

    # Seed each row by the mod's own x, so sibling ordering stays close to
    # what the author intended where the coordinates are meaningful.
    col = {}
    for d in sorted(rows):
        rows[d].sort(key=lambda f: (f.get("x", 0), f["id"]))
        for i, f in enumerate(rows[d]):
            col[f["id"]] = i

    for _ in range(barycenter_passes):
        for d in sorted(rows):
            if d == 0:
                continue
            row = rows[d]

            def key(f):
                parents = _parents(f, by_id)
                if parents:
                    return sum(col[p] for p in parents) / len(parents)
                return col[f["id"]]

            row.sort(key=lambda f: (key(f), f["id"]))
            for i, f in enumerate(row):
                col[f["id"]] = i

    widest = max(len(r) for r in rows.values())
    pos = {}
    for d, row in rows.items():
        offset = (widest - len(row)) / 2.0
        for i, f in enumerate(row):
            pos[f["id"]] = (offset + i, d)
    return pos


def next_free_cell(taken, preferred):
    """Find a free grid cell at or to the right of `preferred`."""
    x, y = preferred
    while (x, y) in taken:
        x += 1
    return x, y
