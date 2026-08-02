"""Pick a starting location - for a division, air wing, fleet, a new
country's capital, or a state's victory point - by clicking the relevant
territory on the map, instead of typing a raw province id you'd otherwise
have to look up in the Map tab or a wiki.

Reuses map_data.WorldMap (the same model the Map tab is built on) but crops
the render down to just the relevant area and reports the province id under
the click, not just the state - locations in history/units files, and
capital/victory-point fields, are all province ids.

Scoping: pass `tag` to zoom to a country's own owned territory (OOB use -
also lets picking outside that territory show an "are you sure" style
warning), or `state_ids` to zoom to one or more specific states directly
(state-editor / new-country use, where there's no owner concept yet).
"""

import tkinter as tk
from tkinter import ttk, messagebox

from PIL import Image, ImageTk

from app.state import state
from app import map_data
from app import theme

_RECENT = []   # session-only [{"province", "state", "label"}, ...], newest first
_RECENT_MAX = 6

# Decoding provinces.bmp plus every state file takes 5-15s on a big mod, and
# the picker is now opened repeatedly (one division, then another, then a
# naval base...). Keyed by mod root so switching mods still reloads.
_WORLD_CACHE = {}


def invalidate_cache():
    """Called when the open mod changes - a cached world belongs to one mod."""
    _WORLD_CACHE.clear()


