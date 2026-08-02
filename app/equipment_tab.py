"""Equipment tab: add a new upgrade tier to an existing equipment archetype
(infantry weapons, tank chassis, plane airframes, ship hulls...) -
common/units/equipment/."""

import tkinter as tk
from tkinter import ttk, messagebox

from app.state import state
from app import equipment_creator as eqc
from app import theme, ui_kit


class EquipmentTab(ttk.Frame):
    def __init__(self, master):
        super().__init__(master, padding=12)
        self._build()
        state.subscribe(self.on_mod_changed)

    def _build(self):
        self.header = ui_kit.PageHeader(
            self, "Equipment",
            "Adds a new upgrade tier to an existing equipment archetype (infantry weapons, tank chassis, plane airframes...) - new archetypes need 3D models this tool can't add, so this is for the 'later-war upgrade' pattern vanilla itself uses.", help_key="equipment")
        ttk.Label(
            self, text="New archetypes need 3D models this tool can't add — what this creates is a new "
                       "upgrade tier of an existing archetype (a later-war infantry rifle, a heavier tank "
                       "chassis...), the same way vanilla's own tiers stack.",
            style="Muted.TLabel", wraplength=980, justify="left",
        ).pack(anchor="w", pady=(0, 8))

        body = ttk.Frame(self)
        body.pack(fill="both", expand=True)

        browse = ui_kit.Section(body, "Archetype")
        browse.pack(side="left", fill="y", padx=(0, ui_kit.PAD_SECTION))
        browse.configure(width=340)
        browse.pack_propagate(False)
        self.archetype_var = tk.StringVar(value="infantry_equipment")
        ttk.Combobox(browse.body, textvariable=self.archetype_var, state="readonly", width=32,
                     values=eqc.ARCHETYPES).pack(fill="x", pady=(2, 8))
        self.archetype_var.trace_add("write", lambda *_: self._refresh_list())

        ttk.Label(browse.body, text="Existing tiers of this archetype", font=("Segoe UI", 10, "bold")).pack(anchor="w")
        self.tree = ttk.Treeview(browse.body, columns=("id", "parent", "year", "src"), show="headings", height=22)
        for col, w in (("id", 150), ("parent", 110), ("year", 45), ("src", 55)):
            self.tree.heading(col, text=col)
            self.tree.column(col, width=w)
        self.tree.pack(fill="both", expand=True, pady=(6, 0))
        self.tree.tag_configure("mod", foreground=theme.GREEN)
        self.tree.bind("<<TreeviewSelect>>", lambda e: self._pick_parent())

        create = ui_kit.Section(body, "Create a new tier")
        create.pack(side="left", fill="both", expand=True)
        right = create.body

        row = ttk.Frame(right)
        row.pack(fill="x", pady=(8, 0))
        ttk.Label(row, text="Equipment id").pack(side="left")
        self.id_var = tk.StringVar()
        ttk.Entry(row, textvariable=self.id_var, width=26).pack(side="left", padx=(4, 16))
        ttk.Label(row, text="Parent (inherits unset stats)").pack(side="left")
        self.parent_var = tk.StringVar()
        ttk.Entry(row, textvariable=self.parent_var, width=22).pack(side="left", padx=4)
        self.id_hint = ttk.Label(right, text="", style="Muted.TLabel")
        self.id_hint.pack(anchor="w")
        self.id_var.trace_add("write", lambda *_: self._check_id())

        row2 = ttk.Frame(right)
        row2.pack(fill="x", pady=(8, 0))
        ttk.Label(row2, text="Year").pack(side="left")
        self.year_var = tk.StringVar(value="1940")
        ttk.Entry(row2, textvariable=self.year_var, width=8).pack(side="left", padx=(4, 16))
        ttk.Label(row2, text="Priority").pack(side="left")
        self.priority_var = tk.StringVar(value="10")
        ttk.Entry(row2, textvariable=self.priority_var, width=6).pack(side="left", padx=(4, 16))
        ttk.Label(row2, text="Visual level").pack(side="left")
        self.visual_var = tk.StringVar()
        ttk.Entry(row2, textvariable=self.visual_var, width=6).pack(side="left", padx=4)

        ttk.Label(right, text="Stats (blank = inherit from parent)", font=("Segoe UI", 9, "bold")).pack(
            anchor="w", pady=(10, 2))
        stat_grid = ttk.Frame(right)
        stat_grid.pack(fill="x")
        self.stat_vars = {}
        for i, tok in enumerate(eqc.STAT_FIELDS):
            cell = ttk.Frame(stat_grid)
            cell.grid(row=i // 3, column=i % 3, sticky="w", padx=(0, 14), pady=2)
            ttk.Label(cell, text=tok, width=14).pack(side="left")
            var = tk.StringVar()
            ttk.Entry(cell, textvariable=var, width=8).pack(side="left")
            self.stat_vars[tok] = var

        ttk.Label(right, text="Resources (per unit)", font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(10, 2))
        res_row = ttk.Frame(right)
        res_row.pack(fill="x")
        self.res_vars = {}
        for i, tok in enumerate(["steel", "chromium", "tungsten", "aluminium", "rubber", "oil"]):
            cell = ttk.Frame(res_row)
            cell.grid(row=0, column=i, sticky="w", padx=(0, 14))
            ttk.Label(cell, text=tok).pack(side="left")
            var = tk.StringVar()
            ttk.Entry(cell, textvariable=var, width=5).pack(side="left", padx=4)
            self.res_vars[tok] = var

        ttk.Button(right, text="Create Equipment", style="Accent.TButton",
                   command=self._create).pack(anchor="w", pady=12)
        self.status = ttk.Label(right, text="", style="Status.TLabel", wraplength=640, justify="left")
        self.status.pack(anchor="w")

        self.on_mod_changed()

    def on_mod_changed(self):
        if state.is_loaded:
            self.header.set_status(True, state.mod_name)
        else:
            self.header.set_status(False, "no mod open")
        self._cache = {}
        self._refresh_list()

    def on_show(self):
        self.on_mod_changed()

    def _data(self):
        if not state.is_loaded:
            return {}
        return eqc.list_equipment(state.mod_root, archetype=self.archetype_var.get())

    def _refresh_list(self):
        self.tree.delete(*self.tree.get_children())
        if not state.is_loaded:
            return
        self._cache = self._data()
        for eq_id, (source, arch, parent, year) in sorted(self._cache.items(), key=lambda kv: kv[1][3]):
            self.tree.insert("", "end", values=(eq_id, parent, year, source),
                              tags=("mod",) if source == "mod" else ())

    def _pick_parent(self):
        sel = self.tree.selection()
        if sel:
            self.parent_var.set(self.tree.item(sel[0], "values")[0])

    def _check_id(self):
        eid = self.id_var.get().strip()
        if not eid:
            self.id_hint.config(text="", foreground=theme.MUTED)
            return
        existing = eqc.list_equipment(state.mod_root) if state.is_loaded else {}
        if eid in existing:
            self.id_hint.config(text=f"'{eid}' already exists ({existing[eid][0]})!", foreground=theme.RED)
        else:
            self.id_hint.config(text="free ✓", foreground=theme.GREEN)

    def _create(self):
        if not state.is_loaded:
            messagebox.showerror("No mod", "Open or create a mod first.")
            return
        eid = self.id_var.get().strip()
        if not eid:
            messagebox.showerror("Missing info", "An equipment id is required.")
            return
        existing = eqc.list_equipment(state.mod_root)
        if eid in existing:
            messagebox.showerror("Id taken", f"'{eid}' already exists ({existing[eid][0]}).")
            return
        try:
            year = int(self.year_var.get())
        except ValueError:
            messagebox.showerror("Bad number", "Year must be a whole number.")
            return

        stats = {}
        for tok, var in self.stat_vars.items():
            v = var.get().strip()
            if v:
                try:
                    float(v)
                except ValueError:
                    messagebox.showerror("Bad number", f"'{tok}' must be a number.")
                    return
                stats[tok] = v
        resources = {tok: v.get().strip() for tok, v in self.res_vars.items() if v.get().strip()}

        try:
            path = eqc.create_equipment(
                state.mod_root, equipment_id=eid, archetype=self.archetype_var.get(),
                parent=self.parent_var.get().strip(), year=year, priority=self.priority_var.get().strip(),
                visual_level=self.visual_var.get().strip(), stats=stats, resources=resources,
            )
        except Exception as exc:
            messagebox.showerror("Failed", f"Equipment creation failed:\n{exc}")
            return

        self._refresh_list()
        self.status.config(
            text=f"Created '{eid}' in {path}.\nTo unlock it, add this to a technology's "
                 f"enable_equipments block:\n\n{eid}\n\n(technologies files are hand-authored, "
                 "so paste this in yourself in the Tech tab or Code editor.)")
