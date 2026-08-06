"""Technology tab: browse and edit the techs in common/technologies.

Tech definitions are deeply engine-flavoured (GUI folder positions, path
chains, per-equipment enables), so instead of pretending a form can cover
them, this tab gives a searchable list and edits the raw block of one tech
at a time - with the surrounding file untouched byte-for-byte, which is
what makes editing someone else's 5000-line tech file safe.
"""

import os
import glob
import re
import shutil
import tkinter as tk
from tkinter import ttk, messagebox

from app.state import state
from app import pds_scan as scan
from app import theme, ui_kit
from app.tech_graph import (find_tech_files, parse_techs, build_graph, folders,
                            resolve_icon, NO_FOLDER)
from app import tech_graph
from app import image_cache
from app import dlc
from app import dlc_prefs
from app import mod_loader
from app import layout as layout_mod
from app import mod_export
from app import undo

NEW_TECH_TEMPLATE = """my_new_tech = {
	research_cost = 1.5
	start_year = 1936
	folder = {
		name = infantry_folder
		position = { x = 0 y = 0 }
	}
	categories = {
		infantry_weapons
	}
}"""


class _RawEditor(ttk.Frame):
    def __init__(self, master):
        super().__init__(master, padding=12)
        self._files = []
        self._text = ""
        self._techs = []
        self._current = None      # (tech_id, start, end)
        self._backed_up = set()
        self._build()
        state.subscribe(self.on_mod_changed)

    def _build(self):
        self.banner = ttk.Label(self, text="", font=("Segoe UI", 10, "bold"))
        self.banner.pack(fill="x", pady=(0, 6))

        top = ttk.Frame(self)
        top.pack(fill="x")
        ttk.Label(top, text="File:").pack(side="left")
        self.file_combo = ttk.Combobox(top, state="readonly", width=44)
        self.file_combo.pack(side="left", padx=6)
        ttk.Button(top, text="Load", command=self._load_file).pack(side="left")
        ttk.Label(top, text="   Search:").pack(side="left")
        self.search_var = tk.StringVar()
        entry = ttk.Entry(top, textvariable=self.search_var, width=24)
        self.search_entry = entry
        entry.pack(side="left", padx=4)
        entry.bind("<KeyRelease>", lambda e: self._refresh_list())
        self.count_label = ttk.Label(top, text="", style="Muted.TLabel")
        self.count_label.pack(side="left", padx=8)

        body = ttk.Frame(self)
        body.pack(fill="both", expand=True, pady=8)

        left = ttk.Frame(body, width=300)
        left.pack(side="left", fill="y", padx=(0, 8))
        left.pack_propagate(False)
        self.listbox = tk.Listbox(left, exportselection=False)
        bar = ttk.Scrollbar(left, orient="vertical", command=self.listbox.yview)
        self.listbox.configure(yscrollcommand=bar.set)
        self.listbox.pack(side="left", fill="both", expand=True)
        bar.pack(side="right", fill="y")
        self.listbox.bind("<<ListboxSelect>>", lambda e: self._pick())

        right = ttk.Frame(body)
        right.pack(side="left", fill="both", expand=True)
        self.editor = tk.Text(right, wrap="none", undo=True, font=("Consolas", 10))
        ebar = ttk.Scrollbar(right, orient="vertical", command=self.editor.yview)
        self.editor.configure(yscrollcommand=ebar.set)
        self.editor.pack(side="left", fill="both", expand=True)
        ebar.pack(side="right", fill="y")

        btns = ttk.Frame(self)
        btns.pack(fill="x")
        ttk.Button(btns, text="Save This Tech", style="Accent.TButton", command=self._save_tech).pack(side="left")
        ttk.Button(btns, text="Add New Tech", command=self._add_tech).pack(side="left", padx=6)
        self.status = ttk.Label(btns, text="", style="Status.TLabel", wraplength=700, justify="left")
        self.status.pack(side="left", padx=10)

        self.on_mod_changed()

    # ---- loading ----

    def on_mod_changed(self):
        if state.is_loaded:
            self.banner.config(text=f"Technologies of: {state.mod_name}", foreground=theme.GREEN)
            self._files = find_tech_files(state.mod_root)
        else:
            self.banner.config(text="No mod open", foreground=theme.MUTED)
            self._files = []
        self.file_combo["values"] = [os.path.basename(p) for p in self._files]
        if self._files:
            self.file_combo.current(0)
        self._techs = []
        self._current = None
        self.listbox.delete(0, "end")
        self.editor.delete("1.0", "end")

    def _load_file(self):
        idx = self.file_combo.current()
        if idx < 0 or not self._files:
            messagebox.showerror("Nothing to load", "This mod has no technology files.")
            return
        self._path = self._files[idx]
        self._text, self._techs = parse_techs(self._path)
        self._current = None
        self.editor.delete("1.0", "end")
        self._refresh_list()
        self.status.config(text=f"{len(self._techs)} techs in {os.path.basename(self._path)}")

    def _refresh_list(self):
        needle = self.search_var.get().strip().lower()
        self.listbox.delete(0, "end")
        self._visible = [t for t in self._techs if not needle or needle in t[0].lower()]
        for name, _, _ in self._visible:
            self.listbox.insert("end", " " + name)
        self.count_label.config(text=f"{len(self._visible)} of {len(self._techs)}")

    def _pick(self):
        sel = self.listbox.curselection()
        if not sel:
            return
        self._current = self._visible[sel[0]]
        _, start, end = self._current
        self.editor.delete("1.0", "end")
        self.editor.insert("1.0", self._text[start:end])
        self.editor.edit_reset()

    # ---- saving ----

    def _backup_once(self):
        if self._path in self._backed_up:
            return
        backup = self._path + ".bak"
        if not os.path.exists(backup):
            try:
                shutil.copy2(self._path, backup)
            except OSError:
                pass
        self._backed_up.add(self._path)

    def _write_text(self, new_text):
        self._backup_once()
        undo.record(self._path, os.path.basename(self._path))
        with open(self._path, "w", encoding="utf-8") as f:
            f.write(new_text)
        self._text, self._techs = parse_techs(self._path)
        self._refresh_list()

    def _save_tech(self):
        if not self._current:
            messagebox.showerror("Nothing selected", "Pick a tech from the list first.")
            return
        block = self.editor.get("1.0", "end-1c").strip()
        if not block:
            messagebox.showerror("Empty", "The tech block is empty — delete techs by hand in the Code tab instead.")
            return
        opens = block.count("{")
        closes = block.count("}")
        if opens != closes:
            messagebox.showerror("Unbalanced braces", f"{opens} '{{' vs {closes} '}}' — fix before saving.")
            return
        name, start, end = self._current
        new_text = self._text[:start] + block + self._text[end:]
        self._write_text(new_text)
        self._current = None
        self.status.config(text=f"Saved '{name}' back into {os.path.basename(self._path)} (backup kept as .bak).")

    def _add_tech(self):
        if not getattr(self, "_path", None):
            messagebox.showerror("No file", "Load a technology file first.")
            return
        m = re.search(r"\btechnologies\s*=\s*\{", self._text)
        if not m:
            messagebox.showerror("Bad file", "No technologies block found in this file.")
            return
        outer_close = scan.find_matching_brace(self._text, m.end() - 1)
        if outer_close == -1:
            messagebox.showerror("Bad file", "The technologies block never closes.")
            return
        insertion = "\n\t" + NEW_TECH_TEMPLATE.replace("\n", "\n\t") + "\n"
        new_text = self._text[:outer_close] + insertion + self._text[outer_close:]
        self._write_text(new_text)
        self.search_var.set("my_new_tech")
        self._refresh_list()
        if self._visible:
            self.listbox.selection_set(0)
            self._pick()
        self.status.config(text="Template tech added — rename 'my_new_tech' and fill it in, then Save This Tech.")


