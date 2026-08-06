"""Render a category of ideas/national spirits the way the political view's
idea list shows them: the game's own row background, the idea's icon, its
name, and a one-line summary of what its modifiers do.
"""

import os
import re
import tkinter as tk
from tkinter import ttk

from app import image_cache
from app import mod_loader as ml
from app.state import state
from app import theme

ROW_W, ROW_H = 337, 75
ICON_W, ICON_H = 60, 68

NAME_TEXT = "#f0dca8"
MOD_TEXT = "#9fc98a"
MOD_TEXT_NEG = "#c98a8a"

from app.game_paths import find_base_game

#: resolved once at import; empty when HOI4 isn't installed here
BASE_GAME = find_base_game()

_MOD_LINE_RE = re.compile(r"^([a-zA-Z_0-9.]+)\s*=\s*(-?[\d.]+)")


def _asset(*parts):
    path = os.path.join(BASE_GAME, "gfx", "interface", *parts)
    return path if os.path.isfile(path) else None


def _modifier_summary(modifier_text, limit=2):
    """Turn `key = value` lines into short "key +value" style captions."""
    lines = []
    for raw_line in modifier_text.splitlines():
        m = _MOD_LINE_RE.match(raw_line.strip())
        if not m:
            continue
        key, value = m.groups()
        try:
            num = float(value)
        except ValueError:
            continue
        sign = "+" if num > 0 else ""
        label = key.replace("_", " ")
        lines.append((f"{label} {sign}{value}", num >= 0))
        if len(lines) >= limit:
            break
    return lines


class IdeaPreview(tk.Toplevel):
    def __init__(self, master, category, ideas):
        super().__init__(master)
        self.title(f"Ideas preview — {category}")
        self.geometry("420x680")
        self.category = category
        self.ideas = ideas
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
        ttk.Label(
            foot, text="Only numeric modifier lines are summarised here.",
            foreground="#888",
        ).pack(side="left")
        ttk.Button(foot, text="Close", command=self.destroy).pack(side="right")

    def _icon_path(self, idea):
        picture = idea.get("picture", "")
        if not picture:
            return None
        sprite = picture if picture.upper().startswith("GFX_") else f"GFX_idea_{picture}"
        return ml.resolve_texture(sprite, state.mod_root, state.gfx_index)

    def _render(self):
        self.canvas.delete("all")
        self.refs = []
        x0 = 20
        y = 14

        row_bg = image_cache.get_scaled(_asset("idea_entry_bg.dds"), (ROW_W, ROW_H))
        for idea in self.ideas:
            if row_bg:
                self.refs.append(row_bg)
                self.canvas.create_image(x0, y, image=row_bg, anchor="nw")
            else:
                self.canvas.create_rectangle(x0, y, x0 + ROW_W, y + ROW_H, fill="#26241c", outline="#6b5a3a")

            icon_path = self._icon_path(idea)
            icon = image_cache.get_scaled(icon_path, (ICON_W, ICON_H)) if icon_path else None
            if icon:
                self.refs.append(icon)
                self.canvas.create_image(x0 + 8, y + 4, image=icon, anchor="nw")
            else:
                self.canvas.create_rectangle(
                    x0 + 8, y + 4, x0 + 8 + ICON_W, y + 4 + ICON_H, outline="#6b5a3a",
                )
                self.canvas.create_text(x0 + 8 + ICON_W / 2, y + 4 + ICON_H / 2, text="?", fill="#777")

            name = state.text_for(idea["id"], idea["id"])
            self.canvas.create_text(
                x0 + ICON_W + 20, y + 14, text=name, fill=NAME_TEXT,
                font=("Segoe UI", 10, "bold"), anchor="w", width=ROW_W - ICON_W - 34,
            )

            if idea.get("removal_cost") == "-1":
                self.canvas.create_text(
                    x0 + ICON_W + 20, y + 30, text="national spirit (permanent)",
                    fill="#9a917c", font=("Segoe UI", 8, "italic"), anchor="w",
                )
                mod_start = 44
            else:
                mod_start = 30

            for i, (label, positive) in enumerate(_modifier_summary(idea.get("modifier", ""))):
                self.canvas.create_text(
                    x0 + ICON_W + 20, y + mod_start + i * 14, text=label,
                    fill=MOD_TEXT if positive else MOD_TEXT_NEG,
                    font=("Segoe UI", 8), anchor="w",
                )

            y += ROW_H + 4

        self.canvas.configure(scrollregion=(0, 0, ROW_W + 40, y + 20))
