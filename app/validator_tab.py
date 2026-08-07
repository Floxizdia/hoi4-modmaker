"""Validate tab: run the whole-mod scan and list findings, filterable by
severity, with the file each one lives in."""

import os
import re
import threading
import tkinter as tk
from tkinter import ttk, messagebox

from app.state import state
from app import validator
from app import theme, ui_kit

SEVERITY_COLORS = {"error": theme.RED, "warning": theme.AMBER, "info": theme.MUTED}


class ValidatorTab(ttk.Frame):
    def __init__(self, master):
        super().__init__(master, padding=12)
        self.issues = []
        self._scan_running = False
        self._build()
        state.subscribe(self.on_mod_changed)

    def _build(self):
        self.header = ui_kit.PageHeader(
            self, "Validate",
            "Runs real checks across the whole mod - unbalanced braces, referenced-but-missing loc keys, dangling ids - and shows a category breakdown of what's wrong.", help_key="validate")

        top = ttk.Frame(self)
        top.pack(fill="x")
        self.run_btn = ttk.Button(top, text="Run Validation", style="Accent.TButton", command=self._run)
        self.run_btn.pack(side="left")
        self.orphans_btn = ttk.Button(top, text="Find Unused Content", command=self._find_orphans)
        self.orphans_btn.pack(side="left", padx=6)
        ttk.Label(top, text="   Show:").pack(side="left")
        self.filter_var = tk.StringVar(value="all")
        for value, label in (("all", "all"), ("error", "errors"), ("warning", "warnings"), ("info", "info")):
            ttk.Radiobutton(top, text=label, value=value, variable=self.filter_var,
                            command=self._refresh).pack(side="left", padx=4)
        self.summary = ttk.Label(top, text="", style="Muted.TLabel")
        self.summary.pack(side="left", padx=14)

        self.by_category = ttk.Label(self, text="", style="Muted.TLabel", wraplength=980, justify="left")
        self.by_category.pack(fill="x", pady=(2, 0))

        cols = ("severity", "category", "file", "message")
        self.tree = ttk.Treeview(self, columns=cols, show="headings", height=18)
        widths = {"severity": 70, "category": 90, "file": 260, "message": 560}
        for c in cols:
            self.tree.heading(c, text=c)
            self.tree.column(c, width=widths[c])
        self.tree.pack(fill="both", expand=True, pady=10)
        self.tree.bind("<Double-Button-1>", lambda e: self._open_in_code())
        for severity, color in SEVERITY_COLORS.items():
            self.tree.tag_configure(severity, foreground=color)

        self.status = ttk.Label(
            self,
            text="Double-click a finding to open that file in the Code tab at the right line.  "
                 "Findings are honest warnings, not verdicts — a submod that extends another mod "
                 "will show \"missing\" for things the parent provides.",
            style="Muted.TLabel", wraplength=980, justify="left",
        )
        self.status.pack(fill="x")

        self.on_mod_changed()

    def on_mod_changed(self):
        if state.is_loaded:
            self.header.set_status(True, state.mod_name)
        else:
            self.header.set_status(False, "no mod open")
        self.issues = []
        self._refresh()

    def _run(self):
        """Runs the scan on a worker thread instead of the UI thread.

        validate() takes 15-20+ seconds on a real multi-hundred-file mod;
        run inline, that stretch left the window unresponsive between the
        eight coarse progress checkpoints, which Windows reports as "Not
        Responding" - read by users as "Validate hung." Worse, since the
        packaged build has no console, an unhandled exception mid-scan used
        to vanish silently, leaving "Scanning..." on screen forever with no
        way to tell a slow scan from a dead one. Both are fixed by moving
        the call off the UI thread and reporting failures explicitly."""
        if not state.is_loaded:
            messagebox.showerror("No mod", "Open a mod first.")
            return
        if self._scan_running:
            return

        self._scan_running = True
        self.run_btn.state(["disabled"])
        self.orphans_btn.state(["disabled"])
        self.summary.config(text="Scanning...")

        loc = dict(state.mod_loc)
        loc.update(state.loc_entries)
        mod_root, gfx_index = state.mod_root, state.gfx_index

        def report(msg):
            self.after(0, lambda: self._apply_progress(msg))

        def work():
            try:
                issues = validator.validate(mod_root, loc, gfx_index, progress=report)
            except Exception as exc:
                self.after(0, lambda: self._apply_run_error(exc))
                return
            self.after(0, lambda: self._apply_run_result(issues))

        threading.Thread(target=work, daemon=True).start()

    def _apply_progress(self, msg):
        if self._scan_running and self.summary.winfo_exists():
            self.summary.config(text=msg)

    def _apply_run_error(self, exc):
        self._scan_running = False
        self.run_btn.state(["!disabled"])
        self.orphans_btn.state(["!disabled"])
        self.summary.config(text=f"Validation failed: {exc}")

    def _apply_run_result(self, issues):
        self._scan_running = False
        self.run_btn.state(["!disabled"])
        self.orphans_btn.state(["!disabled"])
        self.issues = issues
        counts = validator.summarise(self.issues)
        self.summary.config(
            text=f"{counts.get('error', 0)} errors · {counts.get('warning', 0)} warnings · "
                 f"{counts.get('info', 0)} info"
        )
        cat_counts = {}
        for issue in self.issues:
            cat_counts[issue["category"]] = cat_counts.get(issue["category"], 0) + 1
        if cat_counts:
            breakdown = " · ".join(
                f"{cat}: {n}" for cat, n in sorted(cat_counts.items(), key=lambda kv: -kv[1])
            )
            self.by_category.config(text="By category — " + breakdown)
        else:
            self.by_category.config(text="")
        self._refresh()

    def _find_orphans(self):
        """Content nothing reaches. Separate from Validate proper because
        it's a judgement call, not a defect - unreferenced isn't the same as
        broken, so it doesn't belong in the errors/warnings list. Same
        worker-thread + explicit-failure treatment as _run(), for the same
        reason: this walks every script file too."""
        if not state.is_loaded:
            messagebox.showerror("No mod", "Open a mod first.")
            return
        if self._scan_running:
            return

        self._scan_running = True
        self.run_btn.state(["disabled"])
        self.orphans_btn.state(["disabled"])
        self.summary.config(text="Looking for unreferenced content...")
        mod_root = state.mod_root

        def report(msg):
            self.after(0, lambda: self._apply_progress(msg))

        def work():
            from app import references
            try:
                orphans = references.find_orphans(mod_root, progress=report)
            except Exception as exc:
                self.after(0, lambda: self._apply_orphans_error(exc))
                return
            self.after(0, lambda: self._apply_orphans_result(orphans))

        threading.Thread(target=work, daemon=True).start()

    def _apply_orphans_error(self, exc):
        self._scan_running = False
        self.run_btn.state(["!disabled"])
        self.orphans_btn.state(["!disabled"])
        self.summary.config(text=f"Unused-content scan failed: {exc}")

    def _apply_orphans_result(self, orphans):
        self._scan_running = False
        self.run_btn.state(["!disabled"])
        self.orphans_btn.state(["!disabled"])
        self.summary.config(text="")
        if self.winfo_exists():
            OrphanDialog(self, orphans)

    def _open_in_code(self):
        """Jump to the offending file in the Code tab. Several findings put
        a line number in the message text rather than a field of their own
        (braces, oob), so it's pulled back out here rather than plumbing an
        extra column through every check."""
        sel = self.tree.selection()
        if not sel or not state.is_loaded:
            return
        try:
            issue = sorted(self.issues,
                           key=lambda x: {"error": 0, "warning": 1, "info": 2}.get(x["severity"], 3))[int(sel[0])]
        except (ValueError, IndexError):
            return
        rel = issue.get("file")
        if not rel:
            return
        path = rel if os.path.isabs(rel) else os.path.join(state.mod_root, rel)
        if not os.path.isfile(path):
            self.status.config(text=f"Can't open {rel} - the file isn't there any more.")
            return

        line = None
        match = re.search(r"(?:around )?line (\d+)", issue.get("message", ""))
        if match:
            line = int(match.group(1))

        from app.code_editor import open_in_code
        open_in_code(self, path, line=line)

    def _refresh(self):
        self.tree.delete(*self.tree.get_children())
        chosen = self.filter_var.get()
        order = {"error": 0, "warning": 1, "info": 2}
        for i, issue in enumerate(sorted(self.issues, key=lambda x: order.get(x["severity"], 3))):
            if chosen != "all" and issue["severity"] != chosen:
                continue
            self.tree.insert(
                "", "end", iid=str(i), tags=(issue["severity"],),
                values=(issue["severity"], issue["category"], issue["file"], issue["message"]),
            )


