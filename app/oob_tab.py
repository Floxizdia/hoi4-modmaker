"""Starting Forces tab: build land/naval/air order-of-battle files for a
country - the same history/units/<TAG>_1936*.txt files the base game ships,
built with pickers instead of hand-typed regiment/equipment ids."""

import tkinter as tk
from tkinter import ttk, messagebox

from app.state import state
from app import oob_creator as oc
from app.map_picker import MapPickerDialog
from app import theme, ui_kit


class _RowList(ttk.Frame):
    """A vertical stack of rows, each a tuple of Entry/Combobox widgets,
    with an "Add row" button - the same pattern used for sub-ideologies and
    prerequisite picking elsewhere in this app."""

    def __init__(self, master, field_specs, add_label="+ Add row"):
        super().__init__(master)
        self.field_specs = field_specs  # [(key, kind, width, values_or_None)]
        self.rows = []
        self.rows_frame = ttk.Frame(self)
        self.rows_frame.pack(fill="x")
        ttk.Button(self, text=add_label, command=self.add_row).pack(anchor="w", pady=(2, 0))

    def add_row(self, defaults=None):
        defaults = defaults or {}
        i = len(self.rows)
        row_frame = ttk.Frame(self.rows_frame)
        row_frame.grid(row=i, column=0, sticky="w", pady=1)
        vars_ = {}
        col = 0
        for key, kind, width, values in self.field_specs:
            ttk.Label(row_frame, text=key + ":").grid(row=0, column=col, padx=(0, 2))
            col += 1
            var = tk.StringVar(value=str(defaults.get(key, "")))
            if kind == "combo":
                ttk.Combobox(row_frame, textvariable=var, values=values, width=width).grid(
                    row=0, column=col, padx=(0, 8))
            else:
                ttk.Entry(row_frame, textvariable=var, width=width).grid(row=0, column=col, padx=(0, 8))
            vars_[key] = var
            col += 1
        remove_btn = ttk.Button(row_frame, text="x", width=2,
                                 command=lambda: self._remove(row_frame))
        remove_btn.grid(row=0, column=col)
        self.rows.append((row_frame, vars_))

    def _remove(self, frame):
        self.rows = [r for r in self.rows if r[0] is not frame]
        frame.destroy()
        for i, (f, _) in enumerate(self.rows):
            f.grid(row=i, column=0, sticky="w", pady=1)

    def values(self):
        return [{k: v.get().strip() for k, v in vars_.items()} for _, vars_ in self.rows]

    def set_combo_values(self, key, values):
        for spec_i, (k, kind, width, _) in enumerate(self.field_specs):
            if k == key:
                self.field_specs[spec_i] = (k, kind, width, values)


