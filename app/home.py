"""Launcher screen shown before the workspace - composition root only.

The Home screen used to be one ~1000-line file. It's now an assembly of
reusable pieces, the same shape every future screen should follow:

  home_theme.py       colours, spacing, style tokens (screen-agnostic)
  home_data.py        loads and caches whatever the screen needs from disk
  home_table.py        the mod table: search/filter/sort + the list itself
  home_sidebar.py      the left rail: Continue / New mod / Getting started
  home_inspector.py    the right panel: detail on whatever's selected
  home_view.py         static layout - assembles the three above + chrome
  home_controller.py   what each control *does* - the only file that
                        should need edits when a Home action's behaviour
                        changes

This module just builds a controller (which builds the view into itself)
and exposes the one extra hook main.py needs when returning from the
workspace. Keeping this thin, single-purpose top file is what main.py's
`from app.home import HomeScreen` import expects - nothing else in the app
should need to know the screen is built out of six files instead of one.
"""

from tkinter import ttk

from app import home_theme
from app.home_controller import HomeController


class HomeScreen(ttk.Frame):
    def __init__(self, master, on_new_mod, on_open_mod):
        home_theme.install(master)
        super().__init__(master)
        self.controller = HomeController(self, on_new_mod, on_open_mod)
        self.controller.view.pack(fill="both", expand=True)

    def refresh_sidebar(self):
        """Called when returning from the workspace to Home: the mod that
        was just worked on should now show up as resumable."""
        self.controller.view.sidebar.rebuild()
