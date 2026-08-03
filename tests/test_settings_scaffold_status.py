import os
import unittest

from app.settings import scaffold_status


class ScaffoldStatusTests(unittest.TestCase):
    def test_inside_mod_dir_mentions_launcher_and_restart(self):
        user_dir = os.path.join("C:\\", "Users", "Tester", "Documents",
                                 "Paradox Interactive", "Hearts of Iron IV")
        root = os.path.join(user_dir, "mod", "my_mod")
        text = scaffold_status(root, user_dir)
        self.assertIn("Paradox Launcher", text)
        self.assertIn("reopen", text.lower())

    def test_outside_mod_dir_warns_it_will_not_appear(self):
        user_dir = os.path.join("C:\\", "Users", "Tester", "Documents",
                                 "Paradox Interactive", "Hearts of Iron IV")
        root = os.path.join("C:\\", "Users", "Tester", "Desktop", "my_mod")
        text = scaffold_status(root, user_dir)
        self.assertIn("will not list it", text)

    def test_no_hoi4_installation_found(self):
        root = os.path.join("C:\\", "somewhere", "my_mod")
        text = scaffold_status(root, None)
        self.assertIn("not found", text)


if __name__ == "__main__":
    unittest.main()
