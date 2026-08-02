"""Instant focus-tree sanity checks, run right before a save instead of
waiting for a full Validate-tab pass.

The Validate tab already catches these mistakes, but it scans the whole mod
and takes seconds on a large one - by the time it reports a typo'd
prerequisite the tree has moved on. This is the same handful of checks
(broken references, x/y collisions) scoped to just the focuses in front of
the user right now, cheap enough to run on every save.
"""


def check(focuses):
    """[{severity, message}] - 'error' for a reference to an id that plain
    doesn't exist (the game would refuse to load), 'warning' for something
    that loads but looks like a mistake (two focuses stacked on one tile)."""
    issues = []
    ids = {f["id"] for f in focuses}

    for f in focuses:
        for group in f.get("prerequisite_groups") or [[p] for p in f.get("prerequisite", [])]:
            for ref in group:
                if ref not in ids:
                    issues.append({
                        "severity": "error",
                        "message": f"'{f['id']}' requires '{ref}', which isn't in this tree.",
                    })
        for ref in f.get("mutually_exclusive", []):
            if ref not in ids:
                issues.append({
                    "severity": "error",
                    "message": f"'{f['id']}' is mutually exclusive with '{ref}', which isn't in this tree.",
                })
        rel = f.get("relative_position_id")
        if rel and rel not in ids:
            issues.append({
                "severity": "warning",
                "message": f"'{f['id']}' is positioned relative to '{rel}', which isn't in this tree "
                          "(fine if that focus lives in another file of the same tree).",
            })

    positions = {}
    for f in focuses:
        if f.get("relative_position_id"):
            continue          # relative-positioned focuses don't collide on raw x/y
        key = (f.get("x", 0), f.get("y", 0))
        positions.setdefault(key, []).append(f["id"])
    for (x, y), owners in positions.items():
        if len(owners) > 1:
            issues.append({
                "severity": "warning",
                "message": f"{', '.join(owners)} all sit at x={x}, y={y} — they'll overlap on screen.",
            })

    return issues


def format_issues(issues):
    lines = []
    for issue in issues:
        marker = "✕" if issue["severity"] == "error" else "!"
        lines.append(f"{marker}  {issue['message']}")
    return "\n".join(lines)
