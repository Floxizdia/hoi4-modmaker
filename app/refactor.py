"""Renaming and deleting content ids across a whole mod.

Every other screen in this app *adds* things. This is the first that can
change one afterwards, which is what makes a large mod maintainable: an id
used in twelve files can't be renamed by hand without missing one, and a
missed reference doesn't crash the game or reach error.log - the focus just
quietly never unlocks.

Two rules keep this from being find-and-replace with extra steps:

* a script hit only counts when the id stands alone as a token, the same
  boundary rule `references.py` uses, so renaming `my_focus` never touches
  `my_focus_two` and renaming `germany.1` never touches `germany.14`;
* localisation keys are matched by an explicit derivation rule rather than
  by prefix, because `my_focus_two` starts with `my_focus_` and prefix
  matching would silently rewrite an unrelated key.

Nothing here writes on its own. `plan_rename` returns exactly what would
change and `apply_plan` performs it, so the UI can show the whole diff
first - a refactor the user can't inspect beforehand is one they can't
trust with a mod they've spent months on.
"""

import os
import re

from app import mod_files
from app import pds_scan as scan
from app import undo
from app.references import _token_re

#: keyed wrappers that declare their own id inside the block, rather than
#: being named by it - `focus = { id = my_focus ... }`
ID_BLOCK_KEYS = ("focus", "country_event", "news_event", "state_event",
                 "unit_leader_event", "operative_leader_event")

#: derived localisation keys the game builds from a content id. Anything
#: else that merely starts with the id belongs to a different piece of
#: content and must be left alone.
LOC_SUFFIXES = ("", "_desc", "_tt", "_shine")

_LOC_KEY_RE = re.compile(r"^(\s*)([\w.\-]+)(\s*:\s*\d*\s*)(\".*)$")


def loc_key_belongs_to(key, ref_id):
    """True when `key` is this id's own localisation key.

    Two shapes count: the id with one of the game's derived suffixes
    (`my_focus`, `my_focus_desc`), and the id followed by a dot, which is
    how an event's title, description and options are keyed
    (`germany.1.t`, `germany.1.a`).
    """
    if key.startswith(ref_id + "."):
        return True
    return any(key == ref_id + suffix for suffix in LOC_SUFFIXES)


def rename_loc_key(key, old_id, new_id):
    return new_id + key[len(old_id):]


# ---- planning ----

def _rewrite_script_line(line, pattern, new_id):
    return pattern.sub(new_id, line)


def _rewrite_loc_line(line, old_id, new_id):
    """A localisation line, key rewritten and the text left alone.

    Only the key is touched on purpose: the English text of a focus may
    well contain the words of its own id, and rewriting prose is not what
    was asked for.
    """
    match = _LOC_KEY_RE.match(line)
    if not match:
        return line
    indent, key, sep, value = match.groups()
    if not loc_key_belongs_to(key, old_id):
        return line
    return f"{indent}{rename_loc_key(key, old_id, new_id)}{sep}{value}"


def plan_rename(mod_root, old_id, new_id, progress=None):
    """What renaming `old_id` to `new_id` would change.

    Returns [{path, rel, changes: [(line_no, before, after)]}], one entry
    per file that would actually change, in path order.
    """
    if not old_id or not new_id or old_id == new_id:
        return []

    pattern = _token_re(old_id)
    plan = []

    for path in sorted(mod_files.iter_script_files(mod_root)):
        try:
            with open(path, "r", encoding="utf-8-sig", errors="ignore") as handle:
                text = handle.read()
        except OSError:
            continue
        if old_id not in text:
            continue          # cheap reject before touching every line

        is_loc = path.lower().endswith(".yml")
        changes = []
        for number, line in enumerate(text.splitlines(), start=1):
            if old_id not in line:
                continue
            new_line = (_rewrite_loc_line(line, old_id, new_id) if is_loc
                        else _rewrite_script_line(line, pattern, new_id))
            if new_line != line:
                changes.append((number, line, new_line))

        if changes:
            plan.append({"path": path,
                         "rel": os.path.relpath(path, mod_root),
                         "changes": changes})
        if progress:
            progress(f"{len(plan)} file(s) so far...")
    return plan


def plan_summary(plan):
    """(files, lines) the plan would touch."""
    return len(plan), sum(len(entry["changes"]) for entry in plan)


def conflicts(mod_root, new_id):
    """Files where `new_id` already appears as a token - renaming onto a
    name that is already taken merges two pieces of content into one, which
    is never what was meant."""
    pattern = _token_re(new_id)
    found = []
    for path in sorted(mod_files.iter_script_files(mod_root)):
        try:
            with open(path, "r", encoding="utf-8-sig", errors="ignore") as handle:
                text = handle.read()
        except OSError:
            continue
        if new_id in text and pattern.search(text):
            found.append(os.path.relpath(path, mod_root))
    return found


# ---- deleting ----

