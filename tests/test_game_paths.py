import os
import sys
import tempfile
import unittest
from unittest import mock

from app import game_paths


class SteamLibraryTests(unittest.TestCase):
    """The game is regularly installed to a second drive, and on Linux Steam
    lives somewhere else entirely - so the install has to be searched for
    rather than assumed to be under C:\\Program Files (x86)."""

    def _fake_steam(self, root, library=None):
        steamapps = os.path.join(root, "steamapps")
        os.makedirs(steamapps, exist_ok=True)
        if library:
            with open(os.path.join(steamapps, "libraryfolders.vdf"), "w",
                      encoding="utf-8") as handle:
                handle.write('"libraryfolders"\n{\n\t"1"\n\t{\n'
                             f'\t\t"path"\t\t"{library}"\n\t}}\n}}\n')
        return root

    def _install_game(self, library_root):
        path = os.path.join(library_root, "steamapps", "common", "Hearts of Iron IV")
        os.makedirs(path, exist_ok=True)
        return path

    def test_finds_the_game_in_the_default_steam_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            steam = self._fake_steam(os.path.join(tmp, "Steam"))
            expected = self._install_game(steam)
            with mock.patch.object(game_paths, "_steam_roots", return_value=[steam]), \
                 mock.patch.object(game_paths, "_pinned", return_value={}):
                self.assertEqual(game_paths.find_base_game(), expected)

    def test_follows_libraryfolders_to_a_second_drive(self):
        with tempfile.TemporaryDirectory() as tmp:
            other = os.path.join(tmp, "SteamLibrary")
            os.makedirs(os.path.join(other, "steamapps"), exist_ok=True)
            steam = self._fake_steam(os.path.join(tmp, "Steam"), library=other)
            expected = self._install_game(other)      # game is NOT in the main root
            with mock.patch.object(game_paths, "_steam_roots", return_value=[steam]), \
                 mock.patch.object(game_paths, "_pinned", return_value={}):
                self.assertEqual(game_paths.find_base_game(), expected)

    def test_a_pinned_path_wins_over_the_search(self):
        with tempfile.TemporaryDirectory() as tmp:
            manual = os.path.join(tmp, "elsewhere")
            os.makedirs(manual)
            with mock.patch.object(game_paths, "_pinned",
                                   return_value={"base_game": manual}):
                self.assertEqual(game_paths.find_base_game(), manual)

    def test_missing_game_returns_empty_rather_than_raising(self):
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(game_paths, "_steam_roots", return_value=[tmp]), \
                 mock.patch.object(game_paths, "_pinned", return_value={}):
                self.assertEqual(game_paths.find_base_game(), "")
                self.assertEqual(game_paths.find_workshop(), "")


class PinnedPathTests(unittest.TestCase):
    """The Settings screen writes these; "Detect Again" clears them."""

    def _isolated(self, tmp):
        return mock.patch.multiple(game_paths,
                                   CONFIG_DIR=tmp,
                                   PATHS_FILE=os.path.join(tmp, "game_paths.json"))

    def test_saving_then_clearing_a_pin(self):
        with tempfile.TemporaryDirectory() as tmp, self._isolated(tmp):
            game_paths.save_pinned(base_game=r"D:\Games\HOI4")
            self.assertEqual(game_paths._pinned()["base_game"], r"D:\Games\HOI4")

            game_paths.save_pinned(base_game="")          # "Detect Again"
            self.assertNotIn("base_game", game_paths._pinned())

    def test_none_leaves_the_other_setting_untouched(self):
        with tempfile.TemporaryDirectory() as tmp, self._isolated(tmp):
            game_paths.save_pinned(base_game="/games/hoi4", workshop="/games/workshop")
            game_paths.save_pinned(base_game="/elsewhere")   # workshop not mentioned

            pinned = game_paths._pinned()
            self.assertEqual(pinned["base_game"], "/elsewhere")
            self.assertEqual(pinned["workshop"], "/games/workshop")

    def test_a_pin_pointing_at_a_deleted_folder_is_ignored(self):
        with tempfile.TemporaryDirectory() as tmp, self._isolated(tmp):
            game_paths.save_pinned(base_game=os.path.join(tmp, "gone"))
            with mock.patch.object(game_paths, "_steam_roots", return_value=[]):
                self.assertEqual(game_paths.find_base_game(), "")


class UserDirTests(unittest.TestCase):
    def test_windows_covers_onedrive_and_localised_documents(self):
        with mock.patch.object(sys, "platform", "win32"):
            paths = game_paths.user_dir_candidates()
        joined = " ".join(paths)
        self.assertIn("OneDrive", joined)
        self.assertIn("Belgeler", joined)   # Turkish Windows names it this
        self.assertTrue(all("Hearts of Iron IV" in p for p in paths))

    def test_linux_uses_xdg_and_the_proton_prefix(self):
        with mock.patch.object(sys, "platform", "linux"):
            paths = game_paths.user_dir_candidates()
        joined = " ".join(paths)
        self.assertIn(os.path.join(".local", "share"), joined)
        self.assertIn("compatdata", joined)   # Proton keeps its own Documents
        self.assertNotIn("OneDrive", joined)


if __name__ == "__main__":
    unittest.main()
