import os
import tempfile
import unittest
from unittest import mock

from app import scripted


class ScriptedTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.mod = os.path.join(self.tmp.name, "mod")
        # safe_io asks before replacing a file; the prompt has no place in
        # a test run, and "yes" is what the flow under test assumes
        patcher = mock.patch("app.safe_io.messagebox.askyesno", return_value=True)
        patcher.start()
        self.addCleanup(patcher.stop)

    def read(self, kind):
        with open(scripted.target_file(self.mod, kind), encoding="utf-8") as handle:
            return handle.read()


class FormatTest(unittest.TestCase):
    def test_effect_body_is_indented_inside_the_block(self):
        text = scripted.format_definition("effect", "give_pp", "add_political_power = 50")
        self.assertEqual(text, "give_pp = {\n\tadd_political_power = 50\n}\n")

    def test_multi_line_body(self):
        text = scripted.format_definition("trigger", "at_war", "has_war = yes\nhas_stability < 0.4")
        self.assertIn("\thas_war = yes\n\thas_stability < 0.4", text)

    def test_modifier_carries_its_own_fields(self):
        text = scripted.format_definition(
            "modifier", "my_mod", "political_power_gain = 0.2",
            icon="GFX_idea_unknown", enable="always = yes")
        self.assertIn('icon = "GFX_idea_unknown"', text)
        self.assertIn("enable = {\n\t\talways = yes\n\t}", text)
        self.assertIn("\tpolitical_power_gain = 0.2", text)

    def test_modifier_without_optional_fields(self):
        text = scripted.format_definition("modifier", "m", "max_fuel = 100")
        self.assertNotIn("icon", text)
        self.assertNotIn("enable", text)

    def test_braces_balance(self):
        text = scripted.format_definition(
            "modifier", "m", "max_fuel = 100", enable="always = yes",
            remove_trigger="has_war = no")
        self.assertEqual(text.count("{"), text.count("}"))


class CreateTest(ScriptedTestCase):
    def test_writes_a_definition(self):
        scripted.create(self.mod, "trigger", "my_check", "has_war = yes")
        self.assertIn("my_check = {", self.read("trigger"))

    def test_a_second_definition_appends(self):
        """Replacing the file would throw away what was written a minute ago."""
        scripted.create(self.mod, "trigger", "first", "has_war = yes")
        scripted.create(self.mod, "trigger", "second", "has_war = no")
        text = self.read("trigger")
        self.assertIn("first = {", text)
        self.assertIn("second = {", text)

    def test_each_kind_gets_its_own_folder(self):
        scripted.create(self.mod, "effect", "e", "add_political_power = 1")
        scripted.create(self.mod, "trigger", "t", "has_war = yes")
        scripted.create(self.mod, "modifier", "m", "max_fuel = 10")
        self.assertTrue(os.path.isfile(
            os.path.join(self.mod, "common", "scripted_effects",
                         "zzz_custom_scripted_effects.txt")))
        self.assertTrue(os.path.isfile(
            os.path.join(self.mod, "common", "scripted_triggers",
                         "zzz_custom_scripted_triggers.txt")))
        self.assertTrue(os.path.isfile(
            os.path.join(self.mod, "common", "dynamic_modifiers",
                         "zzz_custom_dynamic_modifiers.txt")))

    def test_written_definitions_are_read_back(self):
        scripted.create(self.mod, "effect", "give_pp", "add_political_power = 50")
        defined = scripted.list_defined(self.mod, "effect")
        self.assertIn("give_pp", defined)
        self.assertIn(("mod", "zzz_custom_scripted_effects.txt"), defined["give_pp"])

    def test_read_definition_returns_the_body(self):
        scripted.create(self.mod, "trigger", "my_check", "has_war = yes")
        self.assertIn("has_war = yes", scripted.read_definition(self.mod, "trigger", "my_check"))

    def test_read_definition_missing_is_empty(self):
        self.assertEqual(scripted.read_definition(self.mod, "trigger", "nope"), "")


class OverrideTest(unittest.TestCase):
    """These files are last-one-loaded-wins, so shadowing a base-game name
    silently replaces vanilla behaviour - it has to be noticed."""

    def test_vanilla_name_is_flagged(self):
        defined = {"is_major": [("vanilla", "00_scripted_triggers.txt")]}
        self.assertTrue(scripted.overrides_vanilla(defined, "is_major"))

    def test_mod_only_name_is_not(self):
        defined = {"mine": [("mod", "zzz_custom_scripted_triggers.txt")]}
        self.assertFalse(scripted.overrides_vanilla(defined, "mine"))

    def test_unknown_name_is_not(self):
        self.assertFalse(scripted.overrides_vanilla({}, "brand_new"))


if __name__ == "__main__":
    unittest.main()