# ---- visual tree ----

COL_W, ROW_H = 78, 78
ICON_SIZE = 50

#: same two words the Focus Tree's Layout picker uses, so the choice means
#: the same thing on both screens: draw the authored coordinates, or ignore
#: them and derive a layout from the prerequisite graph
AUTO_LAYOUT = "auto"
MOD_COORDS = "mod coordinates"


class _ScanCache:
    """Shared between the Tech Tree and Doctrines views.

    Both draw from the same three scans - the tech graph, the base/mod
    sprite indexes, and one index per DLC - which together take about a
    second on a large mod and depend only on which mod is open, not on
    which view is asking. Without this the second tab repeated all of it,
    so opening Doctrines cost a second of frozen UI for data already in
    memory. Rescan drops the cache; switching tabs reuses it."""

    def __init__(self):
        self.key = None
        self.data = None

    def get(self, mod_root, build):
        if self.key != mod_root or self.data is None:
            self.data = build()
            self.key = mod_root
        return self.data

    def invalidate(self):
        self.key = None
        self.data = None


_scan_cache = _ScanCache()


_LOC_REF_RE = re.compile(r"^\$([A-Za-z0-9_.\-]+)\$$")


def _display_name(key, fallback=None):
    """The name the game shows. A tech's (and folder's) loc key is just its
    id, and state.text_for already layers session edits over the mod over
    vanilla.

    Vanilla routinely defines one entry as a pointer to another rather than
    repeating the text - `bba_air_techs_folder:0 "$air_techs_folder$"`, and
    27 of the base game's tech names do the same - so a bare lookup would
    put a literal "$air_techs_folder$" on screen where the game shows
    "Air"."""
    original, seen = key, set()
    text = state.text_for(key, "")
    while text and key not in seen:
        seen.add(key)
        match = _LOC_REF_RE.match(text.strip())
        if not match:
            break
        key = match.group(1)
        text = state.text_for(key, "")
    return text or fallback or original


