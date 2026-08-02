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

        self.status = ttk.Label(self, text="", style="Status.TLabel", wraplength=560, justify="left")
        self.status.pack(fill="x", **pad)

        btns = ttk.Frame(self)
        btns.pack(fill="x", pady=(0, 10), padx=10)
        ttk.Button(btns, text="Save", style="Accent.TButton", command=self._save).pack(side="left")
        ttk.Button(btns, text="Cancel", command=self.destroy).pack(side="left", padx=6)
        ttk.Label(btns, text="Province ids: " + ", ".join(str(p) for p in self.st["provinces"][:14])
                            + ("..." if len(self.st["provinces"]) > 14 else ""),
                  style="Muted.TLabel").pack(side="left", padx=10)

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
        self.canvas.bind("<Double-Button-1>", self._on_double_click)
        self.canvas.bind("<Motion>", self._on_motion)
        self.canvas.bind("<MouseWheel>", lambda e: self.canvas.yview_scroll(-1 * (e.delta // 120), "units"))
        self.canvas.bind("<Shift-MouseWheel>", lambda e: self.canvas.xview_scroll(-1 * (e.delta // 120), "units"))
        self.canvas.bind("<ButtonPress-3>", lambda e: self.canvas.scan_mark(e.x, e.y))
        self.canvas.bind("<B3-Motion>", lambda e: self.canvas.scan_dragto(e.x, e.y, gain=1))

        self.status = ttk.Label(self, text="Load the map, click states to select them (click again to unselect), "
                                           "then give them to a tag. Double-click a state to edit its manpower, "
                                           "buildings, resources and victory points. Right-drag pans, "
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
        im = self.world.render(selected=self.selected)
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

    def _on_click(self, event):
        if not self.world:
            return
        x, y = self._canvas_xy(event)
        sid = self.world.state_at(x, y)
        if sid <= 0 or sid == self.world.no_state_id:
            return
        if sid in self.selected:
            self.selected.discard(sid)
        else:
            self.selected.add(sid)
        self._redraw()
        self.status.config(
            text=f"Selected {len(self.selected)} state(s): "
                 + ", ".join(self._state_label(s) for s in sorted(self.selected)[:8])
                 + ("..." if len(self.selected) > 8 else "")
        )

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