class MapPickerDialog(tk.Toplevel):
    """`self.result` = {"province": id, "state": id, "label": str} once a
    province is picked and confirmed, else None if cancelled."""

    def __init__(self, master, mod_root, tag=None, state_ids=None, purpose="a unit"):
        super().__init__(master)
        self.title(f"Pick a location for {purpose}")
        self.mod_root = mod_root
        self.tag = tag.strip().upper() if tag else None
        self.scope_states = set(state_ids) if state_ids else None
        self.result = None
        self.world = None
        self.bbox = None
        self._photo = None
        self._picked = None   # (province_id, state_id, label)
        self._prov_to_state = {}

        self._build()
        self.grab_set()
        self.after(50, self._load)

    def _build(self):
        outer = ttk.Frame(self, padding=12)
        outer.pack(fill="both", expand=True)

        heading = f"{self.tag} TERRITORY" if self.tag else "PICK A LOCATION"
        ttk.Label(outer, text=heading, style="PageTitle.TLabel").pack(anchor="w")
        self.hint = ttk.Label(
            outer, text="Loading the map...", style="Muted.TLabel", wraplength=600, justify="left")
        self.hint.pack(anchor="w", pady=(2, 8))

        goto = ttk.Frame(outer)
        goto.pack(fill="x", pady=(0, 6))
        ttk.Label(goto, text="Already know the province id?", style="FieldLabel.TLabel").pack(side="left")
        self.goto_var = tk.StringVar()
        ttk.Entry(goto, textvariable=self.goto_var, width=8, font=(theme.FACE_MONO, 9)).pack(side="left", padx=6)
        ttk.Button(goto, text="Go", command=self._goto_typed).pack(side="left")

        if _RECENT:
            recent_row = ttk.Frame(outer)
            recent_row.pack(fill="x", pady=(0, 6))
            ttk.Label(recent_row, text="Recent:", style="FieldLabel.TLabel").pack(side="left")
            for entry in _RECENT:
                ttk.Button(
                    recent_row, text=str(entry["province"]), width=6,
                    command=lambda e=entry: self._use_recent(e),
                ).pack(side="left", padx=(4, 0))

        frame = ttk.Frame(outer)
        frame.pack(fill="both", expand=True)
        self.canvas = tk.Canvas(frame, width=640, height=520, background=theme.CANVAS_BG, highlightthickness=0)
        vbar = ttk.Scrollbar(frame, orient="vertical", command=self.canvas.yview)
        hbar = ttk.Scrollbar(frame, orient="horizontal", command=self.canvas.xview)
        self.canvas.configure(yscrollcommand=vbar.set, xscrollcommand=hbar.set)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        vbar.grid(row=0, column=1, sticky="ns")
        hbar.grid(row=1, column=0, sticky="ew")
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)
        self.canvas.bind("<Button-1>", self._on_click)
        self.canvas.bind("<MouseWheel>", lambda e: self.canvas.yview_scroll(-1 * (e.delta // 120), "units"))
        self.canvas.bind("<ButtonPress-3>", lambda e: self.canvas.scan_mark(e.x, e.y))
        self.canvas.bind("<B3-Motion>", lambda e: self.canvas.scan_dragto(e.x, e.y, gain=1))

        self.status = ttk.Label(outer, text="", style="Status.TLabel")
        self.status.pack(anchor="w", pady=(8, 0))

        btns = ttk.Frame(outer)
        btns.pack(fill="x", pady=(8, 0))
        self.use_btn = ttk.Button(btns, text="Use this location", style="Accent.TButton",
                                  command=self._confirm, state="disabled")
        self.use_btn.pack(side="left")
        ttk.Button(btns, text="Cancel", command=self.destroy).pack(side="left", padx=6)

    # ---- loading ----

    SCALE = 3   # upscale the cropped territory so clicking a small province is actually possible

    def _load(self):
        cached = _WORLD_CACHE.get(self.mod_root)
        if cached is not None:
            self.world = cached
        else:
            try:
                self.world = map_data.WorldMap(self.mod_root, downscale=2, progress=self._progress)
            except FileNotFoundError as exc:
                messagebox.showerror("No map", str(exc), parent=self)
                self.destroy()
                return
            _WORLD_CACHE[self.mod_root] = self.world

        for sid, st in self.world.states.items():
            for pid in st["provinces"]:
                self._prov_to_state[pid] = sid

        if self.scope_states is not None:
            highlight = self.scope_states
            self.bbox = self.world.bbox_for_states(highlight, pad=30)
            self.hint.config(
                text="Click a province in the highlighted area to use its id. Zoomed to the "
                     "relevant state(s) so you don't have to hunt across the whole map.")
        else:
            highlight = self.world.states_owned_by(self.tag)
            self.bbox = self.world.bbox_for_states(highlight, pad=30)
            if self.bbox is not None:
                self.hint.config(
                    text=f"{self.tag}'s territory, highlighted. Click a province to use its id as "
                         "a location - any province in the right state works for a division; "
                         "naval bases/air wings need a coastal or owned province specifically.")

        if self.bbox is None:
            self.hint.config(
                text=(f"{self.tag} doesn't own any states yet on this map - " if self.tag else "") +
                     "showing the whole world instead. Click any province.")
            self.bbox = (0, 0, self.world.state_arr.shape[1], self.world.state_arr.shape[0])
            highlight = ()

        img = self.world.render(selected=highlight)
        x0, y0, x1, y1 = self.bbox
        cropped = img.crop((x0, y0, x1, y1))
        w, h = cropped.size
        cropped = cropped.resize((max(1, w * self.SCALE), max(1, h * self.SCALE)), Image.NEAREST)
        self._photo = ImageTk.PhotoImage(cropped)
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, image=self._photo, anchor="nw")
        self.canvas.configure(scrollregion=(0, 0, cropped.width, cropped.height))

    def _progress(self, msg):
        self.hint.config(text=msg)
        self.update_idletasks()

    # ---- interaction ----

    def _select_province(self, pid):
        sid = self._prov_to_state.get(pid, 0)
        st = self.world.states.get(sid)
        owner = st["owner"] if st else None
        label = f"province {pid}"
        if st:
            name = state.text_for(st["name"], st["name"])
            label = f"province {pid} - state {sid} \"{name}\" (owner: {owner or 'none'})"
        self._picked = (pid, sid, label)
        warn = ""
        if self.tag and owner != self.tag:
            warn = f"  -  not owned by {self.tag}, double-check before using it"
        self.status.config(text=label + warn)
        self.use_btn.configure(state="normal")

    def _on_click(self, event):
        if not self.world or not self.bbox:
            return
        cx, cy = int(self.canvas.canvasx(event.x)), int(self.canvas.canvasy(event.y))
        x0, y0, _, _ = self.bbox
        full_x = x0 + cx // self.SCALE
        full_y = y0 + cy // self.SCALE
        pid = self.world.province_at(full_x, full_y)
        if pid <= 0:
            self.status.config(text="That's open sea - pick a province on land.")
            self.use_btn.configure(state="disabled")
            self._picked = None
            return
        self._select_province(pid)

    def _goto_typed(self):
        raw = self.goto_var.get().strip()
        if not raw.isdigit():
            self.status.config(text="Type a whole-number province id first.")
            return
        pid = int(raw)
        if pid not in self._prov_to_state and not any(
            pid in st["provinces"] for st in self.world.states.values()
        ):
            self.status.config(text=f"Province {pid} isn't in any state on this map - check the id.")
            return
        self._select_province(pid)

    def _use_recent(self, entry):
        self.result = dict(entry)
        self.destroy()

    def _confirm(self):
        if not self._picked:
            return
        pid, sid, label = self._picked
        self.result = {"province": pid, "state": sid, "label": label}
        _RECENT.insert(0, self.result)
        del _RECENT[_RECENT_MAX:]
        self.destroy()
