"""HOI4 Mod Maker: a standalone desktop tool that builds HOI4 mods through
visual editors and wizards - and a code editor for those who'd rather type.

Navigation is a grouped sidebar instead of a tab row: twelve sections no
longer fight for horizontal space, and heavy sections only scan the mod
the first time they're shown.
"""

import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox

from app.settings import SettingsTab
from app.events import EventsTab
from app.decisions import DecisionsTab
from app.ideas import IdeasTab
from app.localisation import LocalisationTab
from app.validator_tab import ValidatorTab
from app.country_tab import CountryTab
from app.ideology_tab import IdeologyTab
from app.faction_tab import FactionTab
from app.oob_tab import OobTab
from app.bookmark_tab import BookmarkTab
from app.ai_strategy_tab import AiStrategyTab
from app.diplo_action_tab import DiploActionTab
from app.opinion_modifier_tab import OpinionModifierTab
from app.on_action_tab import OnActionTab
from app.peace_modifier_tab import PeaceModifierTab
from app.state_tab import StateTab
from app.war_goal_tab import WarGoalTab
from app.decision_category_tab import DecisionCategoryTab
from app.equipment_tab import EquipmentTab
from app.agency_upgrade_tab import AgencyUpgradeTab
from app.icon_coverage_tab import IconCoverageTab
from app.error_log_tab import ErrorLogTab
from app.flag_tab import FlagTab
from app.map_tab import MapTab
from app.railway_tab import RailwayTab
from app.scripted_tab import ScriptedTab
from app.division_tab import DivisionTab
from app.translation_tab import TranslationTab
from app.refactor_tab import RefactorTab
from app.guides_tab import GuidesTab
from app.code_editor import CodeEditorTab
from app.tech_tab import TechTab
from app.music_tab import MusicTab
from app.units_tab import UnitsTab
from app.diff_tab import DiffTab
from app.bulk_replace import BulkReplaceTab
from app.loc_coverage_tab import LocCoverageTab
from app.character_editor_tab import CharacterEditorTab
from app.trait_tab import TraitTab
from app.idea_gallery import IdeaGalleryTab
from app.compat_tab import CompatTab
from app.load_order_tab import LoadOrderTab
from app.event_chain_tab import EventChainTab
from app.mod_stats_tab import ModStatsTab
from app.tree_diff_tab import TreeDiffTab
from app import global_search
from app import undo
from app.focus_tree import FocusTreeTab
from app.home import HomeScreen
from app.nav import HeaderBar, NavRail
from app.state import state
from app import theme

SECTIONS = [
    ("VISUAL", [
        ("guides", "Guides", GuidesTab),
        ("open_mod", "Open Mod", FocusTreeTab),
        ("map", "Map", MapTab),
        ("railways", "Railways & Supply", RailwayTab),
    ]),
    ("CONTENT", [
        ("settings", "Settings", SettingsTab),
        ("stats", "Mod Stats", ModStatsTab),
        ("focus", "Focus Tree", FocusTreeTab),
        ("tree_diff", "Tree Diff", TreeDiffTab),
        ("events", "Events", EventsTab),
        ("event_chain", "Event Chains", EventChainTab),
        ("decisions", "Decisions", DecisionsTab),
        ("ideas", "Ideas / Spirits", IdeasTab),
        ("idea_gallery", "Idea Gallery", IdeaGalleryTab),
        ("country", "Country", CountryTab),
        ("flags", "Flags", FlagTab),
        ("ideology", "Ideologies", IdeologyTab),
        ("factions", "Factions", FactionTab),
        ("ai_strategy", "AI Strategy", AiStrategyTab),
        ("diplo_action", "Diplomatic Actions", DiploActionTab),
        ("opinion_modifier", "Opinion Modifiers", OpinionModifierTab),
        ("on_action", "On Actions", OnActionTab),
        ("scripted", "Scripted Effects", ScriptedTab),
        ("peace_modifier", "Peace Conference", PeaceModifierTab),
        ("state_edit", "States", StateTab),
        ("war_goal", "War Goals", WarGoalTab),
        ("decision_category", "Decision Categories", DecisionCategoryTab),
        ("equipment", "Equipment", EquipmentTab),
        ("agency_upgrade", "Agency Upgrades", AgencyUpgradeTab),
        ("characters", "Characters", CharacterEditorTab),
        ("traits", "Traits", TraitTab),
        ("tech", "Tech", TechTab),
        ("units", "Units", UnitsTab),
        ("divisions", "Divisions", DivisionTab),
        ("oob", "Starting Forces", OobTab),
        ("game_setup", "Game Setup", BookmarkTab),
    ]),
    ("TOOLS", [
        ("music", "Music", MusicTab),
        ("code", "Code", CodeEditorTab),
        ("loc", "Localisation", LocalisationTab),
        ("loc_coverage", "Loc Coverage", LocCoverageTab),
        ("translation", "Translation", TranslationTab),
        ("validate", "Validate", ValidatorTab),
        ("icon_coverage", "Icon Coverage", IconCoverageTab),
        ("error_log", "Test Play & Errors", ErrorLogTab),
        ("diff", "What Changed?", DiffTab),
        ("replace", "Find & Replace", BulkReplaceTab),
        ("refactor", "Refactor", RefactorTab),
        ("compat", "Compatibility", CompatTab),
        ("load_order", "Load Order", LoadOrderTab),
    ]),
]

