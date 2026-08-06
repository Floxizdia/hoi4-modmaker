import os
import tempfile
import unittest

from app import dlc


TECH_TAGS = """technology_folders = {
\tinfantry_folder = {
\t\tledger = army
\t}
\tarmour_folder = {
\t\tledger = army
\t\tavailable = {
\t\t\tNOT = {
\t\t\t\thas_dlc = "No Step Back"
\t\t\t}
\t\t}
\t}
\tnsb_armour_folder = {
\t\tledger = army
\t\tavailable = {
\t\t\thas_dlc = "No Step Back"
\t\t}
\t}
\tnaval_folder = {
\t\tavailable = {
\t\t\tnot = { has_dlc = "Man the Guns" }
\t\t}
\t\tledger = navy
\t}
}
"""


def _write_game(root, folders=TECH_TAGS):
    tag_dir = os.path.join(root, "common", "technology_tags")
    os.makedirs(tag_dir, exist_ok=True)
    with open(os.path.join(tag_dir, "00_technology.txt"), "w", encoding="utf-8") as handle:
        handle.write(folders)


def _write_dlc(root, folder, name, category="expansion"):
    path = os.path.join(root, "dlc", folder)
    os.makedirs(path, exist_ok=True)
    with open(os.path.join(path, folder.split("_")[0] + ".dlc"), "w", encoding="utf-8") as handle:
        handle.write(f'name = "{name}"\ncategory = "{category}"\n')
    return path


class FolderRuleTests(unittest.TestCase):
    def test_not_block_becomes_an_exclusion(self):
        """`armour_folder` is the pre-No Step Back armour tree: the game
        shows it only to players WITHOUT that expansion, and shows
        nsb_armour_folder instead to those with it. Reading both as
        available is what put the legacy tree in front of an owner of every
        expansion."""
        with tempfile.TemporaryDirectory() as root:
            _write_game(root)
            rules = dlc.folder_rules([root])

        self.assertEqual(rules["armour_folder"]["exclude"], ["No Step Back"])
        self.assertEqual(rules["armour_folder"]["require"], [])
        self.assertEqual(rules["nsb_armour_folder"]["require"], ["No Step Back"])
        self.assertEqual(rules["nsb_armour_folder"]["exclude"], [])

    def test_lowercase_not_is_handled(self):
        """Vanilla writes `not = { ... }` for naval_folder and `NOT` for
        armour_folder in the same file."""
        with tempfile.TemporaryDirectory() as root:
            _write_game(root)
            rules = dlc.folder_rules([root])

        self.assertEqual(rules["naval_folder"]["exclude"], ["Man the Guns"])

    def test_folder_without_availability_is_unconditional(self):
        with tempfile.TemporaryDirectory() as root:
            _write_game(root)
            rules = dlc.folder_rules([root])

        self.assertEqual(rules["infantry_folder"], {"require": [], "exclude": []})


class AvailabilityTests(unittest.TestCase):
    def setUp(self):
        self.rules = {
            "armour_folder": {"require": [], "exclude": ["No Step Back"]},
            "nsb_armour_folder": {"require": ["No Step Back"], "exclude": []},
            "infantry_folder": {"require": [], "exclude": []},
        }

    def test_owning_the_expansion_swaps_which_folder_shows(self):
        with_nsb = {"No Step Back"}
        self.assertFalse(dlc.folder_available(self.rules, "armour_folder", with_nsb))
        self.assertTrue(dlc.folder_available(self.rules, "nsb_armour_folder", with_nsb))

    def test_without_the_expansion_the_legacy_folder_shows(self):
        self.assertTrue(dlc.folder_available(self.rules, "armour_folder", set()))
        self.assertFalse(dlc.folder_available(self.rules, "nsb_armour_folder", set()))

    def test_ungated_and_unknown_folders_always_show(self):
        self.assertTrue(dlc.folder_available(self.rules, "infantry_folder", set()))
        self.assertTrue(dlc.folder_available(self.rules, "made_up_folder", set()))


