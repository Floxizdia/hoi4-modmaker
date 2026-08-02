"""Mod Stats tab: the dashboard - KPI tiles, unresolved references, recent
edits and the descriptor, so "what am I even looking at" is answered by one
screen instead of clicking through every tab one at a time.
"""

import os
import time
import tkinter as tk
from tkinter import ttk, messagebox

from app.state import state
from app import mod_stats
from app import validator
from app import mod_files
from app import theme, ui_kit

SEVERITY_COLORS = {"error": theme.RED, "warning": theme.AMBER, "info": theme.MUTED}


class ModStatsTab(ttk.Frame):
    def __init__(self, master):
        super().__init__(master, padding=12)
        self.issues = []
        self._build()
        state.subscribe(self.on_mod_changed)

    def _build(self):
        self.header = ui_kit.PageHeader(
            self, "Dashboard",
            "Mod health, content counts, and unresolved references for the open mod.", help_key="stats")

        top = ttk.Frame(self)
        top.pack(fill="x")
        ttk.Button(top, text="Scan Mod", style="Accent.TButton", command=self._scan).pack(side="left")
        ttk.Button(top, text="Profile Performance...", command=self._profile).pack(side="left", padx=6)
        self.status = ttk.Label(top, text="", style="Muted.TLabel")
        self.status.pack(side="left", padx=10)

        # ---- KPI tile row ----
        tiles = ttk.Frame(self)
        tiles.pack(fill="x", pady=(12, 12))
        self.tiles = {}
        for i, (key, label, accent) in enumerate([
            ("files", "FILES PARSED", None),
            ("focuses", "FOCUSES", None),
            ("warnings", "WARNINGS", theme.AMBER),
            ("errors", "ERRORS", theme.RED),
        ]):
            tile = ttk.Frame(tiles, style="Card.TFrame")
            tile.grid(row=0, column=i, sticky="ew", padx=(0 if i == 0 else 10, 0))
            tiles.columnconfigure(i, weight=1)
            inner = ttk.Frame(tile, style="CardInner.TFrame", padding=(12, 10))
            inner.pack(fill="both", expand=True)
            if accent:
                edge = tk.Frame(tile, background=accent, width=2)
                edge.place(x=0, y=0, relheight=1)
            ttk.Label(inner, text=label, style="FieldLabel.TLabel").pack(anchor="w")
            value = ttk.Label(inner, text="—", background=theme.SURFACE,
                              foreground=(accent or theme.TEXT), font=(theme.FACE_DISPLAY, 22, "bold"))
            value.pack(anchor="w")
            self.tiles[key] = value

        # ---- main split: unresolved refs (left) / recent edits + descriptor (right) ----
        body = ttk.Frame(self)
        body.pack(fill="both", expand=True)
        body.columnconfigure(0, weight=13)
        body.columnconfigure(1, weight=10)
        body.rowconfigure(0, weight=1)

        refs = ui_kit.Section(body, "Unresolved references")
        refs.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        cols = ("severity", "category", "file", "message")
        self.refs_tree = ttk.Treeview(refs.body, columns=cols, show="headings", height=14)
        widths = {"severity": 60, "category": 80, "file": 220, "message": 420}
        for c in cols:
            self.refs_tree.heading(c, text=c.upper())
            self.refs_tree.column(c, width=widths[c])
        self.refs_tree.pack(fill="both", expand=True)
        for severity, color in SEVERITY_COLORS.items():
            self.refs_tree.tag_configure(severity, foreground=color)

        right = ttk.Frame(body)
        right.grid(row=0, column=1, sticky="nsew")
        right.rowconfigure(0, weight=1)
        right.columnconfigure(0, weight=1)

        recent = ui_kit.Section(right, "Recent edits")
        recent.grid(row=0, column=0, sticky="nsew", pady=(0, 12))
        self.recent_list = tk.Listbox(recent.body, height=8, relief="flat", borderwidth=0,
                                      background=theme.SURFACE, foreground=theme.TEXT,
                                      font=(theme.FACE_MONO, 9), highlightthickness=0)
        self.recent_list.pack(fill="both", expand=True)

        desc = ui_kit.Section(right, "Descriptor")
        desc.grid(row=1, column=0, sticky="ew")
        self.desc_label = ttk.Label(desc.body, text="—", background=theme.SURFACE,
                                    foreground=theme.MUTED_BRIGHT, font=(theme.FACE_MONO, 9),
                                    justify="left")
        self.desc_label.pack(anchor="w")

        self.on_mod_changed()

    def on_mod_changed(self):
        if state.is_loaded:
            self.header.set_status(True, state.mod_name)
        else:
            self.header.set_status(False, "no mod open")
        self.issues = []
        for value in self.tiles.values():
            value.config(text="—")
        self.refs_tree.delete(*self.refs_tree.get_children())
        self.recent_list.delete(0, "end")
        self.desc_label.config(text="—")
        self.status.config(text="")

    def on_show(self):
        pass   # scanning the whole mod isn't cheap enough to run just for switching tabs

    def _scan(self):
        if not state.is_loaded:
            messagebox.showerror("No mod", "Open a mod first.")
            return
        self.status.config(text="Scanning...")
        self.update_idletasks()

        stats = mod_stats.collect(state.mod_root)
        self.tiles["files"].config(text=str(stats["total_files"]))
        self.tiles["focuses"].config(text=str(stats["focuses"]))

        loc = dict(state.mod_loc)
        loc.update(state.loc_entries)
        self.issues = validator.validate(
            state.mod_root, loc, state.gfx_index,
            progress=lambda m: (self.status.config(text=m), self.update_idletasks()),
        )
        counts = validator.summarise(self.issues)
        self.tiles["warnings"].config(text=str(counts.get("warning", 0)))
        self.tiles["errors"].config(text=str(counts.get("error", 0)))

        self._refresh_refs()
        self._refresh_recent()
        self._refresh_descriptor()
        self.status.config(
            text=f"Last scan {time.strftime('%H:%M:%S')} — "
                 f"{counts.get('error', 0)} errors, {counts.get('warning', 0)} warnings"
        )

    def _refresh_refs(self):
        self.refs_tree.delete(*self.refs_tree.get_children())
        order = {"error": 0, "warning": 1, "info": 2}
        top15 = sorted(self.issues, key=lambda x: order.get(x["severity"], 3))[:15]
        for i, issue in enumerate(top15):
            self.refs_tree.insert(
                "", "end", iid=str(i), tags=(issue["severity"],),
                values=(issue["severity"], issue["category"], issue["file"], issue["message"]),
            )

    def _refresh_recent(self):
        self.recent_list.delete(0, "end")
        entries = []
        for path in mod_files.iter_script_files(state.mod_root):
            try:
                mtime = os.path.getmtime(path)
            except OSError:
                continue
            entries.append((mtime, path))
        entries.sort(reverse=True)
        for mtime, path in entries[:8]:
            rel = os.path.relpath(path, state.mod_root).replace("\\", "/")
            ago = _ago(mtime)
            self.recent_list.insert("end", f"{rel:<44} {ago}")
        if not entries:
            self.recent_list.insert("end", "(no script files found)")

    def _profile(self):
        if not state.is_loaded:
            messagebox.showerror("No mod", "Open a mod first.")
            return
        self.status.config(text="Timing each scan step...")
        self.update_idletasks()
        from app import perf_profile
        steps = perf_profile.profile(
            state.mod_root,
            progress=lambda m: (self.status.config(text=m), self.update_idletasks()),
        )
        self.status.config(text="")
        _PerfDialog(self, steps)

    def _refresh_descriptor(self):
        path = os.path.join(state.mod_root, "descriptor.mod")
        if not os.path.isfile(path):
            self.desc_label.config(text="(no descriptor.mod found)")
            return
        with open(path, "r", encoding="utf-8-sig", errors="ignore") as f:
            text = f.read().strip()
        self.desc_label.config(text=text[:600])


