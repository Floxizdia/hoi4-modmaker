"""The layer that makes 46 screens navigable, and the shortcut mapping it
must not disturb."""

import os
import tempfile
import unittest

import main
from app import guides

import tk_support
from tk_support import HAVE_TK

if HAVE_TK:
    import tkinter as tk


REAL_KEYS = {key for _section, entries in main.SECTIONS for key, _label, _cls in entries}


class GuideDataTest(unittest.TestCase):
    def test_every_step_points_at_a_real_screen(self):
        """The guides are the one place that names screens by key from
        outside main.py, so a renamed screen has to fail here loudly rather
        than produce a button that does nothing."""
        self.assertEqual(guides.screen_keys() - REAL_KEYS, set())

    def test_every_guide_has_steps(self):
        for title, _why, steps in guides.GUIDES:
            self.assertTrue(steps, f"{title} has no steps")

    def test_every_guide_explains_itself(self):
        for title, why, _steps in guides.GUIDES:
            self.assertTrue(why.strip(), f"{title} has no explanation")

    def test_steps_carry_a_hint(self):
        for title, _why, steps in guides.GUIDES:
            for text, _key, hint in steps:
                self.assertTrue(hint.strip(), f"{title}: '{text}' has no hint")

    def test_titles_are_unique(self):
        """Progress is stored per guide title, so a duplicate would make two
        guides share their ticks."""
        titles = [title for title, _why, _steps in guides.GUIDES]
        self.assertEqual(len(titles), len(set(titles)))


class ShortcutTest(unittest.TestCase):
    """Ctrl+1..9 used to be the first nine entries of SECTIONS, so adding a
    screen silently remapped every one of them."""

    def test_shortcuts_point_at_real_screens(self):
        self.assertEqual(set(main.SHORTCUT_KEYS) - REAL_KEYS, set())

    def test_shortcuts_are_not_derived_from_section_order(self):
        flat = [key for _section, entries in main.SECTIONS for key, _l, _c in entries]
        self.assertNotEqual(main.SHORTCUT_KEYS[:9], flat[:9],
                            "adding a screen at the top would move every shortcut again")

    def test_no_duplicate_shortcuts(self):
        self.assertEqual(len(main.SHORTCUT_KEYS), len(set(main.SHORTCUT_KEYS)))


@unittest.skipUnless(HAVE_TK, "no display")
class CollapsibleRailTest(unittest.TestCase):
    SECTIONS = [("VISUAL", [("map", "Map"), ("focus", "Focus Tree")]),
                ("TOOLS", [("code", "Code"), ("validate", "Validate")])]

    def setUp(self):
        from app import nav, theme
        self.nav = nav
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self._real_file = nav.COLLAPSE_FILE
        nav.COLLAPSE_FILE = os.path.join(self.tmp.name, "nav_sections.json")
        self.addCleanup(lambda: setattr(nav, "COLLAPSE_FILE", self._real_file))

        self.win = tk.Toplevel(tk_support.root())
        self.win.withdraw()
        theme.apply(self.win)
        self.picked = []
        self.rail = nav.NavRail(self.win, self.SECTIONS, on_select=self.picked.append)
        self.rail.pack(side="left", fill="y")
        self.win.update()
        self.addCleanup(self.win.destroy)

    def test_everything_is_listed_to_begin_with(self):
        self.assertEqual(set(self.rail._rows), {"map", "focus", "code", "validate"})

    def test_folding_hides_a_section(self):
        self.rail.toggle_section("TOOLS")
        self.assertNotIn("code", self.rail._rows)
        self.assertIn("map", self.rail._rows)

    def test_the_open_screen_stays_reachable_while_folded(self):
        """Folding the section you are in would otherwise strand you."""
        self.rail.select("code")
        self.rail.toggle_section("TOOLS")
        self.assertIn("code", self.rail._rows)
        self.assertNotIn("validate", self.rail._rows)

    def test_folding_is_remembered(self):
        self.rail.toggle_section("TOOLS")
        second = self.nav.NavRail(self.win, self.SECTIONS, on_select=lambda k: None)
        self.assertIn("TOOLS", second.collapsed)

    def test_unfolding_brings_it_back(self):
        self.rail.toggle_section("TOOLS")
        self.rail.toggle_section("TOOLS")
        self.assertIn("code", self.rail._rows)

    def test_clicking_a_header_folds_instead_of_selecting(self):
        import types
        top, bottom = self.rail._headers["TOOLS"]
        self.rail._on_click(types.SimpleNamespace(x=10, y=(top + bottom) // 2))
        self.assertIn("TOOLS", self.rail.collapsed)
        self.assertEqual(self.picked, [])

    def test_clicking_an_item_still_selects(self):
        import types
        top, bottom = self.rail._rows["code"]
        self.rail._on_click(types.SimpleNamespace(x=60, y=(top + bottom) // 2))
        self.assertEqual(self.picked, ["code"])

    def test_a_corrupt_settings_file_is_ignored(self):
        with open(self.nav.COLLAPSE_FILE, "w", encoding="utf-8") as handle:
            handle.write("not json")
        self.assertEqual(self.nav._load_collapsed(), [])


if __name__ == "__main__":
    unittest.main()
