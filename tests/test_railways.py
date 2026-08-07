import os
import tempfile
import unittest

import numpy as np

from app import map_data, railways


class RailwayFileTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def write(self, text, name="railways.txt"):
        path = os.path.join(self.tmp.name, name)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)
        return path


class ParseRailwaysTest(RailwayFileTestCase):
    def test_level_and_path(self):
        path = self.write("3 4 6521 11444 3312 6282 \n")
        self.assertEqual(railways.parse_railways(path), [(3, [6521, 11444, 3312, 6282])])

    def test_several_lines(self):
        path = self.write("3 2 1 2 \n1 3 4 5 6 \n")
        self.assertEqual(len(railways.parse_railways(path)), 2)

    def test_blank_and_comment_lines_are_skipped(self):
        path = self.write("\n# a note\n3 2 1 2 \n\n")
        self.assertEqual(railways.parse_railways(path), [(3, [1, 2])])

    def test_a_malformed_line_does_not_lose_the_others(self):
        path = self.write("3 2 1 2 \nnonsense here\n1 2 7 8 \n")
        self.assertEqual(len(railways.parse_railways(path)), 2)

    def test_a_one_province_railway_is_not_a_railway(self):
        path = self.write("3 1 55 \n")
        self.assertEqual(railways.parse_railways(path), [])

    def test_missing_file_is_empty_not_an_error(self):
        self.assertEqual(railways.parse_railways(os.path.join(self.tmp.name, "nope.txt")), [])


class ParseSupplyNodesTest(RailwayFileTestCase):
    def test_reads_province_ids(self):
        path = self.write("1 67 \n1 101 \n", "supply_nodes.txt")
        self.assertEqual(railways.parse_supply_nodes(path), [67, 101])

    def test_blank_lines_are_skipped(self):
        path = self.write("\n1 67 \n\n", "supply_nodes.txt")
        self.assertEqual(railways.parse_supply_nodes(path), [67])


class WriteTest(RailwayFileTestCase):
    def test_count_is_recomputed_not_carried_over(self):
        """The game trusts the count field, so a stale one is a silent
        corruption - it must always match the ids that follow."""
        text = railways.format_railways([(2, [1, 2, 3, 4, 5])])
        self.assertTrue(text.startswith("2 5 "))

    def test_round_trip(self):
        entries = [(3, [1, 2, 3]), (1, [9, 8])]
        path = self.write(railways.format_railways(entries))
        self.assertEqual(railways.parse_railways(path), entries)

    def test_supply_node_round_trip(self):
        nodes = [67, 101, 121]
        path = self.write(railways.format_supply_nodes(nodes), "supply_nodes.txt")
        self.assertEqual(railways.parse_supply_nodes(path), nodes)

    def test_save_creates_the_map_folder(self):
        mod = os.path.join(self.tmp.name, "mod")
        path = railways.save_railways(mod, [(1, [1, 2])])
        self.assertTrue(os.path.isfile(path))
        self.assertEqual(railways.parse_railways(path), [(1, [1, 2])])

    def test_existing_file_is_backed_up(self):
        mod = os.path.join(self.tmp.name, "mod")
        railways.save_railways(mod, [(1, [1, 2])])
        railways.save_railways(mod, [(2, [3, 4])])
        backup = railways.target_path(mod, railways.RAILWAYS) + ".bak"
        self.assertTrue(os.path.isfile(backup))
        self.assertEqual(railways.parse_railways(backup), [(1, [1, 2])])


class ProblemsTest(unittest.TestCase):
    def test_level_out_of_range(self):
        found = railways.problems([(0, [1, 2])], [])
        self.assertTrue(any("level" in msg for _i, msg in found))

    def test_repeated_province_in_one_line(self):
        found = railways.problems([(1, [1, 2, 1])], [])
        self.assertTrue(any("twice" in msg for _i, msg in found))

    def test_duplicate_supply_nodes(self):
        found = railways.problems([], [5, 5])
        self.assertTrue(any("duplicate" in msg for _i, msg in found))

    def test_provinces_off_the_map(self):
        found = railways.problems([(1, [1, 999])], [], land_provinces={1, 2})
        self.assertTrue(any("999" in msg for _i, msg in found))

    def test_a_clean_network_reports_nothing(self):
        self.assertEqual(railways.problems([(1, [1, 2])], [1], land_provinces={1, 2}), [])


class CentroidTest(unittest.TestCase):
    """Railways carry no coordinates, so drawing them needs a position
    worked out for every province."""

    def test_centre_of_each_province(self):
        world = map_data.WorldMap.__new__(map_data.WorldMap)
        world.province_arr = np.array([[1, 1, 2],
                                       [1, 1, 2]], dtype=np.int32)
        centres = world.province_centroids()
        self.assertEqual(centres[1], (0.5, 0.5))
        self.assertEqual(centres[2], (2.0, 0.5))

    def test_sea_is_not_given_a_centre(self):
        world = map_data.WorldMap.__new__(map_data.WorldMap)
        world.province_arr = np.array([[0, 1]], dtype=np.int32)
        self.assertNotIn(0, world.province_centroids())


if __name__ == "__main__":
    unittest.main()
