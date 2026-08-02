"""Event Chain tab: pick a root event, see everything it fires (and what
those fire) as a flowchart, instead of clicking "next" through option
effects one event at a time to reconstruct a chain by hand.

Layout reuses `layout.auto_layout` - the same depth + barycenter pass the
focus tree uses - by feeding it a synthetic focus-shaped list where an
event's "prerequisite" is whichever event(s) fire it. The algorithm doesn't
care what domain the graph is from.
"""

import os
import tkinter as tk
from tkinter import ttk, messagebox

from app.state import state
from app import event_chain
from app import layout as layout_mod
from app import theme, ui_kit

NODE_W, NODE_H = 170, 56
COL_W, ROW_H = 210, 90


class EventChainTab(ttk.Frame):
    def __init__(self, master):
        super().__init__(master, padding=12)
        self.graph = {}
        self.positions = {}
        self.selected = None
        self._build()
        state.subscribe(self.on_mod_changed)

    def _build(self):
        self.header = ui_kit.PageHeader(
            self, "Event Chains",
            "Maps which events fire which other events (via trigger_event/random_events inside effects), so you can see a whole storyline as one flow instead of clicking through files one at a time.", help_key="event_chain")

        top = ttk.Frame(self)
        top.pack(fill="x")
        ttk.Button(top, text="Scan Event Chains", style="Accent.TButton", command=self._scan).pack(side="left")
        ttk.Label(top, text="  Chain starting at:").pack(side="left")
        self.root_var = tk.StringVar()
        self.root_combo = ttk.Combobox(top, textvariable=self.root_var, state="readonly", width=30)
        self.root_combo.pack(side="left", padx=4)
        self.root_combo.bind("<<ComboboxSelected>>", lambda e: self._show_chain(self.root_var.get()))
        self.count_label = ttk.Label(top, text="", style="Muted.TLabel")
        self.count_label.pack(side="left", padx=10)

        ttk.Label(
            self, style="Muted.TLabel", wraplength=980, justify="left",
            text="Only events that actually fire another event (or are fired by one) show up here — "
                 "a mod's other standalone events are already covered by the Events tab.",
        ).pack(fill="x", pady=(4, 4))

        body = ttk.Frame(self)
        body.pack(fill="both", expand=True, pady=6)
        self.canvas = tk.Canvas(body, background=theme.CANVAS_BG, highlightthickness=0)
        vbar = ttk.Scrollbar(body, orient="vertical", command=self.canvas.yview)
        hbar = ttk.Scrollbar(body, orient="horizontal", command=self.canvas.xview)
        self.canvas.configure(yscrollcommand=vbar.set, xscrollcommand=hbar.set)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        vbar.grid(row=0, column=1, sticky="ns")
        hbar.grid(row=1, column=0, sticky="ew")
        body.rowconfigure(0, weight=1)
        body.columnconfigure(0, weight=1)
        self.canvas.bind("<Button-1>", self._on_click)
        self.canvas.bind("<MouseWheel>", lambda e: self.canvas.yview_scroll(-1 * (e.delta // 120), "units"))

        self.detail = ttk.Label(self, text="Click an event in the chain for details.",
                                style="Status.TLabel", wraplength=980, justify="left")
        self.detail.pack(fill="x")

    # ---- lifecycle ----

    def on_mod_changed(self):
        self.graph = {}
        self.positions = {}
        self.selected = None
        self.canvas.delete("all")
        self.root_combo["values"] = []
        self.count_label.config(text="")
        if state.is_loaded:
            self.header.set_status(True, state.mod_name)
        else:
            self.header.set_status(False, "no mod open")

    def on_show(self):
        if state.is_loaded and not self.graph:
            self._scan()

    def _scan(self):
        if not state.is_loaded:
            messagebox.showerror("No mod", "Open a mod first.")
            return
        self.graph = event_chain.build_graph(state.mod_root)
        root_ids = event_chain.roots(self.graph)
        self.root_combo["values"] = root_ids
        self.count_label.config(
            text=f"{len(self.graph)} event(s) in chains, {len(root_ids)} chain(s) found")
        if root_ids:
            self.root_var.set(root_ids[0])
            self._show_chain(root_ids[0])
        else:
            self.canvas.delete("all")

    # ---- drawing ----

    def _show_chain(self, root_id):
        self.selected = None
        reachable = event_chain.chain_from(self.graph, root_id)
        synthetic = []
        for eid in reachable:
            parents = [p for p in self.graph.get(eid, {}).get("fired_by", []) if p in reachable]
            synthetic.append({"id": eid, "prerequisite": parents,
                              "prerequisite_groups": [[p] for p in parents], "x": 0})
        self.positions = layout_mod.auto_layout(synthetic)
        self._render()

    def _render(self):
        self.canvas.delete("all")
        if not self.positions:
            return
        px = {eid: (60 + col * COL_W, 40 + row * ROW_H) for eid, (col, row) in self.positions.items()}

        for eid in self.positions:
            x1, y1 = px[eid]
            for parent in self.graph.get(eid, {}).get("fired_by", []):
                if parent in px:
                    x0, y0 = px[parent]
                    self.canvas.create_line(x0, y0 + NODE_H / 2, x1, y1 - NODE_H / 2,
                                            fill=theme.GOLD_DIM, width=2, arrow="last")

        for eid, (x, y) in px.items():
            self._draw_node(eid, x, y)

        max_x = max(x for x, _ in px.values()) + COL_W
        max_y = max(y for _, y in px.values()) + ROW_H
        self.canvas.configure(scrollregion=(0, 0, max_x, max_y))

    def _draw_node(self, eid, x, y):
        selected = eid == self.selected
        tag = f"ev::{eid}"
        fill = theme.SELECTED if selected else theme.SURFACE
        outline = theme.GOLD if selected else theme.EDGE
        self.canvas.create_rectangle(x - NODE_W / 2, y - NODE_H / 2, x + NODE_W / 2, y + NODE_H / 2,
                                     fill=fill, outline=outline, width=2 if selected else 1, tags=(tag,))
        self.canvas.create_text(x, y - 10, text=eid, fill=theme.GOLD, font=(theme.FACE_UI, 9, "bold"),
                                width=NODE_W - 12, tags=(tag,))
        etype = self.graph.get(eid, {}).get("type", "")
        self.canvas.create_text(x, y + 12, text=etype, fill=theme.MUTED, font=(theme.FACE_UI, 7),
                                tags=(tag,))

    # ---- interaction ----

    def _on_click(self, event):
        x, y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
        for item in self.canvas.find_overlapping(x - 1, y - 1, x + 1, y + 1):
            for t in self.canvas.gettags(item):
                if t.startswith("ev::"):
                    self._select(t[4:])
                    return

    def _select(self, eid):
        self.selected = eid
        info = self.graph.get(eid, {})
        self.detail.config(
            text=f"{eid}   fired by: {', '.join(info.get('fired_by', [])) or '(chain start)'}"
                 f"   →   fires: {', '.join(info.get('fires', [])) or '(nothing further)'}"
                 f"   file: {os.path.basename(info.get('file', ''))}"
        )
        self._render()
