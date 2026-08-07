import os
import tempfile
import unittest

from app import map_data


STATE = """state = {
\tid = 12
\tname = "STATE_12"
\tmanpower = 1000
\thistory = {
\t\towner = ENG
\t\tbuildings = {
\t\t\tinfrastructure = 5
\t\t\tarms_factory = 2
\t\t\t1234 = {
\t\t\t\tnaval_base = 3
\t\t\t}
\t\t}
\t\tvictory_points = { 1234 10 }
\t}
\tprovinces = { 1234 1235 }
}
"""

NO_BUILDINGS = """state = {
\tid = 9
\thistory = {
\t\towner = FRA
\t}
\tprovinces = { 77 }
}
"""


class ProvinceBuildingsTestCase(unittest.TestCase):
    """A state's port is a per-province building, not a state-wide one, so
    until these were readable a coastal state couldn't be given a harbour."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def state_file(self, text=STATE, name="12.txt"):
        path = os.path.join(self.tmp.name, name)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)
        return path

    def read(self, path):
        with open(path, encoding="utf-8") as handle:
            return handle.read()


class ReadTest(ProvinceBuildingsTestCase):
    def test_reads_province_levels(self):
        details = map_data.read_state_details(self.state_file())
        self.assertEqual(details["province_buildings"], {1234: {"naval_base": "3"}})

    def test_state_wide_values_are_unaffected(self):
        details = map_data.read_state_details(self.state_file())
        self.assertEqual(details["buildings"]["infrastructure"], "5")
        self.assertEqual(details["buildings"]["arms_factory"], "2")

    def test_a_province_level_is_not_read_as_a_state_level(self):
        """The state-wide reader used to search the whole buildings block,
        nested province entries included."""
        text = STATE.replace("naval_base = 3", "air_base = 7")
        details = map_data.read_state_details(self.state_file(text))
        self.assertEqual(details["buildings"]["air_base"], "")
        self.assertEqual(details["province_buildings"], {})

    def test_state_without_province_entries(self):
        details = map_data.read_state_details(self.state_file(NO_BUILDINGS, "9.txt"))
        self.assertEqual(details["province_buildings"], {})


class WriteTest(ProvinceBuildingsTestCase):
    def test_raises_an_existing_level(self):
        path = self.state_file()
        map_data.apply_state_edits(path, province_buildings={1234: {"naval_base": "8"}})
        self.assertEqual(map_data.read_state_details(path)["province_buildings"],
                         {1234: {"naval_base": "8"}})

    def test_adds_a_block_for_a_province_that_had_none(self):
        path = self.state_file()
        map_data.apply_state_edits(path, province_buildings={1235: {"coastal_bunker": "2"}})
        details = map_data.read_state_details(path)
        self.assertEqual(details["province_buildings"],
                         {1234: {"naval_base": "3"}, 1235: {"coastal_bunker": "2"}})

    def test_zero_removes_the_building(self):
        path = self.state_file()
        map_data.apply_state_edits(path, province_buildings={1234: {"naval_base": "0"}})
        self.assertEqual(map_data.read_state_details(path)["province_buildings"], {})
        self.assertNotIn("naval_base", self.read(path))

    def test_creates_a_buildings_block_when_the_state_has_none(self):
        path = self.state_file(NO_BUILDINGS, "9.txt")
        map_data.apply_state_edits(path, province_buildings={77: {"naval_base": "4"}})
        self.assertEqual(map_data.read_state_details(path)["province_buildings"],
                         {77: {"naval_base": "4"}})

    def test_the_rest_of_the_state_survives(self):
        path = self.state_file()
        map_data.apply_state_edits(path, province_buildings={1235: {"naval_base": "1"}})
        details = map_data.read_state_details(path)
        self.assertEqual(details["manpower"], "1000")
        self.assertEqual(details["buildings"]["infrastructure"], "5")
        self.assertEqual(details["victory_points"], [(1234, 10)])
        self.assertIn('name = "STATE_12"', self.read(path))

    def test_braces_stay_balanced(self):
        path = self.state_file()
        map_data.apply_state_edits(path, province_buildings={1235: {"naval_base": "1"}})
        text = self.read(path)
        self.assertEqual(text.count("{"), text.count("}"))

    def test_state_wide_and_province_edits_together(self):
        path = self.state_file()
        map_data.apply_state_edits(path,
                                   buildings={"infrastructure": "9"},
                                   province_buildings={1234: {"naval_base": "6"}})
        details = map_data.read_state_details(path)
        self.assertEqual(details["buildings"]["infrastructure"], "9")
        self.assertEqual(details["province_buildings"], {1234: {"naval_base": "6"}})

    def test_nothing_to_change_writes_nothing(self):
        path = self.state_file()
        before = self.read(path)
        map_data.apply_state_edits(path, province_buildings={1235: {"naval_base": ""}})
        self.assertEqual(self.read(path), before)


if __name__ == "__main__":
    unittest.main()
