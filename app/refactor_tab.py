"""Refactor tab: rename a content id everywhere it is used.

Everything else in this app adds content. This changes content that already
exists, which is the thing that makes a big mod maintainable - and also the
thing most able to damage one, so the preview is not optional: nothing is
written until the whole list of changed lines has been shown.
"""

import threading
import tkinter as tk
from tkinter import messagebox, ttk

from app.state import state
from app import refactor, references
from app import theme, ui_kit


class RefactorTab(ttk.Frame):
    def __init__(self, master):
        super().__init__(master, padding=12)
        self.plan = []
        self.dangling = []
        self._ids = []
        self._busy = False
        self._build()
        state.subscribe(self.on_mod_changed)

    # ---- layout ----

    def _build(self):
        self.header = ui_kit.PageHeader(
            self, "Refactor",
            "Rename a focus, event, decision or idea everywhere it is used - script references "
            "and localisation keys together - after showing you every line it would change.",
            help_key="refactor")

        form = ui_kit.Section(self, "Rename")
        form.pack(fill="x")
        row = ttk.Frame(form.body)
        row.pack(fill="x", pady=(4, 0))

        ttk.Label(row, text="id").pack(side="left")
        self.old_var = tk.StringVar()
        self.old_combo = ttk.Combobox(row, textvariable=self.old_var, width=34)
        self.old_combo.pack(side="left", padx=4)
        ttk.Button(row, text="List ids", command=self._load_ids).pack(side="left")

        ttk.Label(row, text="   new id").pack(side="left")
        self.new_var = tk.StringVar()
        self.new_entry = ttk.Entry(row, textvariable=self.new_var, width=34)
        self.new_entry.pack(side="left", padx=4)

        mode_row = ttk.Frame(form.body)
        mode_row.pack(fill="x", pady=(6, 0))
        self.mode = tk.StringVar(value="rename")
        for label, value in (("rename it", "rename"), ("delete it", "delete")):
            ttk.Radiobutton(mode_row, text=label, value=value, variable=self.mode,
                            command=self._mode_changed).pack(side="left", padx=(0, 10))

        ttk.Button(row, text="Preview", style="Accent.TButton",
                   command=self._preview).pack(side="left", padx=(12, 4))
        self.apply_btn = ttk.Button(row, text="Apply", command=self._apply, state="disabled")
        self.apply_btn.pack(side="left")

        self.summary = ttk.Label(form.body, text="", style="Muted.TLabel",
                                 wraplength=1000, justify="left")
        self.summary.pack(anchor="w", pady=(6, 0))

        preview = ui_kit.Section(self, "What would change")
        preview.pack(fill="both", expand=True, pady=(ui_kit.PAD_SECTION, 0))
        self.tree = ttk.Treeview(preview.body, columns=("file", "line", "before", "after"),
                                 show="headings", height=18)
        for column, heading, width in (("file", "file", 260), ("line", "line", 55),
                                       ("before", "before", 380), ("after", "after", 380)):
            self.tree.heading(column, text=heading)
            self.tree.column(column, width=width)
        self.tree.pack(fill="both", expand=True)
        self.tree.tag_configure("loc", foreground=theme.GOLD_DIM)
        self.tree.tag_configure("broken", foreground=theme.RED)
        self.tree.bind("<Double-Button-1>", lambda e: self._open_in_code())

        self.status = ttk.Label(self, text="", style="Status.TLabel",
                                wraplength=1000, justify="left")
        self.status.pack(fill="x", pady=(6, 0))

        self.on_mod_changed()

    # ---- lifecycle ----

    def on_mod_changed(self):
        if state.is_loaded:
            self.header.set_status(True, state.mod_name)
        else:
            self.header.set_status(False, "no mod open")
        self._clear_plan()
        self._ids = []
        if hasattr(self, "old_combo"):
            self.old_combo.configure(values=[])

    def on_show(self):
        self.on_mod_changed()

    def _clear_plan(self):
        self.plan = []
        self.dangling = []
        if hasattr(self, "tree"):
            self.tree.delete(*self.tree.get_children())
            self.apply_btn.config(state="disabled")
            self.summary.config(text="")

    # ---- ids ----

    def _load_ids(self):
        if not state.is_loaded:
            messagebox.showerror("No mod", "Open a mod first.")
            return
        self.summary.config(text="Collecting ids...")
        self.update_idletasks()
        self._ids = sorted(references.searchable_ids(state.mod_root))
        self.old_combo.configure(values=self._ids)
        self.summary.config(text=f"{len(self._ids)} id(s) found. You can also type one by hand — "
                                 "anything that appears as a token in the mod's script works, "
                                 "including ids this list doesn't collect.")

    # ---- preview ----

    def _preview(self):
        if self._busy:
            return
        if not state.is_loaded:
            messagebox.showerror("No mod", "Open a mod first.")
            return
        old_id = self.old_var.get().strip()
        new_id = self.new_var.get().strip()
        deleting = self.mode.get() == "delete"

        if not old_id:
            self.summary.config(text="Type the id to work on.")
            return
        if not deleting:
            if not new_id:
                self.summary.config(text="Fill in what to rename it to.")
                return
            if old_id == new_id:
                self.summary.config(text="Those are the same id.")
                return
            if " " in new_id or '"' in new_id:
                self.summary.config(text="An id can't contain spaces or quotes.")
                return

        self._clear_plan()
        self._busy = True
        self.summary.config(text="Scanning the mod...")
        mod_root = state.mod_root

        def work():
            if deleting:
                plan, dangling = refactor.plan_delete(mod_root, old_id)
                taken = []
            else:
                plan = refactor.plan_rename(mod_root, old_id, new_id)
                dangling = []
                taken = refactor.conflicts(mod_root, new_id)
            try:
                self.after(0, lambda: self._show_plan(plan, taken, dangling, old_id, new_id))
            except (tk.TclError, RuntimeError):
                pass      # the window went away while the scan was running

        threading.Thread(target=work, daemon=True).start()

    def _mode_changed(self):
        deleting = self.mode.get() == "delete"
        self.new_entry.config(state="disabled" if deleting else "normal")
        self._clear_plan()
        self.status.config(text="")

    def _show_plan(self, plan, taken, dangling, old_id, new_id):
        self._busy = False
        if not self.winfo_exists():
            return
        self.plan = plan
        self.dangling = dangling
        deleting = self.mode.get() == "delete"
        files, lines = refactor.plan_summary(plan)

        if not plan:
            what = "delete" if deleting else "rename"
            self.summary.config(
                text=f"Nothing to {what}: '{old_id}' has no definition in this mod's script. "
                     "Check the spelling — ids are case-sensitive.", foreground=theme.MUTED)
            return

        for entry in plan:
            is_loc = entry["rel"].lower().endswith(".yml")
            for number, before, after in entry["changes"]:
                self.tree.insert(
                    "", "end",
                    values=(entry["rel"], number, before.strip(),
                            "(removed)" if after is None else after.strip()),
                    tags=("loc",) if is_loc else ())

        if deleting:
            note = f"{lines} line(s) in {files} file(s) would be removed."
            if dangling:
                note += (f"  {len(dangling)} reference(s) elsewhere would be left pointing at "
                         "nothing — they are listed below and NOT removed for you, because a "
                         "reference sits inside somebody else's effect block.")
                for reference in dangling:
                    self.tree.insert("", "end",
                                     values=(reference["file"], reference["line"],
                                             reference["snippet"], "-> would break"),
                                     tags=("broken",))
        else:
            note = f"{lines} line(s) in {files} file(s) would change."
            if taken:
                note += (f"  WARNING: '{new_id}' is already used in {len(taken)} file(s) "
                         f"({', '.join(taken[:3])}) — renaming onto a name that exists merges "
                         "two things into one.")

        self.summary.config(text=note,
                            foreground=theme.RED if (taken or dangling) else theme.MUTED)
        self.apply_btn.config(state="normal")

    # ---- applying ----

    def _apply(self):
        if not self.plan:
            return
        files, lines = refactor.plan_summary(self.plan)
        old_id, new_id = self.old_var.get().strip(), self.new_var.get().strip()
        deleting = self.mode.get() == "delete"

        if deleting:
            broken = (f"\n\n{len(self.dangling)} reference(s) elsewhere will be left pointing at "
                      "nothing — fix those afterwards." if self.dangling else "")
            question = (f"Delete '{old_id}'?\n\n{lines} line(s) in {files} file(s).{broken}\n\n"
                        "Each file keeps a one-time .bak, and this is one Ctrl+Z away.")
            title = "Delete from the mod?"
        else:
            question = (f"Rename '{old_id}' to '{new_id}'?\n\n{lines} line(s) in "
                        f"{files} file(s).\n\n"
                        "Each file keeps a one-time .bak, and the whole rename is one "
                        "Ctrl+Z away.")
            title = "Rename across the mod?"

        if not messagebox.askyesno(title, question, parent=self):
            return

        label = f"delete {old_id}" if deleting else f"rename {old_id}"
        written, skipped = refactor.apply_plan(self.plan, label)
        dangling = self.dangling
        self._clear_plan()
        state.content_changed()
        if deleting:
            message = f"Deleted '{old_id}' from {len(written)} file(s)."
            if dangling:
                message += (f"  {len(dangling)} reference(s) still mention it — run Preview in "
                            "delete mode again to see them, or fix them in the Code screen.")
        else:
            message = f"Renamed '{old_id}' to '{new_id}' in {len(written)} file(s)."
        if skipped:
            message += (f"  {len(skipped)} file(s) were skipped because they changed since the "
                        "preview — run Preview again for those.")
        self.status.config(text=message)

    def _open_in_code(self):
        selection = self.tree.selection()
        if not selection or not state.is_loaded:
            return
        import os
        rel, line = self.tree.item(selection[0], "values")[:2]
        path = os.path.join(state.mod_root, rel)
        if not os.path.isfile(path):
            return
        from app.code_editor import open_in_code
        open_in_code(self, path, line=int(line))
