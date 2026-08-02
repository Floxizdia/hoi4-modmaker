"""A searchable library of every focus icon available on this machine -
the base game's goal sprites plus the sprites of every installed workshop
mod - so a modder can reuse an existing icon instead of drawing one.

Indexing is cheap (it only reads .gfx text), but there are tens of
thousands of sprites, so the picker decodes thumbnails lazily for just the
page currently on screen.
"""

import os
import tkinter as tk
from tkinter import ttk

from app import mod_loader as ml
from app import image_cache
from app import theme

PAGE_SIZE = 120
CELL = 116


def build_library(base_game, workshop_root, extra_roots=()):
    """Return a sorted list of {sprite, path, source} for sprites that look
    like focus icons. Later sources win on duplicate sprite names, matching
    how HOI4 resolves overrides."""
    roots = []
    if base_game and os.path.isdir(base_game):
        roots.append(("Base game", base_game))
    for mod in ml.list_workshop_mods(workshop_root):
        roots.append((mod["name"], mod["path"]))
    for root in extra_roots:
        if root and os.path.isdir(root):
            roots.append((os.path.basename(root), root))

    # A sprite name resolves to exactly one texture in game - the last mod
    # to define it wins - so the list is keyed by name and shows that
    # winning texture. Submods routinely redefine their parent's whole icon
    # set, though, so every mod that declares a name is remembered as a
    # source; otherwise the parent mod would vanish from the filter.
    merged = {}
    for source, root in roots:
        for sprite, path in ml.build_gfx_index([root]).items():
            if not _looks_like_focus_icon(sprite, path):
                continue
            entry = merged.get(sprite)
            if entry is None:
                merged[sprite] = {"sprite": sprite, "path": path, "sources": [source]}
            else:
                entry["path"] = path
                if source not in entry["sources"]:
                    entry["sources"].append(source)

    return sorted(merged.values(), key=lambda e: e["sprite"])


def _looks_like_focus_icon(sprite, path):
    if sprite.endswith("_shine"):
        return False
    lowered = sprite.lower()
    if not (lowered.startswith("gfx_goal") or lowered.startswith("gfx_focus")):
        return False
    normalized = path.replace("\\", "/").lower()
    return "/goals/" in normalized or "/goals" in normalized


def _looks_like_idea_icon(sprite, path):
    if not sprite.lower().startswith("gfx_idea_"):
        return False
    if "_slot_" in sprite.lower() or sprite.endswith("_bg"):
        return False
    return "/ideas/" in path.replace("\\", "/").lower()


def build_idea_library(base_game, workshop_root, extra_roots=()):
    """Same idea as build_library, but for national-spirit/idea icons
    (gfx/interface/ideas, ~60x68) instead of focus goal icons."""
    roots = []
    if base_game and os.path.isdir(base_game):
        roots.append(("Base game", base_game))
    for mod in ml.list_workshop_mods(workshop_root):
        roots.append((mod["name"], mod["path"]))
    for root in extra_roots:
        if root and os.path.isdir(root):
            roots.append((os.path.basename(root), root))

    merged = {}
    for source, root in roots:
        for sprite, path in ml.build_gfx_index([root]).items():
            if not _looks_like_idea_icon(sprite, path):
                continue
            entry = merged.get(sprite)
            if entry is None:
                merged[sprite] = {"sprite": sprite, "path": path, "sources": [source]}
            else:
                entry["path"] = path
                if source not in entry["sources"]:
                    entry["sources"].append(source)

    return sorted(merged.values(), key=lambda e: e["sprite"])


