"""App-wide Ctrl+Z: every surgical write already keeps a one-time `.bak`,
but that only ever restores the FIRST version of a file - editing the same
focus twice in one session leaves no way back to the middle state. This
keeps a real stack: each edit pushes what the file looked like right before
that write, so undo steps backward one edit at a time, across any tab, in
the order they actually happened.

Deliberately whole-file snapshots, not diffs - these edits touch files ranging
from a few hundred bytes to tens of megabytes, and a snapshot of "the field
that's about to change" would still need the same before/after bytes to be
useful, so there is no simpler representation that stays correct for every
call site.
"""

import os

MAX_HISTORY = 40

_stack = []        # file snapshots or in-memory action entries
_redo_stack = []    # same shape, populated by undo(), consumed by redo()


def record(path, description=""):
    """Call this immediately BEFORE writing `path`. Captures what's there
    now (or that there was nothing there) so undo() can restore it."""
    original = None
    if os.path.isfile(path):
        with open(path, "rb") as f:
            original = f.read()
    _stack.append((path, original, description or os.path.basename(path)))
    del _stack[:-MAX_HISTORY]
    # a fresh edit branches away from whatever was undone - the old redo
    # path no longer matches what's on disk, so it can't be replayed safely
    _redo_stack.clear()


def record_action(undo_action, redo_action, description=""):
    """Record a reversible in-memory editor operation.

    Most screens write files and can therefore use :func:`record`.  Canvas
    commands such as moving a focus are deliberately staged until the user
    saves, so they need an action pair instead.  Keeping both entry types in
    the same stack preserves the application's chronological Ctrl+Z order.
    """
    _stack.append(("action", undo_action, redo_action, description or "change"))
    del _stack[:-MAX_HISTORY]
    _redo_stack.clear()


def can_undo():
    return bool(_stack)


def can_redo():
    return bool(_redo_stack)


def undo():
    """Restore the most recent recorded edit, pushing what was just
    overwritten onto the redo stack. Returns a description string, or None
    if there was nothing to undo."""
    if not _stack:
        return None
    entry = _stack.pop()
    if entry[0] == "action":
        _, undo_action, _redo_action, description = entry
        undo_action()
        _redo_stack.append(entry)
        return f"Reverted {description}"

    path, original, description = entry
    current = None
    if os.path.isfile(path):
        with open(path, "rb") as f:
            current = f.read()
    _redo_stack.append((path, current, description))

    if original is None:
        if os.path.isfile(path):
            os.remove(path)
        return f"Removed {description} (it was newly created)"
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(original)
    return f"Reverted {description}"


def redo():
    """Re-apply the most recently undone edit, pushing the pre-redo state
    back onto the undo stack. Returns a description string, or None if
    there was nothing to redo."""
    if not _redo_stack:
        return None
    entry = _redo_stack.pop()
    if entry[0] == "action":
        _, _undo_action, redo_action, description = entry
        redo_action()
        _stack.append(entry)
        return f"Re-applied {description}"

    path, snapshot, description = entry
    current = None
    if os.path.isfile(path):
        with open(path, "rb") as f:
            current = f.read()
    _stack.append((path, current, description))

    if snapshot is None:
        if os.path.isfile(path):
            os.remove(path)
        return f"Removed {description} again"
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(snapshot)
    return f"Re-applied {description}"


def clear():
    """Called when a different mod is opened - undo history from mod A
    editing mod B's files would be actively dangerous."""
    _stack.clear()
    _redo_stack.clear()
