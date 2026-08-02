"""Leader portrait creator: the pack's hand-painted portrait backdrops with
the user's photo layered on top, draggable and scalable, saved at the exact
size HOI4 expects (156x210 for leaders, 65x67 for ministers/advisors).

A photo with a transparent background (a cut-out person) sits perfectly on
the painted backdrop; a plain rectangular photo can simply be scaled up to
cover the whole frame instead.
"""

import os
import glob
import tempfile
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from PIL import Image, ImageTk

from app import theme

ASSETS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                      "assets", "ultimate-gfx", "Portrait Templates")

SIZES = {
    "leader": (156, 210),
    "minister": (65, 67),
}
ZOOM = {"leader": 2, "minister": 5}


def pack_available():
    return os.path.isdir(ASSETS)


def _backgrounds(kind):
    needle = "Leader" if kind == "leader" else "Minister"
    return sorted(p for p in glob.glob(os.path.join(ASSETS, "*.png"))
                  if needle.lower() in os.path.basename(p).lower())


class PortraitCreator(tk.Toplevel):
    """`self.result` is the path of the saved PNG once done."""

    def __init__(self, master, kind="leader"):
        super().__init__(master)
        self.title("Create a portrait")
        self.resizable(False, False)
        self.kind = kind
        self.target = SIZES[kind]
        self.zoom = ZOOM[kind]
        self.result = None

        self.bg_path = None
        self.photo_path = None
        # photo placement, centre in target coords
        self.px, self.py = self.target[0] / 2, self.target[1] / 2
        self.scale = 1.0
        self._drag = None
        self._preview_ref = None
        self._pil_cache = {}

        self._build()
        self.grab_set()

    def _build(self):
        left = ttk.Frame(self, padding=10)
        left.grid(row=0, column=0, sticky="n")

        ttk.Label(left, text="Backdrop").pack(anchor="w")
        self.bg_list = tk.Listbox(left, height=6, width=34, exportselection=False)
        self.bg_list.insert("end", "(none)")
        self._bg_paths = _backgrounds(self.kind)
        for p in self._bg_paths:
            self.bg_list.insert("end", os.path.splitext(os.path.basename(p))[0])
        self.bg_list.selection_set(1 if self._bg_paths else 0)
        self.bg_list.pack(pady=(2, 10))
        self.bg_list.bind("<<ListboxSelect>>", lambda e: self._on_bg())

        ttk.Button(left, text="Choose photo...", command=self._pick_photo).pack(anchor="w")
        self.photo_label = ttk.Label(left, text="No photo yet", style="Muted.TLabel", wraplength=220)
        self.photo_label.pack(anchor="w", pady=(4, 10))

        ttk.Label(
            left,
            text="A photo with transparent background\n(a cut-out) blends best. A normal photo\n"
                 "can be scaled to cover the whole frame.",
            style="Muted.TLabel", justify="left",
        ).pack(anchor="w")

        centre = ttk.Frame(self, padding=10)
        centre.grid(row=0, column=1, sticky="n")
        tw, th = self.target
        ttk.Label(centre, text="Drag the photo to place it").pack()
        self.canvas = tk.Canvas(
            centre, width=tw * self.zoom, height=th * self.zoom,
            background=theme.CANVAS_BG, highlightthickness=1, highlightbackground=theme.BRONZE,
        )
        self.canvas.pack(pady=6)
        self.canvas.bind("<Button-1>", self._on_press)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", lambda e: setattr(self, "_drag", None))

        ctrl = ttk.Frame(centre)
        ctrl.pack(fill="x")
        ttk.Label(ctrl, text="Size:").pack(side="left")
        self.scale_var = tk.DoubleVar(value=1.0)
        ttk.Scale(ctrl, from_=0.2, to=3.0, variable=self.scale_var, orient="horizontal",
                  length=200, command=lambda _v: self._on_scale()).pack(side="left", padx=6)

        btns = ttk.Frame(centre)
        btns.pack(pady=10)
        ttk.Button(btns, text="Use this portrait", style="Accent.TButton", command=self._save).pack(side="left", padx=4)
        ttk.Button(btns, text="Cancel", command=self.destroy).pack(side="left", padx=4)

        self._on_bg()

    # ---- model ----

    def _pil(self, path):
        if path not in self._pil_cache:
            self._pil_cache[path] = Image.open(path).convert("RGBA")
        return self._pil_cache[path]

    def _on_bg(self):
        sel = self.bg_list.curselection()
        if sel:
            self.bg_path = None if sel[0] == 0 else self._bg_paths[sel[0] - 1]
        self._render()

    def _pick_photo(self):
        path = filedialog.askopenfilename(
            title="Pick a photo",
            filetypes=[("Images", "*.png *.jpg *.jpeg *.webp *.bmp *.dds *.tga"), ("All files", "*.*")],
        )
        if not path:
            return
        self.photo_path = path
        self.photo_label.config(text=os.path.basename(path))
        src = self._pil(path)
        tw, th = self.target
        # start so the photo's height matches the frame
        self.scale = th / src.height
        self.scale_var.set(self.scale)
        self.px, self.py = tw / 2, th / 2
        self._render()

    def _compose(self):
        tw, th = self.target
        out = Image.new("RGBA", (tw, th), (30, 28, 24, 255))
        if self.bg_path:
            bg = self._pil(self.bg_path)
            out.alpha_composite(bg.resize((tw, th), Image.LANCZOS))
        if self.photo_path:
            src = self._pil(self.photo_path)
            w = max(1, round(src.width * self.scale))
            h = max(1, round(src.height * self.scale))
            resized = src.resize((w, h), Image.LANCZOS)
            layer = Image.new("RGBA", (tw, th), (0, 0, 0, 0))
            layer.alpha_composite(resized, (round(self.px - w / 2), round(self.py - h / 2)))
            out.alpha_composite(layer)
        return out

    def _render(self):
        icon = self._compose()
        tw, th = self.target
        shown = icon.resize((tw * self.zoom, th * self.zoom), Image.NEAREST)
        self._preview_ref = ImageTk.PhotoImage(shown)
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, image=self._preview_ref, anchor="nw")

    # ---- interaction ----

    def _on_press(self, event):
        if not self.photo_path:
            return
        self._drag = (event.x / self.zoom - self.px, event.y / self.zoom - self.py)

    def _on_drag(self, event):
        if self._drag is None:
            return
        dx, dy = self._drag
        self.px = event.x / self.zoom - dx
        self.py = event.y / self.zoom - dy
        self._render()

    def _on_scale(self):
        self.scale = self.scale_var.get()
        self._render()

    # ---- saving ----

    def _save(self):
        if not self.photo_path and not self.bg_path:
            messagebox.showerror("Empty portrait", "Pick a backdrop or a photo first.", parent=self)
            return
        out = self._compose().convert("RGBA")
        fd, path = tempfile.mkstemp(suffix=".png", prefix="portrait_")
        os.close(fd)
        out.save(path, "PNG")
        self.result = path
        self.destroy()
