"""The Focus Tree screen has to finish wiring itself up.

A method was once inserted into the middle of `_build`, which swallowed
everything after it: the mod dropdown was never filled, the function keys
were never bound and the canvas mode was never set. Nothing raised - the
screen just came up empty, reporting "No mod loaded" for a mod that was
sitting right there. These assertions are cheap and would have caught it
the moment it happened.
"""

import unittest

import tk_support
from tk_support import HAVE_TK

if HAVE_TK:
    import tkinter as tk


@unittest.skipUnless(HAVE_TK, "no display")
class ModBrowserWiringTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from app import theme
        from app.mod_browser import ModBrowserTab
        cls.win = tk.Toplevel(tk_support.root())
        cls.win.withdraw()
        theme.apply(cls.win)
        cls.tab = ModBrowserTab(cls.win)
        cls.win.update_idletasks()

    @classmethod
    def tearDownClass(cls):
        cls.win.destroy()

    def test_build_runs_to_the_end(self):
        """These are set by the last lines of _build; if a method gets
        inserted above them they silently stop existing."""
        for attribute in ("_workshop_mods", "selected_id", "_editing_id",
                          "status", "warning_label", "unsaved_label", "_link_from"):
            self.assertTrue(hasattr(self.tab, attribute), f"_build never set {attribute}")

    def test_the_canvas_mode_is_initialised(self):
        self.assertEqual(self.tab.canvas_mode.get(), "select")

    def test_toolbar_widgets_are_exposed_on_the_tab(self):
        for attribute in ("mod_combo", "tree_combo", "mod_label", "tag_var",
                          "find_var", "layout_mode", "sim_mode"):
            self.assertTrue(hasattr(self.tab, attribute), f"missing {attribute}")

    def test_inspector_widgets_are_exposed_on_the_tab(self):
        for attribute in ("detail_form", "icon_var", "cost_var", "x_var", "y_var"):
            self.assertTrue(hasattr(self.tab, attribute), f"missing {attribute}")

    def test_the_mod_dropdown_is_populated_when_a_workshop_folder_exists(self):
        """Skipped where no Workshop content is installed; where there is,
        an empty dropdown means the refresh never ran."""
        from app import game_paths, mod_loader as ml
        found = ml.list_workshop_mods(game_paths.find_workshop())
        if not found:
            self.skipTest("no Workshop mods installed on this machine")
        self.assertEqual(len(self.tab.mod_combo["values"]), len(found))
        self.assertEqual(len(self.tab._workshop_mods), len(found))

    def test_the_tree_picker_filter_is_callable(self):
        self.assertEqual(self.tab._visible_tree_labels(), [])

    def test_mod_only_tick_exists_on_the_toolbar(self):
        self.assertTrue(hasattr(self.tab.toolbar, "mod_only_var"))


@unittest.skipUnless(HAVE_TK, "no display")
class ModOnlyFilterTest(unittest.TestCase):
    """Ticking 'Mod only' on a real mod collapsed the list to one entry.

    Once a tree is picked the combobox holds that entry's whole label, and
    the filter was reading it back as if the user had typed it as a search
    term - so it matched exactly the one item already selected.
    """

    LABELS = ["[MOD] GER | german_focus - germany.txt (700 focuses)",
              "[MOD] AST | australian_focus - australia.txt (115 focuses)",
              "[vanilla] SOV | soviet_focus - soviet.txt (80 focuses)"]

    def setUp(self):
        from app import theme
        from app.focus_tree_toolbar import FocusTreeToolbar
        self.win = tk.Toplevel(tk_support.root())
        self.win.withdraw()
        theme.apply(self.win)
        noop = lambda *a, **k: None
        self.toolbar = FocusTreeToolbar(
            self.win, tree_labels=lambda: list(self.LABELS),
            on_refresh_mods=noop, on_load_mod=noop, on_browse_mod=noop, on_load_tree=noop,
            on_leaders=noop, on_find_next=noop, on_find_changed=noop, on_sim_toggle=noop,
            on_reset_progress=noop, on_layout_changed=noop, on_zoom=noop,
            on_mode_changed=noop, on_help=noop)
        self.toolbar.tree_combo["values"] = self.LABELS
        self.addCleanup(self.win.destroy)

    def test_a_selected_entry_is_not_treated_as_a_search_term(self):
        self.toolbar.tree_combo.current(0)          # user picked a tree
        self.toolbar._on_mod_only_changed()
        self.assertEqual(len(self.toolbar.tree_combo["values"]), len(self.LABELS))

    def test_typed_text_still_narrows_the_list(self):
        self.toolbar.tree_combo.set("germany")      # not an entry, so a search
        self.assertEqual(self.toolbar.tree_combo.current(), -1)
        self.toolbar._on_mod_only_changed()
        self.assertEqual(len(self.toolbar.tree_combo["values"]), 1)

    def test_an_empty_box_shows_everything(self):
        self.toolbar.tree_combo.set("")
        self.toolbar._on_mod_only_changed()
        self.assertEqual(len(self.toolbar.tree_combo["values"]), len(self.LABELS))


if __name__ == "__main__":
    unittest.main()
