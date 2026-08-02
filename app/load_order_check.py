"""Load-order manager: run the same pairwise collision check compat_check
already does for two mods across a whole set, and suggest a load order.

The suggestion is a heuristic, not a guarantee - HOI4 has no dependency
metadata for third-party mods to declare "load after X", so the best any
tool can honestly do is a rule of thumb: mods with fewer script files tend
to be smaller patches/overhauls meant to override a big foundation mod, so
they're suggested to load last (winning the collision). A mod author's own
"load after" instructions in its Workshop description always take priority
over this - the tab says so.
"""

import os

from app import compat_check
from app import mod_files


def mod_file_count(mod_root):
    return sum(1 for _ in mod_files.iter_script_files(mod_root))


def compare_all(mods):
    """`mods` is [(name, path), ...]. Returns [(name_a, name_b, report,
    total)], only pairs with at least one collision, worst pairs first."""
    out = []
    for i in range(len(mods)):
        for j in range(i + 1, len(mods)):
            name_a, path_a = mods[i]
            name_b, path_b = mods[j]
            report = compat_check.compare(path_a, path_b)
            total, _ = compat_check.summarise(report)
            if total:
                out.append((name_a, name_b, report, total))
    out.sort(key=lambda row: -row[3])
    return out


def suggest_order(mods):
    """[(name, path, file_count)], smallest-first (suggested to load last,
    i.e. shown at the BOTTOM of this list - see the tab's own labelling)."""
    counted = [(name, path, mod_file_count(path)) for name, path in mods]
    counted.sort(key=lambda row: (-row[2], row[0].lower()))
    return counted
