"""A mod's states have to be merged with the base game's, not chosen over.

The game loads `history/states` from the base game and then from the mod,
and a mod file replaces the base file of the same name. Reading only the
mod's folder dropped every state it hadn't touched, and all that land drew
as unassigned - which on Europe in Flames was a fifth of the world.
"""

import os
import tempfile
import unittest
from unittest import mock

from app import map_data


def state_text(sid, owner="ENG", provinces=(1, 2)):
    return (f"state = {{\n\tid = {sid}\n\tname = \"STATE_{sid}\"\n"
            f"\thistory = {{\n\t\towner = {owner}\n\t}}\n"
            f"\tprovinces = {{ {' '.join(str(p) for p in provinces)} }}\n}}\n")


class WorldStatesTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = os.path.join(self.tmp.name, "base")
        self.mod = os.path.join(self.tmp.name, "mod")
        os.makedirs(os.path.join(self.base, "history", "states"))
        os.makedirs(os.path.join(self.mod, "history", "states"))

        patcher = mock.patch.object(map_data, "BASE_GAME", self.base)
        patcher.start()
        self.addCleanup(patcher.stop)

    def write(self, root, filename, text):
        path = os.path.join(root, "history", "states", filename)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)
        return path

    def test_untouched_base_states_survive(self):
        self.write(self.base, "1-england.txt", state_text(1))
        self.write(self.base, "2-france.txt", state_text(2, "FRA"))
        self.write(self.mod, "1-england.txt", state_text(1, "GER"))

        states = map_data.load_world_states(self.mod)
        self.assertEqual(set(states), {1, 2})

    def test_the_mod_file_wins_over_the_base_file_it_replaces(self):
        self.write(self.base, "1-england.txt", state_text(1, "ENG"))
        self.write(self.mod, "1-england.txt", state_text(1, "GER"))
        self.assertEqual(map_data.load_world_states(self.mod)[1]["owner"], "GER")

    def test_a_mod_only_state_is_included(self):
        self.write(self.base, "1-england.txt", state_text(1))
        self.write(self.mod, "900-new.txt", state_text(900, "TUR"))
        states = map_data.load_world_states(self.mod)
        self.assertEqual(set(states), {1, 900})

    def test_filename_match_ignores_case(self):
        """Windows and Linux disagree about case; the game does not."""
        self.write(self.base, "1-England.txt", state_text(1, "ENG"))
        self.write(self.mod, "1-england.txt", state_text(1, "GER"))
        states = map_data.load_world_states(self.mod)
        self.assertEqual(len(states), 1)
        self.assertEqual(states[1]["owner"], "GER")

    def test_a_mod_with_no_states_folder_gets_the_base_game(self):
        self.write(self.base, "1-england.txt", state_text(1))
        empty = os.path.join(self.tmp.name, "empty")
        os.makedirs(empty)
        self.assertEqual(set(map_data.load_world_states(empty)), {1})

    def test_no_mod_at_all_gets_the_base_game(self):
        self.write(self.base, "1-england.txt", state_text(1))
        self.assertEqual(set(map_data.load_world_states("")), {1})

    def test_pointing_at_the_base_game_itself_does_not_double_count(self):
        self.write(self.base, "1-england.txt", state_text(1))
        self.assertEqual(set(map_data.load_world_states(self.base)), {1})

    def test_unclaimed_provinces_account_for_the_base_game(self):
        """A province owned by an untouched base-game state is claimed, and
        offering it as free land would let the user build an overlapping
        state on top of it."""
        self.write(self.base, "2-france.txt", state_text(2, "FRA", provinces=(7, 8)))
        self.write(self.mod, "1-england.txt", state_text(1, "GER", provinces=(1,)))

        states = map_data.load_world_states(self.mod)
        claimed = {p for st in states.values() for p in st["provinces"]}
        self.assertIn(7, claimed)
        self.assertIn(8, claimed)

    def test_next_free_id_clears_both_folders(self):
        self.write(self.base, "500-big.txt", state_text(500))
        self.write(self.mod, "1-small.txt", state_text(1))
        self.assertEqual(map_data.next_free_state_id(self.mod), 501)


if __name__ == "__main__":
    unittest.main()
