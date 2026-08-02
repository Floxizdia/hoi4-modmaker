"""State / Province editor: pick an existing state, tune its resources,
building slots, victory points and category without hand-editing
history/states/*.txt."""

import os
import tkinter as tk
from tkinter import ttk, messagebox

from app.state import state
from app import map_data
from app import state_surgery as ss
from app import new_state_creator as nsc
from app import theme, ui_kit

RESOURCE_TOKENS = ["oil", "aluminium", "rubber", "tungsten", "steel", "chromium", "coal"]
STATE_CATEGORIES = [
    "wasteland", "enclave", "tiny_island", "small_island", "pastoral", "rural",
    "town", "large_town", "city", "large_city", "metropolis", "megalopolis",
]
BUILDING_TOKENS = [
    "infrastructure", "arms_factory", "industrial_complex", "air_base",
    "supply_node", "rail_way", "naval_base", "naval_facility", "bunker",
    "coastal_bunker", "dockyard", "anti_air_building", "synthetic_refinery",
    "fuel_silo", "radar_station", "rocket_site",
]


class StateTab(ttk.Frame):
    def __init__(self, master):
        super().__init__(master, padding=12)
        self._states = {}
        self._current_id = None
        self._build()
        state.subscribe(self.on_mod_changed)

    def _build(self):
        self.header = ui_kit.PageHeader(
            self, "States",
            "Edit an existing state's resources, building slots, category and victory points, or build a brand new state from unclaimed map provinces.", help_key="state_edit")

        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True)
        edit_page = ttk.Frame(notebook, padding=8)
        create_page = ttk.Frame(notebook, padding=8)
        notebook.add(edit_page, text="Edit Existing")
        notebook.add(create_page, text="Create New State")

        self._build_edit_page(edit_page)
        self._build_create_page(create_page)

    def _build_edit_page(self, parent):
        body = ttk.Frame(parent)
        body.pack(fill="both", expand=True)

        left = ttk.Frame(body, width=300)
        left.pack(side="left", fill="y", padx=(0, 16))
        left.pack_propagate(False)
        ttk.Label(left, text="States", font=("Segoe UI", 10, "bold")).pack(anchor="w")
        self.search_var = tk.StringVar()
        ttk.Entry(left, textvariable=self.search_var).pack(fill="x", pady=(4, 0))
        self.search_var.trace_add("write", lambda *_: self._refresh_list())
        self.tree = ttk.Treeview(left, columns=("id", "name", "owner"), show="headings", height=26)
        self.tree.heading("id", text="id")
        self.tree.heading("name", text="name")
        self.tree.heading("owner", text="owner")
        self.tree.column("id", width=50)
        self.tree.column("name", width=140)
        self.tree.column("owner", width=50)
        self.tree.pack(fill="both", expand=True, pady=(6, 0))
        self.tree.tag_configure("inmod", foreground=theme.GREEN)
        self.tree.bind("<<TreeviewSelect>>", lambda e: self._load_selected())

        right = ttk.Frame(body)
        right.pack(side="left", fill="both", expand=True)
        self.title_lbl = ttk.Label(right, text="Pick a state on the left", font=("Segoe UI", 10, "bold"))
        self.title_lbl.pack(anchor="w")
        ttk.Label(
            right, text="Editing a base-game state copies it into your mod first — the original "
                        "install file is never touched.",
            style="Muted.TLabel", wraplength=640, justify="left",
        ).pack(anchor="w", pady=(2, 8))

        form = ttk.Frame(right)
        form.pack(fill="x")

        row = ttk.Frame(form)
        row.pack(fill="x", pady=2)
        ttk.Label(row, text="Category").pack(side="left")
        self.cat_var = tk.StringVar()
        ttk.Combobox(row, textvariable=self.cat_var, state="readonly", width=16,
                     values=STATE_CATEGORIES).pack(side="left", padx=(4, 16))
        ttk.Label(row, text="Manpower").pack(side="left")
        self.manpower_var = tk.StringVar()
        ttk.Entry(row, textvariable=self.manpower_var, width=12).pack(side="left", padx=(4, 16))
        ttk.Label(row, text="Local supplies").pack(side="left")
        self.supplies_var = tk.StringVar()
        ttk.Entry(row, textvariable=self.supplies_var, width=8).pack(side="left", padx=4)

        ttk.Label(form, text="Resources (per year)", font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(10, 2))
        res_row = ttk.Frame(form)
        res_row.pack(fill="x")
        self.res_vars = {}
        for i, tok in enumerate(RESOURCE_TOKENS):
            cell = ttk.Frame(res_row)
            cell.grid(row=i // 4, column=i % 4, sticky="w", padx=(0, 14), pady=2)
            ttk.Label(cell, text=tok).pack(side="left")
            var = tk.StringVar()
            ttk.Entry(cell, textvariable=var, width=6).pack(side="left", padx=4)
            self.res_vars[tok] = var

        ttk.Label(form, text="Building slots", font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(10, 2))
        bld_row = ttk.Frame(form)
        bld_row.pack(fill="x")
        self.bld_vars = {}
        for i, tok in enumerate(BUILDING_TOKENS):
            cell = ttk.Frame(bld_row)
            cell.grid(row=i // 4, column=i % 4, sticky="w", padx=(0, 14), pady=2)
            ttk.Label(cell, text=tok).pack(side="left")
            var = tk.StringVar()
            ttk.Entry(cell, textvariable=var, width=5).pack(side="left", padx=4)
            self.bld_vars[tok] = var

        vp_head = ttk.Frame(form)
        vp_head.pack(fill="x", pady=(10, 2))
        ttk.Label(vp_head, text="Victory points (province id, value — one per line)",
                  font=("Segoe UI", 9, "bold")).pack(side="left")
        ttk.Button(vp_head, text="Pick province on map...",
                   command=self._pick_vp_province).pack(side="left", padx=10)
        self.vp_txt = tk.Text(form, height=4, width=40)
        self.vp_txt.pack(anchor="w")

        ttk.Button(right, text="Apply Changes", style="Accent.TButton",
                   command=self._apply).pack(anchor="w", pady=12)
        self.status = ttk.Label(right, text="", style="Status.TLabel", wraplength=640, justify="left")
        self.status.pack(anchor="w")

    def on_mod_changed(self):
        if state.is_loaded:
            self.header.set_status(True, state.mod_name)
        else:
            self.header.set_status(False, "no mod open")
        self._states = {}
        self._current_id = None
        self._refresh_list()
        if hasattr(self, "unclaimed_list"):
            self.unclaimed_list.delete(0, "end")
            self.new_id_var.set("")

    def on_show(self):
        self.on_mod_changed()

    def _all_states(self):
        if not self._states and state.is_loaded:
            try:
                self._states = map_data.load_states(map_data._states_dir(state.mod_root))
            except Exception:
                self._states = {}
        return self._states

    def _refresh_list(self):
        self.tree.delete(*self.tree.get_children())
        if not state.is_loaded:
            return
        needle = self.search_var.get().strip().lower()
        for sid, st in sorted(self._all_states().items()):
            if needle and needle not in st["name"].lower() and needle not in str(sid):
                continue
            in_mod = os.path.abspath(st["file"]).startswith(os.path.abspath(state.mod_root))
            self.tree.insert("", "end", iid=str(sid), values=(sid, st["name"], st["owner"]),
                              tags=("inmod",) if in_mod else ())

    def _load_selected(self):
        sel = self.tree.selection()
        if not sel:
            return
        sid = int(sel[0])
        st = self._all_states().get(sid)
        if not st:
            return
        self._current_id = sid
        self.title_lbl.config(text=f"State {sid} — {st['name']} ({st['owner'] or 'no owner'})")

        fields = ss.read_fields(st["file"])
        if fields is None:
            self.status.config(text="Couldn't parse that state file.", foreground=theme.RED)
            return
        self.cat_var.set(fields["state_category"])
        self.manpower_var.set(fields["manpower"])
        self.supplies_var.set(fields["local_supplies"])
        for tok, var in self.res_vars.items():
            var.set(fields["resources"].get(tok, ""))
        for tok, var in self.bld_vars.items():
            var.set(fields["buildings"].get(tok, ""))
        self.vp_txt.delete("1.0", "end")
        self.vp_txt.insert("1.0", "\n".join(f"{p} {v}" for p, v in fields["victory_points"]))
        self.status.config(text="")

    def _pick_vp_province(self):
        """Victory points must name a province inside this state, so the
        picker is scoped to the state being edited rather than the whole
        map - clicking anywhere else would just produce a line the game
        silently ignores."""
        if not state.is_loaded:
            messagebox.showerror("No mod", "Open a mod first.")
            return
        if self._current_id is None:
            messagebox.showerror("No state", "Load a state first - the picker zooms to it.")
            return
        from app.map_picker import MapPickerDialog
        dlg = MapPickerDialog(self, state.mod_root, state_ids=[self._current_id],
                              purpose="a victory point")
        self.wait_window(dlg)
        if not dlg.result:
            return
        pid = dlg.result["province"]
        st = self._all_states().get(self._current_id)
        if st and pid not in st["provinces"]:
            self.status.config(
                text=f"Province {pid} isn't part of state {self._current_id} — the game would "
                     "ignore a victory point there.", foreground=theme.AMBER)
            return
        existing = self.vp_txt.get("1.0", "end").strip()
        line = f"{pid} 5"
        self.vp_txt.insert("end", ("\n" if existing else "") + line)
        self.status.config(text=f"Added victory point at {dlg.result['label']} (edit the value if needed).",
                            foreground=theme.GREEN)

    def _apply(self):
        if self._current_id is None:
            messagebox.showerror("No state", "Pick a state to edit first.")
            return
        st = self._all_states()[self._current_id]

        map_data.localise_state(state.mod_root, [self._current_id], self._all_states())
        path = self._all_states()[self._current_id]["file"]

        scalars = {
            "state_category": self.cat_var.get().strip(),
            "manpower": self.manpower_var.get().strip(),
            "local_supplies": self.supplies_var.get().strip(),
        }
        resources = {tok: v.get().strip() for tok, v in self.res_vars.items() if v.get().strip()}
        buildings = {tok: v.get().strip() for tok, v in self.bld_vars.items() if v.get().strip()}

        vp = []
        for line in self.vp_txt.get("1.0", "end").splitlines():
            parts = line.split()
            if len(parts) >= 2 and all(p.isdigit() for p in parts[:2]):
                vp.append((parts[0], parts[1]))

        try:
            ss.apply_edits(path, scalars=scalars, resources=resources or None,
                            buildings=buildings or None, victory_points=vp)
        except Exception as exc:
            messagebox.showerror("Failed", f"Couldn't save that state:\n{exc}")
            return

        self._refresh_list()
        self.status.config(text=f"Saved state {self._current_id} to {path}.", foreground=theme.GREEN)

    # ---- create new state ----

    def _build_create_page(self, parent):
        ttk.Label(
            parent, text="For provinces that exist on the map but no state claims yet — mostly "
                        "relevant if you've added a custom map. Vanilla's own map is already fully "
                        "covered by vanilla states, so nothing will show up unclaimed there.",
            style="Muted.TLabel", wraplength=980, justify="left",
        ).pack(anchor="w", pady=(0, 8))

        body = ttk.Frame(parent)
        body.pack(fill="both", expand=True)

        left = ttk.Frame(body, width=280)
        left.pack(side="left", fill="y", padx=(0, 16))
        left.pack_propagate(False)
        ttk.Label(left, text="Unclaimed land provinces", font=("Segoe UI", 10, "bold")).pack(anchor="w")
        self.unclaimed_list = tk.Listbox(left, selectmode="extended", height=26)
        self.unclaimed_list.pack(fill="both", expand=True, pady=(6, 0))
        ttk.Button(left, text="Refresh", command=self._refresh_unclaimed).pack(fill="x", pady=(4, 0))

        right = ttk.Frame(body)
        right.pack(side="left", fill="both", expand=True)
        ttk.Label(right, text="New state", font=("Segoe UI", 10, "bold")).pack(anchor="w")

        row = ttk.Frame(right)
        row.pack(fill="x", pady=(8, 0))
        ttk.Label(row, text="State id").pack(side="left")
        self.new_id_var = tk.StringVar()
        self.new_id_entry = ttk.Entry(row, textvariable=self.new_id_var, width=10)
        self.new_id_entry.pack(side="left", padx=(4, 16))
        ttk.Label(row, text="Name").pack(side="left")
        self.new_name_var = tk.StringVar()
        self.new_name_entry = ttk.Entry(row, textvariable=self.new_name_var, width=22)
        self.new_name_entry.pack(side="left", padx=(4, 16))
        ttk.Label(row, text="Owner tag").pack(side="left")
        self.new_owner_var = tk.StringVar()
        self.new_owner_entry = ttk.Entry(row, textvariable=self.new_owner_var, width=6)
        self.new_owner_entry.pack(side="left", padx=4)

        row2 = ttk.Frame(right)
        row2.pack(fill="x", pady=(8, 0))
        ttk.Label(row2, text="Category").pack(side="left")
        self.new_cat_var = tk.StringVar(value="rural")
        ttk.Combobox(row2, textvariable=self.new_cat_var, state="readonly", width=16,
                     values=STATE_CATEGORIES).pack(side="left", padx=(4, 16))
        ttk.Label(row2, text="Manpower").pack(side="left")
        self.new_manpower_var = tk.StringVar(value="50000")
        ttk.Entry(row2, textvariable=self.new_manpower_var, width=12).pack(side="left", padx=(4, 16))
        ttk.Label(row2, text="Local supplies").pack(side="left")
        self.new_supplies_var = tk.StringVar(value="1.0")
        ttk.Entry(row2, textvariable=self.new_supplies_var, width=8).pack(side="left", padx=4)

        ttk.Label(right, text="Selected provinces become this state's territory — pick them "
                              "on the left (Ctrl/Shift-click for multiple).", style="Muted.TLabel",
                  wraplength=640, justify="left").pack(anchor="w", pady=(8, 0))

        ttk.Label(right, text="Resources (per year)", font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(10, 2))
        res_row = ttk.Frame(right)
        res_row.pack(fill="x")
        self.new_res_vars = {}
        for i, tok in enumerate(RESOURCE_TOKENS):
            cell = ttk.Frame(res_row)
            cell.grid(row=i // 4, column=i % 4, sticky="w", padx=(0, 14), pady=2)
            ttk.Label(cell, text=tok).pack(side="left")
            var = tk.StringVar()
            ttk.Entry(cell, textvariable=var, width=6).pack(side="left", padx=4)
            self.new_res_vars[tok] = var

        self.create_state_btn = ttk.Button(right, text="Create State", style="Accent.TButton",
                                           command=self._create_state)
        self.create_state_btn.pack(anchor="w", pady=12)
        ui_kit.attach_tooltip(
            self.create_state_btn,
            lambda: "Fill in state id, name and owner tag first." if self.create_state_btn["state"] == "disabled"
            else "Writes the new state file, claiming the selected provinces.")
        self.create_status = ttk.Label(right, text="", style="Status.TLabel", wraplength=640, justify="left")
        self.create_status.pack(anchor="w")
        ui_kit.guard_required(
            {self.new_id_entry: self.new_id_var, self.new_name_entry: self.new_name_var,
             self.new_owner_entry: self.new_owner_var},
            self.create_state_btn)

    def _refresh_unclaimed(self):
        self.unclaimed_list.delete(0, "end")
        if not state.is_loaded:
            return
        try:
            unclaimed = map_data.unclaimed_land_provinces(state.mod_root)
            next_id = map_data.next_free_state_id(state.mod_root)
        except Exception as exc:
            self.create_status.config(text=f"Couldn't scan the map: {exc}", foreground=theme.RED)
            return
        for pid in unclaimed:
            self.unclaimed_list.insert("end", str(pid))
        if not self.new_id_var.get().strip():
            self.new_id_var.set(str(next_id))
        self.create_status.config(
            text=f"{len(unclaimed)} unclaimed land province(s) found. Suggested next free state id: {next_id}.",
            foreground=theme.MUTED)

    def _create_state(self):
        if not state.is_loaded:
            messagebox.showerror("No mod", "Open or create a mod first.")
            return
        sel = [self.unclaimed_list.get(i) for i in self.unclaimed_list.curselection()]
        if not sel:
            messagebox.showerror("No provinces", "Select at least one unclaimed province.")
            return
        sid_text = self.new_id_var.get().strip()
        name = self.new_name_var.get().strip()
        if not sid_text or not name:
            messagebox.showerror("Missing info", "A state id and name are required.")
            return
        try:
            sid = int(sid_text)
            manpower = int(self.new_manpower_var.get())
            supplies = float(self.new_supplies_var.get())
        except ValueError:
            messagebox.showerror("Bad number", "State id, manpower and local supplies must be numbers.")
            return

        resources = {tok: v.get().strip() for tok, v in self.new_res_vars.items() if v.get().strip()}

        try:
            path = nsc.create_state(
                state.mod_root, state_id=sid, name=name, owner=self.new_owner_var.get().strip().upper(),
                province_ids=sel, category=self.new_cat_var.get(), manpower=manpower,
                local_supplies=supplies, resources=resources,
            )
        except Exception as exc:
            messagebox.showerror("Failed", f"State creation failed:\n{exc}")
            return

        self._states = {}
        self._refresh_unclaimed()
        self.create_status.config(text=f"Created state {sid} in {path}.", foreground=theme.GREEN)
