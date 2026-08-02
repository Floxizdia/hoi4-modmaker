"""Marks a generator tab (Focus Tree / Events / Decisions / Ideas) dirty
whenever its in-memory list changes, and clean again once that list is
actually written out - so switching tabs or closing the app can warn before
silently discarding edits that were never exported.

Wrapping the existing _add/_edit/_delete/_export methods instead of adding
`self.is_dirty = True` to each one by hand: those four names are identical
across all four tabs already, so one small wrapper here covers all of them
without four near-duplicate edits per file.
"""


def track(tab, mutators=("_add", "_edit", "_delete"), export="_export"):
    tab.is_dirty = False

    def wrap_mutator(fn):
        def inner(*args, **kwargs):
            result = fn(*args, **kwargs)
            tab.is_dirty = True
            return result
        return inner

    for name in mutators:
        if hasattr(tab, name):
            setattr(tab, name, wrap_mutator(getattr(tab, name)))

    if hasattr(tab, export):
        orig_export = getattr(tab, export)

        def wrap_export(*args, **kwargs):
            result = orig_export(*args, **kwargs)
            tab.is_dirty = False
            return result

        setattr(tab, export, wrap_export)
