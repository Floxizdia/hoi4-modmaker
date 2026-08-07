import os
import tempfile
import unittest

from app import refactor


FOCUS_TREE = """focus_tree = {
\tid = my_tree
\tfocus = {
\t\tid = my_focus
\t\tcompletion_reward = { country_event = germany.1 }
\t}
\tfocus = {
\t\tid = my_focus_two
\t\tprerequisite = { focus = my_focus }
\t}
}
"""

EVENTS = """country_event = {
\tid = germany.1
}
country_event = {
\tid = germany.14
\timmediate = { country_event = germany.1 }
}
"""

LOC = ('l_english:\n'
       ' my_focus:0 "Reform the Army"\n'
       ' my_focus_desc:0 "Talks about my_focus in prose"\n'
       ' my_focus_two:0 "Another focus"\n'
       ' germany.1.t:0 "Title"\n'
       ' germany.1.a:0 "Option A"\n'
       ' germany.14.t:0 "Other event"\n')


class RefactorTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.mod = self.tmp.name
        self.tree = self.write("common/national_focus/t.txt", FOCUS_TREE)
        self.events = self.write("events/ger.txt", EVENTS)
        self.loc = self.write("localisation/english/t_l_english.yml", LOC, "utf-8-sig")

    def write(self, rel, text, encoding="utf-8"):
        path = os.path.join(self.mod, rel.replace("/", os.sep))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding=encoding) as handle:
            handle.write(text)
        return path

    def read(self, path, encoding="utf-8"):
        with open(path, encoding=encoding) as handle:
            return handle.read()

    def rename(self, old, new):
        plan = refactor.plan_rename(self.mod, old, new)
        return refactor.apply_plan(plan)


class LocKeyRuleTest(unittest.TestCase):
    """Prefix matching would rewrite my_focus_two when renaming my_focus,
    so derived keys are matched by an explicit rule instead."""

    def test_the_key_itself(self):
        self.assertTrue(refactor.loc_key_belongs_to("my_focus", "my_focus"))

    def test_derived_desc(self):
        self.assertTrue(refactor.loc_key_belongs_to("my_focus_desc", "my_focus"))

    def test_event_sub_keys(self):
        self.assertTrue(refactor.loc_key_belongs_to("germany.1.t", "germany.1"))
        self.assertTrue(refactor.loc_key_belongs_to("germany.1.a", "germany.1"))

    def test_a_different_key_that_merely_starts_the_same(self):
        self.assertFalse(refactor.loc_key_belongs_to("my_focus_two", "my_focus"))

    def test_a_longer_event_number(self):
        self.assertFalse(refactor.loc_key_belongs_to("germany.14.t", "germany.1"))


class PlanTest(RefactorTestCase):
    def test_plan_finds_definition_and_uses(self):
        plan = refactor.plan_rename(self.mod, "my_focus", "great_reform")
        files = {entry["rel"] for entry in plan}
        self.assertIn(os.path.join("common", "national_focus", "t.txt"), files)
        self.assertIn(os.path.join("localisation", "english", "t_l_english.yml"), files)

    def test_plan_changes_nothing_on_disk(self):
        before = self.read(self.tree)
        refactor.plan_rename(self.mod, "my_focus", "great_reform")
        self.assertEqual(self.read(self.tree), before)

    def test_unknown_id_gives_an_empty_plan(self):
        self.assertEqual(refactor.plan_rename(self.mod, "does_not_exist", "x"), [])

    def test_renaming_to_itself_is_empty(self):
        self.assertEqual(refactor.plan_rename(self.mod, "my_focus", "my_focus"), [])

    def test_summary_counts_files_and_lines(self):
        plan = refactor.plan_rename(self.mod, "my_focus", "great_reform")
        files, lines = refactor.plan_summary(plan)
        self.assertEqual(files, 2)
        self.assertEqual(lines, 4)


class RenameScriptTest(RefactorTestCase):
    def test_definition_and_reference_both_move(self):
        self.rename("my_focus", "great_reform")
        text = self.read(self.tree)
        self.assertIn("id = great_reform", text)
        self.assertIn("prerequisite = { focus = great_reform }", text)

    def test_a_longer_id_sharing_the_prefix_is_untouched(self):
        self.rename("my_focus", "great_reform")
        self.assertIn("id = my_focus_two", self.read(self.tree))

    def test_a_longer_event_number_is_untouched(self):
        self.rename("germany.1", "germany.100")
        text = self.read(self.events)
        self.assertIn("id = germany.100", text)
        self.assertIn("id = germany.14", text)

    def test_references_in_other_files_move_too(self):
        self.rename("germany.1", "germany.100")
        self.assertIn("country_event = germany.100", self.read(self.tree))


class RenameLocTest(RefactorTestCase):
    def test_key_and_derived_key_move(self):
        self.rename("my_focus", "great_reform")
        text = self.read(self.loc, "utf-8-sig")
        self.assertIn(' great_reform:0 ', text)
        self.assertIn(' great_reform_desc:0 ', text)

    def test_the_english_text_is_left_alone(self):
        """Prose that happens to mention the id is not a reference."""
        self.rename("my_focus", "great_reform")
        self.assertIn('"Talks about my_focus in prose"', self.read(self.loc, "utf-8-sig"))

    def test_an_unrelated_key_survives(self):
        self.rename("my_focus", "great_reform")
        self.assertIn(' my_focus_two:0 ', self.read(self.loc, "utf-8-sig"))

    def test_event_option_keys_move(self):
        self.rename("germany.1", "germany.100")
        text = self.read(self.loc, "utf-8-sig")
        self.assertIn(' germany.100.t:0 ', text)
        self.assertIn(' germany.100.a:0 ', text)
        self.assertIn(' germany.14.t:0 ', text)

    def test_the_bom_survives(self):
        """HOI4 rejects a localisation file without one."""
        self.rename("my_focus", "great_reform")
        with open(self.loc, "rb") as handle:
            self.assertEqual(handle.read(3), b"\xef\xbb\xbf")


