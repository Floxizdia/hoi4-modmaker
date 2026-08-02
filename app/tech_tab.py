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
from app.tech_graph import find_tech_files, parse_techs, build_graph, folders, resolve_icon
from app import tech_graph
from app import image_cache
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


class TechTreeView(ttk.Frame):
    """The same folder-tab / grid-of-plaques arrangement the game's own
    research screen uses, built from `folder.position` - which the game
    ships pre-laid-out and essentially collision-free, unlike focus trees
    where trusting stored x/y caused the overlap bug this app already fixed
    once. So no auto-layout pass is needed here, just draw where it says."""

    def __init__(self, master):
        super().__init__(master, padding=6)
        self.graph = {}
        self.folder_names = []
        self.current_folder = None
        self.selected = None
        self.icon_refs = []
        self.zoom = 1.0
        self._build()

    def _build(self):
        top = ttk.Frame(self)
        top.pack(fill="x")
        ttk.Button(top, text="Rescan", style="Accent.TButton", command=self.reload).pack(side="left")
        ttk.Label(top, text="  Folder:").pack(side="left")
        self.folder_var = tk.StringVar()
        self.folder_combo = ttk.Combobox(top, textvariable=self.folder_var, state="readonly", width=26)
        self.folder_combo.pack(side="left", padx=4)
        self.folder_combo.bind("<<ComboboxSelected>>", lambda e: self._show_folder(self.folder_var.get()))
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
        ttk.Label(side, text="TECH DETAILS", style="Gold.TLabel").pack(anchor="w")
        self.detail = ttk.Label(side, text="Click a technology.", style="Muted.TLabel",
                                wraplength=280, justify="left")
        self.detail.pack(anchor="w", pady=(6, 10), fill="x")
        ttk.Button(side, text="Edit Raw Block...", command=self._edit_selected).pack(anchor="w")

    # ---- loading ----

    def on_mod_changed(self):
        self.graph = {}
        self.folder_names = []
        self.current_folder = None
        self.selected = None
        self.canvas.delete("all")
        self.folder_combo["values"] = []
        self.count_label.config(text="")
        self.detail.config(text="Click a technology.")
        self.researched = set()
        self.country_combo["values"] = []

    def reload(self):
        if not state.is_loaded:
            messagebox.showerror("No mod", "Open a mod first.")
            return
        self.graph = tech_graph.build_graph(state.mod_root)
        tags = tech_graph.country_tags(state.mod_root)
        self.country_combo["values"] = tags
        if self.country_var.get() not in tags:
            self.country_var.set("GER" if "GER" in tags else (tags[0] if tags else ""))
        self.researched = tech_graph.starting_techs(state.mod_root, self.country_var.get())
        self.folder_names = tech_graph.folders(self.graph)
        self.folder_combo["values"] = self.folder_names
        if self.folder_names:
            self.folder_var.set(self.folder_names[0])
            self._show_folder(self.folder_names[0])
        self.count_label.config(text=f"{len(self.graph)} techs | {self.country_var.get() or '-'}: {len(self.researched)} researched")

    def _load_country_status(self):
        self.researched = tech_graph.starting_techs(state.mod_root, self.country_var.get())
        self.count_label.config(text=f"{len(self.graph)} techs | {self.country_var.get() or '-'}: {len(self.researched)} researched")
        self._show_folder(self.current_folder)

    def _set_zoom(self, z):
        self.zoom = max(0.4, min(2.0, z))
        self._show_folder(self.current_folder)

    # ---- drawing ----

    def _grid_positions(self, items):
        """{tech_id: (col, row)} in the folder's own grid units - straight
        from `folder.position` when that data is real, or derived from the
        prerequisite graph (same depth + barycenter pass the focus tree
        uses) when it isn't. Mods regularly leave position off techs that
        don't need the visual tuning base-game folders got (this mod's own
        air-tech folder has 20 of 21 techs sitting on 0,0) - trusting that
        blindly would stack them all into one node, exactly like the old
        focus-tree overlap bug this app already fixed once."""
        coords = {tid: (info["x"], info["y"]) for tid, info in items.items()}
        distinct = len(set(coords.values()))
        if distinct >= max(2, len(items) * 0.6):
            grid = coords
        else:
            synthetic = [{"id": tid, "x": info["x"],
                         "prerequisite": [r for r in info["requires"] if r in items],
                         "prerequisite_groups": [[r] for r in info["requires"] if r in items]}
                        for tid, info in items.items()]
            grid = layout_mod.auto_layout(synthetic)

        # even "trustworthy" position data isn't always collision-free - some
        # DLC folders (naval/air doctrine expansions in this mod) place a
        # handful of techs from different sub-branches on the exact same
        # cell, which the game's own multi-lane rendering hides but a flat
        # grid can't. Nudge any exact duplicate rightward onto a free cell.
        occupied = set()
        resolved = {}
        for tid in sorted(grid, key=lambda t: (grid[t][1], grid[t][0], t)):
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

        items = {tid: info for tid, info in self.graph.items() if (info["folder"] or "(no folder)") == folder}
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
        icon_path = tech_graph.resolve_icon(state.mod_root, tech_id)
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
            self.canvas.create_text(x, y, text=tech_id[:10], fill=theme.MUTED,
                                    font=(theme.FACE_UI, max(6, int(7 * self.zoom))),
                                    width=size, justify="center", tags=(tag,))

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
        lines = [
            tech_id + ("  (vanilla)" if info.get("is_vanilla") else "  (this mod)"),
            f"Starting status for {self.country_var.get() or '-'}: "
            + ("RESEARCHED" if tech_id in self.researched else "NOT RESEARCHED"),
            f"cost {info.get('research_cost', '?')}   year {info.get('start_year', '?')}",
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
            self.reload()

        btns = ttk.Frame(dialog)
        btns.pack(fill="x", padx=8, pady=(0, 8))
        ttk.Button(btns, text="Save", style="Accent.TButton", command=save).pack(side="left")
        ttk.Button(btns, text="Cancel", command=dialog.destroy).pack(side="left", padx=6)
        dialog.grab_set()


class TechTab(ttk.Frame):
    """Visual research-screen view first, the byte-preserving raw editor
    kept one tab over for anyone who needs to hand-edit an engine-specific
    field the visual view doesn't surface."""

    def __init__(self, master):
        super().__init__(master, padding=6)
        self.header = ui_kit.PageHeader(
            self, "Tech",
            "Edit a technology tree category - technologies, their prerequisites, research "
            "cost and the equipment/bonuses they unlock.", help_key="tech")

        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=2, pady=2)
        self.tree_view = TechTreeView(nb)
        self.raw_editor = _RawEditor(nb)
        nb.add(self.tree_view, text="Tech Tree")
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
        self.tree_view.on_mod_changed()
        # _RawEditor already subscribes to state itself

    def _on_tab_changed(self, event):
        if self._nb.index("current") == 0 and state.is_loaded and not self.tree_view.graph:
            self.tree_view.reload()

    def on_show(self):
        if state.is_loaded and not self.tree_view.graph:
            self.tree_view.reload()