class OrphanDialog(tk.Toplevel):
    def __init__(self, master, orphans):
        super().__init__(master)
        self.title("Unused content")
        self.geometry("760x460")
        outer = ttk.Frame(self, padding=12)
        outer.pack(fill="both", expand=True)

        ttk.Label(outer, text="UNUSED CONTENT", style="PageTitle.TLabel").pack(anchor="w")
        if orphans:
            note = (f"{len(orphans)} item(s) are defined but nothing in this mod ever references "
                    "them. Only events that must be triggered, and country-slot ideas, are checked "
                    "- decisions and focuses are player-facing and reached structurally, so "
                    "'unreferenced' is normal for those and listing them would be noise.")
        else:
            note = ("Nothing unused found - every triggered-only event and country idea in this mod "
                    "is referenced somewhere.")
        ttk.Label(outer, text=note, style="Muted.TLabel", wraplength=700, justify="left").pack(
            anchor="w", pady=(2, 4))
        ttk.Label(
            outer,
            text="Worth a look, not a delete list: an event can still be fired by an on_action in "
                 "another mod, or be waiting on a chain you haven't written yet.",
            style="Muted.TLabel", wraplength=700, justify="left").pack(anchor="w", pady=(0, 10))

        cols = ("kind", "id", "file")
        tree = ttk.Treeview(outer, columns=cols, show="headings")
        for col, width in (("kind", 80), ("id", 280), ("file", 340)):
            tree.heading(col, text=col.upper())
            tree.column(col, width=width)
        bar = ttk.Scrollbar(outer, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=bar.set)
        tree.pack(side="left", fill="both", expand=True)
        bar.pack(side="right", fill="y")
        for o in orphans:
            tree.insert("", "end", values=(o["kind"], o["id"], o["file"]))

        ttk.Button(self, text="Close", command=self.destroy).pack(pady=(0, 10))
        self.grab_set()
