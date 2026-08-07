import os
import tempfile
import unittest
import zipfile

from app import snapshots


class SnapshotTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.mod = os.path.join(self.tmp.name, "mymod")
        os.makedirs(os.path.join(self.mod, "events"))
        self.script = os.path.join(self.mod, "events", "mine.txt")
        self.write(self.script, "version one")

    def write(self, path, text):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)

    def read(self, path):
        with open(path, encoding="utf-8") as handle:
            return handle.read()


class RestoreSafetyTest(SnapshotTestCase):
    """Restoring is the one destructive action on the Settings screen, and
    picking the wrong entry used to destroy the current files outright."""

    def test_restore_brings_back_the_old_content(self):
        snap, _ = snapshots.create(self.mod)
        self.write(self.script, "version two")
        count, _safety = snapshots.restore(self.mod, snap)
        self.assertEqual(self.read(self.script), "version one")
        self.assertGreaterEqual(count, 1)

    def test_current_state_is_snapshotted_before_being_overwritten(self):
        snap, _ = snapshots.create(self.mod)
        self.write(self.script, "work I would hate to lose")
        _count, safety = snapshots.restore(self.mod, snap)

        self.assertIsNotNone(safety)
        with zipfile.ZipFile(safety) as archive:
            saved = archive.read("events/mine.txt").decode("utf-8")
        self.assertEqual(saved, "work I would hate to lose")

    def test_the_safety_snapshot_can_be_restored_in_turn(self):
        snap, _ = snapshots.create(self.mod)
        self.write(self.script, "work I would hate to lose")
        _count, safety = snapshots.restore(self.mod, snap)
        self.assertEqual(self.read(self.script), "version one")

        snapshots.restore(self.mod, safety, safety_snapshot=False)
        self.assertEqual(self.read(self.script), "work I would hate to lose")

    def test_opt_out_skips_it(self):
        snap, _ = snapshots.create(self.mod)
        _count, safety = snapshots.restore(self.mod, snap, safety_snapshot=False)
        self.assertIsNone(safety)


class InsideGuardTest(SnapshotTestCase):
    def test_relative_mod_root_still_restores(self):
        """The guard compared a possibly-relative target against an absolute
        root, so a relative mod folder silently restored zero files."""
        snap, _ = snapshots.create(self.mod)
        self.write(self.script, "changed")
        cwd = os.getcwd()
        os.chdir(self.tmp.name)
        try:
            count, _ = snapshots.restore("mymod", os.path.abspath(snap))
        finally:
            os.chdir(cwd)
        self.assertGreaterEqual(count, 1)
        self.assertEqual(self.read(self.script), "version one")

    def test_sibling_folder_with_a_shared_prefix_is_outside(self):
        self.assertFalse(snapshots._inside(self.mod, self.mod + "-backup"))

    def test_parent_traversal_is_outside(self):
        self.assertFalse(
            snapshots._inside(self.mod, os.path.join(self.mod, "..", "elsewhere.txt")))

    def test_a_real_child_is_inside(self):
        self.assertTrue(snapshots._inside(self.mod, self.script))

    def test_escaping_zip_entry_is_skipped(self):
        outside = os.path.join(self.tmp.name, "pwned.txt")
        evil = os.path.join(self.tmp.name, "evil.zip")
        with zipfile.ZipFile(evil, "w") as archive:
            archive.writestr("../pwned.txt", "should never be written")
        snapshots.restore(self.mod, evil, safety_snapshot=False)
        self.assertFalse(os.path.exists(outside))


if __name__ == "__main__":
    unittest.main()
