import os
import tempfile
import unittest

from app import tech_graph


TECH_FILE = """technologies = {

\t@1936 = 2
\t@1938 = 4

\tinfantry_weapons1 = {
\t\tresearch_cost = 1.5
\t\tstart_year = 1936
\t\tpath = {
\t\t\tleads_to_tech = infantry_weapons2
\t\t}
\t\tfolder = {
\t\t\tname = infantry_folder
\t\t\tposition = { x = 0 y = @1936 }
\t\t}
\t}

\tinfantry_weapons2 = {
\t\tresearch_cost = 2
\t\tfolder = {
\t\t\tname = infantry_folder
\t\t\tposition = { x = -1 y = @1938 }
\t\t}
\t}

\thidden_unlock = {
\t\tresearch_cost = 1
\t}
}
"""


def _write_mod(root):
    tech_dir = os.path.join(root, "common", "technologies")
    os.makedirs(tech_dir, exist_ok=True)
    with open(os.path.join(tech_dir, "infantry.txt"), "w", encoding="utf-8") as handle:
        handle.write(TECH_FILE)


class ScriptedPositionTests(unittest.TestCase):
    def test_scripted_year_variable_resolves_to_a_real_row(self):
        """`position = { x = 0 y = @1936 }` is how vanilla places every
        year-gated tech. Reading @1936 as a literal made float() fail and
        every row collapse to y=0, which stacked a whole folder onto one
        cell and made the view fall back to a synthetic layout instead of
        the one the game itself draws."""
        with tempfile.TemporaryDirectory() as root:
            _write_mod(root)
            graph = tech_graph.build_graph(root)

        self.assertEqual(graph["infantry_weapons1"]["y"], 2.0)
        self.assertEqual(graph["infantry_weapons2"]["y"], 4.0)
        self.assertEqual(graph["infantry_weapons2"]["x"], -1.0)

    def test_tech_without_a_folder_block_is_flagged_unpositioned(self):
        with tempfile.TemporaryDirectory() as root:
            _write_mod(root)
            graph = tech_graph.build_graph(root)

        self.assertTrue(graph["infantry_weapons1"]["positioned"])
        self.assertFalse(graph["hidden_unlock"]["positioned"])
        self.assertEqual(graph["hidden_unlock"]["folder"], "")

    def test_leads_to_becomes_a_reverse_requirement(self):
        with tempfile.TemporaryDirectory() as root:
            _write_mod(root)
            graph = tech_graph.build_graph(root)

        self.assertIn("infantry_weapons1", graph["infantry_weapons2"]["requires"])


class ResolveIconTests(unittest.TestCase):
    def _texture(self, root, rel):
        path = os.path.join(root, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as handle:
            handle.write(b"\x00")
        return os.path.normpath(path)

    def test_sprite_index_wins_over_the_filename_guess(self):
        """The game reaches tech art through a sprite name that can point at
        any filename (GFX_early_ship_hull_light_medium -> early_destroyer.dds),
        so guessing technologies/<id>.dds misses ~40% of base-game techs."""
        with tempfile.TemporaryDirectory() as root:
            texture = self._texture(root, os.path.join("gfx", "custom", "early_destroyer.dds"))
            index = {"GFX_early_ship_hull_light_medium": texture}
            found = tech_graph.resolve_icon(root, "early_ship_hull_light", index)

        self.assertEqual(found, texture)

    def test_country_variant_is_preferred_when_the_tag_has_its_own_art(self):
        with tempfile.TemporaryDirectory() as root:
            generic = self._texture(root, os.path.join("gfx", "a", "generic.dds"))
            jap = self._texture(root, os.path.join("gfx", "a", "jap.dds"))
            index = {"GFX_cv_fighter1_medium": generic, "GFX_JAP_cv_fighter1_medium": jap}

            self.assertEqual(tech_graph.resolve_icon(root, "cv_fighter1", index, "JAP"), jap)
            self.assertEqual(tech_graph.resolve_icon(root, "cv_fighter1", index, "GER"), generic)

    def test_falls_back_to_the_filename_convention_for_loose_mod_art(self):
        with tempfile.TemporaryDirectory() as root:
            texture = self._texture(
                root, os.path.join("gfx", "interface", "technologies", "my_tech.dds"))
            found = tech_graph.resolve_icon(root, "my_tech", {})

        self.assertEqual(found, texture)


if __name__ == "__main__":
    unittest.main()
