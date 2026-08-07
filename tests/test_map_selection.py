import types
import unittest

import numpy as np

from app import map_data


class FakeTab:
    """The selection half of MapTab, driven without a display.

    The methods under test only touch `selected`, the drag flags and the
    world lookup, so they're bound onto a stand-in rather than pulling a
    real Tk canvas (and a real map bitmap) into the suite.
    """

    from app.map_tab import MapTab
    _selectable_at = MapTab._selectable_at
    _paint = MapTab._paint
    _on_click = MapTab._on_click
    _on_drag = MapTab._on_drag
    _on_release = MapTab._on_release

    def __init__(self):
        world = map_data.WorldMap.__new__(map_data.WorldMap)
        # sea, then four states in a row
        world.state_arr = np.array([[0, 1, 2, 3, 4]], dtype=np.int32)
        world.states = {i: {"owner": "ENG", "name": f"S{i}", "provinces": []}
                        for i in (1, 2, 3, 4)}
        world.no_state_id = -1
        self.world = world
        self.selected = set()
        self._press_sid = 0
        self._dragged = False
        self._drag_adding = True
        self.redraws = 0

    # stand-ins for the widget bits
    def _canvas_xy(self, event):
        return event.x, event.y
    def _redraw(self):
        self.redraws += 1
    def _report_selection(self):
        pass
    def _state_label(self, sid):
        return str(sid)


def at(x):
    return types.SimpleNamespace(x=x, y=0)


class ClickTest(unittest.TestCase):
    def setUp(self):
        self.tab = FakeTab()

    def click(self, x):
        self.tab._on_click(at(x))
        self.tab._on_release(at(x))

    def test_click_selects(self):
        self.click(1)
        self.assertEqual(self.tab.selected, {1})

    def test_clicking_again_unselects(self):
        self.click(1)
        self.click(1)
        self.assertEqual(self.tab.selected, set())

    def test_sea_is_not_selectable(self):
        self.click(0)
        self.assertEqual(self.tab.selected, set())


class DragTest(unittest.TestCase):
    def setUp(self):
        self.tab = FakeTab()

    def drag(self, start, *rest):
        self.tab._on_click(at(start))
        for x in rest:
            self.tab._on_drag(at(x))
        self.tab._on_release(at(rest[-1] if rest else start))

    def test_drag_selects_everything_it_crosses(self):
        self.drag(2, 3, 4)
        self.assertEqual(self.tab.selected, {2, 3, 4})

    def test_the_state_the_drag_started_on_is_included(self):
        """It never gets a motion event of its own, so it was being skipped."""
        self.drag(2, 3)
        self.assertIn(2, self.tab.selected)

    def test_drag_from_a_selected_state_erases(self):
        self.tab.selected = {2, 3, 4}
        self.drag(2, 3)
        self.assertEqual(self.tab.selected, {4})

    def test_a_drag_does_not_also_toggle_on_release(self):
        self.drag(2, 3)
        self.assertEqual(self.tab.selected, {2, 3})

    def test_dragging_over_sea_changes_nothing(self):
        self.tab.selected = {1}
        self.drag(0, 0)
        self.assertEqual(self.tab.selected, {1})

    def test_repainting_the_same_state_does_not_redraw_again(self):
        self.tab._on_click(at(2))
        self.tab._on_drag(at(3))
        redraws = self.tab.redraws
        self.tab._on_drag(at(3))
        self.assertEqual(self.tab.redraws, redraws)


if __name__ == "__main__":
    unittest.main()
