"""Render an event roughly the way HOI4 shows it: the game's own window
frame (top piece, tiled midsection, bottom piece), the event picture, and
option buttons drawn on the real option-entry texture.

This is a preview for authoring, not a pixel-exact reproduction of the
in-game window - the intent is that a modder can see whether their title,
description and options read well before launching the game.
"""

import os
import tkinter as tk
from tkinter import ttk

from app import image_cache
from app import mod_loader as ml
from app.state import state
from app import theme

FRAME_W = 581
TOP_H = 121
MID_H = 66
BOTTOM_H = 206
PIC_W, PIC_H = 397, 153
OPTION_W, OPTION_H = 352, 48

# The window body is light parchment (~227,202,154) while the title band at
# the top and the option buttons are near-black, so text colour has to flip
# depending on which piece it sits on.
TITLE_BAND_Y = 36          # centre of the dark band inside the top piece
TITLE_ON_DARK = "#f3d99b"
BODY_TEXT = "#3a2c16"
BODY_TITLE = "#4a3517"
OPTION_TEXT = "#f0dca8"

BASE_GAME = r"C:\Program Files (x86)\Steam\steamapps\common\Hearts of Iron IV"


def _asset(*parts):
    path = os.path.join(BASE_GAME, "gfx", "interface", *parts)
    return path if os.path.isfile(path) else None


class EventPreview(tk.Toplevel):
    def __init__(self, master, event, namespace):
        super().__init__(master)
        self.title(f"Event preview — {namespace}.{event['number']}")
        self.geometry("660x760")
        self.event = event
        self.namespace = namespace
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
        self.note = ttk.Label(foot, text="", foreground="#888", wraplength=600, justify="left")
        self.note.pack(side="left")
        ttk.Button(foot, text="Close", command=self.destroy).pack(side="right")

    def _wrapped_height(self, text, width, font, pad=0):
        """Measure how tall a block of wrapped canvas text will be."""
        probe = self.canvas.create_text(0, 0, text=text or " ", width=width, font=font, anchor="nw")
        box = self.canvas.bbox(probe)
        self.canvas.delete(probe)
        return (box[3] - box[1] if box else 0) + pad

    def _render(self):
        self.canvas.delete("all")
        self.refs = []
        e = self.event
        x0 = 20
        cx = x0 + FRAME_W / 2

        desc = e.get("desc") or "(no description)"
        options = e.get("options") or []

        desc_h = self._wrapped_height(desc, FRAME_W - 90, ("Segoe UI", 10), pad=20)
        # the picture sits in the body, so the tiled section must cover both
        body_needed = PIC_H + 24 + desc_h
        mid_count = max(1, -(-body_needed // MID_H))

        y = 10
        top = image_cache.get_scaled(_asset("event_report_top_win.dds"), (FRAME_W, TOP_H))
        if top:
            self.refs.append(top)
            self.canvas.create_image(x0, y, image=top, anchor="nw")
        else:
            self.canvas.create_rectangle(x0, y, x0 + FRAME_W, y + TOP_H, fill="#2b2620", outline="#6b5a3a")

        self.canvas.create_text(
            cx, y + TITLE_BAND_Y, text=e.get("title") or f"{self.namespace}.{e['number']}",
            fill=TITLE_ON_DARK, font=("Segoe UI", 12, "bold"), width=FRAME_W - 120, justify="center",
        )
        y += TOP_H

        body_top = y
        mid = image_cache.get_scaled(_asset("event_report_tileable_midsection.dds"), (FRAME_W, MID_H))
        for i in range(mid_count):
            if mid:
                self.refs.append(mid)
                self.canvas.create_image(x0, y, image=mid, anchor="nw")
            else:
                self.canvas.create_rectangle(x0, y, x0 + FRAME_W, y + MID_H, fill="#221e19", outline="")
            y += MID_H

        pic_path = self._picture_path()
        pic = image_cache.get_scaled(pic_path, (PIC_W, PIC_H)) if pic_path else None
        pic_y = body_top + 8
        if pic:
            self.refs.append(pic)
            self.canvas.create_image(cx, pic_y, image=pic, anchor="n")
        else:
            self.canvas.create_rectangle(
                cx - PIC_W / 2, pic_y, cx + PIC_W / 2, pic_y + PIC_H,
                fill="#191512", outline="#6b5a3a",
            )
            self.canvas.create_text(
                cx, pic_y + PIC_H / 2, text=f"picture not found:\n{e.get('picture','')}",
                fill="#777", font=("Segoe UI", 9), justify="center",
            )
        self.canvas.create_rectangle(
            cx - PIC_W / 2, pic_y, cx + PIC_W / 2, pic_y + PIC_H, outline="#6b5a3a", width=2,
        )

        self.canvas.create_text(
            cx, pic_y + PIC_H + 16, text=desc, fill=BODY_TEXT, width=FRAME_W - 90,
            font=("Segoe UI", 10), justify="center", anchor="n",
        )

        bottom = image_cache.get_scaled(_asset("event_report_bottom_win.dds"), (FRAME_W, BOTTOM_H))
        if bottom:
            self.refs.append(bottom)
            self.canvas.create_image(x0, y, image=bottom, anchor="nw")
        else:
            self.canvas.create_rectangle(x0, y, x0 + FRAME_W, y + BOTTOM_H, fill="#2b2620", outline="#6b5a3a")

        opt_bg = image_cache.get_scaled(_asset("event_option_entry.dds"), (OPTION_W, OPTION_H))
        oy = y + 18
        for opt in options:
            if opt_bg:
                self.refs.append(opt_bg)
                self.canvas.create_image(cx, oy, image=opt_bg, anchor="n")
            else:
                self.canvas.create_rectangle(
                    cx - OPTION_W / 2, oy, cx + OPTION_W / 2, oy + OPTION_H,
                    fill="#332d24", outline="#8a7444",
                )
            self.canvas.create_text(
                cx, oy + OPTION_H / 2, text=opt.get("name") or "(unnamed option)",
                fill=OPTION_TEXT if opt_bg else BODY_TITLE,
                font=("Segoe UI", 10, "bold"), width=OPTION_W - 40,
            )
            oy += OPTION_H + 6

        y += BOTTOM_H
        needed = oy + 10 - (y - BOTTOM_H)
        if needed > BOTTOM_H:
            y += needed - BOTTOM_H

        self.canvas.configure(scrollregion=(0, 0, FRAME_W + 40, y + 20))

        if not options:
            self.note.config(text="This event has no options — in game it could not be dismissed.")
        else:
            self.note.config(
                text=f"{len(options)} option(s). Effects are not shown here; the preview covers "
                     "what the player sees."
            )

    def _picture_path(self):
        picture = self.event.get("picture") or ""
        if not picture:
            return None
        path = ml.resolve_texture(picture, state.mod_root, state.gfx_index)
        if path:
            return path
        # event pictures are often referenced without the GFX_ sprite wrapper
        for folder in ("event_pictures",):
            for ext in (".dds", ".png", ".tga"):
                guess = os.path.join(BASE_GAME, "gfx", folder, picture + ext)
                if os.path.isfile(guess):
                    return guess
        return None