class IconPicker(tk.Toplevel):
    """Modal grid of icons. `self.result` holds the chosen sprite name."""

    def __init__(self, master, library):
        super().__init__(master)
        self.title("Pick a focus icon")
        self.geometry("980x640")
        self.library = library
        self.result = None
        self.page = 0
        self.image_refs = []
        self._build()
        self._render()
        self.grab_set()

    def _build(self):
        top = ttk.Frame(self, padding=8)
        top.pack(fill="x")
        ttk.Label(top, text="Search:").pack(side="left")
        self.query = tk.StringVar()
        entry = ttk.Entry(top, textvariable=self.query, width=34)
        entry.pack(side="left", padx=6)
        entry.bind("<KeyRelease>", lambda e: self._on_query())
        entry.focus_set()

        ttk.Label(top, text="Source:").pack(side="left", padx=(14, 0))
        sources = ["(all)"] + sorted({s for e in self.library for s in e["sources"]})
        self.source = tk.StringVar(value="(all)")
        ttk.Combobox(top, textvariable=self.source, values=sources, state="readonly", width=28).pack(side="left", padx=6)
        self.source.trace_add("write", lambda *_: self._on_query())

        self.count_label = ttk.Label(top, text="", foreground="#888")
        self.count_label.pack(side="left", padx=10)

        wrap = ttk.Frame(self)
        wrap.pack(fill="both", expand=True, padx=8)
        self.canvas = tk.Canvas(wrap, background=theme.CANVAS_BG, highlightthickness=0)
        bar = ttk.Scrollbar(wrap, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=bar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        bar.pack(side="right", fill="y")
        self.canvas.bind("<MouseWheel>", lambda e: self.canvas.yview_scroll(-1 * (e.delta // 120), "units"))

        nav = ttk.Frame(self, padding=8)
        nav.pack(fill="x")
        ttk.Button(nav, text="< Prev", command=lambda: self._flip(-1)).pack(side="left")
        self.page_label = ttk.Label(nav, text="")
        self.page_label.pack(side="left", padx=8)
        ttk.Button(nav, text="Next >", command=lambda: self._flip(1)).pack(side="left")
        ttk.Button(nav, text="Cancel", command=self.destroy).pack(side="right")
        self.pick_label = ttk.Label(nav, text="Click an icon to choose it.", foreground="#2a7a2a")
        self.pick_label.pack(side="right", padx=12)

        self._filtered = self.library

    def _on_query(self):
        needle = self.query.get().strip().lower()
        source = self.source.get()
        self._filtered = [
            e for e in self.library
            if (source == "(all)" or source in e["sources"]) and (not needle or needle in e["sprite"].lower())
        ]
        self.page = 0
        self._render()

    def _flip(self, delta):
        pages = max(1, (len(self._filtered) + PAGE_SIZE - 1) // PAGE_SIZE)
        self.page = max(0, min(pages - 1, self.page + delta))
        self._render()

    def _render(self):
        self.canvas.delete("all")
        self.image_refs = []

        pages = max(1, (len(self._filtered) + PAGE_SIZE - 1) // PAGE_SIZE)
        start = self.page * PAGE_SIZE
        chunk = self._filtered[start:start + PAGE_SIZE]

        self.count_label.config(text=f"{len(self._filtered)} icons")
        self.page_label.config(text=f"page {self.page + 1} / {pages}")

        columns = max(1, (self.canvas.winfo_width() or 940) // CELL)
        for i, entry in enumerate(chunk):
            col = i % columns
            row = i // columns
            x = 12 + col * CELL
            y = 12 + row * CELL
            tag = f"icon_{i}"

            self.canvas.create_rectangle(
                x, y, x + CELL - 12, y + CELL - 12,
                fill=theme.RAISED, outline=theme.BRONZE, tags=(tag,),
            )
            thumb = image_cache.get_thumbnail(entry["path"], (72, 64))
            if thumb:
                self.image_refs.append(thumb)
                self.canvas.create_image(x + (CELL - 12) / 2, y + 40, image=thumb, tags=(tag,))
            else:
                self.canvas.create_text(x + (CELL - 12) / 2, y + 40, text="(?)", fill="#777", tags=(tag,))

            label = entry["sprite"].replace("GFX_goal_", "").replace("GFX_focus_", "")
            if len(label) > 30:
                label = label[:28] + "…"
            self.canvas.create_text(
                x + (CELL - 12) / 2, y + CELL - 26, text=label, fill="#bbb",
                width=CELL - 18, font=("Segoe UI", 7), tags=(tag,),
            )
            self.canvas.tag_bind(tag, "<Button-1>", lambda e, en=entry: self._choose(en))

        bbox = self.canvas.bbox("all")
        if bbox:
            self.canvas.configure(scrollregion=(0, 0, bbox[2] + 12, bbox[3] + 12))

    def _choose(self, entry):
        self.result = entry["sprite"]
        self.destroy()