class OobTab(ttk.Frame):
    def __init__(self, master):
        super().__init__(master, padding=12)
        self._cache = {}
        self._build()
        state.subscribe(self.on_mod_changed)

    def _build(self):
        self.header = ui_kit.PageHeader(
            self, "Starting Forces",
            "Order of battle: a country's starting divisions, division templates (regiments + support companies), and where they're deployed on the map.", help_key="oob")

        top = ttk.Frame(self)
        top.pack(fill="x")
        ttk.Label(top, text="Country tag").pack(side="left")
        self.tag_var = tk.StringVar()
        ttk.Entry(top, textvariable=self.tag_var, width=6).pack(side="left", padx=(4, 16))
        ttk.Label(top, text="OOB name (e.g. 1936)").pack(side="left")
        self.oob_name_var = tk.StringVar(value="1936")
        ttk.Entry(top, textvariable=self.oob_name_var, width=10).pack(side="left", padx=4)
        ttk.Label(
            top, text="Files are written into history/units/ — the exact line to paste "
                      "into the country's history file is shown after Create.",
            style="Muted.TLabel",
        ).pack(side="left", padx=16)

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, pady=(10, 0))
        self._build_land_page()
        self._build_air_page()
        self._build_naval_page()

        self.status = ttk.Label(self, text="", style="Status.TLabel", wraplength=900, justify="left")
        self.status.pack(anchor="w", pady=(8, 0))
        self.ref_row = ttk.Frame(self)
        self.ref_row.pack(anchor="w")
        self.ref_entry_var = tk.StringVar()
        self.ref_entry = ttk.Entry(self.ref_row, textvariable=self.ref_entry_var, width=40, state="readonly")

        self.on_mod_changed()

    # ---- land ----

    def _build_land_page(self):
        page = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(page, text="Land")

        ttk.Label(page, text="Template name (shown in-game)").pack(anchor="w")
        self.land_template_name = tk.StringVar(value="")
        ttk.Entry(page, textvariable=self.land_template_name, width=32).pack(anchor="w")
        self.land_name_hint = ttk.Label(page, text="", style="Muted.TLabel")
        self.land_name_hint.pack(anchor="w")
        self.land_template_name.trace_add("write", lambda *_: self._check_template_name())

        ttk.Label(page, text="Regiments (combat rows)").pack(anchor="w", pady=(8, 0))
        self.regiment_rows = _RowList(page, [
            ("type", "combo", 20, []), ("x", "entry", 4, None), ("y", "entry", 4, None),
        ])
        self.regiment_rows.pack(fill="x")

        ttk.Label(page, text="Support companies (optional)").pack(anchor="w", pady=(8, 0))
        self.support_rows = _RowList(page, [
            ("type", "combo", 20, []), ("x", "entry", 4, None), ("y", "entry", 4, None),
        ])
        self.support_rows.pack(fill="x")

        div_head = ttk.Frame(page)
        div_head.pack(fill="x", pady=(8, 0))
        ttk.Label(div_head, text="Divisions to place").pack(side="left")
        ttk.Button(div_head, text="Pick location on map...",
                   command=lambda: self._pick_location(self._add_division_row, "a division")).pack(side="left", padx=10)
        self.division_rows = _RowList(page, [
            ("name", "entry", 22, None), ("location (province id)", "entry", 10, None),
            ("count", "entry", 5, None),
        ], add_label="+ Add division group")
        self.division_rows.pack(fill="x")

        opts = ttk.Frame(page)
        opts.pack(fill="x", pady=(8, 0))
        ttk.Label(opts, text="Start experience").pack(side="left")
        self.start_exp_var = tk.StringVar(value="0.2")
        ttk.Entry(opts, textvariable=self.start_exp_var, width=6).pack(side="left", padx=(4, 16))
        ttk.Label(opts, text="Start equipment").pack(side="left")
        self.start_equip_var = tk.StringVar(value="0.8")
        ttk.Entry(opts, textvariable=self.start_equip_var, width=6).pack(side="left", padx=4)

        ttk.Button(page, text="Create Land OOB", style="Accent.TButton",
                   command=self._create_land).pack(anchor="w", pady=10)

        # sensible starting rows so the tab isn't empty on first open
        self.regiment_rows.add_row({"type": "infantry", "x": 0, "y": 0})
        self.regiment_rows.add_row({"type": "infantry", "x": 0, "y": 1})
        self.support_rows.add_row({"type": "recon", "x": 0, "y": 0})
        self.division_rows.add_row({"name": "1st Infantry Division", "location (province id)": "", "count": "1"})

    # ---- air ----

    def _build_air_page(self):
        page = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(page, text="Air")
        air_head = ttk.Frame(page)
        air_head.pack(fill="x")
        ttk.Label(air_head, text="Air wings (grouped by location automatically)").pack(side="left")
        ttk.Button(air_head, text="Pick location on map...",
                   command=lambda: self._pick_location(self._add_wing_row, "an air wing")).pack(side="left", padx=10)
        self.wing_rows = _RowList(page, [
            ("location (province id)", "entry", 10, None),
            ("equipment", "combo", 22, []), ("amount", "entry", 6, None),
        ])
        self.wing_rows.pack(fill="x", pady=(4, 0))
        ttk.Button(page, text="Create Air OOB", style="Accent.TButton",
                   command=self._create_air).pack(anchor="w", pady=10)
        self.wing_rows.add_row({"location (province id)": "", "equipment": "fighter_equipment_0", "amount": "18"})

    # ---- naval ----

    def _build_naval_page(self):
        page = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(page, text="Naval")
        row = ttk.Frame(page)
        row.pack(fill="x")
        ttk.Label(row, text="Fleet name").pack(side="left")
        self.fleet_name_var = tk.StringVar(value="")
        ttk.Entry(row, textvariable=self.fleet_name_var, width=28).pack(side="left", padx=(4, 16))
        ttk.Label(row, text="Naval base (province id)").pack(side="left")
        self.naval_base_var = tk.StringVar()
        ttk.Entry(row, textvariable=self.naval_base_var, width=10).pack(side="left", padx=4)
        ttk.Button(row, text="Pick on map...",
                   command=lambda: self._pick_location(self._set_naval_base, "a naval base")).pack(side="left", padx=6)

        ttk.Label(page, text="Ships").pack(anchor="w", pady=(8, 0))
        self.ship_rows = _RowList(page, [
            ("name", "entry", 22, None), ("hull", "combo", 16, []),
            ("equipment", "combo", 20, []), ("amount", "entry", 5, None),
        ])
        self.ship_rows.pack(fill="x")
        ttk.Button(page, text="Create Naval OOB", style="Accent.TButton",
                   command=self._create_naval).pack(anchor="w", pady=10)
        self.ship_rows.add_row({"name": "", "hull": "destroyer", "equipment": "destroyer_1", "amount": "1"})

    # ---- data ----

    def on_mod_changed(self):
        if state.is_loaded:
            self.header.set_status(True, state.mod_name)
        else:
            self.header.set_status(False, "no mod open")
        self._cache = {}
        self._reload_lists()

    def on_show(self):
        self.on_mod_changed()

    def _data(self):
        if not self._cache and state.is_loaded:
            self._cache = {
                "templates": oc.list_division_templates(state.mod_root),
                "regiment_types": oc.list_regiment_types(state.mod_root),
                "equipment": oc.list_equipment_ids(state.mod_root),
            }
        return self._cache

    def _reload_lists(self):
        data = self._data()
        regs = data.get("regiment_types", [])
        equip = data.get("equipment", [])
        for rowlist in (self.regiment_rows, self.support_rows):
            rowlist.set_combo_values("type", regs)
        self.wing_rows.set_combo_values("equipment", equip)
        self.ship_rows.set_combo_values("hull", regs)
        self.ship_rows.set_combo_values("equipment", equip)
        self._check_template_name()

    def _check_template_name(self):
        name = self.land_template_name.get().strip()
        existing = self._data().get("templates", {})
        if not name:
            self.land_name_hint.config(text="", foreground=theme.MUTED)
        elif name in existing:
            self.land_name_hint.config(text=f"'{name}' already used ({existing[name]}) — pick a unique name",
                                        foreground=theme.RED)
        else:
            self.land_name_hint.config(text="name is free ✓", foreground=theme.GREEN)

    def _show_ref(self, ref_line):
        self.ref_entry_var.set(ref_line)
        self.ref_entry.pack(side="left")
        ttk.Label(self.ref_row, text="  ← paste into this TAG's history/countries file",
                  style="Muted.TLabel").pack(side="left")

    def _tag(self):
        return self.tag_var.get().strip().upper()

    # ---- map picker ----

    def _pick_location(self, on_picked, purpose):
        if not state.is_loaded:
            messagebox.showerror("No mod", "Open a mod first.")
            return
        tag = self._tag()
        if not tag:
            messagebox.showerror("No country tag", "Type the country tag at the top first - "
                                  "the map picker zooms to that country's own territory.")
            return
        dlg = MapPickerDialog(self, state.mod_root, tag, purpose=purpose)
        self.wait_window(dlg)
        if dlg.result:
            on_picked(dlg.result)

    def _add_division_row(self, picked):
        self.division_rows.add_row({
            "name": f"Division at state {picked['state']}",
            "location (province id)": picked["province"],
            "count": "1",
        })
        self.status.config(text=f"Added a division row at {picked['label']}.")

    def _add_wing_row(self, picked):
        self.wing_rows.add_row({
            "location (province id)": picked["province"],
            "equipment": "fighter_equipment_0", "amount": "18",
        })
        self.status.config(text=f"Added an air wing row at {picked['label']}.")

    def _set_naval_base(self, picked):
        self.naval_base_var.set(str(picked["province"]))
        self.status.config(text=f"Naval base set to {picked['label']}.")

    # ---- create ----

    def _create_land(self):
        if not state.is_loaded:
            messagebox.showerror("No mod", "Open or create a mod first.")
            return
        tag, oob_name = self._tag(), self.oob_name_var.get().strip()
        name = self.land_template_name.get().strip()
        if not tag or not oob_name or not name:
            messagebox.showerror("Missing info", "Country tag, OOB name and template name are all required.")
            return
        existing = self._data().get("templates", {})
        if name in existing:
            messagebox.showerror("Name taken", f"'{name}' already exists ({existing[name]}).")
            return
        regiments = [(r["type"], r["x"] or 0, r["y"] or 0) for r in self.regiment_rows.values() if r["type"]]
        support = [(r["type"], r["x"] or 0, r["y"] or 0) for r in self.support_rows.values() if r["type"]]
        if not regiments:
            messagebox.showerror("No regiments", "Add at least one regiment row.")
            return
        divisions = []
        for r in self.division_rows.values():
            if not r["name"] or not r["location (province id)"]:
                continue
            try:
                divisions.append({
                    "name": r["name"], "location": int(r["location (province id)"]),
                    "count": int(r["count"] or 1),
                })
            except ValueError:
                messagebox.showerror("Bad number", "Location and count must be numbers.")
                return
        if not divisions:
            messagebox.showerror("No divisions", "Add at least one division group with a location.")
            return

        try:
            path, ref = oc.create_land_oob(
                state.mod_root, tag=tag, oob_name=oob_name, template_name=name,
                regiments=regiments, support=support, divisions=divisions,
                start_experience=float(self.start_exp_var.get() or 0.2),
                start_equipment=float(self.start_equip_var.get() or 0.8),
            )
        except Exception as exc:
            messagebox.showerror("Failed", f"Land OOB creation failed:\n{exc}")
            return

        existing[name] = "mod"
        total = sum(d["count"] for d in divisions)
        self.status.config(text=f"Created {total} division(s) using template '{name}' in {path}.")
        self._show_ref(ref)

    def _create_air(self):
        if not state.is_loaded:
            messagebox.showerror("No mod", "Open or create a mod first.")
            return
        tag, oob_name = self._tag(), self.oob_name_var.get().strip()
        if not tag or not oob_name:
            messagebox.showerror("Missing info", "Country tag and OOB name are required.")
            return
        wings = []
        for r in self.wing_rows.values():
            if not r["location (province id)"] or not r["equipment"]:
                continue
            try:
                wings.append({
                    "location": int(r["location (province id)"]), "equipment": r["equipment"],
                    "amount": int(r["amount"] or 1),
                })
            except ValueError:
                messagebox.showerror("Bad number", "Location and amount must be numbers.")
                return
        if not wings:
            messagebox.showerror("No wings", "Add at least one air wing row.")
            return

        try:
            path, ref = oc.create_air_oob(state.mod_root, tag=tag, oob_name=oob_name, wings=wings)
        except Exception as exc:
            messagebox.showerror("Failed", f"Air OOB creation failed:\n{exc}")
            return
        self.status.config(text=f"Created {len(wings)} air wing group(s) in {path}.")
        self._show_ref(ref)

    def _create_naval(self):
        if not state.is_loaded:
            messagebox.showerror("No mod", "Open or create a mod first.")
            return
        tag, oob_name = self._tag(), self.oob_name_var.get().strip()
        fleet_name = self.fleet_name_var.get().strip()
        if not tag or not oob_name or not fleet_name or not self.naval_base_var.get().strip():
            messagebox.showerror("Missing info", "Country tag, OOB name, fleet name and naval base are required.")
            return
        ships = []
        for r in self.ship_rows.values():
            if not r["name"] or not r["hull"] or not r["equipment"]:
                continue
            try:
                ships.append({"name": r["name"], "hull": r["hull"], "equipment": r["equipment"],
                              "amount": int(r["amount"] or 1)})
            except ValueError:
                messagebox.showerror("Bad number", "Amount must be a number.")
                return
        if not ships:
            messagebox.showerror("No ships", "Add at least one ship row.")
            return
        try:
            naval_base = int(self.naval_base_var.get())
        except ValueError:
            messagebox.showerror("Bad number", "Naval base must be a province id number.")
            return

        try:
            path, ref = oc.create_naval_oob(
                state.mod_root, tag=tag, oob_name=oob_name, fleet_name=fleet_name,
                naval_base=naval_base, ships=ships,
            )
        except Exception as exc:
            messagebox.showerror("Failed", f"Naval OOB creation failed:\n{exc}")
            return
        self.status.config(text=f"Created fleet '{fleet_name}' with {len(ships)} ship(s) in {path}.")
        self._show_ref(ref)
