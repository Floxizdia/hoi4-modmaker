"""Map tab: the mod's political map, coloured by owner, where clicking
states selects them and one button hands them to a country of your choice.
"""

import tkinter as tk
from tkinter import ttk, messagebox

from PIL import ImageTk

from app.state import state
from app import map_data
from app import mod_export
from app import theme, ui_kit


class StateEditor(tk.Toplevel):
    """Everything about one state that isn't ownership: how many people live
    there, what's built, and which provinces are worth fighting over."""

    def __init__(self, master, mod_root, sid, st, on_saved=None):
        super().__init__(master)
        self.title(f"State {sid} — {st['name']}")
        self.resizable(False, False)
        self.mod_root = mod_root
        self.sid = sid
        self.st = st
        self.on_saved = on_saved
        self.details = map_data.read_state_details(st["file"])
        self._build()
        self.grab_set()

    def _build(self):
        pad = {"padx": 10, "pady": 3}
        head = ttk.Frame(self)
        head.pack(fill="x", **pad)
        ttk.Label(head, text=f"{self.st['name']}", style="Gold.TLabel",
                  font=("Segoe UI", 13, "bold")).pack(side="left")
        ttk.Label(head, text=f"  id {self.sid} · owner {self.st['owner'] or 'none'} · "
                             f"{len(self.st['provinces'])} provinces",
                  style="Muted.TLabel").pack(side="left")

        body = ttk.Frame(self)
        body.pack(fill="both", expand=True, **pad)

        basics = ttk.LabelFrame(body, text="Basics", padding=8)
        basics.grid(row=0, column=0, sticky="nw", padx=(0, 10))
        ttk.Label(basics, text="Manpower").grid(row=0, column=0, sticky="w")
        self.manpower = tk.StringVar(value=self.details["manpower"])
        ttk.Entry(basics, textvariable=self.manpower, width=12).grid(row=0, column=1, padx=4, pady=2)
        ttk.Label(basics, text="Category").grid(row=1, column=0, sticky="w")
        self.category = tk.StringVar(value=self.details["state_category"])
        ttk.Combobox(basics, textvariable=self.category, width=14,
                     values=map_data.STATE_CATEGORIES).grid(row=1, column=1, padx=4, pady=2)
        ttk.Label(basics, text="the category caps how many\nbuilding slots the state has",
                  style="Muted.TLabel", justify="left").grid(row=2, column=0, columnspan=2, sticky="w", pady=(6, 0))

        res = ttk.LabelFrame(body, text="Resources", padding=8)
        res.grid(row=1, column=0, sticky="nw", pady=(10, 0))
        self.resources = {}
        for i, key in enumerate(map_data.RESOURCE_KEYS):
            ttk.Label(res, text=key).grid(row=i, column=0, sticky="w")
            var = tk.StringVar(value=self.details["resources"][key])
            ttk.Entry(res, textvariable=var, width=8).grid(row=i, column=1, padx=4, pady=1)
            self.resources[key] = var

        builds = ttk.LabelFrame(body, text="Buildings", padding=8)
        builds.grid(row=0, column=1, rowspan=2, sticky="nw")
        self.buildings = {}
        for i, key in enumerate(map_data.BUILDING_KEYS):
            ttk.Label(builds, text=key.replace("_", " ")).grid(row=i, column=0, sticky="w")
            var = tk.StringVar(value=self.details["buildings"][key])
            ttk.Spinbox(builds, textvariable=var, from_=0, to=99, width=6).grid(row=i, column=1, padx=4, pady=1)
            self.buildings[key] = var

        vp = ttk.LabelFrame(body, text="Victory points", padding=8)
        vp.grid(row=0, column=2, rowspan=2, sticky="nw", padx=(10, 0))
        self.vp_list = tk.Listbox(vp, height=9, width=20, exportselection=False)
        self.vp_list.pack()
        for prov, val in self.details["victory_points"]:
            self.vp_list.insert("end", f"{prov}  →  {val}")
        add = ttk.Frame(vp)
        add.pack(fill="x", pady=(6, 0))
        ttk.Label(add, text="prov").pack(side="left")
        self.vp_prov = tk.StringVar()
        ttk.Entry(add, textvariable=self.vp_prov, width=7).pack(side="left", padx=2)
        ttk.Label(add, text="pts").pack(side="left")
        self.vp_val = tk.StringVar(value="5")
        ttk.Entry(add, textvariable=self.vp_val, width=4).pack(side="left", padx=2)
        ttk.Button(add, text="+", width=3, command=self._add_vp).pack(side="left")
        ttk.Button(vp, text="Remove selected", command=self._del_vp).pack(fill="x", pady=(4, 0))
        ttk.Label(vp, text="province ids come from the\nstate's province list",
                  style="Muted.TLabel", justify="left").pack(anchor="w", pady=(4, 0))

        # per-province buildings: a state's port lives here rather than in
        # the state-wide list, so a coastal state can't be given a harbour
        # from the Buildings column on the left
        prov = ttk.LabelFrame(body, text="Province buildings", padding=8)
        prov.grid(row=0, column=3, rowspan=2, sticky="nw", padx=(10, 0))
        self.prov_buildings = {int(p): dict(v)
                               for p, v in self.details["province_buildings"].items()}
        self.prov_list = tk.Listbox(prov, height=9, width=26, exportselection=False)
        self.prov_list.pack()

        row = ttk.Frame(prov)
        row.pack(fill="x", pady=(6, 0))
        self.pb_prov = tk.StringVar(value=str(self.st["provinces"][0]) if self.st["provinces"] else "")
        ttk.Combobox(row, textvariable=self.pb_prov, width=8,
                     values=[str(p) for p in self.st["provinces"]]).pack(side="left")
        self.pb_kind = tk.StringVar(value=map_data.PROVINCE_BUILDING_KEYS[0])
        ttk.Combobox(row, textvariable=self.pb_kind, width=13,
                     values=list(map_data.PROVINCE_BUILDING_KEYS)).pack(side="left", padx=2)
        self.pb_level = tk.StringVar(value="1")
        ttk.Spinbox(row, textvariable=self.pb_level, from_=0, to=10, width=4).pack(side="left")
        ttk.Button(prov, text="Set", command=self._set_prov_building).pack(fill="x", pady=(4, 0))
        ttk.Button(prov, text="Remove selected", command=self._del_prov_building).pack(fill="x", pady=(2, 0))
        ttk.Label(prov, text="naval base = this state's port.\nOnly coastal provinces can have one.",
                  style="Muted.TLabel", justify="left").pack(anchor="w", pady=(4, 0))
        self._refresh_prov_list()

        self.status = ttk.Label(self, text="", style="Status.TLabel", wraplength=560, justify="left")
        self.status.pack(fill="x", **pad)

        btns = ttk.Frame(self)
        btns.pack(fill="x", pady=(0, 10), padx=10)
        ttk.Button(btns, text="Save", style="Accent.TButton", command=self._save).pack(side="left")
        ttk.Button(btns, text="Cancel", command=self.destroy).pack(side="left", padx=6)
        ttk.Label(btns, text="Province ids: " + ", ".join(str(p) for p in self.st["provinces"][:14])
                            + ("..." if len(self.st["provinces"]) > 14 else ""),
                  style="Muted.TLabel").pack(side="left", padx=10)

    def _refresh_prov_list(self):
        self.prov_list.delete(0, "end")
        self._prov_rows = []
        for province in sorted(self.prov_buildings):
            for kind, level in sorted(self.prov_buildings[province].items()):
                if str(level).strip() in ("", "0"):
                    continue
                self.prov_list.insert("end", f"{province}  {kind}  {level}")
                self._prov_rows.append((province, kind))

    def _set_prov_building(self):
        try:
            province = int(self.pb_prov.get())
            level = int(self.pb_level.get())
        except ValueError:
            self.status.config(text="Province id and level both have to be whole numbers.")
            return
        if province not in self.st["provinces"]:
            self.status.config(text=f"Province {province} isn't in this state — the game would ignore it.")
            return
        self.prov_buildings.setdefault(province, {})[self.pb_kind.get()] = str(level)
        self._refresh_prov_list()
        self.status.config(text="")

    def _del_prov_building(self):
        for index in reversed(self.prov_list.curselection()):
            province, kind = self._prov_rows[index]
            # 0 rather than dropping the key: the writer reads a zero as
            # "take this building out of the file", and simply forgetting it
            # here would leave the old level sitting in the state untouched
            self.prov_buildings.setdefault(province, {})[kind] = "0"
        self._refresh_prov_list()

    def _add_vp(self):
        try:
            prov = int(self.vp_prov.get())
            val = int(self.vp_val.get())
        except ValueError:
            self.status.config(text="Province id and points both have to be whole numbers.")
            return
        if prov not in self.st["provinces"]:
            self.status.config(text=f"Province {prov} isn't in this state — the game would ignore it.")
            return
        self.vp_list.insert("end", f"{prov}  →  {val}")
        self.vp_prov.set("")

    def _del_vp(self):
        for i in reversed(self.vp_list.curselection()):
            self.vp_list.delete(i)

    def _victory_points(self):
        out = []
        for i in range(self.vp_list.size()):
            prov, val = self.vp_list.get(i).split("→")
            out.append((int(prov.strip()), int(val.strip())))
        return out

    def _save(self):
        # a base-game state has to come into the mod before it can be edited
        map_data.localise_state(
            self.mod_root, [self.sid], {self.sid: self.st},
            record=lambda paths: mod_export.record_created(self.mod_root, paths),
        )
        try:
            changed = map_data.apply_state_edits(
                self.st["file"],
                manpower=self.manpower.get().strip(),
                state_category=self.category.get().strip(),
                buildings={k: v.get().strip() for k, v in self.buildings.items()},
                resources={k: v.get().strip() for k, v in self.resources.items()},
                victory_points=self._victory_points(),
                province_buildings=self.prov_buildings,
            )
        except (OSError, ValueError) as exc:
            messagebox.showerror("Save failed", str(exc))
            return
        if self.on_saved:
            self.on_saved(changed)
        self.destroy()


