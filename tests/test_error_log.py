import os
import tempfile
import unittest

from app import error_log


def line(msg, ts="18:59:02", source="trigger.cpp:540"):
    return f"[{ts}][no_game_date][{source}]: {msg}"


class ParseErrorsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.mod_root = os.path.join(self.tmp.name, "mod")
        os.makedirs(os.path.join(self.mod_root, "events"))
        with open(os.path.join(self.mod_root, "events", "mine.txt"), "w",
                  encoding="utf-8") as handle:
            handle.write("# a real file, so the path check can resolve it\n")

    def write_log(self, lines):
        path = os.path.join(self.tmp.name, "error.log")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write("\n".join(lines) + "\n")
        return path

    def test_identical_messages_collapse_with_a_count(self):
        path = self.write_log([line("boom")] * 5)
        rows = error_log.parse_errors(path)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][5], 5)

    def test_first_timestamp_is_kept(self):
        path = self.write_log([line("boom", ts="01:00:00"),
                               line("boom", ts="02:00:00")])
        self.assertEqual(error_log.parse_errors(path)[0][0], "01:00:00")

    def test_reads_the_whole_file_not_the_tail(self):
        """Script errors are reported while the game loads - the very start
        of the log. Reading only the last N lines hid every one of them."""
        lines = [line("events/mine.txt:10: broken")] + [line(f"noise {i}") for i in range(3000)]
        path = self.write_log(lines)
        rows = error_log.parse_errors(path, mod_root=self.mod_root)
        self.assertTrue(any(row[3] for row in rows))

    def test_cap_keeps_mod_rows_and_drops_others(self):
        lines = [line(f"unrelated {i}") for i in range(50)]
        lines.append(line("events/mine.txt:10: broken"))
        path = self.write_log(lines)
        rows = error_log.parse_errors(path, mod_root=self.mod_root, limit=10)
        self.assertEqual(len(rows), 10)
        self.assertEqual(sum(1 for row in rows if row[3]), 1)

    def test_continuation_lines_are_merged(self):
        """The game breaks long quoted errors across lines, and it's the
        trailing half that names the file."""
        path = self.write_log([
            line('Error: "Unknown trigger-type: x, near line: 12'),
            'Unknown trigger-type: x, near line: 13" in file: "events/mine.txt" near line: 14',
        ])
        rows = error_log.parse_errors(path, mod_root=self.mod_root)
        self.assertEqual(len(rows), 1)
        self.assertIn("events/mine.txt", rows[0][2])
        self.assertTrue(rows[0][3], "merged text should make the row mod-relevant")

    def test_continuation_after_a_repeat_attaches_to_the_right_row(self):
        path = self.write_log([
            line("first"),
            line("second"),
            line("first"),                    # folds into row 0
            'tail of the first message',      # must attach to row 0, not row 1
        ])
        rows = error_log.parse_errors(path)
        self.assertIn("tail of the first message", rows[0][2])
        self.assertEqual(rows[1][2], "second")

    def test_noise_is_filtered(self):
        path = self.write_log([line("Could not find animation blah"), line("real problem")])
        rows = error_log.parse_errors(path)
        self.assertEqual([row[2] for row in rows], ["real problem"])

    def test_mod_file_carries_the_line_number(self):
        path = self.write_log([line("events/mine.txt:100: create_ship failed")])
        rows = error_log.parse_errors(path, mod_root=self.mod_root)
        self.assertEqual(rows[0][4], os.path.join("events", "mine.txt") + ":100")

    def test_other_mods_files_are_not_claimed_as_ours(self):
        path = self.write_log([line("events/somebody_else.txt:5: broken")])
        rows = error_log.parse_errors(path, mod_root=self.mod_root)
        self.assertFalse(rows[0][3])

    def test_start_offset_limits_to_the_new_tail(self):
        path = self.write_log([line("old")])
        offset = os.path.getsize(path)
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(line("new") + "\n")
        rows = error_log.parse_errors(path, start_offset=offset)
        self.assertEqual([row[2] for row in rows], ["new"])

    def test_offset_past_the_end_means_a_fresh_log(self):
        """The game truncates error.log on startup, so an offset taken
        before the run can be past the new end - that must not hide it all."""
        path = self.write_log([line("after restart")])
        rows = error_log.parse_errors(path, start_offset=10 ** 6)
        self.assertEqual([row[2] for row in rows], ["after restart"])

    def test_missing_file_returns_empty(self):
        self.assertEqual(error_log.parse_errors(os.path.join(self.tmp.name, "nope.log")), [])


class HintTest(unittest.TestCase):
    def test_known_pattern_gets_a_hint(self):
        self.assertTrue(error_log.hint_for("No valid option for event foo.1"))

    def test_unknown_pattern_gets_none(self):
        self.assertIsNone(error_log.hint_for("something nobody has seen before"))


if __name__ == "__main__":
    unittest.main()