class _PerfDialog(tk.Toplevel):
    def __init__(self, master, steps):
        super().__init__(master)
        self.title("Performance Profile")
        self.resizable(False, False)
        outer = ttk.Frame(self, padding=14)
        outer.pack(fill="both", expand=True)

        ttk.Label(outer, text="PERFORMANCE PROFILE", style="PageTitle.TLabel").pack(anchor="w")
        total = sum(t for _, t, _ in steps)
        ttk.Label(outer, text=f"Total: {total:.2f}s across {len(steps)} scan step(s).",
                  style="Muted.TLabel").pack(anchor="w", pady=(2, 10))

        cols = ("step", "time", "detail")
        tree = ttk.Treeview(outer, columns=cols, show="headings", height=len(steps))
        widths = {"step": 160, "time": 80, "detail": 260}
        for c in cols:
            tree.heading(c, text=c.upper())
            tree.column(c, width=widths[c], anchor=("e" if c == "time" else "w"))
        tree.pack(fill="both", expand=True)
        slowest = max(steps, key=lambda s: s[1])[0] if steps else None
        tree.tag_configure("slow", foreground=theme.AMBER)
        for label, seconds, detail in sorted(steps, key=lambda s: -s[1]):
            tags = ("slow",) if label == slowest and seconds > 0.2 else ()
            tree.insert("", "end", values=(label, f"{seconds:.3f}s", detail), tags=tags)

        ttk.Label(
            outer, text="Slowest step highlighted in amber - if it's consistently the gfx index or "
                       "localisation load, that scales with total file count in the mod, not with any "
                       "one screen you're using.",
            style="Muted.TLabel", wraplength=520, justify="left",
        ).pack(anchor="w", pady=(8, 10))

        ttk.Button(outer, text="Close", command=self.destroy).pack(anchor="e")


def _ago(mtime):
    delta = time.time() - mtime
    if delta < 60:
        return "just now"
    if delta < 3600:
        return f"{int(delta // 60)}m ago"
    if delta < 86400:
        return f"{int(delta // 3600)}h ago"
    return f"{int(delta // 86400)}d ago"
