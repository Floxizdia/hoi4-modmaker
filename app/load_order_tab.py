"""Load Order tab: pick several installed mods, see every collision across
the whole set at once (not just one pair at a time like Compatibility), and
get a heuristic suggested load order."""

import os
import tkinter as tk
from tkinter import ttk, filedialog

from app.state import state
from app import load_order_check as loc
from app import mod_loader as ml
from app.mod_browser import DEFAULT_STEAM_WORKSHOP
from app import theme, ui_kit


class LoadOrderTab(ttk.Frame):
    def __init__(self, master):
        super().__init__(master, padding=12)
        self._workshop_mods = []
        self._extra_mods = []  # [(name, path)] added via Browse
        self._checks = {}      # path -> BooleanVar
        self._build()

    def _build(self):
        self.header = ui_kit.PageHeader(
            self, "Load Order & Multi-mod Compatibility",
            "Check several mods together for id/file collisions, and get a heuristic suggested "
            "load order. This never edits any mod — always defer to a mod's own Workshop "
            "description if it says \"load after X\".", help_key="load_order")

        top = ttk.Frame(self)
        top.pack(fill="x")
        ttk.Button(top, text="↻ Refresh installed mods", command=self._refresh_list).pack(side="left")
        ttk.Button(top, text="Add folder...", command=self._browse).pack(side="left", padx=6)
        ttk.Button(top, text="Check Selected", style="Accent.TButton",
                   command=self._check).pack(side="left", padx=10)

        body = ttk.Frame(self)
        body.pack(fill="both", expand=True, pady=(10, 0))

        left = ui_kit.Section(body, "Installed mods (pick 2+)")
        left.configure(width=280)
        left.pack(side="left", fill="y", padx=(0, 12))
        left.pack_propagate(False)
        list_frame = ttk.Frame(left.body, style="CardInner.TFrame")
        list_frame.pack(fill="both", expand=True, pady=(4, 0))
        self.canvas = tk.Canvas(list_frame, background=theme.SURFACE, highlightthickness=0)
        bar = ttk.Scrollbar(list_frame, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=bar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        bar.pack(side="right", fill="y")
        self.check_frame = ttk.Frame(self.canvas)
        self.canvas.create_window((0, 0), window=self.check_frame, anchor="nw")
        self.check_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))

        right = ttk.Frame(body)
        right.pack(side="left", fill="both", expand=True)
        self.notebook = ttk.Notebook(right)
        self.notebook.pack(fill="both", expand=True)

        order_page = ttk.Frame(self.notebook, padding=8)
        self.notebook.add(order_page, text="Suggested order")
        ttk.Label(
            order_page, text="Top loads first. Mods with fewer script files are suggested to load "
                             "last, so their smaller/patch content wins any collision.",
            style="Muted.TLabel", wraplength=560, justify="left",
        ).pack(anchor="w")
        self.order_list = ttk.Treeview(order_page, columns=("pos", "name", "files"), show="headings", height=18)
        for col, text, width in (("pos", "#", 30), ("name", "mod", 300), ("files", "script files", 90)):
            self.order_list.heading(col, text=text)
            self.order_list.column(col, width=width)
        self.order_list.pack(fill="both", expand=True, pady=(6, 0))

        collide_page = ttk.Frame(self.notebook, padding=8)
        self.notebook.add(collide_page, text="Collisions")
        self.collide_tree = ttk.Treeview(collide_page, columns=("pair", "total"), show="headings", height=10)
        self.collide_tree.heading("pair", text="mod pair")
        self.collide_tree.heading("total", text="collisions")
        self.collide_tree.column("pair", width=380)
        self.collide_tree.column("total", width=80)
        self.collide_tree.pack(fill="x", pady=(0, 6))
        self.collide_tree.bind("<<TreeviewSelect>>", lambda e: self._show_pair_detail())
        self.collide_detail = tk.Listbox(collide_page, height=10)
        self.collide_detail.pack(fill="both", expand=True)

        self.status = ttk.Label(self, text="", style="Status.TLabel", wraplength=980, justify="left")
        self.status.pack(fill="x", pady=(8, 0))

        self._refresh_list()

    def on_show(self):
        self._refresh_list()

    def _all_mods(self):
        seen = {p for _, p in self._extra_mods}
        mods = list(self._extra_mods)
        for m in self._workshop_mods:
            if m["path"] not in seen:
                mods.append((m["name"], m["path"]))
                seen.add(m["path"])
        return mods

    def _refresh_list(self):
        self._workshop_mods = ml.list_workshop_mods(DEFAULT_STEAM_WORKSHOP)
        for w in self.check_frame.winfo_children():
            w.destroy()
        self._checks = {}
        for name, path in self._all_mods():
            var = tk.BooleanVar(value=False)
            ttk.Checkbutton(self.check_frame, text=name, variable=var, style="TCheckbutton").pack(
                anchor="w", pady=1)
            self._checks[path] = (var, name)

    def _browse(self):
        path = filedialog.askdirectory(title="Add a mod folder", initialdir=DEFAULT_STEAM_WORKSHOP)
        if path and path not in {p for _, p in self._extra_mods}:
            self._extra_mods.append((os.path.basename(path), path))
            self._refresh_list()

    def _selected(self):
        return [(name, path) for path, (var, name) in self._checks.items() if var.get()]

    def _check(self):
        mods = self._selected()
        if len(mods) < 2:
            self.status.config(text="Pick at least 2 mods to compare.")
            return
        self.status.config(text=f"Checking {len(mods)} mods against each other...")
        self.update_idletasks()

        order = loc.suggest_order(mods)
        self.order_list.delete(*self.order_list.get_children())
        for i, (name, path, count) in enumerate(order, start=1):
            self.order_list.insert("", "end", values=(i, name, count))

        self._pair_reports = {}
        pairs = loc.compare_all(mods)
        self.collide_tree.delete(*self.collide_tree.get_children())
        for name_a, name_b, report, total in pairs:
            iid = f"{name_a}|{name_b}"
            self._pair_reports[iid] = report
            self.collide_tree.insert("", "end", iid=iid, values=(f"{name_a}  ×  {name_b}", total))
        self.collide_detail.delete(0, "end")

        if pairs:
            self.status.config(
                text=f"{len(pairs)} colliding pair(s) out of {len(mods) * (len(mods) - 1) // 2} checked. "
                     "Open the Collisions tab for details."
            )
        else:
            self.status.config(text=f"No collisions found across all {len(mods)} mods — looks safe together.")

    def _show_pair_detail(self):
        sel = self.collide_tree.selection()
        self.collide_detail.delete(0, "end")
        if not sel:
            return
        report = self._pair_reports.get(sel[0], {})
        for category, items in report.items():
            if not items:
                continue
            self.collide_detail.insert("end", f"— {category} ({len(items)}) —")
            for item in items[:50]:
                self.collide_detail.insert("end", "    " + str(item))
            if len(items) > 50:
                self.collide_detail.insert("end", f"    ... and {len(items) - 50} more")
