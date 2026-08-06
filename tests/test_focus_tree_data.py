import os
import tempfile
import time
import unittest

from app.focus_tree_data import FocusTreeData
from app.focus_tree_controller import FocusTreeController
from app.focus_tree_inspector import FocusTreeInspector
from app import focus_surgery, mod_loader, starter, undo


class FocusTreeDataTests(unittest.TestCase):
    def setUp(self):
        undo.clear()

    def tearDown(self):
        undo.clear()

    def _write(self, root, relative_path, content):
        path = os.path.join(root, relative_path)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(content)
        return path

    def test_load_mod_preserves_mod_browser_result_shape(self):
        with tempfile.TemporaryDirectory() as base_game, tempfile.TemporaryDirectory() as mod:
            self._write(mod, "descriptor.mod", 'name = "Test Mod"\ntags = { "Alternative History" "Events" }\n')
            self._write(mod, "common/national_focus/test.txt", """
                focus_tree = {
                    id = TEST_tree
                    focus = { id = TEST_start x = 1 y = 2 cost = 10 }
                }
            """)
            self._write(mod, "localisation/english/test_l_english.yml", 'l_english:\n TEST_start:0 "Test Start"\n')
            self._write(mod, "common/characters/TEST.txt", """
                characters = {
                    TEST_leader = { name = TEST_leader_name country_leader = { ideology = neutral } }
                }
            """)

            result = FocusTreeData(base_game).load_mod(mod)

        self.assertEqual(
            set(result),
            {"path", "tree_files", "gfx_index", "loc", "characters", "items", "mod_name", "tags"},
        )
        self.assertEqual(result["mod_name"], "Test Mod")
        self.assertEqual(result["tags"], ["Alternative History", "Events"])
        self.assertEqual(result["loc"]["TEST_start"], "Test Start")
        self.assertEqual(result["items"][0][2]["id"], "TEST_tree")
        self.assertEqual(result["items"][0][2]["focuses"][0]["id"], "TEST_start")
        self.assertIn("TEST", result["characters"])

    def test_newer_async_request_discards_stale_result(self):
        data = FocusTreeData("")

        def fake_load(path):
            if path == "slow":
                time.sleep(0.08)
            return {"path": path}

        data.load_mod = fake_load
        stale_id = data.load_mod_async("slow")
        current_id = data.load_mod_async("current")

        result = None
        deadline = time.monotonic() + 1
        while time.monotonic() < deadline and result is None:
            result = data.take_load_result(current_id)
            time.sleep(0.01)

        self.assertEqual(result, {"path": "current"})
        self.assertIsNone(data.take_load_result(stale_id))

    def test_mod_load_exposes_vanilla_trees_for_other_countries(self):
        with tempfile.TemporaryDirectory() as base_game, tempfile.TemporaryDirectory() as mod:
            self._write(base_game, "common/national_focus/germany.txt", """
                focus_tree = {
                    id = GER_focus
                    country = { factor = 0 modifier = { add = 10 tag = GER } }
                    focus = { id = GER_start x = 1 y = 1 }
                }
            """)
            self._write(mod, "descriptor.mod", 'name = "Test Mod"\n')
            result = FocusTreeData(base_game).load_mod(mod)

        label, _path, tree = result["items"][0]
        self.assertIn("GER", label)
        self.assertEqual(tree["id"], "GER_focus")
        self.assertTrue(tree["is_vanilla"])

    def test_first_write_to_vanilla_tree_copies_it_to_the_mod(self):
        with tempfile.TemporaryDirectory() as base_game, tempfile.TemporaryDirectory() as mod_root:
            source_path = self._write(base_game, "common/national_focus/germany.txt", """
                focus_tree = { id = GER_focus focus = { id = GER_start } }
            """)
            view = type("View", (), {
                "mod_root": mod_root,
                "current_tree": {"source_file": source_path, "is_vanilla": True},
            })()
            controller = FocusTreeController(view, base_game, "")
            destination = controller.ensure_editable_tree()

            self.assertEqual(
                destination,
                os.path.join(mod_root, "common", "national_focus", "germany.txt"),
            )
            self.assertTrue(os.path.isfile(destination))
            self.assertFalse(view.current_tree["is_vanilla"])
            self.assertEqual(view.current_tree["source_file"], destination)

    def test_export_additions_writes_focus_and_localisation_files(self):
        class Status:
            def config(self, **kwargs):
                self.text = kwargs.get("text", "")

        class View:
            def __init__(self, mod_root):
                self.mod_root = mod_root
                self.source_path = os.path.join(
                    mod_root, "common", "national_focus", "test_tree.txt"
                )
                os.makedirs(os.path.dirname(self.source_path), exist_ok=True)
                with open(self.source_path, "w", encoding="utf-8") as handle:
                    handle.write("focus_tree = {\n\tid = TEST_tree\n}\n")
                self.current_tree = {"id": "TEST_tree", "source_file": self.source_path}
                self.focuses = [
                    {"id": "TEST_start", "x": 0, "y": 0, "prerequisite": [], "mutually_exclusive": []},
                    {"id": "TEST_rival", "x": 1, "y": 0, "prerequisite": [], "mutually_exclusive": []},
                ]
                self.new_focuses = [{
                    "id": "TEST_added",
                    "title": "Test Added",
                    "desc": "A test focus.",
                    "icon": "GFX_goal_test",
                    "x": 2,
                    "y": 3,
                    "cost": 8,
                    "prerequisite": ["TEST_start"],
                    "prerequisite_groups": [["TEST_start"]],
                    "available_raw": "has_war = no",
                    "mutually_exclusive": ["TEST_rival"],
                    "completion_reward_raw": "add_political_power = 10",
                }]
                self.status = Status()
                self.render_count = 0

            def _all_focuses(self):
                return list(self.focuses) + list(self.new_focuses)

            def _render_tree(self):
                self.render_count += 1

        with tempfile.TemporaryDirectory() as mod_root:
            view = View(mod_root)
            FocusTreeController(view, "", "").export_additions()

            loc_path = os.path.join(
                mod_root, "localisation", "english", "TEST_tree_additions_l_english.yml"
            )
            with open(view.source_path, encoding="utf-8") as handle:
                focus_content = handle.read()
            with open(loc_path, encoding="utf-8-sig") as handle:
                loc_content = handle.read()

        self.assertIn("id = TEST_added", focus_content)
        self.assertIn("focus = TEST_start", focus_content)
        self.assertIn("mutually_exclusive", focus_content)
        self.assertIn("available", focus_content)
        self.assertIn("has_war = no", focus_content)
        self.assertFalse(os.path.exists(
            os.path.join(mod_root, "common", "national_focus", "TEST_tree_additions.txt")
        ))
        self.assertEqual(view.new_focuses, [])
        self.assertEqual([focus["id"] for focus in view.current_tree["focuses"]], ["TEST_added"])
        self.assertIn('TEST_added:0 "Test Added"', loc_content)

    def test_add_focus_places_it_below_its_prerequisite(self):
        class Status:
            def config(self, **kwargs):
                self.text = kwargs.get("text", "")

        class View:
            def __init__(self):
                self.current_tree = {"focuses": [{"id": "TEST_start", "x": 4, "y": 5}]}
                self.new_focuses = []
                self.selected_id = None
                self.status = Status()
                self.details_id = None

            def _all_focuses(self):
                return list(self.current_tree["focuses"]) + list(self.new_focuses)

            def _mod_grid(self, focuses):
                return {focus["id"]: (focus["x"], focus["y"]) for focus in focuses}

            def _render_tree(self):
                self.rendered = True

            def _show_details(self, focus_id):
                self.details_id = focus_id

        focus = {
            "id": "TEST_added", "prerequisite": ["TEST_start"], "x": 0, "y": 0,
        }
        view = View()
        FocusTreeController(view, "", "").add_focus(focus)

        self.assertEqual((focus["x"], focus["y"]), (4, 6))
        self.assertEqual(view.selected_id, "TEST_added")
        self.assertEqual(view.details_id, "TEST_added")

    def test_complete_selected_updates_play_mode_state(self):
        class SimMode:
            def __init__(self, value):
                self.value = value

            def get(self):
                return self.value

            def set(self, value):
                self.value = value

        class View:
            def __init__(self):
                self.sim_mode = SimMode(True)
                self.selected_id = "TEST_available"
                self._available_now = {"TEST_available"}
                self.completed = set()
                self.details_id = None
                self.render_count = 0

            def _render_tree(self):
                self.render_count += 1

            def _show_details(self, focus_id):
                self.details_id = focus_id

        view = View()
        controller = FocusTreeController(view, "", "")
        controller.complete_selected()

        self.assertEqual(view.completed, {"TEST_available"})
        self.assertEqual(view.details_id, "TEST_available")
        controller.toggle_simulation()
        self.assertFalse(view.sim_mode.get())
        self.assertEqual(view.completed, set())

    def test_find_matches_searches_id_title_and_description(self):
        class FindVar:
            def get(self):
                return "harbor"

        class View:
            current_tree = {"id": "TEST_tree"}
            find_var = FindVar()
            loc = {
                "TEST_title": "Harbor Development",
                "TEST_description_desc": "Improve the naval harbor.",
            }

            def _all_focuses(self):
                return [
                    {"id": "TEST_title"},
                    {"id": "TEST_description"},
                    {"id": "TEST_other", "title": "Unrelated"},
                ]

        matches = FocusTreeController(View(), "", "").find_matches()

        self.assertEqual(matches, ["TEST_title", "TEST_description"])

    def test_tree_settings_uses_the_loaded_tree_metadata(self):
        class Label:
            def configure(self, **kwargs):
                self.text = kwargs["text"]

        class Inspector:
            tree_info_label = Label()

        FocusTreeInspector.show_tree_settings(Inspector(), {
            "id": "TEST_tree",
            # built with the running platform's separator: a hardcoded
            # Windows path made basename() return the whole string on Linux
            "source_file": os.path.join("mods", "test", "common",
                                        "national_focus", "test.txt"),
            "focuses": [{"id": "TEST_start"}],
            "default": "no",
        })

        self.assertIn("Tree id: TEST_tree", Inspector.tree_info_label.text)
        self.assertIn("File: test.txt", Inspector.tree_info_label.text)

    def test_focus_file_edit_records_a_reversible_undo_step(self):
        source = """focus_tree = {
    id = TEST_tree
    focus = { id = TEST_start cost = 2 x = 1 y = 2 }
}
"""
        with tempfile.TemporaryDirectory() as root:
            path = self._write(root, "common/national_focus/test.txt", source)
            self.assertTrue(focus_surgery.apply_edits(path, "TEST_start", scalars={"cost": 8}))
            self.assertTrue(undo.can_undo())
            self.assertIn("TEST_start", undo.undo())
            with open(path, encoding="utf-8") as handle:
                self.assertEqual(handle.read(), source)

    def test_relationship_save_preserves_and_or_groups_and_mutexes(self):
        source = """focus_tree = {
    id = TEST_tree
    focus = {
        id = TEST_target
        prerequisite = { focus = OLD_a }
        prerequisite = { focus = OLD_b }
        mutually_exclusive = { focus = OLD_mutex }
        completion_reward = { add_political_power = 10 }
    }
}
"""
        with tempfile.TemporaryDirectory() as root:
            path = self._write(root, "common/national_focus/test.txt", source)
            self.assertTrue(focus_surgery.apply_edits(
                path,
                "TEST_target",
                blocks={
                    "prerequisite_groups": [["TEST_a", "TEST_b"], ["TEST_c"]],
                    "mutually_exclusive": ["TEST_mutex_a", "TEST_mutex_b"],
                },
            ))
            parsed = mod_loader.parse_focus_trees(path)[0]["focuses"][0]

        self.assertEqual(parsed["prerequisite_groups"], [["TEST_a", "TEST_b"], ["TEST_c"]])
        self.assertEqual(parsed["mutually_exclusive"], ["TEST_mutex_a", "TEST_mutex_b"])
        self.assertEqual(parsed["completion_reward_raw"].strip(), "add_political_power = 10")

    def test_in_memory_action_is_undone_and_redone_in_global_history(self):
        values = []
        undo.record_action(lambda: values.pop(), lambda: values.append("focus"), "adding TEST_focus")
        values.append("focus")

        self.assertEqual(undo.undo(), "Reverted adding TEST_focus")
        self.assertEqual(values, [])
        self.assertEqual(undo.redo(), "Re-applied adding TEST_focus")
        self.assertEqual(values, ["focus"])

    def test_adding_a_focus_can_be_undone_before_export(self):
        class Status:
            def config(self, **kwargs):
                self.text = kwargs.get("text", "")

        class View:
            def __init__(self):
                self.current_tree = {"focuses": [{"id": "TEST_start", "x": 0, "y": 0}]}
                self.new_focuses = []
                self._moved = set()
                self._relationship_dirty = set()
                self.selected_id = None
                self.status = Status()
                self._by_id = {}

            def _all_focuses(self):
                return list(self.current_tree["focuses"]) + list(self.new_focuses)

            def _mod_grid(self, focuses):
                return {focus["id"]: (focus["x"], focus["y"]) for focus in focuses}

            def _render_tree(self):
                self._by_id = {focus["id"]: focus for focus in self._all_focuses()}

            def _show_details(self, focus_id):
                self.details_id = focus_id

        view = View()
        controller = FocusTreeController(view, "", "")
        controller.add_focus({"id": "TEST_added", "prerequisite": ["TEST_start"], "x": 0, "y": 0})
        self.assertEqual([focus["id"] for focus in view.new_focuses], ["TEST_added"])

        self.assertEqual(undo.undo(), "Reverted adding TEST_added")
        self.assertEqual(view.new_focuses, [])
        self.assertEqual(undo.redo(), "Re-applied adding TEST_added")
        self.assertEqual([focus["id"] for focus in view.new_focuses], ["TEST_added"])

    def test_canvas_background_handler_does_not_clear_a_node_click(self):
        class Mode:
            def get(self):
                return "select"

        class Canvas:
            def canvasx(self, value):
                return value

            def canvasy(self, value):
                return value

            def find_overlapping(self, *_coords):
                return (42,)

            def gettags(self, item):
                return ("focus_TEST_start",) if item == 42 else ()

        class View:
            canvas_mode = Mode()
            canvas = Canvas()
            selected_id = "TEST_start"

            def _render_tree(self):
                raise AssertionError("A node click must not be treated as empty canvas")

        event = type("Event", (), {"x": 10, "y": 20})()
        FocusTreeController(View(), "", "").on_canvas_press(event)

        self.assertEqual(View.selected_id, "TEST_start")

    def test_starter_focus_tree_has_priority_over_the_vanilla_country_tree(self):
        with tempfile.TemporaryDirectory() as mod_root:
            created = starter.write_starter(mod_root, "demo", "GER")
            focus_path = next(
                path for path in created
                if os.path.normpath(path).endswith(
                    os.path.normpath(os.path.join("common", "national_focus", "demo_starter.txt"))
                )
            )
            with open(focus_path, encoding="utf-8") as handle:
                content = handle.read()

        self.assertIn("id = demo_tree", content)
        self.assertIn("add = 1000", content)
        self.assertIn("tag = GER", content)


if __name__ == "__main__":
    unittest.main()
