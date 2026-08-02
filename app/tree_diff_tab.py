"""Tree Diff tab: pick a snapshot, see the current focus trees laid out
with green/amber for what's new or changed since then, and a plain list of
what's gone - the visual counterpart to What Changed?'s line-by-line text
diff, scoped to focuses specifically.
"""

import os
import tkinter as tk
from tkinter import ttk, messagebox

from app.state import state
from app import snapshots
from app import tree_diff
from app import layout as layout_mod
from app import image_cache
from app import mod_loader as ml
from app import theme, ui_kit

CELL_W, CELL_H = 190, 90
NODE_W, NODE_H = 150, 56

STATUS_COLOUR = {
    "added": theme.GREEN,
    "changed": theme.AMBER,
    "unchanged": theme.EDGE,
}


class TreeDiffTab(ttk.Frame):
    def __init__(self, master):
        super().__init__(master, padding=12)
        self.diff = None
        self.selected = None
        self.icon_refs = []
        self._build()
        state.subscribe(self.on_mod_changed)

    def _build(self):
        self.header = ui_kit.PageHeader(
            self, "Tree Diff",
            "Compares two focus trees (e.g. your mod's vs. vanilla's, or two versions of your own) side by side and highlights what changed.", help_key="tree_diff")

        top = ttk.Frame(self)
        top.pack(fill="x")
        ttk.Label(top, text="Compare against snapshot:").pack(side="left")
        self.snap_var = tk.StringVar()
        self.snap_combo = ttk.Combobox(top, textvariable=self.snap_var, state="readonly", width=44)
        self.snap_combo.pack(side="left", padx=6)
        ttk.Button(top, text="Refresh List", command=self._refresh_snapshots).pack(side="left")
        ttk.Button(top, text="Compare", style="Accent.TButton", command=self._compare).pack(side="left", padx=6)

        legend = ttk.Frame(self)
        legend.pack(fill="x", pady=(6, 0))
        for label, colour in (("Added", theme.GREEN), ("Changed", theme.AMBER), ("Unchanged", theme.MUTED)):
            dot = tk.Canvas(legend, width=10, height=10, highlightthickness=0, background=theme.BG)
            dot.pack(side="left", padx=(10 if label != "Added" else 0, 4))
            dot.create_oval(1, 1, 9, 9, fill=colour, outline="")
            ttk.Label(legend, text=label, style="Muted.TLabel").pack(side="left")
        self.summary_label = ttk.Label(legend, text="", style="Muted.TLabel")
        self.summary_label.pack(side="left", padx=20)

        body = ttk.Frame(self)
        body.pack(fill="both", expand=True, pady=8)

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

        side = ttk.Frame(body, width=300, padding=(10, 0, 0, 0))
        side.pack(side="left", fill="y")
        side.pack_propagate(False)
        ttk.Label(side, text="DETAILS", style="Gold.TLabel").pack(anchor="w")
        self.detail = ttk.Label(side, text="Click a focus for details.", style="Muted.TLabel",
                                wraplength=280, justify="left")
        self.detail.pack(anchor="w", pady=(6, 12), fill="x")

        ttk.Label(side, text="REMOVED SINCE SNAPSHOT", style="Gold.TLabel").pack(anchor="w")
        self.removed_list = tk.Listbox(side, height=14)
        self.removed_list.pack(fill="both", expand=True, pady=(4, 0))

        self.on_mod_changed()

    def on_mod_changed(self):
        if state.is_loaded:
            self.header.set_status(True, state.mod_name)
        else:
            self.header.set_status(False, "no mod open")
        self.diff = None
        self.canvas.delete("all")
        self.removed_list.delete(0, "end")
        self.detail.config(text="Click a focus for details.")
        self.summary_label.config(text="")
        self._refresh_snapshots()

    def on_show(self):
        if state.is_loaded and not self.snap_combo["values"]:
            self._refresh_snapshots()

    def _refresh_snapshots(self):
        if not state.is_loaded:
            self.snap_combo["values"] = []
            return
        snaps = snapshots.list_snapshots(state.mod_root)
        self._snaps = snaps
        self.snap_combo["values"] = [f"{label}  ({size:.1f} MB)" for _, label, size in snaps]
        if snaps:
            self.snap_combo.current(0)

    def _compare(self):
        if not state.is_loaded:
            messagebox.showerror("No mod", "Open a mod first.")
            return
        idx = self.snap_combo.current()
        if idx < 0 or not getattr(self, "_snaps", None):
            messagebox.showerror(
                "No snapshots", "Take a snapshot first (Settings tab) so there's an earlier version to compare against.")
            return
        zip_path = self._snaps[idx][0]

        self.summary_label.config(text="Comparing...")
        self.update_idletasks()
        tmp = tree_diff.extract_snapshot(zip_path)
        try:
            self.diff = tree_diff.compare(tmp, state.mod_root)
        finally:
            tree_diff.cleanup(tmp)

        d = self.diff
        self.summary_label.config(
            text=f"{len(d['added'])} added · {len(d['changed'])} changed · "
                 f"{len(d['removed'])} removed · {len(d['unchanged'])} unchanged")

        self.removed_list.delete(0, "end")
        for fid in d["removed"]:
            title = d["old"][fid].get("title", fid)
            self.removed_list.insert("end", f" {fid}  —  {title}")

        self._render()

    def _status_of(self, fid):
        if fid in self.diff["added"]:
            return "added"
        if fid in self.diff["changed"]:
            return "changed"
        return "unchanged"

    def _render(self):
        self.canvas.delete("all")
        self.icon_refs = []
        if not self.diff:
            return
        focuses = list(self.diff["new"].values())
        positions = layout_mod.auto_layout(focuses)
        if not positions:
            return

        pixel = {fid: (60 + col * CELL_W, 50 + row * CELL_H) for fid, (col, row) in positions.items()}

        for fid, f in self.diff["new"].items():
            x1, y1 = pixel[fid]
            for pre in f.get("prerequisite", []):
                if pre in pixel:
                    x0, y0 = pixel[pre]
                    self.canvas.create_line(x0, y0 + NODE_H / 2, x1, y1 - NODE_H / 2, fill=theme.EDGE, width=1.5)

        for fid, f in self.diff["new"].items():
            self._draw_node(fid, f, *pixel[fid])

        max_x = max(p[0] for p in pixel.values()) + CELL_W
        max_y = max(p[1] for p in pixel.values()) + CELL_H
        self.canvas.configure(scrollregion=(0, 0, max_x, max_y))

    def _draw_node(self, fid, f, x, y):
        status = self._status_of(fid)
        selected = fid == self.selected
        colour = STATUS_COLOUR[status]
        tag = f"node::{fid}"

        icon_path = ml.resolve_texture(f.get("icon", ""), state.mod_root, state.gfx_index)
        thumb = image_cache.get_thumbnail(icon_path, (28, 28)) if icon_path else None

        self.canvas.create_rectangle(x - NODE_W / 2, y - NODE_H / 2, x + NODE_W / 2, y + NODE_H / 2,
                                     fill=theme.SURFACE, outline=theme.GOLD if selected else colour,
                                     width=3 if selected else 2, tags=(tag,))
        if thumb:
            self.icon_refs.append(thumb)
            self.canvas.create_image(x - NODE_W / 2 + 20, y, image=thumb, tags=(tag,))
        title = state.text_for(fid, f.get("title", fid))
        self.canvas.create_text(x + 8, y, text=title, fill=theme.TEXT, width=NODE_W - 40,
                                font=(theme.FACE_UI, 8), justify="left", tags=(tag,))

    def _on_click(self, event):
        x, y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
        for item in self.canvas.find_overlapping(x - 1, y - 1, x + 1, y + 1):
            for t in self.canvas.gettags(item):
                if t.startswith("node::"):
                    self._select(t[6:])
                    return

    def _select(self, fid):
        self.selected = fid
        status = self._status_of(fid)
        lines = [f"{fid}   ({status})"]
        if status == "changed":
            fields = self.diff["changed"][fid]
            old_f, new_f = self.diff["old"][fid], self.diff["new"][fid]
            lines.append("")
            for field in fields:
                lines.append(f"{field}: {old_f.get(field)!r} → {new_f.get(field)!r}")
        elif status == "added":
            lines.append("\nNew since the snapshot.")
        else:
            lines.append("\nUnchanged since the snapshot.")
        self.detail.config(text="\n".join(lines))
        self._render()
