"""The Guide window has to fit the screen it is opened on.

The guides were expanded until the longest run past 850px tall. That fits a
1080p desktop and is cut off on a 768px laptop - with the window fixed-size
and unscrollable, the Close button went with it.
"""

import unittest

import tk_support
from tk_support import HAVE_TK

if HAVE_TK:
    import tkinter as tk

from app import help_content


@unittest.skipUnless(HAVE_TK, "no display")
class HelpDialogFitTest(unittest.TestCase):
    def setUp(self):
        from app import theme, ui_kit
        self.ui_kit = ui_kit
        self.root = tk_support.root()
        theme.apply(self.root)

    def open(self, entry, screen_height=None):
        dialog = self.ui_kit.HelpDialog(self.root, entry)
        if screen_height is not None:
            dialog.winfo_screenheight = lambda: screen_height
        dialog.update()
        dialog._fit()
        self.addCleanup(dialog.destroy)
        dialog.grab_release()
        return dialog

    def tallest_entry(self):
        return max(help_content.HELP.values(),
                   key=lambda e: len(e.get("what", "")) + sum(len(s) for s in e.get("how", [])))

    def test_a_short_guide_is_shown_whole(self):
        entry = min(help_content.HELP.values(),
                    key=lambda e: sum(len(s) for s in e.get("how", [])))
        dialog = self.open(entry)
        self.assertEqual(int(dialog._canvas.cget("height")), dialog._canvas.bbox("all")[3])

    def test_a_long_guide_is_capped_to_the_screen(self):
        dialog = self.open(self.tallest_entry(), screen_height=768)
        self.assertLessEqual(int(dialog._canvas.cget("height")), 768 - 120)

    def test_a_capped_guide_can_still_be_scrolled_to_the_end(self):
        dialog = self.open(self.tallest_entry(), screen_height=768)
        content_height = dialog._canvas.bbox("all")[3]
        self.assertGreater(content_height, int(dialog._canvas.cget("height")),
                           "this entry should be taller than the capped window")
        region = [int(v) for v in str(dialog._canvas.cget("scrollregion")).split()]
        self.assertEqual(region[3], content_height,
                         "scrollregion must cover the whole content or the end is unreachable")

    def test_every_guide_opens_without_error(self):
        for key, entry in help_content.HELP.items():
            with self.subTest(key=key):
                dialog = self.open(entry)
                self.assertTrue(dialog._canvas.bbox("all"))


if __name__ == "__main__":
    unittest.main()
