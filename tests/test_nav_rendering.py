"""The navigation rail must paint itself without waiting for a <Configure>.

A Linux/Wayland user reported the rail showing nothing while its entries
were still clickable. Painting was bound only to <Configure>: the row table
that hit-testing reads is built during painting, so wherever that event
arrived once and never again the clicks kept working over a blank rail.
"""

import unittest

import tk_support
from tk_support import HAVE_TK

if HAVE_TK:
    import tkinter as tk


SECTIONS = [("VISUAL", [("map", "Map"), ("focus", "Focus Tree")]),
            ("TOOLS", [("code", "Code"), ("validate", "Validate")])]


@unittest.skipUnless(HAVE_TK, "no display")
class RailPaintTest(unittest.TestCase):
    def setUp(self):
        import os
        import tempfile
        from app import nav, theme
        from app.nav import NavRail
        # the rail remembers folded sections in the user's own config; left
        # pointing at it, these tests pass or fail depending on what the
        # person running them last collapsed in the real app
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        real_file = nav.COLLAPSE_FILE
        nav.COLLAPSE_FILE = os.path.join(self.tmp.name, "nav_sections.json")
        self.addCleanup(lambda: setattr(nav, "COLLAPSE_FILE", real_file))

        self.win = tk.Toplevel(tk_support.root())
        self.win.withdraw()
        theme.apply(self.win)
        self.clicked = []
        self.rail = NavRail(self.win, SECTIONS, on_select=self.clicked.append)
        self.rail.pack(side="left", fill="y")
        self.addCleanup(self.win.destroy)

    def settle(self):
        self.win.update_idletasks()
        self.win.update()

    def test_it_paints_without_a_configure_event(self):
        self.settle()
        self.assertGreater(len(self.rail.find_all()), 0)

    def test_every_label_is_drawn(self):
        self.settle()
        drawn = {self.rail.itemcget(i, "text") for i in self.rail.find_all()
                 if self.rail.type(i) == "text"}
        for _title, entries in SECTIONS:
            for _key, label in entries:
                self.assertIn(label, drawn)

    def test_section_titles_are_drawn(self):
        self.settle()
        drawn = {self.rail.itemcget(i, "text") for i in self.rail.find_all()
                 if self.rail.type(i) == "text"}
        self.assertIn("VISUAL", drawn)

    def test_rows_are_registered_for_hit_testing(self):
        self.settle()
        self.assertEqual(set(self.rail._rows),
                         {key for _t, entries in SECTIONS for key, _l in entries})

    def test_a_click_lands_on_the_row_that_was_drawn(self):
        """What was visible and what is clickable have to agree."""
        self.settle()
        for key, (top, bottom) in self.rail._rows.items():
            self.assertEqual(self.rail._key_at((top + bottom) // 2), key)

    def test_selecting_repaints(self):
        self.settle()
        self.rail.select("code")
        self.settle()
        self.assertEqual(self.rail.current, "code")
        self.assertGreater(len(self.rail.find_all()), 0)


@unittest.skipUnless(HAVE_TK, "no display")
class HeaderPaintTest(unittest.TestCase):
    def test_header_paints_without_a_configure_event(self):
        from app import theme
        from app.nav import HeaderBar
        win = tk.Toplevel(tk_support.root())
        win.withdraw()
        theme.apply(win)
        header = HeaderBar(win, on_home=lambda: None)
        header.pack(fill="x")
        win.update_idletasks()
        win.update()
        self.assertGreater(len(header.find_all()), 0)
        win.destroy()


class GlyphCoverageTest(unittest.TestCase):
    """Every nav entry needs an icon; draw() returns nothing for a key it
    doesn't know, which is a silently blank slot rather than an error."""

    def test_every_nav_key_has_a_glyph(self):
        import main
        from app import glyphs
        missing = [key for _section, entries in main.SECTIONS
                   for key, _label, _cls in entries
                   if key not in glyphs.GLYPHS]
        self.assertEqual(missing, [])


if __name__ == "__main__":
    unittest.main()
