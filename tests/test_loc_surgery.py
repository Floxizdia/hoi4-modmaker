import os
import tempfile
import unittest

from app import loc_surgery


class SetKeyTests(unittest.TestCase):
    def _write_loc(self, root, name, content):
        loc_dir = os.path.join(root, "localisation", "english")
        os.makedirs(loc_dir, exist_ok=True)
        path = os.path.join(loc_dir, name)
        with open(path, "w", encoding="utf-8-sig") as handle:
            handle.write(content)
        return path

    def _read(self, path):
        with open(path, "r", encoding="utf-8-sig") as handle:
            return handle.read()

    def test_edits_existing_key_in_place(self):
        with tempfile.TemporaryDirectory() as root:
            path = self._write_loc(root, "test_l_english.yml", (
                'l_english:\n'
                ' GER_focus_x:0 "Old Name"\n'
            ))
            written = loc_surgery.set_key(root, "GER_focus_x", "New Name")
            self.assertEqual(written, path)
            self.assertIn('GER_focus_x:0 "New Name"', self._read(path))

    def test_trailing_comment_does_not_hide_the_existing_key(self):
        """Same bug class as the mod_loader parser: a key line ending in a
        '# comment' (a common HOI4/vanilla convention) wasn't matched by
        the closing-quote-at-end-of-line regex, so editing an existing key
        silently fell through to the fallback path and appended a
        duplicate/shadowed entry instead of updating the real one."""
        with tempfile.TemporaryDirectory() as root:
            path = self._write_loc(root, "test_l_english.yml", (
                'l_english:\n'
                ' GER_focus_x:0 "Old Name" # TODO: revisit wording\n'
            ))
            written = loc_surgery.set_key(root, "GER_focus_x", "New Name")

            self.assertEqual(written, path)
            text = self._read(path)
            self.assertIn('GER_focus_x:0 "New Name" # TODO: revisit wording', text)
            # No fallback file should have been created - the real key was found.
            fallback = os.path.join(root, "localisation", "english",
                                     "zzz_focus_overrides_l_english.yml")
            self.assertFalse(os.path.isfile(fallback))

    def test_appends_to_fallback_when_key_is_undefined(self):
        with tempfile.TemporaryDirectory() as root:
            written = loc_surgery.set_key(root, "GER_focus_new", "Brand New")
            self.assertTrue(written.endswith("zzz_focus_overrides_l_english.yml"))
            self.assertIn('GER_focus_new:0 "Brand New"', self._read(written))


if __name__ == "__main__":
    unittest.main()
