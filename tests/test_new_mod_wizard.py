import os
import tempfile
import unittest

from app.new_mod_wizard import create_mod


class NewModWizardTests(unittest.TestCase):
    def _write(self, root, relative_path, content):
        path = os.path.join(root, relative_path)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(content)
        return path

    def test_safe_addon_starter_does_not_assign_or_replace_a_country(self):
        with tempfile.TemporaryDirectory() as location:
            root = create_mod(
                name="Safe", folder="safe", location=location, tags=["Gameplay"],
                supported="1.19.*", launcher_entry=False, starter_prefix="demo",
                starter_tag="GER", content_mode="safe_addon",
            )
            focus_path = os.path.join(root, "common", "national_focus", "demo_starter.txt")
            history_path = os.path.join(root, "history", "countries", "GER - Starter.txt")
            with open(focus_path, encoding="utf-8") as handle:
                focus_content = handle.read()
            history_exists = os.path.exists(history_path)

        self.assertIn("Unassigned sample tree", focus_content)
        self.assertNotIn("add = 1000", focus_content)
        self.assertFalse(history_exists)

    def test_vanilla_clone_copies_the_target_tree_without_country_history(self):
        source = """focus_tree = {
    id = GER_focus
    country = { factor = 0 modifier = { add = 10 tag = GER } }
    focus = { id = GER_start x = 0 y = 0 }
}
"""
        with tempfile.TemporaryDirectory() as base_game, tempfile.TemporaryDirectory() as location:
            self._write(base_game, "common/national_focus/germany.txt", source)
            root = create_mod(
                name="Clone", folder="clone", location=location, tags=["Gameplay"],
                supported="1.19.*", launcher_entry=False, starter_prefix="demo",
                starter_tag="GER", content_mode="vanilla_clone", base_game=base_game,
            )
            copied_path = os.path.join(root, "common", "national_focus", "germany.txt")
            history_path = os.path.join(root, "history", "countries", "GER - Starter.txt")
            with open(copied_path, encoding="utf-8") as handle:
                copied_content = handle.read()
            history_exists = os.path.exists(history_path)
            sample_tree_exists = os.path.exists(
                os.path.join(root, "common", "national_focus", "demo_starter.txt")
            )

        self.assertEqual(copied_content, source)
        self.assertFalse(history_exists)
        self.assertFalse(sample_tree_exists)


if __name__ == "__main__":
    unittest.main()
