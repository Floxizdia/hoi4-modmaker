"""Divisions tab: build a division template on a grid and write it into an
OOB file, instead of typing regiment coordinates by hand.

The grid is the game's own layout - five columns of five, plus five support
slots - so what you see here is the shape the template will have in game.
"""

import os
import tkinter as tk
from tkinter import messagebox, ttk

from app.state import state
from app import division_designer as dd
from app import mod_export, safe_io
from app import theme, ui_kit

PRESETS = {
    "Infantry (9/0)": ([("infantry", 3, 3)], []),
    "Infantry + artillery (9/3)": ([("infantry", 3, 3), ("artillery_brigade", 1, 3)], []),
    "Armour (6 armour / 4 mot)": ([("light_armor", 2, 3), ("motorized", 2, 2)], []),
    "Cavalry (3)": ([("cavalry", 1, 3)], []),
}


class DivisionTab(ttk.Frame):
    def __init__(self, master):
        super().__init__(master, padding=12)
        self.catalogue = {}
        self.cells = {}          # (x, y) -> StringVar
        self.support_vars = []
        self._build()
        state.subscribe(self.on_mod_changed)

    # ---- layout ----

    def _build(self):
        self.header = ui_kit.PageHeader(
            self, "Divisions",
            "Build a division template on the game's own 5x5 grid, see its combat width and "
            "manpower as you go, then write it into an OOB file.", help_key="divisions")

        top = ttk.Frame(self)
        top.pack(fill="x", pady=(0, 8))
        ttk.Button(top, text="Load battalions", style="Accent.TButton",
                   command=self._load).pack(side="left")
        ttk.Label(top, text="   Template name:").pack(side="left")
        self.name_var = tk.StringVar(value="My Infantry Division")
        ttk.Entry(top, textvariable=self.name_var, width=28).pack(side="left", padx=4)
        ttk.Label(top, text="   Preset:").pack(side="left")
        self.preset_var = tk.StringVar()
        preset = ttk.Combobox(top, textvariable=self.preset_var, state="readonly",
                              width=26, values=list(PRESETS))
        preset.pack(side="left", padx=4)
        preset.bind("<<ComboboxSelected>>", lambda e: self._apply_preset())
        ttk.Button(top, text="Clear", command=self._clear).pack(side="left", padx=6)
        self.count_label = ttk.Label(top, text="", style="Muted.TLabel")
        self.count_label.pack(side="left", padx=8)

        body = ttk.Frame(self)
        body.pack(fill="both", expand=True)

        grid_box = ui_kit.Section(body, "Regiments")
        grid_box.pack(side="left", fill="y", padx=(0, ui_kit.PAD_SECTION))
        grid = grid_box.body
        for x in range(dd.COLUMNS):
            ttk.Label(grid, text=f"col {x + 1}", style="Muted.TLabel").grid(
                row=0, column=x, padx=2, pady=(0, 2))
        for y in range(dd.ROWS):
            for x in range(dd.COLUMNS):
                var = tk.StringVar()
                combo = ttk.Combobox(grid, textvariable=var, width=17, state="readonly")
                combo.grid(row=y + 1, column=x, padx=2, pady=2)
                combo.bind("<<ComboboxSelected>>", lambda e: self._recompute())
                self.cells[(x, y)] = (var, combo)

        right = ttk.Frame(body)
        right.pack(side="left", fill="both", expand=True)

        support_box = ui_kit.Section(right, "Support companies")
        support_box.pack(fill="x")
        for i in range(dd.SUPPORT_SLOTS):
            var = tk.StringVar()
            combo = ttk.Combobox(support_box.body, textvariable=var, width=24, state="readonly")
            combo.grid(row=i // 3, column=i % 3, padx=3, pady=3)
            combo.bind("<<ComboboxSelected>>", lambda e: self._recompute())
            self.support_vars.append((var, combo))

        stats_box = ui_kit.Section(right, "Division totals")
        stats_box.pack(fill="x", pady=(ui_kit.PAD_SECTION, 0))
        self.stat_labels = {}
        for i, key in enumerate(dd.STAT_KEYS):
            ttk.Label(stats_box.body, text=key.replace("_", " ")).grid(
                row=i, column=0, sticky="w", pady=1)
            label = ttk.Label(stats_box.body, text="—", style="Gold.TLabel")
            label.grid(row=i, column=1, sticky="e", padx=(30, 0), pady=1)
            self.stat_labels[key] = label
        ttk.Label(stats_box.body, style="Muted.TLabel", wraplength=330, justify="left",
                  text="Support companies add no combat width, and organisation is the average "
                       "across battalions rather than the total — both as the game does it. "
                       "Attack and defence aren't shown because a battalion gets those from its "
                       "equipment, not from the template.").grid(
            row=len(dd.STAT_KEYS), column=0, columnspan=2, sticky="w", pady=(6, 0))

        out_box = ui_kit.Section(right, "Write it out")
        out_box.pack(fill="both", expand=True, pady=(ui_kit.PAD_SECTION, 0))
        row = ttk.Frame(out_box.body)
        row.pack(fill="x")
        ttk.Label(row, text="OOB file:").pack(side="left")
        self.oob_var = tk.StringVar()
        self.oob_combo = ttk.Combobox(row, textvariable=self.oob_var, width=32, state="readonly")
        self.oob_combo.pack(side="left", padx=4)
        ttk.Button(row, text="Add to file", command=self._append).pack(side="left", padx=4)
        ttk.Button(row, text="Copy text", command=self._copy).pack(side="left")

        self.preview = tk.Text(out_box.body, height=12, wrap="none")
        self.preview.pack(fill="both", expand=True, pady=(6, 0))

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
        self.catalogue = {}
        self.count_label.config(text="")

    def on_show(self):
        self.on_mod_changed()

    def _load(self):
        if not state.is_loaded:
            messagebox.showerror("No mod", "Open a mod first.")
            return
        self.catalogue = dd.load_sub_units(state.mod_root)
        line = sorted(n for n, v in self.catalogue.items() if not v.get("support"))
        support = sorted(n for n, v in self.catalogue.items() if v.get("support"))
        for _var, combo in self.cells.values():
            combo.configure(values=[""] + line)
        for _var, combo in self.support_vars:
            combo.configure(values=[""] + support)

        files = dd.oob_files(state.mod_root)
        self.oob_combo.configure(values=[os.path.basename(p) for p in files])
        self.count_label.config(
            text=f"{len(line)} battalions · {len(support)} support companies")
        self._recompute()

    # ---- editing ----

    def _regiments(self):
        out = {}
        for (x, y), (var, _combo) in self.cells.items():
            name = var.get().strip()
            if name:
                out[(x, y)] = name
        return out

    def _support(self):
        return [var.get().strip() for var, _combo in self.support_vars if var.get().strip()]

    def _clear(self):
        for var, _combo in self.cells.values():
            var.set("")
        for var, _combo in self.support_vars:
            var.set("")
        self._recompute()

    def _apply_preset(self):
        recipe = PRESETS.get(self.preset_var.get())
        if not recipe:
            return
        self._clear()
        columns, _support = recipe
        x = 0
        for name, width, height in columns:
            for column in range(width):
                for y in range(height):
                    if x + column < dd.COLUMNS and y < dd.ROWS:
                        self.cells[(x + column, y)][0].set(name)
            x += width
        self._recompute()

    def _recompute(self):
        regiments, support = self._regiments(), self._support()
        totals = dd.division_stats(regiments, support, self.catalogue)
        for key, label in self.stat_labels.items():
            value = totals.get(key)
            label.config(text="—" if value is None else f"{value:g}")

        text = dd.format_template(self.name_var.get().strip() or "My Division",
                                  regiments, support)
        self.preview.delete("1.0", "end")
        self.preview.insert("1.0", text)

        found = dd.problems(regiments, support, self.catalogue)
        self.status.config(text="  ".join(found) if found else "")

    # ---- output ----

    def _template_text(self):
        return dd.format_template(self.name_var.get().strip() or "My Division",
                                  self._regiments(), self._support())

    def _copy(self):
        self.clipboard_clear()
        self.clipboard_append(self._template_text())
        self.status.config(text="Template copied — paste it at the top of an OOB file.")

    def _append(self):
        if not state.is_loaded:
            messagebox.showerror("No mod", "Open a mod first.")
            return
        regiments = self._regiments()
        if not regiments:
            self.status.config(text="Put at least one battalion in the grid first.")
            return
        chosen = self.oob_var.get().strip()
        if not chosen:
            self.status.config(text="Pick an OOB file — 'Load battalions' fills that list from "
                                    "the mod's history/units folder.")
            return

        found = dd.problems(regiments, self._support(), self.catalogue)
        if found and not messagebox.askyesno(
                "Write it anyway?", "\n".join(found) + "\n\nWrite the template as it is?"):
            return

        path = os.path.join(state.mod_root, dd.OOB_DIR, chosen)
        content = dd.append_to_oob(path, self._template_text())
        if not safe_io.write_text(path, content, parent=self, describe=chosen):
            self.status.config(text="Left the file alone.")
            return
        mod_export.record_created(state.mod_root, [path])
        # notifying clears this screen's own catalogue via on_mod_changed,
        # so the battalion lists are put back straight afterwards rather
        # than leaving the grid pointing at units it no longer knows
        state.content_changed()
        self._load()
        self.status.config(
            text=f"Template added to the top of {chosen}, where the game looks for it before "
                 "the units that use it. Original kept as .bak.")
