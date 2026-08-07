import os
import tempfile
import unittest

import numpy as np

from app import map_data


STATE = """state = {
\tid = 5
\tname = "STATE_5"
\thistory = {
\t\towner = HUN
\t\tadd_core_of = HUN
\t}
\tprovinces = { 11 12 }
}
"""

UNOWNED = """state = {
\tid = 6
\thistory = {
\t}
\tprovinces = { 20 }
}
"""


class ClaimsTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def state_file(self, text=STATE, name="5.txt"):
        path = os.path.join(self.tmp.name, name)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)
        return path

    def states(self):
        return map_data.load_states(self.tmp.name)

    def read(self, path):
        with open(path, encoding="utf-8") as handle:
            return handle.read()


class ReadTest(ClaimsTestCase):
    def test_cores_and_claims_are_read(self):
        self.state_file(STATE.replace("\t\tadd_core_of = HUN",
                                      "\t\tadd_core_of = HUN\n\t\tadd_claim_by = ROM"))
        st = self.states()[5]
        self.assertEqual(st["cores"], ["HUN"])
        self.assertEqual(st["claims"], ["ROM"])

    def test_state_with_neither(self):
        self.state_file(UNOWNED, "6.txt")
        st = self.states()[6]
        self.assertEqual(st["cores"], [])
        self.assertEqual(st["claims"], [])


class WriteTest(ClaimsTestCase):
    def test_add_core(self):
        path = self.state_file()
        map_data.apply_state_claims(path, add=["YUG"], kind="core")
        self.assertEqual(self.states()[5]["cores"], ["HUN", "YUG"])

    def test_add_claim(self):
        path = self.state_file()
        map_data.apply_state_claims(path, add=["ROM"], kind="claim")
        self.assertEqual(self.states()[5]["claims"], ["ROM"])

    def test_adding_an_existing_core_is_a_no_op(self):
        path = self.state_file()
        self.assertFalse(map_data.apply_state_claims(path, add=["HUN"], kind="core"))
        self.assertEqual(self.read(path).count("add_core_of = HUN"), 1)

    def test_remove_core(self):
        path = self.state_file()
        map_data.apply_state_claims(path, remove=["HUN"], kind="core")
        self.assertEqual(self.states()[5]["cores"], [])
        self.assertNotIn("add_core_of", self.read(path))

    def test_removing_one_tag_leaves_the_others(self):
        path = self.state_file(STATE.replace("\t\tadd_core_of = HUN",
                                             "\t\tadd_core_of = HUN\n\t\tadd_core_of = YUG"))
        map_data.apply_state_claims(path, remove=["HUN"], kind="core")
        self.assertEqual(self.states()[5]["cores"], ["YUG"])

    def test_a_state_nobody_owns_can_still_be_claimed(self):
        path = self.state_file(UNOWNED, "6.txt")
        map_data.apply_state_claims(path, add=["ITA"], kind="claim")
        self.assertEqual(self.states()[6]["claims"], ["ITA"])

    def test_owner_and_provinces_survive(self):
        path = self.state_file()
        map_data.apply_state_claims(path, add=["YUG"], kind="core")
        st = self.states()[5]
        self.assertEqual(st["owner"], "HUN")
        self.assertEqual(st["provinces"], [11, 12])

    def test_braces_stay_balanced(self):
        path = self.state_file()
        map_data.apply_state_claims(path, add=["YUG"], kind="core")
        text = self.read(path)
        self.assertEqual(text.count("{"), text.count("}"))

    def test_removing_something_absent_writes_nothing(self):
        path = self.state_file()
        before = self.read(path)
        self.assertFalse(map_data.apply_state_claims(path, remove=["FRA"], kind="core"))
        self.assertEqual(self.read(path), before)


class OverlayTest(unittest.TestCase):
    """The map overlay answers 'what does this country think is theirs'."""

    def setUp(self):
        self.world = map_data.WorldMap.__new__(map_data.WorldMap)
        self.world.state_arr = np.array([[0, 1, 1], [2, 2, 3]], dtype=np.int32)
        self.world.states = {
            1: {"owner": "HUN", "cores": ["HUN"], "claims": []},
            2: {"owner": "ROM", "cores": ["HUN"], "claims": []},
            3: {"owner": "ROM", "cores": ["ROM"], "claims": ["HUN"]},
        }

    def test_owned_and_cored_differs_from_cored_only(self):
        lut = self.world.claim_lut("HUN", kind="core")
        self.assertEqual(tuple(lut[1]), map_data.CORE_OWNED_COLOR)
        self.assertEqual(tuple(lut[2]), map_data.CORE_FOREIGN_COLOR)

    def test_states_without_the_core_are_dimmed(self):
        lut = self.world.claim_lut("HUN", kind="core")
        self.assertEqual(tuple(lut[3]), map_data.INACTIVE_COLOR)

    def test_sea_stays_sea(self):
        self.assertEqual(tuple(self.world.claim_lut("HUN")[0]), map_data.SEA_COLOR)

    def test_claim_layer_uses_the_claim_colour(self):
        lut = self.world.claim_lut("HUN", kind="claim")
        self.assertEqual(tuple(lut[3]), map_data.CLAIM_COLOR)
        self.assertEqual(tuple(lut[1]), map_data.INACTIVE_COLOR)


if __name__ == "__main__":
    unittest.main()
