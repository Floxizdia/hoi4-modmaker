"""Render a decision category the way HOI4's decisions panel shows it:
the category header, then one row per decision on the game's own item
background, with icon, name and political-power cost.
"""

import os
import tkinter as tk
from tkinter import ttk

from app import image_cache
from app import mod_loader as ml
from app.state import state
from app import theme

HEADER_W, HEADER_H = 516, 53
ITEM_W, ITEM_H = 511, 40
ICON = 30

HEADER_TEXT = "#f3d99b"
ITEM_TEXT = "#e6dcc4"
DIM_TEXT = "#9a917c"
COST_TEXT = "#e0b23c"

from app.game_paths import find_base_game

#: resolved once at import; empty when HOI4 isn't installed here
BASE_GAME = find_base_game()


def _asset(*parts):
    path = os.path.join(BASE_GAME, "gfx", "interface", "decisionview", *parts)
    return path if os.path.isfile(path) else None


class DecisionPreview(tk.Toplevel):
    def __init__(self, master, category, decisions):
        super().__init__(master)
        self.title(f"Decisions preview — {category}")
        self.geometry("600x680")
        self.category = category
        self.decisions = decisions
        self.refs = []
        self._build()
        self._render()

    def _build(self):
        wrap = ttk.Frame(self)
        wrap.pack(fill="both", expand=True)
        self.canvas = tk.Canvas(wrap, background=theme.CANVAS_BG, highlightthickness=0)
        bar = ttk.Scrollbar(wrap, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=bar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        bar.pack(side="right", fill="y")
        self.canvas.bind("<MouseWheel>", lambda e: self.canvas.yview_scroll(-1 * (e.delta // 120), "units"))

        foot = ttk.Frame(self, padding=8)
        foot.pack(fill="x")
        self.note = ttk.Label(foot, text="", foreground="#888", wraplength=520, justify="left")
        self.note.pack(side="left")
        ttk.Button(foot, text="Close", command=self.destroy).pack(side="right")

    def _render(self):
        self.canvas.delete("all")
        self.refs = []
        x0 = 20
        y = 14

        header = image_cache.get_scaled(_asset("category_header_bg.dds"), (HEADER_W, HEADER_H))
        if header:
            self.refs.append(header)
            self.canvas.create_image(x0, y, image=header, anchor="nw")
        else:
            self.canvas.create_rectangle(x0, y, x0 + HEADER_W, y + HEADER_H, fill="#1c1917", outline="#6b5a3a")

        self.canvas.create_text(
            x0 + 20, y + HEADER_H / 2, text=state.text_for(self.category, self.category).upper(),
            fill=HEADER_TEXT, font=("Segoe UI", 11, "bold"), anchor="w",
        )
        self.canvas.create_text(
            x0 + HEADER_W - 20, y + HEADER_H / 2, text=f"{len(self.decisions)}",
            fill=DIM_TEXT, font=("Segoe UI", 10), anchor="e",
        )
        y += HEADER_H + 6

        item_bg = image_cache.get_scaled(_asset("decision_item_bg_single.dds"), (ITEM_W, ITEM_H))
        for d in self.decisions:
            if item_bg:
                self.refs.append(item_bg)
                self.canvas.create_image(x0, y, image=item_bg, anchor="nw")
            else:
                self.canvas.create_rectangle(x0, y, x0 + ITEM_W, y + ITEM_H, fill="#263324", outline="#4a5a44")

            icon_path = ml.resolve_texture(d.get("icon", ""), state.mod_root, state.gfx_index)
            icon = image_cache.get_scaled(icon_path, (ICON, ICON)) if icon_path else None
            if icon:
                self.refs.append(icon)
                self.canvas.create_image(x0 + 10, y + ITEM_H / 2, image=icon, anchor="w")
            else:
                self.canvas.create_rectangle(
                    x0 + 10, y + 5, x0 + 10 + ICON, y + 5 + ICON, outline="#5a6a54",
                )

            self.canvas.create_text(
                x0 + 52, y + ITEM_H / 2, text=d.get("title") or d["id"],
                fill=ITEM_TEXT, font=("Segoe UI", 10, "bold"), anchor="w", width=ITEM_W - 160,
            )

            cost = d.get("cost")
            if cost not in ("", None):
                self.canvas.create_text(
                    x0 + ITEM_W - 16, y + ITEM_H / 2, text=f"{cost} PP",
                    fill=COST_TEXT, font=("Segoe UI", 10, "bold"), anchor="e",
                )

            timer = d.get("days_re_enable")
            if timer:
                self.canvas.create_text(
                    x0 + ITEM_W - 70, y + ITEM_H / 2, text=f"{timer}d",
                    fill=DIM_TEXT, font=("Segoe UI", 9), anchor="e",
                )

            y += ITEM_H + 3

        self.canvas.configure(scrollregion=(0, 0, HEADER_W + 40, y + 20))
        self.note.config(
            text="Availability conditions are not evaluated here — in game a decision only "
                 "shows when its visible/available triggers pass."
        )
