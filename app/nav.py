"""The chrome the user sees on every screen: the title bar across the top
and the navigation rail down the left.

Both are canvases rather than frames full of ttk widgets. A ttk.Button can't
sit on a textured panel without punching a flat rectangle through it, and it
can't show a gold selection bar or an icon that recolours on hover. Drawing
the rail by hand costs about a hundred lines and buys a navigation that looks
like it belongs to the game instead of to Tk.
"""

import tkinter as tk

from app import chrome
from app import glyphs
from app import theme

RAIL_WIDTH = 208
ITEM_HEIGHT = 34
SECTION_GAP = 18
HEADER_HEIGHT = 58


class HeaderBar(tk.Canvas):
    """Title strip: wordmark on the left, open mod on the right."""

    def __init__(self, master, on_home):
        super().__init__(master, height=HEADER_HEIGHT, highlightthickness=0,
                         background=theme.BG, bd=0)
        self.on_home = on_home
        self.mod_text = ""
        self._home_ids = []
        self._home_hot = False
        self.bind("<Configure>", lambda e: self._render())
        self.bind("<Motion>", self._on_motion)
        self.bind("<Button-1>", self._on_click)
        self.bind("<Leave>", lambda e: self._set_home_hot(False))

    def set_mod(self, text):
        self.mod_text = text
        self._render()

    def flash(self, text, ms=2600):
        """A transient message where the mod name normally sits - for
        one-off confirmations (undo, save) that don't deserve a dialog."""
        self._flash_text = text
        self._render()
        self.after(ms, lambda: (setattr(self, "_flash_text", None), self._render()))

    # ---- geometry ----

    def _home_box(self):
        return 14, 14, 104, HEADER_HEIGHT - 14

    def _in_home(self, x, y):
        x0, y0, x1, y1 = self._home_box()
        return x0 <= x <= x1 and y0 <= y <= y1

    # ---- painting ----

    def _render(self):
        width = max(self.winfo_width(), 1)
        self.delete("all")
        chrome.paint(self, "header", width, HEADER_HEIGHT, tint=theme.CHROME_TINT)

        x0, y0, x1, y1 = self._home_box()
        hot = self._home_hot
        button = chrome.photo("button", x1 - x0, y1 - y0)
        if button is not None:
            self._button_photo = button
            self.create_image(x0, y0, image=button, anchor="nw")
        else:
            self.create_rectangle(x0, y0, x1, y1, fill=theme.RAISED, outline=theme.BRONZE)
        self.create_text((x0 + x1) / 2, (y0 + y1) / 2, text="◀  HOME",
                         fill=theme.GOLD if hot else theme.TEXT,
                         font=(theme.FACE_UI, 9, "bold"))

        self.create_text(x1 + 22, HEADER_HEIGHT / 2 - 7, anchor="w",
                         text="HOI4  MOD  MAKER", fill=theme.GOLD,
                         font=(theme.FACE_DISPLAY, 15, "bold"))
        self.create_text(x1 + 23, HEADER_HEIGHT / 2 + 12, anchor="w",
                         text="focus trees · events · decisions · map",
                         fill=theme.MUTED, font=(theme.FACE_UI, 8))

        flash_text = getattr(self, "_flash_text", None)
        if flash_text:
            self.create_text(width - 18, HEADER_HEIGHT / 2, anchor="e",
                             text=flash_text, fill=theme.GREEN,
                             font=(theme.FACE_DISPLAY, 12, "bold"))
        elif self.mod_text:
            self.create_text(width - 18, HEADER_HEIGHT / 2, anchor="e",
                             text=self.mod_text, fill=theme.TEXT,
                             font=(theme.FACE_DISPLAY, 12))
        self.create_line(0, HEADER_HEIGHT - 1, width, HEADER_HEIGHT - 1,
                         fill=theme.GOLD_DIM)

    # ---- interaction ----

    def _set_home_hot(self, hot):
        if hot != self._home_hot:
            self._home_hot = hot
            self.configure(cursor="hand2" if hot else "")
            self._render()

    def _on_motion(self, event):
        self._set_home_hot(self._in_home(event.x, event.y))

    def _on_click(self, event):
        if self._in_home(event.x, event.y):
            self.on_home()