class MapTab(ttk.Frame):
    def __init__(self, master):
        super().__init__(master, padding=10)
        self.world = None
        self.selected = set()
        self._photo = None
        self._hover_sid = 0
        self._press_sid = 0      # state the current click started on
        self._dragged = False    # became a drag, so release must not toggle
        self._drag_adding = True
        self._build()
        state.subscribe(self.on_mod_changed)

    def _build(self):
        self.header = ui_kit.PageHeader(
            self, "Map",
            "A clickable political map of the whole game world, coloured by owner.", help_key="map")

        top = ttk.Frame(self)
        top.pack(fill="x")
        ttk.Button(top, text="Load Map", style="Accent.TButton", command=self._load).pack(side="left")
        ttk.Label(top, text="   Detail:").pack(side="left")
        self.detail_var = tk.StringVar(value="normal")
        ttk.Combobox(top, textvariable=self.detail_var, state="readonly", width=10,
                     values=["normal", "high"]).pack(side="left", padx=4)
        ttk.Label(top, text="   Give to tag:").pack(side="left", padx=(14, 0))
        self.tag_var = tk.StringVar()
        ttk.Entry(top, textvariable=self.tag_var, width=6).pack(side="left", padx=4)
        ttk.Button(top, text="Give Selected States", command=self._give).pack(side="left", padx=6)
        ttk.Button(top, text="Edit State...", command=self._edit_state).pack(side="left")
        ttk.Button(top, text="Clear Selection", command=self._clear_sel).pack(side="left", padx=6)
        self.info = ttk.Label(top, text="", style="Muted.TLabel")
        self.info.pack(side="left", padx=14)

        # cores and claims: who calls a state theirs, and who is owed it.
        # Both decide war goals and annexation in game, and both used to be
        # hand-written into the state files
        claims = ttk.Frame(self)
        claims.pack(fill="x", pady=(6, 0))
        ttk.Label(claims, text="View:").pack(side="left")
        self.layer_var = tk.StringVar(value="owner")
        layer = ttk.Combobox(claims, textvariable=self.layer_var, state="readonly", width=10,
                             values=["owner", "cores", "claims"])
        layer.pack(side="left", padx=4)
        layer.bind("<<ComboboxSelected>>", lambda e: self._redraw())
        ttk.Label(claims, text="for tag:").pack(side="left")
        self.layer_tag = tk.StringVar()
        tag_entry = ttk.Entry(claims, textvariable=self.layer_tag, width=6)
        tag_entry.pack(side="left", padx=4)
        tag_entry.bind("<KeyRelease>", lambda e: self._redraw())
        ttk.Button(claims, text="Add core", command=lambda: self._claim_edit("core", True)).pack(side="left", padx=(10, 2))
        ttk.Button(claims, text="Remove core", command=lambda: self._claim_edit("core", False)).pack(side="left", padx=2)
        ttk.Button(claims, text="Add claim", command=lambda: self._claim_edit("claim", True)).pack(side="left", padx=(10, 2))
        ttk.Button(claims, text="Remove claim", command=lambda: self._claim_edit("claim", False)).pack(side="left", padx=2)
        self.claim_info = ttk.Label(claims, text="", style="Muted.TLabel")
        self.claim_info.pack(side="left", padx=10)

        frame = ttk.Frame(self)
        frame.pack(fill="both", expand=True, pady=8)
        self.canvas = tk.Canvas(frame, background=theme.CANVAS_BG, highlightthickness=0)
        vbar = ttk.Scrollbar(frame, orient="vertical", command=self.canvas.yview)
        hbar = ttk.Scrollbar(frame, orient="horizontal", command=self.canvas.xview)
        self.canvas.configure(yscrollcommand=vbar.set, xscrollcommand=hbar.set)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        vbar.grid(row=0, column=1, sticky="ns")
        hbar.grid(row=1, column=0, sticky="ew")
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)

        self.canvas.bind("<Button-1>", self._on_click)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)
        self.canvas.bind("<Double-Button-1>", self._on_double_click)
        self.canvas.bind("<Motion>", self._on_motion)
        self.canvas.bind("<MouseWheel>", lambda e: self.canvas.yview_scroll(-1 * (e.delta // 120), "units"))
        self.canvas.bind("<Shift-MouseWheel>", lambda e: self.canvas.xview_scroll(-1 * (e.delta // 120), "units"))
        self.canvas.bind("<ButtonPress-3>", lambda e: self.canvas.scan_mark(e.x, e.y))
        self.canvas.bind("<B3-Motion>", lambda e: self.canvas.scan_dragto(e.x, e.y, gain=1))

        self.status = ttk.Label(self, text="Load the map, click states to select them (click again to unselect) "
                                           "or drag across several at once — a drag starting on an unselected "
                                           "state adds, starting on a selected one rubs out. Then give them to "
                                           "a tag. Double-click a state to edit its manpower, "
                                           "buildings, resources, ports and victory points. Right-drag pans, "
                                           "Shift+wheel scrolls sideways. Dark olive patches are real land this "
                                           "mod hasn't assigned to any state yet — not clickable, not sea.",
                                style="Muted.TLabel", wraplength=1000, justify="left")
        self.status.pack(fill="x")

        self.on_mod_changed()

    # ---- lifecycle ----

    def on_mod_changed(self):
        if state.is_loaded:
            self.header.set_status(True, state.mod_name)
        else:
            self.header.set_status(False, "no mod open")
        self.world = None
        self.selected = set()
        self.canvas.delete("all")

    def _load(self):
        if not state.is_loaded:
            messagebox.showerror("No mod", "Open a mod first.")
            return
        downscale = 2 if self.detail_var.get() == "high" else 4
        self.info.config(text="Loading...")
        self.update_idletasks()
        try:
            self.world = map_data.WorldMap(
                state.mod_root, downscale=downscale,
                progress=lambda m: (self.info.config(text=m), self.update_idletasks()),
            )
        except FileNotFoundError as exc:
            messagebox.showerror("No map", str(exc))
            self.info.config(text="")
            return
        self.selected = set()
        self._redraw()
        owned = sum(1 for s in self.world.states.values() if s["owner"])
        self.info.config(text=f"{len(self.world.states)} states · {owned} owned")

    # ---- drawing ----

    def _redraw(self):
        if not self.world:
            return
        lut = None
        layer, tag = self.layer_var.get(), self.layer_tag.get().strip().upper()
        if layer in ("cores", "claims") and len(tag) == 3:
            kind = "core" if layer == "cores" else "claim"
            lut = self.world.claim_lut(tag, kind=kind)
            field = "cores" if kind == "core" else "claims"
            hits = sum(1 for s in self.world.states.values() if tag in s.get(field, ()))
            self.claim_info.config(text=f"{tag}: {hits} state(s) with a {kind}")
        elif layer in ("cores", "claims"):
            self.claim_info.config(text="type a 3-letter tag to see its cores/claims")
        else:
            self.claim_info.config(text="")
        im = self.world.render(selected=self.selected, lut=lut)
        self._photo = ImageTk.PhotoImage(im)
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, image=self._photo, anchor="nw")
        self.canvas.configure(scrollregion=(0, 0, im.width, im.height))

    # ---- interaction ----

    def _canvas_xy(self, event):
        return int(self.canvas.canvasx(event.x)), int(self.canvas.canvasy(event.y))

    def _state_label(self, sid):
        if sid == self.world.no_state_id:
            return f"(land with no state defined)"
        st = self.world.states.get(sid)
        if not st:
            return ""
        name = state.text_for(st["name"], st["name"])
        owner = st["owner"] or "unowned"
        return f"{sid}: {name} ({owner})"

    def _selectable_at(self, event):
        """The state under the cursor, or 0 for sea and unassigned land."""
        if not self.world:
            return 0
        x, y = self._canvas_xy(event)
        sid = self.world.state_at(x, y)
        if sid <= 0 or sid == self.world.no_state_id:
            return 0
        return sid

    def _report_selection(self):
        self.status.config(
            text=f"Selected {len(self.selected)} state(s): "
                 + ", ".join(self._state_label(s) for s in sorted(self.selected)[:8])
                 + ("..." if len(self.selected) > 8 else "")
        )

    def _on_click(self, event):
        sid = self._selectable_at(event)
        if not sid:
            return
        # a press starts a possible drag; whether it counts as a plain click
        # is only known on release, so the toggle waits until then. Which way
        # the drag paints is decided here, from the state under the cursor:
        # starting on an unselected state adds, starting on a selected one
        # rubs out, which is what a paint tool does everywhere else.
        self._drag_adding = sid not in self.selected
        self._dragged = False
        self._press_sid = sid

    def _paint(self, sid):
        """Apply the drag's mode to one state. True when it changed."""
        if self._drag_adding:
            if sid in self.selected:
                return False
            self.selected.add(sid)
        else:
            if sid not in self.selected:
                return False
            self.selected.discard(sid)
        return True

    def _on_drag(self, event):
        sid = self._selectable_at(event)
        if not sid:
            return
        changed = False
        if not self._dragged:
            # the state the drag started on never gets a motion event of its
            # own, so paint it as the stroke begins - otherwise a drag skips
            # the one state the user actually pressed on
            self._dragged = True
            if self._press_sid:
                changed = self._paint(self._press_sid)
        changed = self._paint(sid) or changed
        if not changed:
            return
        self._redraw()
        self._report_selection()

    def _on_release(self, event):
        if self._dragged or not self._press_sid:
            self._press_sid = 0
            return
        sid = self._press_sid
        self._press_sid = 0
        if sid in self.selected:
            self.selected.discard(sid)
        else:
            self.selected.add(sid)
        self._redraw()
        self._report_selection()

    def _on_motion(self, event):
        if not self.world:
            return
        x, y = self._canvas_xy(event)
        sid = self.world.state_at(x, y)
        if sid != self._hover_sid:
            self._hover_sid = sid
            self.info.config(text=self._state_label(sid) if sid > 0 else "")

    def _on_double_click(self, event):
        if not self.world:
            return
        x, y = self._canvas_xy(event)
        sid = self.world.state_at(x, y)
        if sid > 0 and sid != self.world.no_state_id:
            # the single click that came first toggled it - undo that
            self.selected.discard(sid)
            self.selected.add(sid)
            self._open_editor(sid)

    def _edit_state(self):
        if not self.world or len(self.selected) != 1:
            messagebox.showerror(
                "Pick one state",
                "Select exactly one state (or just double-click it on the map) to edit it.")
            return
        self._open_editor(next(iter(self.selected)))

    def _open_editor(self, sid):
        st = self.world.states.get(sid)
        if not st:
            return
        StateEditor(self, state.mod_root, sid, st, on_saved=self._after_edit)

    def _after_edit(self, changed):
        self.status.config(
            text="State saved into the mod (original kept as .bak)." if changed
            else "Nothing changed — the state file was left alone."
        )

    def _clear_sel(self):
        self.selected = set()
        self._redraw()
        self.status.config(text="Selection cleared.")

    # ---- giving ----

    def _claim_edit(self, kind, adding):
        """Add or remove a core/claim for the tag in the View row across
        every selected state."""
        if not self.world or not self.selected:
            messagebox.showerror("Nothing selected",
                                 "Load the map and click at least one state first.")
            return
        tag = self.layer_tag.get().strip().upper()
        if len(tag) != 3:
            messagebox.showerror("Bad tag", "Type the 3-letter tag in the 'for tag' box first.")
            return

        # base-game states have to come into the mod before being edited
        map_data.localise_state(
            state.mod_root, sorted(self.selected), self.world.states,
            record=lambda paths: mod_export.record_created(state.mod_root, paths),
        )

        changed = 0
        field = "cores" if kind == "core" else "claims"
        for sid in sorted(self.selected):
            st = self.world.states.get(sid)
            if not st:
                continue
            try:
                wrote = map_data.apply_state_claims(
                    st["file"], add=[tag] if adding else [],
                    remove=[] if adding else [tag], kind=kind)
            except OSError as exc:
                self.status.config(text=f"state {sid}: {exc}")
                continue
            if wrote:
                changed += 1
            tags = set(st.get(field, ()))
            tags.add(tag) if adding else tags.discard(tag)
            st[field] = sorted(tags)

        self._redraw()
        verb = "given to" if adding else "taken from"
        self.status.config(text=f"{changed} state file(s) updated — {kind} {verb} {tag}.")

    def _give(self):
        if not self.world or not self.selected:
            messagebox.showerror("Nothing selected", "Load the map and click at least one state first.")
            return
        tag = self.tag_var.get().strip().upper()
        if len(tag) != 3:
            messagebox.showerror("Bad tag", "Type the 3-letter country tag to give the states to.")
            return

        names = ", ".join(self._state_label(s) for s in sorted(self.selected)[:10])
        if not messagebox.askyesno(
            "Change state ownership?",
            f"Give {len(self.selected)} state(s) to {tag}?\n\n{names}\n\n"
            "The state history files are edited in place — each gets a one-time .bak backup, "
            "and files from the base game are copied into the mod instead of being touched.",
        ):
            return

        changed, errors = map_data.give_states(
            state.mod_root, sorted(self.selected), tag, self.world.states,
            record=lambda paths: mod_export.record_created(state.mod_root, paths),
        )
        self.world.refresh_owner_colors()
        self.selected = set()
        self._redraw()

        message = f"{len(changed)} state(s) now owned by {tag}."
        if errors:
            message += "  Problems: " + "; ".join(errors[:3])
        self.status.config(text=message)
