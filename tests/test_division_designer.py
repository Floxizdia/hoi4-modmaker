import os
import tempfile
import unittest

from app import division_designer as dd


CATALOGUE = {
    "infantry": {"combat_width": 2.0, "manpower": 1000.0, "max_strength": 25.0,
                 "max_organisation": 60.0, "support": False},
    "artillery_brigade": {"combat_width": 3.0, "manpower": 500.0, "max_strength": 5.0,
                          "max_organisation": 10.0, "support": False},
    "engineer": {"combat_width": 0.0, "manpower": 300.0, "max_strength": 2.0,
                 "max_organisation": 20.0, "soft_attack": -0.5, "support": True},
}


def block(width, height, name="infantry"):
    return {(x, y): name for x in range(width) for y in range(height)}


class StatsTest(unittest.TestCase):
    def test_combat_width_is_the_sum_of_the_regiments(self):
        totals = dd.division_stats(block(3, 3), [], CATALOGUE)
        self.assertEqual(totals["combat_width"], 18.0)

    def test_support_companies_add_no_combat_width(self):
        """A 40-width template can still carry five support companies."""
        with_support = dd.division_stats(block(3, 3), ["engineer"], CATALOGUE)
        without = dd.division_stats(block(3, 3), [], CATALOGUE)
        self.assertEqual(with_support["combat_width"], without["combat_width"])

    def test_manpower_counts_support_as_well(self):
        totals = dd.division_stats(block(3, 3), ["engineer"], CATALOGUE)
        self.assertEqual(totals["manpower"], 9000.0 + 300.0)

    def test_organisation_is_averaged_not_summed(self):
        """Nine 60-org battalions make a 60-org division, not a 540-org one."""
        totals = dd.division_stats(block(3, 3), [], CATALOGUE)
        self.assertEqual(totals["max_organisation"], 60.0)

    def test_organisation_average_includes_support(self):
        totals = dd.division_stats(block(1, 1), ["engineer"], CATALOGUE)
        self.assertEqual(totals["max_organisation"], 40.0)

    def test_attack_is_not_reported(self):
        """Support values like soft_attack = -0.5 are multipliers; adding
        them to a regiment's number produced negative division attack."""
        totals = dd.division_stats(block(3, 3), ["engineer"], CATALOGUE)
        self.assertNotIn("soft_attack", totals)

    def test_empty_template_has_no_totals(self):
        self.assertEqual(dd.division_stats({}, [], CATALOGUE), {})


class ProblemsTest(unittest.TestCase):
    def test_empty_division_is_flagged(self):
        self.assertTrue(dd.problems({}, []))

    def test_a_gap_in_a_column_is_flagged(self):
        found = dd.problems({(0, 0): "infantry", (0, 2): "infantry"}, [])
        self.assertTrue(any("gap" in msg for msg in found))

    def test_a_full_column_is_fine(self):
        self.assertEqual(dd.problems(block(1, 3), [], CATALOGUE), [])

    def test_too_many_support_companies(self):
        found = dd.problems(block(1, 1), ["engineer"] * 6, CATALOGUE)
        self.assertTrue(any("support companies" in msg for msg in found))

    def test_support_company_in_the_regiment_grid(self):
        found = dd.problems({(0, 0): "engineer"}, [], CATALOGUE)
        self.assertTrue(any("belongs in the support" in msg for msg in found))

    def test_line_battalion_in_a_support_slot(self):
        found = dd.problems(block(1, 1), ["infantry"], CATALOGUE)
        self.assertTrue(any("not a support company" in msg for msg in found))

    def test_unknown_battalion_name(self):
        found = dd.problems({(0, 0): "made_up_unit"}, [], CATALOGUE)
        self.assertTrue(any("made_up_unit" in msg for msg in found))


class FormatTest(unittest.TestCase):
    def test_coordinates_match_the_grid(self):
        text = dd.format_template("Test", {(0, 0): "infantry", (1, 2): "artillery_brigade"}, [])
        self.assertIn("infantry = { x = 0 y = 0 }", text)
        self.assertIn("artillery_brigade = { x = 1 y = 2 }", text)

    def test_name_is_quoted(self):
        self.assertIn('name = "My Division"',
                      dd.format_template("My Division", block(1, 1), []))

    def test_support_block_only_when_there_is_support(self):
        self.assertNotIn("support = {", dd.format_template("T", block(1, 1), []))
        self.assertIn("support = {", dd.format_template("T", block(1, 1), ["engineer"]))

    def test_support_slots_are_numbered_down_one_column(self):
        text = dd.format_template("T", block(1, 1), ["engineer", "engineer"])
        self.assertIn("engineer = { x = 0 y = 0 }", text)
        self.assertIn("engineer = { x = 0 y = 1 }", text)

    def test_braces_balance(self):
        text = dd.format_template("T", block(2, 2), ["engineer"], names_group="GER_Inf_01")
        self.assertEqual(text.count("{"), text.count("}"))

    def test_names_group_is_optional(self):
        self.assertNotIn("division_names_group", dd.format_template("T", block(1, 1), []))


class OobTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def test_template_goes_above_the_units_that_use_it(self):
        """The game reads an OOB in order, so a template defined below its
        first use is never found."""
        path = os.path.join(self.tmp.name, "GER_1936.txt")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write("units = {\n\tdivision = { name = \"1. Div\" }\n}\n")
        result = dd.append_to_oob(path, dd.format_template("T", block(1, 1), []))
        self.assertLess(result.index("division_template"), result.index("units = {"))

    def test_existing_content_is_kept(self):
        path = os.path.join(self.tmp.name, "GER_1936.txt")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write("units = { }\n")
        result = dd.append_to_oob(path, "division_template = { }\n")
        self.assertIn("units = { }", result)

    def test_missing_file_is_not_an_error(self):
        result = dd.append_to_oob(os.path.join(self.tmp.name, "nope.txt"), "x\n")
        self.assertEqual(result.strip(), "x")


if __name__ == "__main__":
    unittest.main()
