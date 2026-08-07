"""One Tk root shared by every test module that needs a display.

Two `tk.Tk()` instances in one process are two separate interpreters, and
widgets built on the second one quietly stop painting - which showed up as
the rail tests passing alone and failing in a full run. Everything that
needs a display asks for the root here instead of making its own.
"""

try:
    import tkinter as tk

    def root():
        """The shared hidden root, created on first use."""
        existing = tk._default_root
        if existing is not None:
            return existing
        made = tk.Tk()
        made.withdraw()
        return made

    root()
    HAVE_TK = True
except Exception:                       # headless build machine
    HAVE_TK = False

    def root():
        raise RuntimeError("no display")