def find_definition_spans(text, ref_id):
    """[(start, end)] of the blocks that *define* `ref_id` in this text.

    Two shapes cover everything the game uses: a keyed wrapper carrying its
    own id (`focus = { id = my_focus ... }`, and the event variants), and a
    block simply named after the id (`my_decision = { ... }`, which is how
    decisions, ideas and scripted effects declare themselves).
    """
    spans = []
    for key in ID_BLOCK_KEYS:
        for start, end, inner in scan.iter_blocks(text, key):
            if scan.scalar(inner, "id") == ref_id:
                spans.append((start, end))

    pattern = re.compile(r"(?<![A-Za-z0-9_.])" + re.escape(ref_id) + r"\s*=\s*\{")
    for match in pattern.finditer(text):
        close = scan.find_matching_brace(text, match.end() - 1)
        if close == -1:
            continue
        span = (match.start(), close + 1)
        if not any(s <= span[0] and span[1] <= e for s, e in spans):
            spans.append(span)
    return sorted(set(spans))


def _line_range(text, start, end):
    """The 1-based line numbers a character span covers, extended to whole
    lines so a definition is removed without leaving its indentation."""
    first = text.count("\n", 0, start) + 1
    last = text.count("\n", 0, end - 1) + 1
    return first, last


def plan_delete(mod_root, ref_id, progress=None):
    """What deleting `ref_id` would remove, and what it would break.

    Returns (plan, dangling): `plan` has the same shape as a rename plan
    but with `after` set to None for lines that go away, so the preview and
    the writer are shared. `dangling` lists the references left pointing at
    nothing - those are deliberately NOT auto-removed, because a reference
    sits inside somebody else's effect block and cutting the line out can
    leave that block meaning something different.
    """
    if not ref_id:
        return [], []

    pattern = _token_re(ref_id)
    plan, dangling = [], []

    for path in sorted(mod_files.iter_script_files(mod_root)):
        try:
            with open(path, "r", encoding="utf-8-sig", errors="ignore") as handle:
                text = handle.read()
        except OSError:
            continue
        if ref_id not in text:
            continue

        rel = os.path.relpath(path, mod_root)
        lines = text.splitlines()
        removed = set()

        if path.lower().endswith(".yml"):
            for number, line in enumerate(lines, start=1):
                match = _LOC_KEY_RE.match(line)
                if match and loc_key_belongs_to(match.group(2), ref_id):
                    removed.add(number)
        else:
            for start, end in find_definition_spans(text, ref_id):
                first, last = _line_range(text, start, end)
                removed.update(range(first, last + 1))

        if removed:
            plan.append({"path": path, "rel": rel,
                         "changes": [(n, lines[n - 1], None) for n in sorted(removed)]})

        # anything still mentioning the id outside what we are removing
        for match in pattern.finditer(text):
            number = text.count("\n", 0, match.start()) + 1
            if number in removed:
                continue
            line_start = text.rfind("\n", 0, match.start()) + 1
            line_end = text.find("\n", match.start())
            snippet = text[line_start:line_end if line_end != -1 else len(text)].strip()
            dangling.append({"file": rel, "abs_path": path,
                             "line": number, "snippet": snippet[:160]})
        if progress:
            progress(f"{len(plan)} file(s) so far...")
    return plan, dangling


# ---- applying ----

def apply_plan(plan, description="rename"):
    """Write a plan out, one undo entry and one .bak per file.

    Lines are replaced by number against a fresh read, so a file that
    changed since the plan was built is skipped rather than corrupted. An
    `after` of None removes the line, which is how a delete plan is
    expressed - same preview, same writer, same safety net.

    Returns (written_paths, skipped_paths).
    """
    import shutil

    written, skipped = [], []
    for entry in plan:
        path = entry["path"]
        try:
            with open(path, "r", encoding="utf-8-sig", errors="ignore") as handle:
                text = handle.read()
        except OSError:
            skipped.append(path)
            continue

        lines = text.splitlines(keepends=True)
        stale = False
        for number, before, _after in entry["changes"]:
            if number > len(lines) or lines[number - 1].rstrip("\r\n") != before:
                stale = True
                break
        if stale:
            skipped.append(path)
            continue

        # highest line first, so removing one doesn't shift the numbers of
        # the ones not yet handled
        for number, _before, after in sorted(entry["changes"], reverse=True):
            if after is None:
                del lines[number - 1]
                continue
            ending = lines[number - 1][len(lines[number - 1].rstrip("\r\n")):]
            lines[number - 1] = after + ending

        backup = path + ".bak"
        if not os.path.exists(backup):
            shutil.copy2(path, backup)
        undo.record(path, f"{description}: {os.path.basename(path)}")
        # utf-8-sig for localisation, which the game rejects without a BOM;
        # plain utf-8 for script, which does not want one
        encoding = "utf-8-sig" if path.lower().endswith(".yml") else "utf-8"
        with open(path, "w", encoding=encoding, newline="") as handle:
            handle.write("".join(lines))
        written.append(path)
    return written, skipped
