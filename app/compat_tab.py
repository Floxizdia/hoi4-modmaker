"""Mod Compatibility tab: point at a second installed mod, see everything
it shares with the currently open one - tag registrations, focus/event/
decision/idea/tech ids, and files both mods override. Read-only: comparing
two mods never writes to either.
"""

import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from app.state import state
from app import compat_check
from app import mod_loader as ml
from app.mod_browser import DEFAULT_STEAM_WORKSHOP
from app import theme, ui_kit


class CompatTab(ttk.Frame):
    def __init__(self, master):
        super().__init__(master, padding=12)
        self._other_path = None
        self._workshop_mods = []
        self._build()
        state.subscribe(self.on_mod_changed)

    def _build(self):
        self.header = ui_kit.PageHeader(
            self, "Compatibility",
            "Checks this mod against other installed mods for file-level overwrite conflicts (two mods shipping the same path silently means one wins).", help_key="compat")

        top = ttk.Frame(self)
        top.pack(fill="x")
        ttk.Label(top, text="Compare against:").pack(side="left")
        self.other_combo = ttk.Combobox(top, state="readonly", width=44)
        self.other_combo.pack(side="left", padx=6)
        ttk.Button(top, text="↻", width=3, command=self._refresh_list).pack(side="left")
        ttk.Button(top, text="Folder...", command=self._browse).pack(side="left", padx=4)
        ttk.Button(top, text="Check vs Installed Game Version",
                   command=self._version_check).pack(side="right")
        ttk.Button(top, text="Check Compatibility", style="Accent.TButton",
                   command=self._check).pack(side="left", padx=10)

        ttk.Label(
            self,
            text="Read-only — this only compares two mods, never edits either. Tag collisions and shared "
                 "ids are the #1 cause of \"works alone, crashes together\": whichever mod loads second "
                 "silently overwrites the other's definition.",
            style="Muted.TLabel", wraplength=980, justify="left",
        ).pack(fill="x", pady=(8, 4))

        body = ttk.Frame(self)
        body.pack(fill="both", expand=True, pady=6)

        left = ttk.Frame(body, width=260)
        left.pack(side="left", fill="y", padx=(0, 8))
        left.pack_propagate(False)
        self.cat_tree = ttk.Treeview(left, columns=("count",), show="headings", height=10)
        self.cat_tree.heading("count", text="Category / count")
        self.cat_tree.pack(fill="both", expand=True)
        self.cat_tree.bind("<<TreeviewSelect>>", lambda e: self._show_category())

        right = ttk.Frame(body)
        right.pack(side="left", fill="both", expand=True)
        self.detail_list = tk.Listbox(right)
        bar = ttk.Scrollbar(right, orient="vertical", command=self.detail_list.yview)
        self.detail_list.configure(yscrollcommand=bar.set)
        self.detail_list.pack(side="left", fill="both", expand=True)
        bar.pack(side="right", fill="y")

        self.status = ttk.Label(self, text="", style="Status.TLabel", wraplength=980, justify="left")
        self.status.pack(fill="x")

        self.on_mod_changed()
        self._refresh_list()

    def on_mod_changed(self):
        if state.is_loaded:
            self.header.set_status(True, state.mod_name)
        else:
            self.header.set_status(False, "no mod open")
        self._report = {}
        self.cat_tree.delete(*self.cat_tree.get_children())
        self.detail_list.delete(0, "end")

    def _refresh_list(self):
        self._workshop_mods = [m for m in ml.list_workshop_mods(DEFAULT_STEAM_WORKSHOP)
                               if not state.is_loaded or m["path"] != state.mod_root]
        self.other_combo["values"] = [f"{m['name']}" for m in self._workshop_mods]

    def _version_check(self):
        """Different question from mod-vs-mod: after a HOI4 patch, does this
        mod still reference vanilla ids that the installed game defines?"""
        if not state.is_loaded:
            messagebox.showerror("No mod", "Open a mod first.")
            return
        self.status.config(text="Reading the installed game...")
        self.update_idletasks()
        from app import version_check
        findings = version_check.check(
            state.mod_root,
            progress=lambda m: (self.status.config(text=m), self.update_idletasks()),
        )
        self.status.config(text="")
        VersionCheckDialog(self, findings)

    def _browse(self):
        path = filedialog.askdirectory(title="Select the other mod's folder", initialdir=DEFAULT_STEAM_WORKSHOP)
        if path:
            self._other_path = path
            self.other_combo.set(os.path.basename(path))

    def _check(self):
        if not state.is_loaded:
            messagebox.showerror("No mod", "Open a mod first (this is what gets compared).")
            return
        idx = self.other_combo.current()
        other = self._other_path if self._other_path and self.other_combo.get() == os.path.basename(self._other_path) \
            else (self._workshop_mods[idx]["path"] if 0 <= idx < len(self._workshop_mods) else None)
        if not other:
            messagebox.showerror("Pick a mod", "Choose a mod from the list or Browse to one.")
            return

        self.status.config(text="Comparing...")
        self.update_idletasks()
        self._report = compat_check.compare(state.mod_root, other)
        total, counts = compat_check.summarise(self._report)

        self.cat_tree.delete(*self.cat_tree.get_children())
        self.cat_tree.insert("", "end", iid="tags", values=(f"Country tags ({counts.get('tags', 0)})",))
        for label in compat_check.CATEGORY_BUILDERS:
            self.cat_tree.insert("", "end", iid=label, values=(f"{label} ({counts.get(label, 0)})",))
        self.cat_tree.insert("", "end", iid="files", values=(f"Overridden files ({counts.get('files', 0)})",))

        self.detail_list.delete(0, "end")
        self.status.config(
            text=f"{total} total collision(s) found." if total
            else "No collisions found — these two mods look safe to run together."
        )

    def _show_category(self):
        sel = self.cat_tree.selection()
        self.detail_list.delete(0, "end")
        if not sel or not self._report:
            return
        for item in self._report.get(sel[0], []):
            self.detail_list.insert("end", " " + item)


class VersionCheckDialog(tk.Toplevel):
    def __init__(self, master, findings):
        super().__init__(master)
        self.title("Compatibility with the installed game version")
        self.geometry("880x520")
        outer = ttk.Frame(self, padding=12)
        outer.pack(fill="both", expand=True)

        ttk.Label(outer, text="VS INSTALLED GAME VERSION", style="PageTitle.TLabel").pack(anchor="w")
        if findings:
            summary = (f"{len(findings)} reference(s) point at a vanilla id the installed game no longer "
                       "defines. Paradox renames and removes ids between patches; the game reports "
                       "nothing when a mod asks for one that's gone - the effect just quietly does nothing.")
        else:
            summary = ("Nothing found - every vanilla idea, technology and focus this mod references "
                       "exists in the installed game.")
        ttk.Label(outer, text=summary, style="Muted.TLabel", wraplength=820, justify="left").pack(
            anchor="w", pady=(2, 10))

        cols = ("kind", "id", "where")
        tree = ttk.Treeview(outer, columns=cols, show="headings")
        for col, width in (("kind", 90), ("id", 260), ("where", 460)):
            tree.heading(col, text=col.upper())
            tree.column(col, width=width)
        bar = ttk.Scrollbar(outer, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=bar.set)
        tree.pack(side="left", fill="both", expand=True)
        bar.pack(side="right", fill="y")
        for f in findings:
            tree.insert("", "end", values=(f["kind"], f["id"], f["where"]))

        ttk.Button(self, text="Close", command=self.destroy).pack(pady=(0, 10))
        self.grab_set()
