"""Targeted, byte-preserving edits to a single existing history/states/*.txt
file - same philosophy as focus_surgery.py: locate the field, rewrite only
that field, leave every other byte (comments, spacing, unrelated fields) as
it was. State files are hand-authored map data, often shared with other
mods' compatibility patches, so this never regenerates the whole file.
"""

import os
import re
import shutil

from app import pds_scan as scan
from app import undo

ROOT_SCALAR_KEYS = ("manpower", "state_category", "local_supplies")


def _set_scalar(block, key, value):
    pattern = re.compile(r"(\b" + key + r"\s*=\s*)(?!\{)(\"[^\"]*\"|\S+)")
    if pattern.search(block):
        return pattern.sub(lambda m: m.group(1) + str(value), block, count=1)
    return re.sub(r"(\bid\s*=\s*\S+)", rf"\1\n\t{key} = {value}", block, count=1)


def _set_block(block, key, new_inner, indent="\t"):
    """Replace/insert `key = { ... }` at the top level of `block` (not
    inside a nested sub-block), indenting new lines with `indent`."""
    # `block` itself is wrapped in its own outer `{...}`, so a genuine
    # immediate child sits at brace-depth 1, not 0 - anything deeper is
    # nested inside some other sub-block and must be skipped
    for match in re.finditer(r"\b" + key + r"\s*=\s*\{", block):
        prefix = block[:match.start()]
        if prefix.count("{") - prefix.count("}") != 1:
            continue
        open_idx = match.end() - 1
        close_idx = scan.find_matching_brace(block, open_idx)
        if close_idx == -1:
            continue
        indented = "\n" + "\n".join(indent + "\t" + line for line in new_inner.strip().splitlines()) + "\n" + indent
        return block[:open_idx + 1] + indented + block[close_idx:]
    if not new_inner.strip():
        return block
    tail = block.rstrip()
    assert tail.endswith("}")
    indented = "\n".join(indent + "\t" + line for line in new_inner.strip().splitlines())
    return tail[:-1].rstrip() + f"\n{indent}{key} = {{\n{indented}\n{indent}}}\n}}"


def apply_edits(path, *, scalars=None, resources=None, buildings=None, victory_points=None):
    """Edit one state file in place.
    `scalars` maps manpower/state_category/local_supplies to values.
    `resources` maps resource token -> amount (root-level `resources={}`).
    `buildings` maps building token -> level (inside `history={}`).
    `victory_points` is a list of (province_id, value) pairs, replacing all
    existing victory_points blocks inside `history={}` with this set.
    """
    with open(path, "r", encoding="utf-8-sig", errors="ignore") as f:
        text = f.read()

    span = None
    for start, end, _ in scan.iter_blocks(text, "state"):
        span = (start, end)
        break
    if span is None:
        return False
    start, end = span
    block = text[start:end]

    for key, value in (scalars or {}).items():
        if key in ROOT_SCALAR_KEYS and value is not None and value != "":
            block = _set_scalar(block, key, value)

    if resources:
        inner = "\n".join(f"{tok} = {amt}" for tok, amt in resources.items())
        block = _set_block(block, "resources", inner, indent="\t")

    if buildings is not None or victory_points is not None:
        hist_m = re.search(r"\bhistory\s*=\s*\{", block)
        if hist_m:
            open_idx = hist_m.end() - 1
            close_idx = scan.find_matching_brace(block, open_idx)
            hist_block = block[open_idx:close_idx + 1]

            if buildings is not None:
                inner = "\n".join(f"{tok} = {lvl}" for tok, lvl in buildings.items() if lvl)
                hist_block = _set_block(hist_block, "buildings", inner, indent="\t\t")

            if victory_points is not None:
                # strip every existing victory_points={...} block, then append fresh ones
                stripped = ""
                pos = 0
                for m in re.finditer(r"\bvictory_points\s*=\s*\{", hist_block):
                    if m.start() < pos:
                        continue
                    o = m.end() - 1
                    c = scan.find_matching_brace(hist_block, o)
                    if c == -1:
                        continue
                    stripped += hist_block[pos:m.start()]
                    pos = c + 1
                stripped += hist_block[pos:]
                hist_block = stripped
                if victory_points:
                    tail = hist_block.rstrip()
                    assert tail.endswith("}")
                    vp_text = "".join(
                        f"\n\t\tvictory_points = {{\n\t\t\t{prov} {val}\n\t\t}}"
                        for prov, val in victory_points
                    )
                    hist_block = tail[:-1].rstrip() + vp_text + "\n\t}"

            block = block[:open_idx] + hist_block + block[close_idx + 1:]

    backup = path + ".bak"
    if not os.path.exists(backup):
        shutil.copy2(path, backup)
    undo.record(path, f"state {os.path.basename(path)}")
    with open(path, "w", encoding="utf-8") as f:
        f.write(text[:start] + block + text[end:])
    return True


def read_fields(path):
    """Current values for the edit form: scalars, resources, buildings,
    victory_points (list of (province, value))."""
    with open(path, "r", encoding="utf-8-sig", errors="ignore") as f:
        text = scan.strip_comments(f.read())

    block = None
    for _, _, inner in scan.iter_blocks(text, "state"):
        block = inner
        break
    if block is None:
        return None

    res_block = scan.first_block(block, "resources") or ""
    resources = dict(re.findall(r"(\w+)\s*=\s*(-?\d+(?:\.\d+)?)", res_block))

    history = scan.first_block(block, "history") or ""
    bld_block = scan.first_block(history, "buildings") or ""
    buildings = dict(re.findall(r"(\w+)\s*=\s*(-?\d+(?:\.\d+)?)", bld_block))

    victory_points = []
    for vp_block, _ in [(m, None) for m in re.findall(r"victory_points\s*=\s*\{([^}]*)\}", history)]:
        nums = re.findall(r"\d+", vp_block)
        if len(nums) >= 2:
            victory_points.append((nums[0], nums[1]))

    return {
        "manpower": scan.scalar(block, "manpower") or "",
        "state_category": scan.scalar(block, "state_category") or "",
        "local_supplies": scan.scalar(block, "local_supplies") or "",
        "resources": resources,
        "buildings": buildings,
        "victory_points": victory_points,
    }
