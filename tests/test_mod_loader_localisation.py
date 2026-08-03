import os
import tempfile
import unittest

from app import mod_loader as ml


class LoadLocalisationTests(unittest.TestCase):
    def _write_loc(self, root, content):
        loc_dir = os.path.join(root, "localisation", "english")
        os.makedirs(loc_dir, exist_ok=True)
        path = os.path.join(loc_dir, "test_l_english.yml")
        with open(path, "w", encoding="utf-8-sig") as handle:
            handle.write(content)
        return path

    def test_trailing_comment_does_not_hide_a_valid_key(self):
        """Reported symptom: Validate flags a focus/event as having no
        localisation even though the .yml clearly defines the key. Root
        cause: HOI4's own convention of a trailing '# note' comment on a
        loc line (vanilla does this too, e.g. aat_ideas_l_english.yml)
        wasn't tolerated by the line regex, which required the closing
        quote to be the last non-whitespace character on the line."""
        with tempfile.TemporaryDirectory() as root:
            self._write_loc(root, (
                'l_english:\n'
                ' GER_focus_x:0 "Focus Name" # TODO: revisit wording\n'
                ' GER_focus_y:0 "Other Name"\n'
            ))
            loc = ml.load_localisation(root)

        self.assertEqual(loc.get("GER_focus_x"), "Focus Name")
        self.assertEqual(loc.get("GER_focus_y"), "Other Name")

    def test_comment_only_line_is_not_mistaken_for_a_key(self):
        with tempfile.TemporaryDirectory() as root:
            self._write_loc(root, (
                'l_english:\n'
                ' # just a comment, no key here\n'
                ' GER_focus_y:0 "Other Name"\n'
            ))
            loc = ml.load_localisation(root)

        self.assertEqual(len(loc), 1)
        self.assertEqual(loc.get("GER_focus_y"), "Other Name")

    def test_escaped_quotes_inside_text_still_parse(self):
        with tempfile.TemporaryDirectory() as root:
            self._write_loc(root, (
                'l_english:\n'
                ' GER_focus_z:0 "Text with \\"escaped\\" quotes" # note\n'
            ))
            loc = ml.load_localisation(root)

        self.assertEqual(loc.get("GER_focus_z"), 'Text with "escaped" quotes')


if __name__ == "__main__":
    unittest.main()
