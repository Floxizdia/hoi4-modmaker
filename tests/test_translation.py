import os
import tempfile
import unittest

from app import loc_coverage, translation


class TranslationTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.mod = self.tmp.name

    def write_lang(self, lang, entries, filename=None):
        folder = os.path.join(self.mod, "localisation", lang)
        os.makedirs(folder, exist_ok=True)
        path = os.path.join(folder, filename or f"test_l_{lang}.yml")
        lines = [f"l_{lang}:"] + [f' {k}:0 "{v}"' for k, v in entries.items()]
        with open(path, "w", encoding="utf-8-sig") as handle:
            handle.write("\n".join(lines) + "\n")
        return path


class UntranslatedTest(unittest.TestCase):
    """Loc Coverage can bulk-copy English text in to stop raw keys showing.
    After that every key exists, so 'missing' stops being a useful measure -
    a placeholder is text identical to the English."""

    def test_empty_is_untranslated(self):
        self.assertTrue(translation.is_untranslated("Hello", ""))

    def test_whitespace_only_is_untranslated(self):
        self.assertTrue(translation.is_untranslated("Hello", "   "))

    def test_a_copy_of_the_english_is_untranslated(self):
        self.assertTrue(translation.is_untranslated("Build Factories", "Build Factories"))

    def test_real_translation_counts(self):
        self.assertFalse(translation.is_untranslated("Build Factories", "Fabrikalar kur"))


class LoadPairsTest(TranslationTestCase):
    def test_pairs_cover_every_english_key(self):
        self.write_lang("english", {"a": "One", "b": "Two"})
        self.write_lang("french", {"a": "Un"})
        pairs = translation.load_pairs(self.mod, "french")
        self.assertEqual([(k, e, c) for k, e, c in pairs],
                         [("a", "One", "Un"), ("b", "Two", "")])

    def test_progress_ignores_placeholders(self):
        self.write_lang("english", {"a": "One", "b": "Two", "c": "Three"})
        self.write_lang("french", {"a": "Un", "b": "Two"})
        self.assertEqual(translation.progress(translation.load_pairs(self.mod, "french")),
                         (1, 3))

    def test_no_english_gives_nothing(self):
        self.assertEqual(translation.load_pairs(self.mod, "french"), [])


class SaveTest(TranslationTestCase):
    def test_writes_the_entries(self):
        self.write_lang("english", {"a": "One"})
        path = translation.save(self.mod, "My Mod", "french", {"a": "Un"})
        self.assertEqual(loc_coverage.scan_language(self.mod, "french")["a"], "Un")
        self.assertTrue(os.path.isfile(path))

    def test_filename_sorts_after_other_files(self):
        """A language folder loads alphabetically and the last definition of
        a key wins, so a translation file that sorts early is overwritten by
        the very placeholder it was meant to replace."""
        self.write_lang("english", {"a": "One"})
        self.write_lang("french", {"a": "One"}, filename="t_l_french.yml")
        translation.save(self.mod, "My Mod", "french", {"a": "Un"})

        names = sorted(os.listdir(os.path.join(self.mod, "localisation", "french")))
        self.assertEqual(names[-1], os.path.basename(
            translation.target_path(self.mod, "My Mod", "french")))
        self.assertEqual(loc_coverage.scan_language(self.mod, "french")["a"], "Un")

    def test_a_second_save_keeps_the_first(self):
        self.write_lang("english", {"a": "One", "b": "Two"})
        translation.save(self.mod, "My Mod", "french", {"a": "Un"})
        translation.save(self.mod, "My Mod", "french", {"b": "Deux"})
        found = loc_coverage.scan_language(self.mod, "french")
        self.assertEqual(found["a"], "Un")
        self.assertEqual(found["b"], "Deux")

    def test_blank_entries_are_not_written(self):
        self.write_lang("english", {"a": "One"})
        translation.save(self.mod, "My Mod", "french", {"a": "   "})
        self.assertNotIn("a", loc_coverage.scan_language(self.mod, "french"))

    def test_quotes_are_escaped(self):
        self.write_lang("english", {"a": "One"})
        translation.save(self.mod, "My Mod", "french", {"a": 'Le "grand" jour'})
        self.assertEqual(loc_coverage.scan_language(self.mod, "french")["a"],
                         'Le "grand" jour')

    def test_file_has_the_language_header(self):
        self.write_lang("english", {"a": "One"})
        path = translation.save(self.mod, "My Mod", "french", {"a": "Un"})
        with open(path, encoding="utf-8-sig") as handle:
            self.assertTrue(handle.read().startswith("l_french:"))

    def test_file_carries_a_bom(self):
        """HOI4 refuses a localisation file without one."""
        self.write_lang("english", {"a": "One"})
        path = translation.save(self.mod, "My Mod", "french", {"a": "Un"})
        with open(path, "rb") as handle:
            self.assertTrue(handle.read(3) == b"\xef\xbb\xbf")


class LanguagesTest(unittest.TestCase):
    def test_english_is_not_a_target(self):
        self.assertNotIn("english", translation.languages())

    def test_there_are_targets(self):
        self.assertTrue(translation.languages())


if __name__ == "__main__":
    unittest.main()
