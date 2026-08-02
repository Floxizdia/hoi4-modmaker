"""Targeted edits to a single focus inside an existing focus-tree file.

The whole point is byte-preservation: the file may be 50k lines of someone
else's carefully formatted work, so instead of parse-and-regenerate we
locate the one `focus = { ... }` block whose id matches and rewrite only
the fields that changed, leaving every other byte exactly as it was.
"""

import os
import re
import shutil

from app import pds_scan as scan
from app import undo

SCALAR_KEYS = ("icon", "cost", "x", "y")
BLOCK_KEYS = ("completion_reward", "available")


def find_focus_span(text, focus_id):
    """(start, end) of the whole `focus = { ... }` block with this id."""
    for start, end, inner in scan.iter_blocks(text, "focus"):
        if scan.scalar(inner, "id") == focus_id:
            return start, end
    return None


def _set_scalar(block, key, value):
    pattern = re.compile(r"(\b" + key + r"\s*=\s*)(?!\{)(\"[^\"]*\"|\S+)")
    if pattern.search(block):
        return pattern.sub(lambda m: m.group(1) + str(value), block, count=1)
    # field absent - slot it in right after the id line
    return re.sub(r"(\bid\s*=\s*\S+)", rf"\1\n\t\t{key} = {value}", block, count=1)


def _set_block(block, key, new_inner):
    """Replace the inner text of `key = { ... }` inside the focus block, or
    append the whole sub-block before the focus's closing brace."""
    for match in re.finditer(r"\b" + key + r"\s*=\s*\{", block):
        open_idx = match.end() - 1
        close_idx = scan.find_matching_brace(block, open_idx)
        if close_idx == -1:
            continue
        indented = "\n" + "\n".join("\t\t\t" + line for line in new_inner.strip().splitlines()) + "\n\t\t"
        return block[:open_idx + 1] + indented + block[close_idx:]
    if not new_inner.strip():
        return block
    tail = block.rstrip()
    assert tail.endswith("}")
    indented = "\n".join("\t\t\t" + line for line in new_inner.strip().splitlines())
    return tail[:-1].rstrip() + f"\n\t\t{key} = {{\n{indented}\n\t\t}}\n\t}}"


def _brace_depth_at(text, target):
    """Return structural brace depth immediately before ``target``."""
    depth = 0
    in_quotes = False
    index = 0
    while index < target:
        char = text[index]
        if in_quotes:
            if char == "\\":
                index += 2
                continue
            if char == '"':
                in_quotes = False
        elif char == '"':
            in_quotes = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
        index += 1
    return depth


def _set_repeated_blocks(block, key, groups):
    """Replace direct child blocks while preserving unrelated nested PDS.

    HOI4 uses one ``prerequisite`` block per AND condition and the focuses
    inside a block are OR alternatives.  A simple single-block replacement
    would leave stale conditions behind, so this deliberately removes every
    direct child block of that key before emitting the current groups.
    """
    spans = [
        (start, end)
        for start, end, _inner in scan.iter_blocks(block, key)
        if _brace_depth_at(block, start) == 1
    ]
    for start, end in reversed(spans):
        block = block[:start] + block[end:]

    clean_groups = [list(group) for group in groups if group]
    if not clean_groups:
        return block

    rendered = []
    for group in clean_groups:
        lines = "\n".join(f"\t\t\tfocus = {focus_id}" for focus_id in group)
        rendered.append(f"\t\t{key} = {{\n{lines}\n\t\t}}")
    tail = block.rstrip()
    assert tail.endswith("}")
    return tail[:-1].rstrip() + "\n" + "\n".join(rendered) + "\n\t}"


def apply_edits(path, focus_id, scalars=None, blocks=None):
    """Edit one focus in place. `scalars` maps icon/cost/x/y to values,
    `blocks` maps completion_reward/available to raw inner text.
    Returns True on success, False if the focus wasn't found."""
    with open(path, "r", encoding="utf-8-sig", errors="ignore") as f:
        text = f.read()

    span = find_focus_span(text, focus_id)
    if not span:
        return False
    start, end = span
    block = text[start:end]

    for key, value in (scalars or {}).items():
        if key in SCALAR_KEYS and value is not None and value != "":
            block = _set_scalar(block, key, value)
    for key, value in (blocks or {}).items():
        if key in BLOCK_KEYS and value is not None:
            block = _set_block(block, key, value)
        elif key == "prerequisite_groups" and value is not None:
            block = _set_repeated_blocks(block, "prerequisite", value)
        elif key == "mutually_exclusive" and value is not None:
            block = _set_repeated_blocks(block, "mutually_exclusive", [value])

    backup = path + ".bak"
    if not os.path.exists(backup):
        shutil.copy2(path, backup)
    undo.record(path, f"{focus_id} in {os.path.basename(path)}")
    with open(path, "w", encoding="utf-8") as f:
        f.write(text[:start] + block + text[end:])
    return True


def append_focus_blocks(path, tree_id, focus_blocks):
    """Append rendered ``focus = { ... }`` blocks to one loaded tree.

    HOI4 selects one ``focus_tree`` definition by id; a second file with the
    same id is not a reliable extension mechanism.  New focuses therefore
    belong inside the selected tree's source file.  The surrounding file is
    otherwise kept byte-for-byte intact and the write participates in undo.
    """
    if not focus_blocks:
        return False
    with open(path, "r", encoding="utf-8-sig", errors="ignore") as handle:
        text = handle.read()

    tree_span = None
    for start, end, inner in scan.iter_blocks(text, "focus_tree"):
        if scan.scalar(inner, "id") == tree_id:
            tree_span = (start, end)
            break
    if not tree_span:
        return False

    existing_ids = {
        scan.scalar(inner, "id")
        for _, _, inner in scan.iter_blocks(text[tree_span[0]:tree_span[1]], "focus")
    }
    incoming_ids = {
        scan.scalar(inner, "id")
        for _, _, inner in scan.iter_blocks(focus_blocks, "focus")
    }
    if None in incoming_ids or existing_ids.intersection(incoming_ids):
        return False

    _start, end = tree_span
    rendered = "\n".join("\t" + line if line.strip() else line for line in focus_blocks.splitlines())
    insert_at = end - 1  # the focus_tree closing brace
    updated = text[:insert_at].rstrip() + "\n" + rendered + "\n" + text[insert_at:]

    backup = path + ".bak"
    if not os.path.exists(backup):
        shutil.copy2(path, backup)
    undo.record(path, f"new focuses in {os.path.basename(path)}")
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(updated)
    return True
