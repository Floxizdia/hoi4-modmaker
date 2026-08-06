import types
import unittest

from app.tech_tab import TechTreeView, AUTO_LAYOUT, MOD_COORDS


def _view(mode):
    """_grid_positions only reads self.layout_mode, so it can be exercised
    without building a real Tk widget - the same no-live-widgets convention
    the rest of the suite follows."""
    return types.SimpleNamespace(layout_mode=types.SimpleNamespace(get=lambda: mode))


def _tech(x, y, requires=(), positioned=True):
    return {"x": x, "y": y, "requires": list(requires), "positioned": positioned}


class LayoutModeTests(unittest.TestCase):
    def test_mod_coordinates_draws_the_authored_cells(self):
        items = {
            "a": _tech(0, 0),
            "b": _tech(-1, 2, ["a"]),
            "c": _tech(3, 4, ["b"]),
        }
        grid = TechTreeView._grid_positions(_view(MOD_COORDS), items)

        self.assertEqual(grid, {"a": (0, 0), "b": (-1, 2), "c": (3, 4)})

    def test_auto_ignores_authored_cells(self):
        items = {
            "a": _tech(0, 0),
            "b": _tech(-1, 2, ["a"]),
            "c": _tech(3, 4, ["b"]),
        }
        grid = TechTreeView._grid_positions(_view(AUTO_LAYOUT), items)

        self.assertNotEqual(grid, {"a": (0, 0), "b": (-1, 2), "c": (3, 4)})
        self.assertEqual(len(set(grid.values())), 3)

    def test_unpositioned_folder_falls_back_even_in_mod_coordinates(self):
        """A folder a mod extended without positioning anything would stack
        every tech on one cell if the authored zeros were taken at face
        value."""
        items = {name: _tech(0, 0, positioned=False) for name in "abcd"}
        grid = TechTreeView._grid_positions(_view(MOD_COORDS), items)

        self.assertEqual(len(set(grid.values())), 4)


class CollisionTests(unittest.TestCase):
    def test_only_the_extra_claimant_moves_off_a_shared_cell(self):
        """Vanilla's mutually-exclusive doctrine branches share cells on
        purpose. Nudging used to cascade: a displaced tech could land on a
        cell another tech legitimately owned and push that one too, so techs
        that were uncontested in the game data still drifted."""
        items = {
            "shared_a": _tech(0, 0),
            "shared_b": _tech(0, 0),
            "neighbour": _tech(1, 0),
        }
        grid = TechTreeView._grid_positions(_view(MOD_COORDS), items)

        self.assertEqual(grid["shared_a"], (0, 0))
        self.assertEqual(grid["neighbour"], (1, 0))
        self.assertNotIn(grid["shared_b"], [(0, 0), (1, 0)])
        self.assertEqual(len(set(grid.values())), 3)

    def test_no_two_techs_ever_occupy_the_same_cell(self):
        items = {f"t{i}": _tech(0, 0) for i in range(6)}
        grid = TechTreeView._grid_positions(_view(MOD_COORDS), items)

        self.assertEqual(len(set(grid.values())), 6)


if __name__ == "__main__":
    unittest.main()
