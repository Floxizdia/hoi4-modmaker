"""Railways tab: the supply network drawn on the map, and editable.

Supply in HOI4 flows from a supply node along railways, and both are stored
as bare province ids in `map/railways.txt` and `map/supply_nodes.txt` with
no coordinates at all - which is why a mod that added states or moved a
front had no practical way to connect them. Here the ids are put back on
the map so a line can be drawn by clicking the provinces it runs through.

Edits are held in memory until Save, because a railway only makes sense as
a whole path: writing each click straight to disk would leave half-built
lines in the file every time the user changed their mind.
"""

import tkinter as tk
from tkinter import messagebox, ttk

from PIL import Image, ImageDraw, ImageTk

from app.state import state
from app import map_data, mod_export, railways
from app import theme, ui_kit

RAIL_COLOR = (222, 196, 130)
RAIL_SELECTED = (255, 120, 90)
NODE_COLOR = (120, 200, 235)
DRAFT_COLOR = (120, 235, 140)


class RailwayTab(ttk.Frame):
    def __init__(self, master):
        super().__init__(master, padding=ui_kit.PAD_PAGE)
        self.world = None
        self.centroids = {}
        self.entries = []          # [(level, [province ids])]
        self.nodes = []            # [province id]
        self.draft = []            # path being built by clicking
        self.selected = None       # index into self.entries
        self.dirty = False
        self._photo = None
        self._build()
        state.subscribe(self.on_mod_changed)

    # ---- layout ----

    def _build(self):
        self.header = ui_kit.PageHeader(
            self, "Railways & Supply",
            "The railway network and supply nodes that decide where supply can actually reach, "
            "drawn on the map instead of being bare province numbers in a text file.",
            help_key="railways")

        top = ttk.Frame(self)
        top.pack(fill="x", pady=(0, 6))
        ttk.Button(top, text="Load Map", style="Accent.TButton",
                   command=self._load).pack(side="left")
        ttk.Label(top, text="   Mode:").pack(side="left")
        self.mode = tk.StringVar(value="railway")
        for label, value in (("draw railway", "railway"), ("supply nodes", "node")):
            ttk.Radiobutton(top, text=label, value=value,
                            variable=self.mode).pack(side="left", padx=3)
        ttk.Label(top, text="   Level:").pack(side="left")
        self.level = tk.StringVar(value="1")
        ttk.Spinbox(top, textvariable=self.level, from_=1, to=railways.MAX_LEVEL,
                    width=4, command=self._level_changed).pack(side="left", padx=4)
        ttk.Button(top, text="Finish line", command=self._finish).pack(side="left", padx=(10, 2))
        ttk.Button(top, text="Undo point", command=self._undo_point).pack(side="left", padx=2)
        ttk.Button(top, text="Delete selected", command=self._delete).pack(side="left", padx=(10, 2))
        self.save_btn = ttk.Button(top, text="Save", command=self._save)
        self.save_btn.pack(side="left", padx=10)
        self.info = ttk.Label(top, text="", style="Muted.TLabel")
        self.info.pack(side="left", padx=8)

        body = ttk.Frame(self)
        body.pack(fill="both", expand=True)

        side = ttk.Frame(body)
        side.pack(side="left", fill="y", padx=(0, 8))
        ttk.Label(side, text="Railways").pack(anchor="w")
        self.listbox = tk.Listbox(side, width=34, height=26, exportselection=False)
        self.listbox.pack(fill="y", expand=True)
        self.listbox.bind("<<ListboxSelect>>", lambda e: self._select_from_list())

        frame = ttk.Frame(body)
        frame.pack(side="left", fill="both", expand=True)
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
        self.canvas.bind("<ButtonPress-3>", lambda e: self.canvas.scan_mark(e.x, e.y))
        self.canvas.bind("<B3-Motion>", lambda e: self.canvas.scan_dragto(e.x, e.y, gain=1))
        self.canvas.bind("<MouseWheel>",
                         lambda e: self.canvas.yview_scroll(-1 * (e.delta // 120), "units"))
        self.canvas.bind("<Shift-MouseWheel>",
                         lambda e: self.canvas.xview_scroll(-1 * (e.delta // 120), "units"))

        self.status = ttk.Label(
            self, text="Load the map, then click the provinces a railway runs through and press "
                       "'Finish line'. In supply-node mode a click adds or removes a node. "
                       "Right-drag pans. Nothing is written until you press Save.",
            style="Muted.TLabel", wraplength=1000, justify="left")
        self.status.pack(fill="x", pady=(6, 0))

        self.on_mod_changed()

    # ---- lifecycle ----

    def on_mod_changed(self):
        if state.is_loaded:
            self.header.set_status(True, state.mod_name)
        else:
            self.header.set_status(False, "no mod open")
        self.world = None
        self.entries = []
        self.nodes = []
        self.draft = []
        self.selected = None
        self.dirty = False
        self.canvas.delete("all")
        if hasattr(self, "listbox"):
            self.listbox.delete(0, "end")

    def on_show(self):
        self.on_mod_changed()

    @property
    def is_dirty(self):
        return self.dirty

    def _load(self):
        if not state.is_loaded:
            messagebox.showerror("No mod", "Open a mod first.")
            return
        self.info.config(text="Loading...")
        self.update_idletasks()
        try:
            self.world = map_data.WorldMap(
                state.mod_root, downscale=4,
                progress=lambda m: (self.info.config(text=m), self.update_idletasks()))
        except FileNotFoundError as exc:
            messagebox.showerror("No map", str(exc))
            self.info.config(text="")
            return

        self.centroids = self.world.province_centroids()
        self.entries = railways.parse_railways(
            railways.source_path(state.mod_root, railways.RAILWAYS))
        self.nodes = railways.parse_supply_nodes(
            railways.source_path(state.mod_root, railways.SUPPLY_NODES))
        self.draft = []
        self.selected = None
        self.dirty = False
        self._refresh_list()
        self._redraw()
        self.info.config(text=f"{len(self.entries)} railways · {len(self.nodes)} supply nodes")

    # ---- drawing ----

    def _redraw(self):
        if not self.world:
            return
        image = self.world.render()
        draw = ImageDraw.Draw(image)

        for index, (level, provinces) in enumerate(self.entries):
            colour = RAIL_SELECTED if index == self.selected else RAIL_COLOR
            self._draw_path(draw, provinces, colour, width=max(1, min(level, 4)))

        for province in self.nodes:
            point = self.centroids.get(province)
            if point:
                x, y = point
                draw.ellipse([x - 3, y - 3, x + 3, y + 3], fill=NODE_COLOR)

        if self.draft:
            self._draw_path(draw, self.draft, DRAFT_COLOR, width=2)
            for province in self.draft:
                point = self.centroids.get(province)
                if point:
                    x, y = point
                    draw.rectangle([x - 2, y - 2, x + 2, y + 2], fill=DRAFT_COLOR)

        self._photo = ImageTk.PhotoImage(image)
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, image=self._photo, anchor="nw")
        self.canvas.configure(scrollregion=(0, 0, image.width, image.height))

    def _draw_path(self, draw, provinces, colour, width=1):
        points = [self.centroids[p] for p in provinces if p in self.centroids]
        if len(points) >= 2:
            draw.line(points, fill=colour, width=width)

    def _refresh_list(self):
        self.listbox.delete(0, "end")
        for level, provinces in self.entries:
            self.listbox.insert(
                "end", f"L{level}  {provinces[0]} → {provinces[-1]}  ({len(provinces)} prov)")

    # ---- interaction ----

    def _province_at(self, event):
        x = int(self.canvas.canvasx(event.x))
        y = int(self.canvas.canvasy(event.y))
        return self.world.province_at(x, y) if self.world else 0

    def _on_click(self, event):
        if not self.world:
            return
        province = self._province_at(event)
        if province <= 0:
            return

        if self.mode.get() == "node":
            if province in self.nodes:
                self.nodes.remove(province)
                self.status.config(text=f"Supply node removed from province {province}.")
            else:
                self.nodes.append(province)
                self.status.config(text=f"Supply node added on province {province}.")
            self.dirty = True
            self._redraw()
            return

        # railway mode: clicking an existing line selects it, otherwise the
        # province joins the path being drawn
        hit = self._railway_at(province)
        if hit is not None and not self.draft:
            self.selected = hit
            self.listbox.selection_clear(0, "end")
            self.listbox.selection_set(hit)
            self.level.set(str(self.entries[hit][0]))
            self._redraw()
            self.status.config(text=f"Selected railway {hit + 1}. Change Level to retype it, "
                                    "or press Delete selected.")
            return

        if self.draft and self.draft[-1] == province:
            return
        self.draft.append(province)
        self._redraw()
        self.status.config(text="Drawing: " + " → ".join(str(p) for p in self.draft))

    def _railway_at(self, province):
        for index, (_level, provinces) in enumerate(self.entries):
            if province in provinces:
                return index
        return None

    def _undo_point(self):
        if not self.draft:
            return
        self.draft.pop()
        self._redraw()
        self.status.config(text="Drawing: " + " → ".join(str(p) for p in self.draft))

    def _finish(self):
        if len(self.draft) < 2:
            self.status.config(text="A railway needs at least two provinces — click a few more.")
            return
        try:
            level = int(self.level.get())
        except ValueError:
            self.status.config(text="Level has to be a whole number.")
            return
        self.entries.append((level, list(self.draft)))
        self.draft = []
        self.dirty = True
        self._refresh_list()
        self._redraw()
        self.status.config(text=f"Railway added ({len(self.entries)} total). Press Save to write it.")

    def _select_from_list(self):
        selection = self.listbox.curselection()
        if not selection:
            return
        self.selected = selection[0]
        self.level.set(str(self.entries[self.selected][0]))
        self._redraw()

    def _level_changed(self):
        """Retyping the level applies to whichever railway is selected; with
        nothing selected it's just the level the next drawn line will get."""
        if self.selected is None:
            return
        try:
            level = int(self.level.get())
        except ValueError:
            return
        _old, provinces = self.entries[self.selected]
        self.entries[self.selected] = (level, provinces)
        self.dirty = True
        self._refresh_list()
        self.listbox.selection_set(self.selected)
        self._redraw()

    def _delete(self):
        if self.selected is None:
            self.status.config(text="Click a railway on the map or in the list first.")
            return
        del self.entries[self.selected]
        self.selected = None
        self.dirty = True
        self._refresh_list()
        self._redraw()
        self.status.config(text="Railway deleted. Press Save to write it.")

    # ---- saving ----

    def _save(self):
        if not state.is_loaded or not self.world:
            messagebox.showerror("Nothing to save", "Load the map first.")
            return

        land = set(self.centroids)
        found = railways.problems(self.entries, self.nodes, land_provinces=land)
        if found:
            summary = "\n".join(
                (f"railway {i + 1}: {msg}" if i is not None else msg) for i, msg in found[:6])
            if not messagebox.askyesno(
                    "Save anyway?",
                    f"These look wrong:\n\n{summary}\n\nSave the files as they are?"):
                return

        try:
            written = [railways.save_railways(state.mod_root, self.entries),
                       railways.save_supply_nodes(state.mod_root, self.nodes)]
        except OSError as exc:
            messagebox.showerror("Save failed", str(exc))
            return
        mod_export.record_created(state.mod_root, written)
        self.dirty = False
        self.status.config(
            text=f"Wrote {len(self.entries)} railways and {len(self.nodes)} supply nodes into "
                 "the mod's map folder (any existing files kept as .bak).")