# "Focus Tree" reuses the same rich canvas editor as "Open Mod" (that's
# always been where it actually lived - Open Mod's tree picker, drag/drop
# canvas and focus-properties panel *is* the visual focus tree editor) so
# a modder looking for "the focus tree tool" finds it under the name that
# says so, without splitting one editor's state across two half-built tabs.
TAB_ALIASES = {"focus": "open_mod"}

#: What Ctrl+1..9 open, written out instead of taken from the order of
#: SECTIONS. Deriving them from the list meant that inserting one screen
#: silently remapped every shortcut - the kind of change that breaks a
#: user's muscle memory without producing a single error message.
SHORTCUT_KEYS = ["open_mod", "map", "railways", "settings", "stats",
                 "focus", "tree_diff", "events", "event_chain"]


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("HOI4 Mod Maker")
        # The executable icon and the live Windows title-bar icon must both
        # use the bundled branding asset.  _MEIPASS is PyInstaller's asset
        # root; the fallback keeps `python main.py` working in development.
        asset_root = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
        icon_path = os.path.join(asset_root, "assets", "app_icon.ico")
        if os.path.isfile(icon_path):
            try:
                # `-default` is a Windows-only Tk option; on X11 it raises and
                # .ico isn't a format Tk can read there anyway, so the window
                # keeps the toolkit's own icon rather than failing to open
                self.iconbitmap(default=icon_path)
            except tk.TclError:
                pass
        self.geometry("1320x840")
        self.minsize(1000, 660)
        theme.apply(self)

        self.workspace = None
        self.tabs = {}
        self._tab_classes = {}
        self.buttons = {}
        self.current_key = None
        self._auto_snap_on = False
        self._auto_snap_minutes = 15
        self._auto_snap_job = None

        # a test run that was interrupted (app closed while the game was
        # still up) leaves the launcher holding only the test mod; put the
        # user's own selection back before anything else happens
        from app import test_play
        test_play.restore_pending()

        self.home = HomeScreen(self, on_new_mod=self._show_new_mod, on_open_mod=self._show_open_mod)
        self.home.pack(fill="both", expand=True)

    # ---- workspace ----

    def _build_workspace(self):
        if self.workspace is not None:
            return
        self.workspace = ttk.Frame(self)

        self.header = HeaderBar(self.workspace, on_home=self._show_home)
        self.header.pack(fill="x")
        state.subscribe(self._refresh_mod_label)

        body = ttk.Frame(self.workspace)
        body.pack(fill="both", expand=True)

        self.rail = NavRail(
            body,
            [(section, [(key, label) for key, label, _ in entries])
             for section, entries in SECTIONS],
            on_select=self.show,
        )
        self.rail.pack(side="left", fill="y")

        self.content = ttk.Frame(body, padding=(2, 0, 0, 0))
        self.content.pack(side="left", fill="both", expand=True)

        # Most editor tabs create many widgets, lists and preview surfaces.
        # Register their factories now but instantiate a tab only when the
        # user actually opens it.  This keeps opening a mod and switching
        # between Home/Focus Tree responsive on large installations.
        self._tab_classes = {
            key: cls
            for _, entries in SECTIONS
            for key, _, cls in entries
            if key not in TAB_ALIASES
        }

        self._flat_keys = [key for _, entries in SECTIONS for key, _, _ in entries]

        self.show("open_mod")
        self.bind_all("<Control-k>", self._open_search)
        self.bind_all("<Control-z>", self._undo)
        self.bind_all("<Control-y>", self._redo)
        self.bind_all("<Control-Shift-Key-Z>", self._redo)
        self.bind_all("<Control-f>", self._focus_search)
        self.bind_all("<Control-s>", self._save_current)
        for i, key in enumerate(SHORTCUT_KEYS[:9], start=1):
            self.bind_all(f"<Control-Key-{i}>", lambda e, k=key: self.show(k))
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _tab(self, key):
        """Return an existing tab or construct its canonical screen once."""
        canonical_key = TAB_ALIASES.get(key, key)
        tab = self.tabs.get(canonical_key)
        if tab is None:
            tab_class = self._tab_classes[canonical_key]
            tab = tab_class(self.content)
            self.tabs[canonical_key] = tab
            for alias, target in TAB_ALIASES.items():
                if target == canonical_key:
                    self.tabs[alias] = tab
        return tab

    def _undo(self, event=None):
        description = undo.undo()
        self.header.flash(description if description else "Nothing to undo")
        self._refresh_current_tab()

    def _redo(self, event=None):
        description = undo.redo()
        self.header.flash(description if description else "Nothing to redo")
        self._refresh_current_tab()

    def _refresh_current_tab(self):
        # the tab currently open may be holding a now-stale in-memory copy
        # of whatever file just got reverted/reapplied - if it knows how to
        # rescan itself, do that so the screen matches what's on disk again
        if self.current_key:
            tab = self._tab(self.current_key)
            if hasattr(tab, "on_show"):
                tab.on_show()
            elif hasattr(tab, "refresh"):
                tab.refresh()

    def _focus_search(self, event=None):
        tab = self._tab(self.current_key) if self.current_key else None
        if tab is not None and hasattr(tab, "search_entry"):
            tab.search_entry.focus_set()
            return "break"   # stop Tk's own Ctrl+F (nothing bound, but harmless either way)

    def _save_current(self, event=None):
        tab = self._tab(self.current_key) if self.current_key else None
        if tab is not None and hasattr(tab, "_export"):
            tab._export()
            self.header.flash("Exported")
        return "break"

    def _tab_is_dirty(self, key):
        return getattr(self.tabs.get(key), "is_dirty", False)

    def _confirm_leave(self, key):
        """True if it's fine to navigate away from `key` (clean, or the
        user said to discard). Only the generator tabs (Focus/Events/
        Decisions/Ideas) track this - everything else either has no
        unexported in-memory state or writes immediately on every action."""
        if not self._tab_is_dirty(key):
            return True
        label = next((lbl for _, entries in SECTIONS for k, lbl, _ in entries if k == key), key)
        return messagebox.askyesno(
            "Discard unsaved changes?",
            f"'{label}' has changes that were never exported to the mod. Leave anyway?",
        )

    def _on_close(self):
        dirty_labels = [lbl for _, entries in SECTIONS for k, lbl, _ in entries if self._tab_is_dirty(k)]
        if dirty_labels and not messagebox.askyesno(
            "Discard unsaved changes?",
            "These tabs have changes that were never exported:\n\n" + "\n".join(dirty_labels) +
            "\n\nClose anyway?",
        ):
            return
        self.destroy()

    def _open_search(self, event=None):
        if not state.is_loaded:
            return
        if state.search_index is None:
            state.search_index = global_search.build_index(state.mod_root)
        if getattr(self, "_palette", None) is not None:
            try:
                self._palette.destroy()
            except tk.TclError:
                pass
        self._palette = global_search.SearchPalette(self, state.search_index, self._jump_to)

    def _jump_to(self, item):
        self.show(item["tab"])
        tab = self._tab(item["tab"])
        if item["kind"] == "File":
            if hasattr(tab, "open_file"):
                tab.open_file(item["term"])
            return
        if item["kind"] == "Character":
            tab.tag_var.set(item["term"])
            tab._load_tag()
            for i, c in enumerate(getattr(tab, "_visible", [])):
                if c["id"] == item["label"]:
                    tab.listbox.selection_clear(0, "end")
                    tab.listbox.selection_set(i)
                    tab.listbox.see(i)
                    tab._select()
                    break
            return
        if hasattr(tab, "search_var"):
            tab.search_var.set(item["term"])
        if hasattr(tab, "_refresh"):
            tab._refresh()

    def show(self, key):
        if self.current_key == key:
            return
        if self.current_key and not self._confirm_leave(self.current_key):
            return
        if self.current_key:
            self._tab(self.current_key).pack_forget()
        self.current_key = key
        tab = self._tab(key)
        tab.pack(fill="both", expand=True)
        self.rail.select(key)

        # lazy per-tab loading + the localisation list refresh
        if hasattr(tab, "on_show"):
            tab.on_show()
        elif hasattr(tab, "refresh"):
            tab.refresh()

    # ---- navigation from home ----

    def _enter_workspace(self):
        first_build = self.workspace is None
        self._build_workspace()
        self.home.pack_forget()
        self.workspace.pack(fill="both", expand=True)
        if first_build:
            from app import onboarding
            self.after(400, lambda: onboarding.maybe_show(self))

    def _show_home(self):
        if self.current_key and not self._confirm_leave(self.current_key):
            return
        if self.workspace is not None:
            self.workspace.pack_forget()
        self.home.refresh_sidebar()   # the mod just worked on is now resumable
        self.home.pack(fill="both", expand=True)

    def _show_new_mod(self):
        from app.new_mod_wizard import NewModWizard
        wizard = NewModWizard(self)
        self.wait_window(wizard)
        if not wizard.result:
            return
        self._enter_workspace()
        self.tabs["open_mod"].load_mod_async(wizard.result)
        # land on the focus tab: with starter content there's a tree to load,
        # without it the "New empty tree" button is right there
        self.show("focus")

    def _show_open_mod(self, path):
        self._enter_workspace()
        self.show("open_mod")
        self.tabs["open_mod"].load_mod_async(path)

    # ---- auto-snapshot ----

    def set_auto_snapshot(self, on, minutes):
        self._auto_snap_on = on
        self._auto_snap_minutes = minutes
        if self._auto_snap_job is not None:
            self.after_cancel(self._auto_snap_job)
            self._auto_snap_job = None
        if on:
            self._auto_snap_job = self.after(minutes * 60_000, self._auto_snap_tick)

    def _auto_snap_tick(self):
        from app import snapshots
        if self._auto_snap_on and state.is_loaded:
            try:
                snapshots.create(state.mod_root, "auto")
                snapshots.prune_auto(state.mod_root)
                self.header.flash("Auto-snapshot saved")
                settings_tab = self.tabs.get("settings")
                if settings_tab is not None and hasattr(settings_tab, "_snap_refresh"):
                    settings_tab._snap_refresh()
            except OSError:
                pass
        if self._auto_snap_on:
            self._auto_snap_job = self.after(self._auto_snap_minutes * 60_000, self._auto_snap_tick)

    def _refresh_mod_label(self):
        if state.is_loaded:
            self.header.set_mod(state.mod_name)
            self.title(f"HOI4 Mod Maker — {state.mod_name}")
        else:
            self.header.set_mod("no mod open")
            self.title("HOI4 Mod Maker")

    # kept for older callers/tests that expect these names
    @property
    def mod_tab(self):
        return self._tab("open_mod")


if __name__ == "__main__":
    App().mainloop()
