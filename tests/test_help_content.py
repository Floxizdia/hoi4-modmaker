"""Every screen's Guide has to actually explain the screen.

An audit found a third of the entries were two lines with no example while
the newest ones were five steps plus a worked example. These tests hold the
floor so a screen added in a hurry can't ship with a stub.
"""

import unittest

import main
from app import help_content

HELP = help_content.HELP
SCREEN_KEYS = {key for _section, entries in main.SECTIONS for key, _label, _cls in entries}

#: screens that browse or report rather than write script - a snippet of
#: HOI4 script would be an invention, so they are exempt from needing one
NO_EXAMPLE_NEEDED = {"open_mod", "map", "settings", "idea_gallery", "traits", "units", "code"}


class CoverageTest(unittest.TestCase):
    def test_every_screen_has_a_guide(self):
        self.assertEqual(SCREEN_KEYS - set(HELP), set())

    def test_no_guide_points_at_a_screen_that_is_gone(self):
        """A leftover entry is dead weight nobody will ever open."""
        self.assertEqual(set(HELP) - SCREEN_KEYS, set())


class QualityTest(unittest.TestCase):
    def test_every_entry_has_a_title(self):
        for key, entry in HELP.items():
            self.assertTrue(entry.get("title", "").strip(), key)

    def test_every_entry_explains_what_it_does(self):
        for key, entry in HELP.items():
            self.assertGreater(len(entry.get("what", "")), 80,
                               f"{key}: 'what' is too thin to be useful")

    def test_every_entry_has_at_least_three_steps(self):
        for key, entry in HELP.items():
            self.assertGreaterEqual(len(entry.get("how", [])), 3,
                                    f"{key}: fewer than three steps")

    def test_steps_are_sentences_not_labels(self):
        for key, entry in HELP.items():
            for step in entry.get("how", []):
                self.assertGreater(len(step), 40, f"{key}: step too short to say anything")

    def test_script_screens_carry_a_worked_example(self):
        missing = [key for key, entry in HELP.items()
                   if not entry.get("example") and key not in NO_EXAMPLE_NEEDED]
        self.assertEqual(missing, [], "these screens write script but show no example")

    def test_the_exempt_list_only_names_real_screens(self):
        self.assertEqual(NO_EXAMPLE_NEEDED - SCREEN_KEYS, set())


if __name__ == "__main__":
    unittest.main()
