"""The right panel: whatever's currently selected in the mod table, in as
much detail as is worth showing before actually opening it.

`show(mods, all_mods)` is the only entry point the rest of the screen needs.
It skips its own rebuild when the selection hasn't actually changed - the
table re-fires its selection event on every keystroke in search and every
filter click (it always re-selects "row 0" after rebuilding), even when
that row is still the same mod, so without this check typing a search would
re-render the panel - and re-run its health/stats checks - on every letter.
"""

import os
import tkinter as tk
from tkinter import ttk

from app import home_data
from app import home_theme as ht


class HomeInspector(ttk.Frame):
    def __init__(self, parent, data, *, on_open, on_duplicate, on_validate_one,
                 on_validate_many, on_open_folder):
        super().__init__(parent, style="Home.Surface.TFrame", width=340)
        self.grid_propagate(False)
        self.data = data
        self._on_open = on_open
        self._on_duplicate = on_duplicate
        self._on_validate_one = on_validate_one
        self._on_validate_many = on_validate_many
        self._on_open_folder = on_open_folder
        self._thumbs = {}
        self._key = None
        self._stats_labels = {}
        self.show([], [])

    # ---- entry point ----

    def show(self, mods, all_mods, force=False):
        key = tuple(m["path"] for m in mods)
        if not force and key == self._key:
            return
        self._key = key

        for child in self.winfo_children():
            child.destroy()

        head = ttk.Frame(self, style="Home.CardHead.TFrame", padding=(12, 6))
        head.pack(fill="x")
        ttk.Label(head, text="SELECTED MOD", style="Home.Eyebrow.TLabel").pack(side="left")
        total = len(all_mods)
        if mods and total:
            idx = next((i for i, m in enumerate(all_mods) if m["path"] == mods[0]["path"]), 0)
            ttk.Label(head, text=f"{idx + 1} of {total}", style="Home.Eyebrow.TLabel").pack(side="right")
        tk.Frame(self, height=1, background=ht.LINE).pack(fill="x")

        body = ttk.Frame(self, style="Home.Surface.TFrame", padding=12)
        body.pack(fill="both", expand=True)

        if not mods:
            self._build_empty(body)
        elif len(mods) > 1:
            self._build_multi(body, mods)
        else:
            self._build_single(body, mods[0])

    # ---- empty ----

    def _build_empty(self, body):
        body.pack_configure(padx=16)
        wrap = ttk.Frame(body, style="Home.Surface.TFrame")
        wrap.pack(expand=True)
        ttk.Label(wrap, text="Improve an existing mod", style="Home.CardTitle.TLabel",
                  justify="center").pack(pady=(40, 8))
        ttk.Label(wrap, text="Pick a mod on the left to see its focus trees, events and "
                             "health check here. Open it to browse them visually, walk them "
                             "like in game, and add focuses, leaders or ideas on top.",
                  style="Home.SurfaceMuted.TLabel", wraplength=280,
                  justify="center").pack()
        ttk.Label(wrap, text="Your changes never overwrite the original without asking.",
                  style="Home.SurfaceMuted.TLabel", wraplength=280,
                  justify="center").pack(pady=(9, 0))
        btn = ttk.Button(body, text="Open selected mod", style="Home.Secondary.TButton",
                         state="disabled")
        btn.pack(side="bottom", fill="x", pady=(12, 0))

    # ---- multi-select ----

    def _build_multi(self, body, mods):
        ttk.Label(body, text=f"{len(mods)} mods selected", style="Home.CardTitle.TLabel").pack(
            anchor="w", pady=(0, 10))
        grid = ttk.Frame(body, style="Home.Surface.TFrame")
        grid.pack(fill="x", pady=(0, 10))
        total_bytes = sum(home_data.bytes_for(m["path"]) for m in mods if os.path.isdir(m["path"]))
        compat_n = sum(1 for m in mods if home_data.compat_class(m, self.data.detected_mm) == "compatible")
        for i, (label, val, color) in enumerate((
            ("Combined size", home_data.fmt_size(total_bytes), ht.TEXT_HI),
            ("Compatible", f"{compat_n} of {len(mods)}", ht.OK if compat_n == len(mods) else ht.TEXT_HI),
        )):
            ttk.Label(grid, text=label, style="Home.SurfaceMuted.TLabel").grid(
                row=i, column=0, sticky="w", pady=2)
            tk.Label(grid, text=val, background=ht.SURFACE, foreground=color,
                    font=(ht.FACE_MONO, 9)).grid(row=i, column=1, sticky="e", padx=(14, 0))
        grid.columnconfigure(1, weight=1)
        ttk.Label(body, text="Only actions that make sense for several mods at once stay enabled.",
                  style="Home.SurfaceMuted.TLabel", wraplength=280, justify="left").pack(anchor="w")

        actions = ttk.Frame(body, style="Home.Surface.TFrame")
        actions.pack(fill="x", side="bottom")
        ttk.Button(actions, text="Validate all", style="Home.Secondary.TButton",
                  command=lambda: self._on_validate_many(mods)).pack(fill="x", pady=(0, 6))
        ttk.Button(actions, text="Open selected mod", style="Home.Secondary.TButton",
                  state="disabled").pack(fill="x")

    # ---- single selection ----

    def _build_single(self, body, mod):
        thumb_frame = tk.Canvas(body, height=118, highlightthickness=1,
                                highlightbackground=ht.LINE_STRONG, background=ht.RAISED, bd=0)
        thumb_frame.pack(fill="x")
        photo = home_data.load_thumb(mod["path"], home_data.THUMB_SIZE_BIG)
        if photo is not None:
            self._thumbs["inspector"] = photo
            thumb_frame.create_image(158, 59, image=photo, anchor="center")
        else:
            thumb_frame.create_text(150, 100, text="thumbnail.png", fill=ht.TEXT_OFF,
                                    font=(ht.FACE_MONO, 8), anchor="s")

        ttk.Label(body, text=mod["name"], style="Home.CardTitle.TLabel",
                 font=(ht.FACE_UI, 13, "bold"), wraplength=300).pack(anchor="w", pady=(10, 0))
        sub = f"workshop id {mod['workshop_id']}" if mod.get("workshop_id") else "local mod"
        ttk.Label(body, text=sub, style="Home.SurfaceMuted.TLabel").pack(anchor="w", pady=(2, 0))

        cls = home_data.compat_class(mod, self.data.detected_mm)
        tags_row = ttk.Frame(body, style="Home.Surface.TFrame")
        tags_row.pack(anchor="w", pady=(8, 0))
        badge_specs = []
        if cls == "compatible":
            badge_specs.append(("COMPATIBLE", ht.OK, "#16302B"))
        elif cls == "needs_update":
            badge_specs.append(("NEEDS UPDATE", ht.WARN, "#302713"))
        badge_specs.append(("WORKSHOP" if mod.get("workshop_id") else "LOCAL", ht.TEXT_MID, ht.RAISED))
        if mod.get("supported_version"):
            badge_specs.append((mod["supported_version"], ht.TEXT_MID, ht.RAISED))
        for text, fg, bg in badge_specs:
            tk.Label(tags_row, text=text, background=bg, foreground=fg,
                    font=(ht.FACE_MONO, 8, "bold"), padx=6, pady=1).pack(side="left", padx=(0, 5))

        tk.Frame(body, height=1, background=ht.LINE).pack(fill="x", pady=(10, 9))
        stats_grid = ttk.Frame(body, style="Home.Surface.TFrame")
        stats_grid.pack(fill="x")
        self._stats_labels = {}
        for i, label in enumerate(("Focus trees", "Events", "Countries touched", "Files")):
            ttk.Label(stats_grid, text=label, style="Home.SurfaceMuted.TLabel").grid(
                row=i, column=0, sticky="w", pady=2)
            val = tk.Label(stats_grid, text="…", background=ht.SURFACE, foreground=ht.TEXT_HI,
                          font=(ht.FACE_MONO, 9))
            val.grid(row=i, column=1, sticky="e", padx=(14, 0))
            self._stats_labels[label] = val
        stats_grid.columnconfigure(1, weight=1)
        self.data.load_stats_async(mod["path"], lambda stats: self._apply_stats(stats))

        loc_box = tk.Frame(body, background=ht.CANVAS, highlightthickness=1,
                           highlightbackground=ht.LINE)
        loc_box.pack(fill="x", pady=(9, 0))
        inner = ttk.Frame(loc_box, style="Home.TFrame", padding=(8, 6))
        inner.pack(fill="x")
        ttk.Label(inner, text="LOCATION", style="Home.EyebrowAccent.TLabel",
                 foreground=ht.TEXT_OFF).pack(anchor="w")
        ttk.Label(inner, text=mod["path"], style="Home.Muted.TLabel", font=(ht.FACE_MONO, 9),
                 wraplength=300, justify="left").pack(anchor="w", pady=(2, 0))

        self._build_health_box(body, mod["path"])

        footer = ttk.Frame(body, style="Home.Surface.TFrame")
        footer.pack(fill="x", side="bottom")
        ttk.Label(footer, text="Open it to browse its focus trees visually, walk them like in "
                              "game, and add focuses, leaders or ideas on top. Your changes "
                              "never overwrite the original without asking.",
                 style="Home.SurfaceMuted.TLabel", wraplength=300, justify="left").pack(
            anchor="w", pady=(0, 10))
        open_btn = ttk.Button(footer, text="Open selected mod", style="Home.Primary.TButton",
                              command=lambda: self._on_open(mod["path"]))
        open_btn.pack(fill="x", pady=(0, 6))
        row = ttk.Frame(footer, style="Home.Surface.TFrame")
        row.pack(fill="x")
        for i, (text, cmd) in enumerate((
            ("Duplicate", lambda: self._on_duplicate(mod)),
            ("Validate", lambda: self._on_validate_one(mod)),
            ("Folder", lambda: self._on_open_folder(mod["path"])),
        )):
            b = ttk.Button(row, text=text, style="Home.Secondary.TButton", command=cmd)
            b.grid(row=0, column=i, sticky="ew", padx=(0 if i == 0 else 6, 0))
            row.columnconfigure(i, weight=1)

    def _build_health_box(self, body, mod_path):
        box = ttk.Frame(body, style="Home.CardHead.TFrame")
        box.pack(fill="x", pady=(9, 9))
        head = ttk.Frame(box, style="Home.CardHead.TFrame", padding=(10, 4))
        head.pack(fill="x")
        ttk.Label(head, text="HEALTH", style="Home.Eyebrow.TLabel").pack(side="left")
        badges = ttk.Frame(head, style="Home.CardHead.TFrame")
        badges.pack(side="right")
        content = ttk.Frame(box, style="Home.TFrame", padding=(10, 7))
        content.pack(fill="x")
        line = ttk.Label(content, text="Checking…", style="Home.Muted.TLabel", font=(ht.FACE_MONO, 9))
        line.pack(anchor="w")

        self.data.check_health_async(
            mod_path, lambda stats: self._apply_health_box(box, badges, line, stats))
        return box

    def _apply_health_box(self, box, badges, line, stats):
        if not box.winfo_exists():
            return
        if not stats:
            line.config(text="Couldn't check.")
            return
        errs, warns = stats.get("errors", 0), stats.get("warnings", 0)
        if errs:
            tk.Label(badges, text=f"{errs} ERR", background="#2A1614", foreground=ht.ERR,
                    font=(ht.FACE_MONO, 8), padx=5).pack(side="left", padx=(0, 4))
        if warns:
            tk.Label(badges, text=f"{warns} WARN", background="#302713", foreground=ht.WARN,
                    font=(ht.FACE_MONO, 8), padx=5).pack(side="left")
        if not errs and not warns:
            line.config(text="No structural problems found.", foreground=ht.OK)
        else:
            line.config(text=f"{errs} error(s), {warns} warning(s) — open Validate after "
                             "opening this mod for details.", foreground=ht.TEXT_MID)

    def _apply_stats(self, stats):
        if not self._stats_labels:
            return
        if stats is None:
            for lbl in self._stats_labels.values():
                if lbl.winfo_exists():
                    lbl.config(text="—")
            return
        mapping = {
            "Focus trees": stats.get("focus_trees", 0),
            "Events": stats.get("events", 0),
            "Countries touched": stats.get("countries_with_focuses", 0),
            "Files": stats.get("total_files", 0),
        }
        for label, val in mapping.items():
            lbl = self._stats_labels.get(label)
            if lbl is not None and lbl.winfo_exists():
                lbl.config(text=str(val))