class InstalledTests(unittest.TestCase):
    def test_reads_names_and_sorts_expansions_first(self):
        with tempfile.TemporaryDirectory() as root:
            _write_dlc(root, "dlc011_music", "German March Order", category="music")
            _write_dlc(root, "dlc034_nsb", "No Step Back")
            found = dlc.installed(root)

        self.assertEqual([entry["name"] for entry in found],
                         ["No Step Back", "German March Order"])

    def test_gfx_roots_only_returns_active_dlc(self):
        with tempfile.TemporaryDirectory() as root:
            nsb = _write_dlc(root, "dlc034_nsb", "No Step Back")
            _write_dlc(root, "dlc036_bba", "By Blood Alone")
            roots = dlc.gfx_roots(root, {"No Step Back"})

        self.assertEqual(roots, [nsb])

    def test_no_dlc_folder_is_not_an_error(self):
        with tempfile.TemporaryDirectory() as root:
            self.assertEqual(dlc.installed(root), [])


DLC_INFO = """dlcs = {
\tdlc023 = {
\t\tname = "Man the Guns"
\t\tsteam_id = "815460"
\t}
\tdlc034 = {
\t\tname = "No Step Back"
\t\tsteam_id = "1520460"
\t}
}
"""


def _write_catalogue(root, text=DLC_INFO):
    info_dir = os.path.join(root, "dlc_metadata", "dlc_info")
    os.makedirs(info_dir, exist_ok=True)
    with open(os.path.join(info_dir, "00_dlc_info.txt"), "w", encoding="utf-8") as handle:
        handle.write(text)


class AvailableTests(unittest.TestCase):
    def test_catalogued_dlc_with_no_folder_counts_as_bundled(self):
        """Man the Guns stopped shipping its own dlc/<folder> once its
        content became part of the base game, so "no folder" no longer
        means "the player doesn't have it" - treating it that way put the
        pre-MtG naval tree in front of everyone."""
        with tempfile.TemporaryDirectory() as root:
            _write_catalogue(root)
            _write_dlc(root, "dlc034_nsb", "No Step Back")
            entries = {e["name"]: e for e in dlc.available(root)}

        self.assertTrue(entries["Man the Guns"]["bundled"])
        self.assertTrue(entries["Man the Guns"]["default_on"])
        self.assertIsNone(entries["Man the Guns"]["path"])
        self.assertFalse(entries["No Step Back"]["bundled"])

    def test_bundled_dlc_contributes_no_sprite_root(self):
        """Its art is already in the base game's own gfx folders."""
        with tempfile.TemporaryDirectory() as root:
            _write_catalogue(root)
            nsb = _write_dlc(root, "dlc034_nsb", "No Step Back")
            entries = dlc.available(root)
            roots = dlc.gfx_roots(root, {"Man the Guns", "No Step Back"}, entries)

        self.assertEqual(roots, [nsb])

    def test_focus_branches_gated_on_dlc_are_hidden_without_it(self):
        """68 of vanilla's focuses carry
        `allow_branch = { has_dlc = "..." }`; drawing them regardless shows
        a tree no player without that expansion ever sees."""
        focuses = [
            {"id": "plain", "allow_branch_raw": ""},
            {"id": "needs_nsb", "allow_branch_raw": ' has_dlc = "No Step Back" '},
            {"id": "legacy", "allow_branch_raw": ' NOT = { has_dlc = "No Step Back" } '},
        ]
        gates, names = dlc.focus_gates(focuses)

        self.assertEqual(names, {"No Step Back"})
        self.assertEqual(dlc.hidden_focuses(gates, {"No Step Back"}), {"legacy"})
        self.assertEqual(dlc.hidden_focuses(gates, set()), {"needs_nsb"})

    def test_a_focus_with_a_non_dlc_allow_branch_is_never_hidden(self):
        focuses = [{"id": "tagged", "allow_branch_raw": ' tag = POL '}]
        gates, names = dlc.focus_gates(focuses)

        self.assertEqual(gates, {})
        self.assertEqual(names, set())

    def test_a_dlc_present_on_disk_is_not_duplicated_by_the_catalogue(self):
        with tempfile.TemporaryDirectory() as root:
            _write_catalogue(root)
            _write_dlc(root, "dlc034_nsb", "No Step Back")
            names = [e["name"] for e in dlc.available(root)]

        self.assertEqual(names.count("No Step Back"), 1)


if __name__ == "__main__":
    unittest.main()
