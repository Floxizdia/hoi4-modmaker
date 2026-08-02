"""'What did I change?' — every file this tool ever edited keeps a one-time
.bak made right before the first edit, so the .bak IS the original and the
live file IS the current state. Diffing the two needs no history database,
just difflib pointed at a pair of files that already exist on disk.
"""

import difflib
import os
import shutil
import tkinter as tk
from tkinter import ttk, messagebox

from app.state import state
from app import mod_files
from app import theme, ui_kit

BAK = ".bak"


def find_changed_files(mod_root):
    """[(path, bak_path)] for every file that has a sibling .bak and still
    differs from it - a .bak with no drift usually means an edit that
    matched the original content, so it's left off the list."""
    out = []
    for path in mod_files.iter_script_files(mod_root):
        bak = path + BAK
        if not os.path.isfile(bak):
            continue
        try:
            current = mod_files.read_text(path)
            original = mod_files.read_text(bak)
        except OSError:
            continue
        if current != original:
            out.append((path, bak))
    return out


class DiffTab(ttk.Frame):
    def __init__(self, master):
        super().__init__(master, padding=12)
        self._changed = []
        self._current = None
        self._build()
        state.subscribe(self.on_mod_changed)

    def _build(self):
        self.header = ui_kit.PageHeader(
            self, "What Changed?",
            "Compares the mod's current files against a snapshot (or another folder) and shows a file-by-file diff of what's different.", help_key="diff")

        top = ttk.Frame(self)
        top.pack(fill="x")
        ttk.Button(top, text="Scan for Changes", style="Accent.TButton",
                   command=self._scan).pack(side="left")
        self.count_label = ttk.Label(top, text="", style="Muted.TLabel")
        self.count_label.pack(side="left", padx=10)
        ttk.Label(
            top, text="Compares every file against its one-time backup — "
                     "only files this tool has actually touched show up here.",
            style="Muted.TLabel",
        ).pack(side="left", padx=14)

        body = ttk.Frame(self)
        body.pack(fill="both", expand=True, pady=8)

        left = ttk.Frame(body, width=340)
        left.pack(side="left", fill="y", padx=(0, 8))
        left.pack_propagate(False)
        self.listbox = tk.Listbox(left, exportselection=False)
        bar = ttk.Scrollbar(left, orient="vertical", command=self.listbox.yview)
        self.listbox.configure(yscrollcommand=bar.set)
        self.listbox.pack(side="left", fill="both", expand=True)
        bar.pack(side="right", fill="y")
        self.listbox.bind("<<ListboxSelect>>", lambda e: self._show_diff())

        right = ttk.Frame(body)
        right.pack(side="left", fill="both", expand=True)
        self.diff_text = tk.Text(right, wrap="none", font=("Consolas", 9), state="disabled")
        dbar = ttk.Scrollbar(right, orient="vertical", command=self.diff_text.yview)
        self.diff_text.configure(yscrollcommand=dbar.set)
        self.diff_text.pack(side="left", fill="both", expand=True)
        dbar.pack(side="right", fill="y")
        self.diff_text.tag_configure("add", foreground=theme.GREEN)
        self.diff_text.tag_configure("remove", foreground=theme.RED)
        self.diff_text.tag_configure("hunk", foreground=theme.GOLD)
        self.diff_text.tag_configure("meta", foreground=theme.MUTED)

        btns = ttk.Frame(self)
        btns.pack(fill="x")
        ttk.Button(btns, text="Revert This File to Original",
                   command=self._revert).pack(side="left")
        self.status = ttk.Label(btns, text="", style="Status.TLabel",
                                wraplength=800, justify="left")
        self.status.pack(side="left", padx=10)

        self.on_mod_changed()

    # ---- lifecycle ----

    def on_mod_changed(self):
        if state.is_loaded:
            self.header.set_status(True, state.mod_name)
        else:
            self.header.set_status(False, "no mod open")
        self._changed = []
        self._current = None
        self.listbox.delete(0, "end")
        self._set_diff_text("")

    def on_show(self):
        if state.is_loaded and not self._changed:
            self._scan()

    # ---- scanning ----

    def _scan(self):
        if not state.is_loaded:
            messagebox.showerror("No mod", "Open a mod first.")
            return
        self._changed = find_changed_files(state.mod_root)
        self.listbox.delete(0, "end")
        for path, _ in self._changed:
            self.listbox.insert("end", " " + os.path.relpath(path, state.mod_root))
        self.count_label.config(text=f"{len(self._changed)} changed file(s)")
        self._set_diff_text("")

    def _set_diff_text(self, text, tags_lines=None):
        self.diff_text.configure(state="normal")
        self.diff_text.delete("1.0", "end")
        if tags_lines:
            for line, tag in tags_lines:
                self.diff_text.insert("end", line + "\n", tag)
        else:
            self.diff_text.insert("end", text)
        self.diff_text.configure(state="disabled")

    def _show_diff(self):
        sel = self.listbox.curselection()
        if not sel:
            return
        self._current = self._changed[sel[0]]
        path, bak = self._current
        try:
            original = mod_files.read_text(bak).splitlines(keepends=True)
            current = mod_files.read_text(path).splitlines(keepends=True)
        except OSError as exc:
            self._set_diff_text(f"Couldn't read: {exc}")
            return

        lines = []
        for line in difflib.unified_diff(original, current, fromfile="original", tofile="current"):
            tag = "meta"
            if line.startswith("+++") or line.startswith("---"):
                tag = "meta"
            elif line.startswith("@@"):
                tag = "hunk"
            elif line.startswith("+"):
                tag = "add"
            elif line.startswith("-"):
                tag = "remove"
            lines.append((line.rstrip("\n"), tag))
        if not lines:
            lines = [("(no textual difference)", "meta")]
        self._set_diff_text(None, tags_lines=lines)

    # ---- reverting ----

    def _revert(self):
        if not self._current:
            messagebox.showerror("Nothing selected", "Pick a changed file from the list first.")
            return
        path, bak = self._current
        rel = os.path.relpath(path, state.mod_root)
        if not messagebox.askyesno(
            "Revert to original?",
            f"Overwrite your edits to:\n{rel}\n\nwith the original backup? This can't be undone."):
            return
        shutil.copy2(bak, path)
        self.status.config(text=f"Reverted {rel} to its original content.")
        self._scan()