class TechTreeView(ttk.Frame):
    """The same folder-tab / grid-of-plaques arrangement the game's own
    research screen uses, built from `folder.position`.

    Defaults to those authored coordinates rather than the focus tree's
    "auto", because the game ships its research folders pre-laid-out and
    the point of this screen is to match what the player sees. The Layout
    picker still offers the derived layout for folders a mod extended
    without positioning anything."""

    def __init__(self, master, doctrines=False):
        super().__init__(master, padding=6)
        self.doctrines = doctrines
        self.graph = {}
        self.folder_names = []
        self._folder_by_label = {}
        self.current_folder = None
        self.selected = None
        self.icon_refs = []
        self.zoom = 1.0
        self._all_folders = []
        self._dlc_catalogue = []
        self._dlc_rules = {}
        self._dlc_vars = {}
        self._dlc_gfx = {}
        self._gfx_base = {}
        self._gfx_mod = {}
        self._gfx = {}
        self._build()

    def _build(self):
        top = ttk.Frame(self)
        top.pack(fill="x")
        ttk.Button(top, text="Rescan", style="Accent.TButton",
                   command=lambda: self.reload(force=True)).pack(side="left")
        ttk.Label(top, text="  Folder:").pack(side="left")
        self.folder_var = tk.StringVar()
        self.folder_combo = ttk.Combobox(top, textvariable=self.folder_var, state="readonly", width=26)
        self.folder_combo.pack(side="left", padx=4)
        self.folder_combo.bind("<<ComboboxSelected>>", lambda e: self._pick_folder())
        ttk.Label(top, text="  Layout:").pack(side="left")
        self.layout_mode = tk.StringVar(value=MOD_COORDS)
        ttk.Combobox(top, textvariable=self.layout_mode, state="readonly", width=15,
                     values=[AUTO_LAYOUT, MOD_COORDS]).pack(side="left", padx=4)
        self.layout_mode.trace_add("write", lambda *_a: self._show_folder(self.current_folder))
        self.dlc_button = ttk.Menubutton(top, text="DLC", width=12)
        self.dlc_menu = tk.Menu(self.dlc_button, tearoff=False)
        self.dlc_button["menu"] = self.dlc_menu
        self.dlc_button.pack(side="left", padx=(10, 0))
        ttk.Button(top, text="−", width=3, command=lambda: self._set_zoom(self.zoom / 1.2)).pack(side="left", padx=(14, 0))
        ttk.Button(top, text="100%", width=5, command=lambda: self._set_zoom(1.0)).pack(side="left", padx=2)
        ttk.Button(top, text="+", width=3, command=lambda: self._set_zoom(self.zoom * 1.2)).pack(side="left")
        self.count_label = ttk.Label(top, text="", style="Muted.TLabel")
        self.count_label.pack(side="left", padx=14)
        ttk.Label(top, text="Country:").pack(side="left")
        self.country_var = tk.StringVar()
        self.country_combo = ttk.Combobox(top, textvariable=self.country_var, state="readonly", width=7)
        self.country_combo.pack(side="left", padx=4)
        self.country_combo.bind("<<ComboboxSelected>>", lambda _event: self._load_country_status())
        self.researched = set()

        body = ttk.Frame(self)
        body.pack(fill="both", expand=True, pady=(8, 0))

        canvas_frame = ttk.Frame(body)
        canvas_frame.pack(side="left", fill="both", expand=True)
        self.canvas = tk.Canvas(canvas_frame, background=theme.CANVAS_BG, highlightthickness=0)
        vbar = ttk.Scrollbar(canvas_frame, orient="vertical", command=self.canvas.yview)
        hbar = ttk.Scrollbar(canvas_frame, orient="horizontal", command=self.canvas.xview)
        self.canvas.configure(yscrollcommand=vbar.set, xscrollcommand=hbar.set)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        vbar.grid(row=0, column=1, sticky="ns")
        hbar.grid(row=1, column=0, sticky="ew")
        canvas_frame.rowconfigure(0, weight=1)
        canvas_frame.columnconfigure(0, weight=1)
        self.canvas.bind("<Button-1>", self._on_click)
        self.canvas.bind("<MouseWheel>", lambda e: self.canvas.yview_scroll(-1 * (e.delta // 120), "units"))
        self.canvas.bind("<Shift-MouseWheel>", lambda e: self.canvas.xview_scroll(-1 * (e.delta // 120), "units"))

        side = ttk.Frame(body, width=300, padding=(10, 0, 0, 0))
        side.pack(side="left", fill="y")
        side.pack_propagate(False)
        ttk.Label(side, text="DOCTRINE DETAILS" if self.doctrines else "TECH DETAILS",
                  style="Gold.TLabel").pack(anchor="w")
        self.detail = ttk.Label(side, text="Click a technology.", style="Muted.TLabel",
                                wraplength=280, justify="left")
        self.detail.pack(anchor="w", pady=(6, 10), fill="x")
        ttk.Button(side, text="Edit Raw Block...", command=self._edit_selected).pack(anchor="w")
        if self.doctrines:
            ttk.Button(side, text="How doctrines work...",
                       command=self._show_doctrine_help).pack(anchor="w", pady=(6, 0))

    def _show_doctrine_help(self):
        DoctrineHelpDialog(self)

    # ---- loading ----

    def on_mod_changed(self):
        self.graph = {}
        self.folder_names = []
        self._all_folders = []
        self._folder_by_label = {}
        self._gfx = {}
        self.current_folder = None
        self.selected = None
        self.canvas.delete("all")
        self.folder_combo["values"] = []
        self.count_label.config(text="")
        self.detail.config(text="Click a technology.")
        self.researched = set()
        self.country_combo["values"] = []

    def reload(self, force=False):
        if not state.is_loaded:
            messagebox.showerror("No mod", "Open a mod first.")
            return
        if force:
            _scan_cache.invalidate()
        scan_data = _scan_cache.get(state.mod_root, self._scan)
        self.graph = scan_data["graph"]
        tags = scan_data["tags"]
        self.country_combo["values"] = tags
        if self.country_var.get() not in tags:
            self.country_var.set("GER" if "GER" in tags else (tags[0] if tags else ""))
        self.researched = tech_graph.starting_techs(state.mod_root, self.country_var.get())
        self._load_dlc(scan_data)
        self._all_folders = [f for f in tech_graph.folders(self.graph)
                             if tech_graph.is_doctrine_folder(self.graph, f) == self.doctrines]
        self._apply_dlc()

    @staticmethod
    def _scan():
        """Everything a reload needs off disk, in one place so the cache can
        hold it. Each DLC's sprites are indexed separately, so toggling one
        later is a dict merge rather than a rescan of every .gfx in the
        game."""
        from app.map_data import BASE_GAME

        entries = dlc.available(BASE_GAME)
        return {
            "graph": tech_graph.build_graph(state.mod_root),
            "tags": tech_graph.country_tags(state.mod_root),
            "dlc_entries": entries,
            "dlc_rules": dlc.folder_rules([BASE_GAME, state.mod_root]),
            "gfx_base": mod_loader.build_gfx_index([BASE_GAME]),
            "gfx_mod": mod_loader.build_gfx_index([state.mod_root]),
            "dlc_gfx": {entry["name"]: mod_loader.build_gfx_index([entry["path"]])
                        for entry in entries if entry["path"]},
        }

    # ---- DLC ----

    def _load_dlc(self, scan_data):
        self._dlc_rules = scan_data["dlc_rules"]
        self._gfx_base = scan_data["gfx_base"]
        self._gfx_mod = scan_data["gfx_mod"]
        self._dlc_gfx = scan_data["dlc_gfx"]
        self._dlc_catalogue = [e for e in scan_data["dlc_entries"] if self._affects_tech(e)]

        turned_off = set(dlc_prefs.load_disabled())
        self._dlc_vars = {}
        self.dlc_menu.delete(0, "end")
        previous_category = None
        for entry in self._dlc_catalogue:
            if previous_category is not None and entry["category"] != previous_category:
                self.dlc_menu.add_separator()
            previous_category = entry["category"]
            var = tk.BooleanVar(value=entry["default_on"] and entry["name"] not in turned_off)
            self._dlc_vars[entry["name"]] = var
            note = "in the base game" if entry["bundled"] else (entry["category"] or "dlc")
            self.dlc_menu.add_checkbutton(label=f"{entry['name']}  ({note})",
                                          variable=var, command=self._apply_dlc)
        if not self._dlc_catalogue:
            self.dlc_menu.add_command(label="No DLC found in the game folder", state="disabled")

    def _affects_tech(self, entry):
        """Whether toggling this DLC would change anything on this screen.

        Decided from the data rather than from the DLC's category: it counts
        if it gates a technology folder, or if it ships a sprite some tech
        actually draws. Music and wallpaper packs do neither and would
        otherwise pad the menu with two dozen entries that do nothing here.
        Bundled DLC has no folder of its own, so it stays if it gates."""
        if entry["name"] in dlc.gating_dlc(self._dlc_rules):
            return True
        for sprite in self._dlc_gfx.get(entry["name"], ()):
            if not sprite.startswith("GFX_"):
                continue
            core = sprite[4:]
            core = core[:-7] if core.endswith("_medium") else core
            if core in self.graph or core[4:] in self.graph:
                return True
        return False

    def _active_dlc(self):
        return {name for name, var in self._dlc_vars.items() if var.get()}

    def refresh_dlc_from_prefs(self):
        """Pick up a DLC choice made on the sibling view. Both views write
        the same preference file, so re-reading it is enough to keep the
        Tech Tree and Doctrines tabs from disagreeing about what is on."""
        if not self._dlc_vars:
            return
        disabled = set(dlc_prefs.load_disabled())
        changed = False
        for name, var in self._dlc_vars.items():
            wanted = name not in disabled
            if var.get() != wanted:
                var.set(wanted)
                changed = True
        if changed:
            self._apply_dlc()

    def _apply_dlc(self):
        """Rebuild everything a DLC toggle changes: which folders the game
        would show, and which art it would draw them with."""
        active = self._active_dlc()
        dlc_prefs.save_disabled([name for name in self._dlc_vars if name not in active])

        self._gfx = dict(self._gfx_base)
        for entry in self._dlc_catalogue:          # catalogue order, mod last
            if entry["name"] in active and entry["name"] in self._dlc_gfx:
                self._gfx.update(self._dlc_gfx[entry["name"]])
        self._gfx.update(self._gfx_mod)

        self.folder_names = [f for f in self._all_folders
                             if dlc.folder_available(self._dlc_rules, f, active)]
        self._folder_by_label = self._folder_labels(self.folder_names)
        self.folder_combo["values"] = list(self._folder_by_label)

        if self.current_folder not in self.folder_names:
            self.current_folder = self.folder_names[0] if self.folder_names else None
        label = next((lbl for lbl, raw in self._folder_by_label.items()
                      if raw == self.current_folder), "")
        self.folder_var.set(label)
        self._show_folder(self.current_folder)

        hidden = len(self._all_folders) - len(self.folder_names)
        self.dlc_button.config(text=f"DLC: {len(active)}/{len(self._dlc_catalogue)}")
        self.count_label.config(
            text=f"{len(self.graph)} techs | {self.country_var.get() or '-'}: "
                 f"{len(self.researched)} researched"
            + (f" | {hidden} folder(s) hidden by DLC" if hidden else ""))

    @staticmethod
    def _folder_labels(folder_names):
        """{label shown in the picker: raw folder name}, using the game's own
        folder names ("Armor", not "armour_folder"). Vanilla localises both
        armour_folder and nsb_armour_folder to "Armor", so a label that would
        be ambiguous keeps the raw id alongside it."""
        display = {name: _display_name(name) for name in folder_names}
        # techs with no folder block aren't on the game's research screen at
        # all - hidden hull/variant unlocks granted at gamestart - so say that
        # rather than showing a bare "(no folder)"
        if NO_FOLDER in display:
            display[NO_FOLDER] = "Not on the research screen"
        clashes = {t for t in display.values() if list(display.values()).count(t) > 1}
        labels = {}
        for name in folder_names:
            text = display[name]
            labels[f"{text}  ({name})" if text in clashes else text] = name
        return labels

    def _pick_folder(self):
        self._show_folder(self._folder_by_label.get(self.folder_var.get()))

    def _load_country_status(self):
        self.researched = tech_graph.starting_techs(state.mod_root, self.country_var.get())
        self.count_label.config(text=f"{len(self.graph)} techs | {self.country_var.get() or '-'}: {len(self.researched)} researched")
        self._show_folder(self.current_folder)

    def _set_zoom(self, z):
        self.zoom = max(0.4, min(2.0, z))
        self._show_folder(self.current_folder)

    # ---- drawing ----

    def _grid_positions(self, items):
        """{tech_id: (col, row)} in the folder's own grid units.

        "mod coordinates" draws `folder.position` as authored, which is the
        layout the game itself renders; "auto" ignores it and derives one
        from the prerequisite graph (the same depth + barycenter pass the
        focus tree uses), which is what makes a folder readable when a mod
        adds techs without positioning them.

        Even in "mod coordinates" a folder whose techs mostly carry no
        position block at all falls through to the derived layout - drawing
        those would stack the lot on one cell. The test is whether a
        position is declared, not whether the coordinates look varied
        enough: vanilla's four mutually-exclusive doctrine branches
        genuinely share cells (the game shows one branch at a time in that
        slot), and an earlier distinct-coordinate heuristic read that as
        corrupt data and threw the real layout away."""
        coords = {tid: (info["x"], info["y"]) for tid, info in items.items()}
        positioned = sum(1 for info in items.values() if info.get("positioned"))
        if self.layout_mode.get() == MOD_COORDS and positioned >= max(2, len(items) * 0.6):
            grid = coords
        else:
            synthetic = [{"id": tid, "x": info["x"],
                         "prerequisite": [r for r in info["requires"] if r in items],
                         "prerequisite_groups": [[r] for r in info["requires"] if r in items]}
                        for tid, info in items.items()]
            grid = layout_mod.auto_layout(synthetic)

        # Authored positions aren't always collision-free: vanilla's doctrine
        # branches are mutually exclusive and share cells, which the game
        # hides by showing one branch at a time but a flat grid can't. Only
        # the extra claimants on a contested cell get nudged aside - every
        # cell claimed once is reserved up front, so a tech that had the grid
        # to itself in the game data still draws exactly where the game puts
        # it instead of being displaced by a neighbour's overflow.
        first_claim = {}
        overflow = []
        for tid in sorted(grid, key=lambda t: (grid[t][1], grid[t][0], t)):
            cell = grid[tid]
            if cell in first_claim:
                overflow.append(tid)
            else:
                first_claim[cell] = tid

        resolved = {tid: cell for cell, tid in first_claim.items()}
        occupied = set(first_claim)
        for tid in overflow:
            cell = layout_mod.next_free_cell(occupied, grid[tid])
            occupied.add(cell)
            resolved[tid] = cell
        return resolved

    def _show_folder(self, folder):
        self.current_folder = folder
        self.selected = None
        self.icon_refs = []
        self.canvas.delete("all")
        if not folder:
            return

        items = {tid: info for tid, info in self.graph.items()
                 if (info["folder"] or NO_FOLDER) == folder}
        if not items:
            return

        cw, ch = COL_W * self.zoom, ROW_H * self.zoom
        grid = self._grid_positions(items)
        min_x = min(c for c, _ in grid.values())
        min_y = min(r for _, r in grid.values())
        positions = {tid: (40 + (c - min_x) * cw, 40 + (r - min_y) * ch) for tid, (c, r) in grid.items()}

        # connectors first, drawn with the game's own right-angle routing
        # (out of the parent's right edge, over, then into the child's left
        # edge) rather than a raw diagonal - matches the real tech screen
        # and reads far more clearly once a folder has any real width to it
        half = (ICON_SIZE * self.zoom) / 2
        for tid, info in items.items():
            x1, y1 = positions[tid]
            for req in info["requires"]:
                if req not in positions:
                    continue
                x0, y0 = positions[req]
                if abs(y1 - y0) < 1:
                    self.canvas.create_line(x0 + half, y0, x1 - half, y1, fill=theme.EDGE, width=2)
                else:
                    mid_x = x0 + (x1 - x0) / 2
                    self.canvas.create_line(x0 + half, y0, mid_x, y0, mid_x, y1, x1 - half, y1,
                                            fill=theme.EDGE, width=2, joinstyle="round")

        for tid, info in items.items():
            self._draw_node(tid, info, *positions[tid])

        max_x = max(p[0] for p in positions.values()) + cw
        max_y = max(p[1] for p in positions.values()) + ch
        self.canvas.configure(scrollregion=(0, 0, max_x, max_y))

    def _draw_node(self, tech_id, info, x, y):
        size = int(ICON_SIZE * self.zoom)
        selected = tech_id == self.selected
        icon_path = tech_graph.resolve_icon(state.mod_root, tech_id, self._gfx,
                                            self.country_var.get())
        thumb = image_cache.get_scaled(icon_path, (size, size)) if icon_path else None
        tag = f"tech::{tech_id}"

        # a tight square plaque - close to the game's own small icon tiles,
        # not the wider bevelled panel used for focus nodes
        half = size / 2
        researched = tech_id in self.researched
        self.canvas.create_rectangle(x - half - 3, y - half - 3, x + half + 3, y + half + 3,
                                     fill=theme.SURFACE, outline=theme.GOLD if selected else (theme.GREEN if researched else theme.EDGE),
                                     width=2 if selected else 1, tags=(tag,))
        if researched:
            self.canvas.create_text(x + half - 4, y - half + 4, text="✓", fill=theme.GREEN,
                                    font=(theme.FACE_UI, max(7, int(9 * self.zoom)), "bold"), tags=(tag,))
        if thumb:
            self.icon_refs.append(thumb)
            self.canvas.create_image(x, y, image=thumb, tags=(tag,))
        else:
            self.canvas.create_text(x, y, text=_display_name(tech_id)[:22], fill=theme.MUTED,
                                    font=(theme.FACE_UI, max(6, int(7 * self.zoom))),
                                    width=size, justify="center", tags=(tag,))

        # the game labels every tech under its plaque; without it a folder of
        # unfamiliar icons is unreadable to anyone who hasn't memorised them
        if self.zoom >= 0.75:
            self.canvas.create_text(
                x, y + half + 9, text=_display_name(tech_id), fill=theme.TEXT,
                font=(theme.FACE_UI, max(6, int(7 * self.zoom))),
                width=int(COL_W * self.zoom) - 4, justify="center", tags=(tag,))

    # ---- interaction ----

    def _on_click(self, event):
        x, y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
        for item in self.canvas.find_overlapping(x - 1, y - 1, x + 1, y + 1):
            for t in self.canvas.gettags(item):
                if t.startswith("tech::"):
                    self._select(t[6:])
                    return

    def _select(self, tech_id):
        self.selected = tech_id
        info = self.graph.get(tech_id, {})
        name = _display_name(tech_id)
        lines = [
            name + ("  (vanilla)" if info.get("is_vanilla") else "  (this mod)"),
            "" if name == tech_id else f"id: {tech_id}",
            f"Starting status for {self.country_var.get() or '-'}: "
            + ("RESEARCHED" if tech_id in self.researched else "NOT RESEARCHED"),
            f"cost {info.get('research_cost', '?')}   year {info.get('start_year', '?')}",
            # doctrines are paid for in XP, so the research cost alone is
            # misleading on that tab
            (f"unlock: {info['xp_cost']} {info.get('xp_type') or ''} XP"
             if info.get("xp_cost") else ""),
            "",
            "Requires: " + (", ".join(info.get("requires", [])) or "(nothing)"),
            "",
            "Leads to: " + (", ".join(info.get("leads_to", [])) or "(nothing)"),
        ]
        self.detail.config(text="\n".join(lines))
        self._show_folder(self.current_folder)   # redraw to show the highlight

    def _edit_selected(self):
        if not self.selected or self.selected not in self.graph:
            messagebox.showerror("Nothing selected", "Click a technology on the tree first.")
            return
        info = self.graph[self.selected]
        path, start, end = info["file"], info["start"], info["end"]

        if info.get("is_vanilla"):
            # never write into the real game install - bring this file into
            # the mod first, exactly like map_data.py does for base-game states
            dest_dir = os.path.join(state.mod_root, "common", "technologies")
            os.makedirs(dest_dir, exist_ok=True)
            dest = os.path.join(dest_dir, os.path.basename(path))
            if not os.path.isfile(dest):
                shutil.copy2(path, dest)
                mod_export.record_created(state.mod_root, [dest])
            path = dest

        with open(path, "r", encoding="utf-8-sig", errors="ignore") as f:
            text = f.read()

        dialog = tk.Toplevel(self)
        dialog.title(f"Edit {self.selected}")
        editor = tk.Text(dialog, wrap="none", width=70, height=26, font=("Consolas", 10))
        editor.pack(fill="both", expand=True, padx=8, pady=8)
        editor.insert("1.0", text[start:end])

        def save():
            block = editor.get("1.0", "end-1c").strip()
            if block.count("{") != block.count("}"):
                messagebox.showerror("Unbalanced braces", "Fix the braces before saving.")
                return
            new_text = text[:start] + block + text[end:]
            backup = path + ".bak"
            if not os.path.exists(backup):
                shutil.copy2(path, backup)
            undo.record(path, self.selected)
            with open(path, "w", encoding="utf-8") as f:
                f.write(new_text)
            dialog.destroy()
            self.reload(force=True)   # the file on disk just changed

        btns = ttk.Frame(dialog)
        btns.pack(fill="x", padx=8, pady=(0, 8))
        ttk.Button(btns, text="Save", style="Accent.TButton", command=save).pack(side="left")
        ttk.Button(btns, text="Cancel", command=dialog.destroy).pack(side="left", padx=6)
        dialog.grab_set()


DOCTRINE_GUIDE = """WHAT A DOCTRINE IS

A doctrine is an ordinary technology carrying `doctrine = yes`. What makes
it behave differently in game is that it is bought with experience, not
research time:

    xp_research_type = army        # army | navy | air
    xp_unlock_cost   = 100         # how much XP unlocking it costs

The four land branches, three naval and three air branches are mutually
exclusive. That is what `xor` on the branch root does - picking one locks
the others out for the rest of the game:

    mobile_warfare = {
        doctrine_name = "MOBILE_WARFARE_DOCTRINE"   # loc key for the branch
        xor = { superior_firepower trench_warfare mass_assault }
        ...
    }

Only branch roots carry `doctrine_name` and `xor`; the techs further down a
branch are chained with `path = { leads_to_tech = ... }` like any other
technology.

WHY THEY OVERLAP ON THIS SCREEN

Branch roots share the same `folder.position` in vanilla - the game shows
one branch at a time in that slot, so the data has them stacked. This
editor draws every alternative at once and nudges the extras sideways, so a
row here is "the four choices at that depth", not four separate slots.

ADDING A DOCTRINE OF YOUR OWN

1. Put it in a file of its own under common/technologies/ so a game patch
   editing vanilla's doctrine files can't collide with your work.
2. Give the branch root `doctrine = yes`, a `doctrine_name`, an
   `xp_research_type`, an `xp_unlock_cost`, and a `folder` block naming an
   existing doctrine folder (or one you add in
   common/technology_tags/) with a position.
3. If it replaces one of vanilla's branches, add your id to the `xor` of
   every branch it competes with AND add theirs to yours - xor is not
   applied symmetrically for you.
4. Chain the rest of the branch with `path = { leads_to_tech = ... }`.
5. Add localisation for the tech id and for the `doctrine_name` key, then
   run Validate - a doctrine with no loc shows as a blank plaque in game.

A new doctrine folder also needs a `ledger` (army/navy/air) in
common/technology_tags/, otherwise it never appears on the research screen.
"""


class DoctrineHelpDialog(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("How doctrines work")
        self.geometry("720x560")
        outer = ttk.Frame(self, padding=12)
        outer.pack(fill="both", expand=True)
        ttk.Label(outer, text="DOCTRINES", style="PageTitle.TLabel").pack(anchor="w")

        text = tk.Text(outer, wrap="word", relief="flat", borderwidth=0,
                       background=theme.CANVAS_BG, foreground=theme.TEXT,
                       font=(theme.FACE_MONO, 9), padx=8, pady=8)
        bar = ttk.Scrollbar(outer, orient="vertical", command=text.yview)
        text.configure(yscrollcommand=bar.set)
        text.pack(side="left", fill="both", expand=True, pady=(6, 0))
        bar.pack(side="right", fill="y", pady=(6, 0))
        text.insert("1.0", DOCTRINE_GUIDE)
        text.configure(state="disabled")

        ttk.Button(self, text="Close", command=self.destroy).pack(pady=(0, 10))
        self.grab_set()


class TechTab(ttk.Frame):
    """Visual research-screen view first, doctrines on a tab of their own
    because they are bought with XP and mutually exclusive rather than
    researched in sequence, and the byte-preserving raw editor last for
    anyone who needs to hand-edit a field the visual view doesn't surface."""

    def __init__(self, master):
        super().__init__(master, padding=6)
        self.header = ui_kit.PageHeader(
            self, "Tech",
            "Edit a technology tree category - technologies, their prerequisites, research "
            "cost and the equipment/bonuses they unlock.", help_key="tech")

        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=2, pady=2)
        self.tree_view = TechTreeView(nb)
        self.doctrine_view = TechTreeView(nb, doctrines=True)
        self.raw_editor = _RawEditor(nb)
        nb.add(self.tree_view, text="Tech Tree")
        nb.add(self.doctrine_view, text="Doctrines")
        nb.add(self.raw_editor, text="Raw Editor")
        nb.bind("<<NotebookTabChanged>>", self._on_tab_changed)
        self._nb = nb

        state.subscribe(self.on_mod_changed)
        self.on_mod_changed()

    def on_mod_changed(self):
        if state.is_loaded:
            self.header.set_status(True, state.mod_name)
        else:
            self.header.set_status(False, "no mod open")
        _scan_cache.invalidate()   # a different mod means different files
        self.tree_view.on_mod_changed()
        self.doctrine_view.on_mod_changed()
        # _RawEditor already subscribes to state itself

    def _views(self):
        return {0: self.tree_view, 1: self.doctrine_view}

    def _on_tab_changed(self, event):
        view = self._views().get(self._nb.index("current"))
        if view is None or not state.is_loaded:
            return
        if not view.graph:
            view.reload()
        else:
            # the other view may have changed the DLC selection since
            view.refresh_dlc_from_prefs()

    def on_show(self):
        if state.is_loaded and not self.tree_view.graph:
            self.tree_view.reload()
