import json
import os
import tempfile
import unittest
from unittest import mock

from app import test_play


def write_mod_file(mod_dir, filename, name, path):
    os.makedirs(mod_dir, exist_ok=True)
    with open(os.path.join(mod_dir, filename), "w", encoding="utf-8") as handle:
        handle.write(f'name="{name}"\npath="{path.replace(os.sep, "/")}"\n')


class DescriptorLookupTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.user_dir = self.tmp.name
        self.mod_dir = os.path.join(self.user_dir, "mod")
        self.addCleanup(self.tmp.cleanup)

    def test_matches_on_folder_not_name(self):
        """Two mods can share a display name - the one whose path points at
        the open folder has to win, or Test Play launches the wrong mod."""
        write_mod_file(self.mod_dir, "a.mod", "My HOI4 Mod", r"C:\somewhere\a")
        write_mod_file(self.mod_dir, "b.mod", "My HOI4 Mod", r"C:\somewhere\b")
        entry = test_play.entry_for_mod(r"C:\somewhere\b", "My HOI4 Mod", self.user_dir)
        self.assertEqual(entry, "mod/b.mod")

    def test_falls_back_to_name(self):
        write_mod_file(self.mod_dir, "a.mod", "Cool Mod", r"C:\elsewhere\a")
        entry = test_play.entry_for_mod(r"C:\not\exported\yet", "Cool Mod", self.user_dir)
        self.assertEqual(entry, "mod/a.mod")

    def test_none_when_never_exported(self):
        write_mod_file(self.mod_dir, "a.mod", "Cool Mod", r"C:\elsewhere\a")
        self.assertIsNone(test_play.entry_for_mod(r"C:\other", "Other Mod", self.user_dir))

    def test_no_mod_folder_is_not_an_error(self):
        self.assertEqual(test_play.descriptor_entries(self.user_dir), [])


class DlcLoadTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.user_dir = self.tmp.name
        self.addCleanup(self.tmp.cleanup)

    def test_preserves_unrelated_keys(self):
        """disabled_dlcs belongs to the user, not to us - a test run that
        silently re-enabled their turned-off DLC would change the game."""
        path = os.path.join(self.user_dir, test_play.DLC_LOAD)
        with open(path, "w", encoding="utf-8") as handle:
            json.dump({"enabled_mods": ["mod/x.mod"],
                       "disabled_dlcs": ["Waking the Tiger"]}, handle)

        data = test_play.read_dlc_load(self.user_dir)
        data["enabled_mods"] = ["mod/test.mod"]
        test_play.write_dlc_load(data, self.user_dir)

        with open(path, encoding="utf-8") as handle:
            written = json.load(handle)
        self.assertEqual(written["disabled_dlcs"], ["Waking the Tiger"])
        self.assertEqual(written["enabled_mods"], ["mod/test.mod"])

    def test_missing_file_gives_usable_shape(self):
        data = test_play.read_dlc_load(self.user_dir)
        self.assertEqual(data, {"enabled_mods": [], "disabled_dlcs": []})

    def test_corrupt_file_does_not_raise(self):
        with open(os.path.join(self.user_dir, test_play.DLC_LOAD), "w",
                  encoding="utf-8") as handle:
            handle.write("{ not json")
        self.assertEqual(test_play.read_dlc_load(self.user_dir)["enabled_mods"], [])


class ExportForTestTest(unittest.TestCase):
    """Test Play used to stop at 'export it first'; it now does that step
    itself, and has to hand back the entry for the descriptor it wrote."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.mod_root = os.path.join(self.tmp.name, "source")
        os.makedirs(os.path.join(self.mod_root, "events"))
        self.own = os.path.join(self.mod_root, "events", "mine.txt")
        with open(self.own, "w", encoding="utf-8") as handle:
            handle.write("country_event = { id = mine.1 }\n")

        self.user_dir = os.path.join(self.tmp.name, "user")
        os.makedirs(self.user_dir)
        patcher = mock.patch("app.mod_export.find_user_dir", return_value=self.user_dir)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_exports_and_returns_the_entry_it_wrote(self):
        from app import mod_export
        mod_export.record_created(self.mod_root, [self.own])

        entry = test_play.export_for_test(self.mod_root, "Cool Mod")
        self.assertEqual(entry, "mod/Cool_Mod.mod")
        self.assertTrue(os.path.isfile(os.path.join(self.user_dir, "mod", "Cool_Mod.mod")))
        self.assertTrue(os.path.isfile(
            os.path.join(self.user_dir, "mod", "Cool_Mod", "events", "mine.txt")))

    def test_entry_is_not_guessed_from_the_display_name(self):
        """The submod lands in the launcher's folder, not at mod_root, so
        looking the entry back up by path misses and would fall through to
        matching on name - which picks the wrong mod when two share one."""
        from app import mod_export
        mod_export.record_created(self.mod_root, [self.own])
        write_mod_file(os.path.join(self.user_dir, "mod"), "impostor.mod",
                       "Cool Mod", r"C:\somewhere\else")

        entry = test_play.export_for_test(self.mod_root, "Cool Mod")
        self.assertEqual(entry, "mod/Cool_Mod.mod")

    def test_nothing_of_our_own_is_a_clear_error(self):
        with self.assertRaises(RuntimeError) as caught:
            test_play.export_for_test(self.mod_root, "Cool Mod")
        self.assertIn("Full copy", str(caught.exception))


class PendingRestoreTest(unittest.TestCase):
    """Closing Mod Maker while the game is still running used to leave the
    launcher holding only the test mod, with the user's own selection gone."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.user_dir = self.tmp.name
        self.addCleanup(self.tmp.cleanup)
        self.marker = os.path.join(self.user_dir, "restore.json")
        patcher = mock.patch.object(test_play, "PENDING_RESTORE", self.marker)
        patcher.start()
        self.addCleanup(patcher.stop)

        with open(os.path.join(self.user_dir, test_play.DLC_LOAD), "w",
                  encoding="utf-8") as handle:
            json.dump({"enabled_mods": ["mod/theirs.mod"], "disabled_dlcs": []}, handle)

    def _clobber(self):
        """What launch() does to dlc_load.json before starting the game."""
        previous = test_play.read_dlc_load(self.user_dir)
        test_play._remember_restore(previous, self.user_dir)
        test_play.write_dlc_load({"enabled_mods": ["mod/test.mod"],
                                  "disabled_dlcs": []}, self.user_dir)

    def test_restores_after_an_interrupted_run(self):
        self._clobber()
        self.assertTrue(test_play.restore_pending())
        self.assertEqual(test_play.read_dlc_load(self.user_dir)["enabled_mods"],
                         ["mod/theirs.mod"])

    def test_restore_is_consumed_once(self):
        self._clobber()
        test_play.restore_pending()
        self.assertFalse(os.path.exists(self.marker))
        self.assertFalse(test_play.restore_pending())

    def test_nothing_pending_is_a_no_op(self):
        self.assertFalse(test_play.restore_pending())

    def test_corrupt_marker_does_not_raise(self):
        with open(self.marker, "w", encoding="utf-8") as handle:
            handle.write("garbage")
        self.assertFalse(test_play.restore_pending())


if __name__ == "__main__":
    unittest.main()
