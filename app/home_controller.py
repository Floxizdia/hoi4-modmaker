"""Wires the Home screen's view widgets to user actions: open/duplicate/
validate a mod, refresh the list, add a folder, react to selection changes.

Owns the single HomeData instance and the full (unfiltered) mod list - the
view's sub-widgets only ever see the slice they need to render. This is the
only file that should ever change if a Home action's *behaviour* changes;
home_view.py and the widget modules should only need edits for layout.
"""

import os
import shutil
import threading

from tkinter import filedialog

from app import local_mods
from app import game_paths
from app.home_data import HomeData
from app.home_view import HomeView
from app.mod_browser import DEFAULT_STEAM_WORKSHOP


class HomeController:
    def __init__(self, root, on_new_mod, on_open_mod):
        self.root = root
        self.on_new_mod = on_new_mod
        self.on_open_mod = on_open_mod
        self.data = HomeData(schedule=root.after)
        self._mods = []
        self.view = HomeView(root, self)
        self.refresh()

    # ---- mod list ----

    def refresh(self):
        self.view.table.show_scanning()
        self.view.status_count_label.config(text="Scanning…")
        self.data.list_mods_async(self._apply_mod_list)

    def _apply_mod_list(self, mods):
        self._mods = mods
        self.view.table.set_mods(mods)
        self.view.status_count_label.config(
            text=f"{len(mods)} mods indexed · scanned just now")
        self.root.after(300, lambda: self.data.scan_sizes_async(
            mods, self.view.table.update_row_size))

    # ---- selection / navigation ----

    def on_selection_changed(self):
        mods = self.view.table.get_selected_mods()
        self.view.inspector.show(mods, self._mods)

    def open_mod(self, path):
        self.on_open_mod(path)

    def new_mod(self):
        self.on_new_mod()

    def open_folder(self, path):
        # os.startfile doesn't exist off Windows; game_paths picks the right
        # file manager for the platform
        game_paths.open_folder(path)

    def browse(self):
        path = filedialog.askdirectory(title="Select a mod folder", initialdir=DEFAULT_STEAM_WORKSHOP)
        if path:
            self.on_open_mod(path)

    def add_local_folder(self):
        path = filedialog.askdirectory(title="Add a mod folder", initialdir=DEFAULT_STEAM_WORKSHOP)
        if not path:
            return
        local_mods.add(path)
        self.refresh()

    # ---- mod actions ----

    def duplicate_mod(self, mod):
        """Copies the whole mod folder on a worker thread - for a large mod
        (GB+ of textures) a synchronous shutil.copytree freezes the window
        for as long as the copy takes, which reads as a hang."""
        src = mod["path"]
        base = src.rstrip("\\/") + " (copy)"
        dest = base
        n = 2
        while os.path.exists(dest):
            dest = f"{base} {n}"
            n += 1

        self.view.table.hint.config(text=f"Duplicating {os.path.basename(src)}...")

        def work():
            try:
                shutil.copytree(src, dest)
            except OSError as exc:
                self.root.after(0, lambda: self._apply_duplicate_error(exc))
                return
            self.root.after(0, lambda: self._apply_duplicate_done(dest))

        threading.Thread(target=work, daemon=True).start()

    def _apply_duplicate_error(self, exc):
        self.view.table.hint.config(text=f"Couldn't duplicate: {exc}")

    def _apply_duplicate_done(self, dest):
        local_mods.add(dest)
        self.refresh()
        self.view.table.hint.config(text=f"Duplicated to {os.path.basename(dest)}")

    def validate_one(self, mod):
        self._revalidate(mod["path"])

    def validate_many(self, mods):
        for m in mods:
            self._revalidate(m["path"])

    def _revalidate(self, mod_path):
        self.data.invalidate_health(mod_path)
        selected_paths = self.view.table.get_selected_paths()
        if selected_paths == [mod_path] or len(selected_paths) > 1:
            self.view.inspector.show(self.view.table.get_selected_mods(), self._mods, force=True)