class ApplyTest(RefactorTestCase):
    def test_a_backup_is_left(self):
        self.rename("my_focus", "great_reform")
        self.assertTrue(os.path.isfile(self.tree + ".bak"))

    def test_backup_holds_the_original(self):
        original = self.read(self.tree)
        self.rename("my_focus", "great_reform")
        self.assertEqual(self.read(self.tree + ".bak"), original)

    def test_a_stale_plan_is_skipped_not_forced(self):
        """A file edited between preview and apply must not be rewritten
        from line numbers that no longer mean anything."""
        plan = refactor.plan_rename(self.mod, "my_focus", "great_reform")
        self.write("common/national_focus/t.txt", "focus_tree = {\n}\n")
        written, skipped = refactor.apply_plan(plan)
        self.assertIn(self.tree, skipped)
        self.assertNotIn(self.tree, written)

    def test_untouched_files_are_not_rewritten(self):
        before = self.read(self.events)
        self.rename("my_focus", "great_reform")
        self.assertEqual(self.read(self.events), before)
        self.assertFalse(os.path.isfile(self.events + ".bak"))

    def test_rename_is_undoable(self):
        from app import undo
        undo.clear()
        original = self.read(self.tree)
        self.rename("my_focus", "great_reform")
        self.assertTrue(undo.can_undo())
        while undo.can_undo():
            undo.undo()
        self.assertEqual(self.read(self.tree), original)


class DefinitionSpanTest(unittest.TestCase):
    """Deleting needs to know where a thing is *defined*, which the game
    writes two different ways."""

    def test_keyed_block_carrying_its_own_id(self):
        text = "focus = {\n\tid = my_focus\n}\n"
        self.assertEqual(len(refactor.find_definition_spans(text, "my_focus")), 1)

    def test_block_named_after_the_id(self):
        text = "my_decision = {\n\tcost = 5\n}\n"
        self.assertEqual(len(refactor.find_definition_spans(text, "my_decision")), 1)

    def test_a_mere_reference_is_not_a_definition(self):
        text = "focus = {\n\tid = other\n\tprerequisite = { focus = my_focus }\n}\n"
        self.assertEqual(refactor.find_definition_spans(text, "my_focus"), [])

    def test_a_longer_name_is_not_matched(self):
        text = "my_focus_two = {\n\tcost = 1\n}\n"
        self.assertEqual(refactor.find_definition_spans(text, "my_focus"), [])


class DeleteTest(RefactorTestCase):
    def delete(self, ref_id):
        plan, dangling = refactor.plan_delete(self.mod, ref_id)
        refactor.apply_plan(plan)
        return dangling

    def test_the_definition_goes(self):
        self.delete("my_focus")
        self.assertNotIn("id = my_focus\n", self.read(self.tree))

    def test_the_rest_of_the_file_survives(self):
        self.delete("my_focus")
        text = self.read(self.tree)
        self.assertIn("id = my_focus_two", text)
        self.assertIn("id = my_tree", text)

    def test_braces_stay_balanced(self):
        self.delete("my_focus")
        text = self.read(self.tree)
        self.assertEqual(text.count("{"), text.count("}"))

    def test_localisation_keys_go_too(self):
        self.delete("my_focus")
        text = self.read(self.loc, "utf-8-sig")
        self.assertNotIn(" my_focus:0", text)
        self.assertNotIn(" my_focus_desc:0", text)

    def test_unrelated_localisation_survives(self):
        self.delete("my_focus")
        self.assertIn(" my_focus_two:0", self.read(self.loc, "utf-8-sig"))

    def test_references_are_reported_not_removed(self):
        """A reference sits inside somebody else's effect block; cutting the
        line could change what that block means."""
        dangling = self.delete("my_focus")
        self.assertTrue(dangling)
        self.assertIn("prerequisite = { focus = my_focus }", self.read(self.tree))

    def test_the_dangling_report_points_at_a_real_line(self):
        plan, dangling = refactor.plan_delete(self.mod, "my_focus")
        reference = dangling[0]
        lines = self.read(os.path.join(self.mod, reference["file"])).splitlines()
        self.assertIn("my_focus", lines[reference["line"] - 1])

    def test_deleting_an_event_takes_its_option_keys(self):
        self.delete("germany.1")
        text = self.read(self.loc, "utf-8-sig")
        self.assertNotIn(" germany.1.t:0", text)
        self.assertNotIn(" germany.1.a:0", text)
        self.assertIn(" germany.14.t:0", text)

    def test_a_backup_is_left(self):
        self.delete("my_focus")
        self.assertTrue(os.path.isfile(self.tree + ".bak"))

    def test_delete_is_undoable(self):
        from app import undo
        undo.clear()
        original = self.read(self.tree)
        self.delete("my_focus")
        while undo.can_undo():
            undo.undo()
        self.assertEqual(self.read(self.tree), original)

    def test_unknown_id_removes_nothing(self):
        plan, dangling = refactor.plan_delete(self.mod, "never_defined")
        self.assertEqual(plan, [])
        self.assertEqual(dangling, [])


class ConflictTest(RefactorTestCase):
    def test_an_existing_name_is_reported(self):
        self.assertTrue(refactor.conflicts(self.mod, "my_focus_two"))

    def test_a_free_name_is_not(self):
        self.assertEqual(refactor.conflicts(self.mod, "nothing_uses_this"), [])


if __name__ == "__main__":
    unittest.main()