class NavRail(tk.Canvas):
    """Grouped navigation. `sections` is [(title, [(key, label), ...])]."""

    def __init__(self, master, sections, on_select):
        super().__init__(master, width=RAIL_WIDTH, highlightthickness=0,
                         background=theme.BG, bd=0)
        self.sections = sections
        self.on_select = on_select
        self.current = None
        self.hover = None
        self._rows = {}          # key -> (top, bottom)
        self.bind("<Configure>", lambda e: self._render())
        self.bind("<Motion>", self._on_motion)
        self.bind("<Button-1>", self._on_click)
        self.bind("<Leave>", lambda e: self._set_hover(None))
        self.bind("<MouseWheel>", self._on_wheel)

    def select(self, key):
        if key != self.current:
            self.current = key
            self._render()

    # ---- painting ----

    def _layout(self):
        """Walk the sections once, recording where every row lands."""
        self._rows = {}
        y = 14
        plan = []
        for title, entries in self.sections:
            plan.append(("section", (title, len(entries)), y))
            y += SECTION_GAP
            for key, label in entries:
                self._rows[key] = (y, y + ITEM_HEIGHT)
                plan.append(("item", (key, label), y))
                y += ITEM_HEIGHT + 2
            y += 10
        return plan, y

    def _render(self):
        view_height = max(self.winfo_height(), 1)
        plan, content_height = self._layout()
        height = max(view_height, content_height + 14)
        self.delete("all")
        chrome.paint(self, "rail", RAIL_WIDTH, height, tint=theme.CHROME_TINT)
        self.create_line(RAIL_WIDTH - 1, 0, RAIL_WIDTH - 1, height, fill=theme.EDGE)
        self.configure(scrollregion=(0, 0, RAIL_WIDTH, height))

        for kind, payload, y in plan:
            if kind == "section":
                title, count = payload
                self.create_text(16, y + 6, anchor="w", text=title,
                                 fill=theme.GOLD_DIM, font=(theme.FACE_UI, 8, "bold"))
                self.create_text(RAIL_WIDTH - 16, y + 6, anchor="e", text=str(count),
                                 fill=theme.MUTED, font=(theme.FACE_MONO, 8))
                self.create_line(16, y + 16, RAIL_WIDTH - 16, y + 16, fill=theme.EDGE)
            else:
                self._render_item(*payload, y=y)

    def _render_item(self, key, label, y):
        selected = key == self.current
        hovered = key == self.hover and not selected

        if selected:
            self.create_rectangle(6, y, RAIL_WIDTH - 8, y + ITEM_HEIGHT,
                                  fill=theme.SELECTED, outline="")
            self.create_rectangle(6, y, 9, y + ITEM_HEIGHT, fill=theme.GOLD, outline="")
        elif hovered:
            self.create_rectangle(6, y, RAIL_WIDTH - 8, y + ITEM_HEIGHT,
                                  fill=theme.HOVER, outline="")

        colour = theme.GOLD if selected else (theme.TEXT if hovered else theme.MUTED_BRIGHT)
        glyphs.draw(self, key, 20, y + (ITEM_HEIGHT - 16) / 2, 16, colour)
        self.create_text(48, y + ITEM_HEIGHT / 2, anchor="w", text=label,
                         fill=theme.TEXT if (selected or hovered) else theme.MUTED_BRIGHT,
                         font=(theme.FACE_UI, 10, "bold" if selected else "normal"))

    # ---- interaction ----

    def _key_at(self, y):
        for key, (top, bottom) in self._rows.items():
            if top <= y <= bottom:
                return key
        return None

    def _set_hover(self, key):
        if key != self.hover:
            self.hover = key
            self.configure(cursor="hand2" if key else "")
            self._render()

    def _on_motion(self, event):
        self._set_hover(self._key_at(self.canvasy(event.y)))

    def _on_click(self, event):
        key = self._key_at(self.canvasy(event.y))
        if key:
            self.on_select(key)

    def _on_wheel(self, event):
        self.yview_scroll(-1 * (event.delta // 120), "units")
