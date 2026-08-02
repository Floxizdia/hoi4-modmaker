"""Idea Gallery tab: every national spirit / idea in the mod, across every
category, shown the way the political view shows them - icon, name, and a
one-line summary of what the modifier actually does - instead of opening
`IdeaPreview` one category at a time from inside the Ideas tab.
"""

import os
import tkinter as tk
from tkinter import ttk

from app.state import state
from app import image_cache
from app import mod_loader as ml
from app import theme, ui_kit
from app.idea_preview import _asset, _modifier_summary
from app.map_data import BASE_GAME

ROW_W, ROW_H = 337, 75
ICON_W, ICON_H = 60, 68


class IdeaGalleryTab(ttk.Frame):
    def __init__(self, master):
        super().__init__(master, padding=12)
        self._all = []      # [(category, idea_dict)]
        self.refs = []
        # Rendering thousands of icon cards at once is needlessly expensive.
        # Keep the complete catalogue in memory but draw one manageable page.
        self.page = 0
        self.page_size = 160
        self._build()
        state.subscribe(self.on_mod_changed)

    def _build(self):
        self.header = ui_kit.PageHeader(
            self, "Idea Gallery",
            "Browses every idea already in the base game plus your mod as an icon grid, so you can see what exists before inventing a duplicate.", help_key="idea_gallery")

        top = ttk.Frame(self)
        top.pack(fill="x")
        ttk.Button(top, text="Scan Ideas", style="Accent.TButton", command=self._scan).pack(side="left")
        ttk.Label(top, text="  Category:").pack(side="left")
        self.cat_var = tk.StringVar(value="All")
        self.cat_combo = ttk.Combobox(top, textvariable=self.cat_var, state="readonly", width=22)
        self.cat_combo.pack(side="left", padx=4)
        self.cat_combo.bind("<<ComboboxSelected>>", lambda e: self._render())
        ttk.Label(top, text="  Search:").pack(side="left")
        self.search_var = tk.StringVar()
        entry = ttk.Entry(top, textvariable=self.search_var, width=24)
        entry.pack(side="left", padx=4)
        entry.bind("<KeyRelease>", lambda e: self._render())
        self.count_label = ttk.Label(top, text="", style="Muted.TLabel")
        self.count_label.pack(side="left", padx=10)
        ttk.Button(top, text="<", width=3, command=lambda: self._set_page(self.page - 1)).pack(side="right")
        self.page_label = ttk.Label(top, text="", style="Muted.TLabel")
        self.page_label.pack(side="right", padx=6)
        ttk.Button(top, text=">", width=3, command=lambda: self._set_page(self.page + 1)).pack(side="right")

        wrap = ttk.Frame(self)
        wrap.pack(fill="both", expand=True, pady=8)
        self.canvas = tk.Canvas(wrap, background=theme.CANVAS_BG, highlightthickness=0)
        bar = ttk.Scrollbar(wrap, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=bar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        bar.pack(side="right", fill="y")
        self.canvas.bind("<MouseWheel>", lambda e: self.canvas.yview_scroll(-1 * (e.delta // 120), "units"))
        self.canvas.bind("<Configure>", lambda e: self._render())

        self.on_mod_changed()

    # ---- lifecycle ----

    def on_mod_changed(self):
        if state.is_loaded:
            self.header.set_status(True, state.mod_name)
        else:
            self.header.set_status(False, "no mod open")
        self._all = []
        self.page = 0
        self.canvas.delete("all")
        self.cat_combo["values"] = ["All"]
        self.count_label.config(text="")

    def on_show(self):
        if state.is_loaded and not self._all:
            self._scan()

    # ---- scanning ----

    def _scan(self):
        self._all = []
        self.page = 0
        # Gallery is a catalogue: show vanilla first, then let the open mod
        # layer its own definitions on top.
        for root in (BASE_GAME, state.mod_root):
            for path in ml.find_idea_files(root):
                for category in ml.parse_ideas(path):
                    for idea in category["ideas"]:
                        self._all.append((category["category"], idea))
        categories = sorted({c for c, _ in self._all})
        self.cat_combo["values"] = ["All"] + categories
        self.cat_var.set("All")
        self.count_label.config(text=f"{len(self._all)} idea(s) in {len(categories)} categor(y/ies)")
        self._render()

    def _icon_path(self, idea):
        picture = idea.get("picture", "")
        if not picture:
            return None
        sprite = picture if picture.upper().startswith("GFX_") else f"GFX_idea_{picture}"
        return ml.resolve_texture(sprite, state.mod_root, state.gfx_index)

    # ---- rendering (same row style as idea_preview.IdeaPreview) ----

    def _render(self):
        self.canvas.delete("all")
        self.refs = []
        needle = self.search_var.get().strip().lower()
        category = self.cat_var.get()

        filtered = [(c, i) for c, i in self._all
                    if (category == "All" or c == category)
                    and (not needle or needle in i["id"].lower()
                         or needle in state.text_for(i["id"], "").lower())]
        pages = max(1, (len(filtered) + self.page_size - 1) // self.page_size)
        self.page = min(max(0, self.page), pages - 1)
        start = self.page * self.page_size
        shown = filtered[start:start + self.page_size]
        self.page_label.config(text=f"Page {self.page + 1}/{pages}")

        width = max(self.canvas.winfo_width(), ROW_W + 40)
        cols = max(1, width // (ROW_W + 20))
        row_bg = image_cache.get_scaled(_asset("idea_entry_bg.dds"), (ROW_W, ROW_H))

        col_x = [20 + c * (ROW_W + 20) for c in range(cols)]
        col_y = [14] * cols

        for cat_id, idea in shown:
            col = min(range(cols), key=lambda c: col_y[c])
            x0, y = col_x[col], col_y[col]

            if row_bg:
                self.refs.append(row_bg)
                self.canvas.create_image(x0, y, image=row_bg, anchor="nw")
            else:
                self.canvas.create_rectangle(x0, y, x0 + ROW_W, y + ROW_H, fill=theme.SURFACE, outline=theme.EDGE)

            icon_path = self._icon_path(idea)
            icon = image_cache.get_scaled(icon_path, (ICON_W, ICON_H)) if icon_path else None
            if icon:
                self.refs.append(icon)
                self.canvas.create_image(x0 + 8, y + 4, image=icon, anchor="nw")
            else:
                self.canvas.create_rectangle(x0 + 8, y + 4, x0 + 8 + ICON_W, y + 4 + ICON_H, outline=theme.EDGE)
                self.canvas.create_text(x0 + 8 + ICON_W / 2, y + 4 + ICON_H / 2, text="?", fill=theme.MUTED)

            name = state.text_for(idea["id"], idea["id"])
            self.canvas.create_text(
                x0 + ICON_W + 20, y + 14, text=name, fill=theme.TEXT,
                font=(theme.FACE_UI, 10, "bold"), anchor="w", width=ROW_W - ICON_W - 34,
            )
            self.canvas.create_text(
                x0 + ICON_W + 20, y + 28, text=cat_id, fill=theme.MUTED,
                font=(theme.FACE_MONO, 7), anchor="w",
            )

            for i, (label, positive) in enumerate(_modifier_summary(idea.get("modifier", ""))):
                self.canvas.create_text(
                    x0 + ICON_W + 20, y + 44 + i * 14, text=label,
                    fill=theme.GREEN if positive else theme.RED,
                    font=(theme.FACE_MONO, 8), anchor="w",
                )

            col_y[col] += ROW_H + 10

        self.canvas.configure(scrollregion=(0, 0, width, max(col_y) + 20))

    def _set_page(self, page):
        self.page = max(0, page)
        self._render()
