"""Compose a custom event picture from the Ultimate-HOI4-GFX pack's focus
backgrounds/pieces, the same drag-to-place workflow as the focus/idea icon
composer - just at the real event-picture size (210x176, the size of the
base game's own gfx/event_pictures/report_event_001.dds) and registered as
picture = "GFX_..." instead of a focus icon.

The pack has no dedicated "event background" set, so this reuses the Focus
Backgrounds/Pieces folders - the same trade-off the Portrait Creator makes
reusing portrait templates for leaders. Good enough for a distinct, on-brand
"big moment" picture without needing separate art assets.
"""

import os
import glob
import tkinter as tk
from tkinter import ttk, messagebox

from PIL import Image, ImageTk

from app import theme
from app.icon_creator import register_sprite

ASSETS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "ultimate-gfx")
TARGET = (210, 176)   # gfx/event_pictures/report_event_001.dds, the vanilla reference size
PREFIX = "GFX_report_event_"
OUT_FOLDER = ("gfx", "event_pictures")
PIECES_DIR = "Focus & National Spirits Pieces"
BG_FOLDER = "Focus Backgrounds"
ZOOM = 2


def pack_available():
    return os.path.isdir(os.path.join(ASSETS, PIECES_DIR))


def _pngs(folder):
    return sorted(glob.glob(os.path.join(ASSETS, folder, "*.png")))


class EventPictureComposer(tk.Toplevel):
    """`self.result` = {"sprite", "path"} once saved."""

    def __init__(self, master, mod_root, suggested_name="my_event_picture"):
        super().__init__(master)
        self.title("Compose an event picture")
        self.resizable(False, False)
        self.mod_root = mod_root
        self.result = None

        self.bg_path = None
        self.pieces = []   # {path, x, y (centre, target coords), scale}
        self.selected = None
        self._drag = None
        self._preview_ref = None
        self._pil_cache = {}

        self._build(suggested_name)
        self.grab_set()

    def _build(self, suggested_name):
        ttk.Label(self, text="EVENT PICTURE COMPOSER", style="PageTitle.TLabel").grid(
            row=0, column=0, columnspan=2, sticky="w", padx=10, pady=(10, 0))
        ttk.Label(
            self, text=f"Output is {TARGET[0]}x{TARGET[1]} - the same size the base game uses "
                       "for its own event pictures.",
            style="Muted.TLabel",
        ).grid(row=1, column=0, columnspan=2, sticky="w", padx=10, pady=(0, 8))

        left = ttk.Frame(self, padding=10)
        left.grid(row=2, column=0, sticky="n")

        ttk.Label(left, text="Background", style="FieldLabel.TLabel").pack(anchor="w")
        self.bg_list = tk.Listbox(left, height=8, width=34, exportselection=False)
        self.bg_list.insert("end", "(none)")
        self._bg_paths = _pngs(BG_FOLDER)
        for p in self._bg_paths:
            self.bg_list.insert("end", os.path.splitext(os.path.basename(p))[0])
        self.bg_list.selection_set(0)
        self.bg_list.pack(pady=(2, 8))
        self.bg_list.bind("<<ListboxSelect>>", lambda e: self._on_bg())

        ttk.Label(left, text="Pieces (double-click to add)", style="FieldLabel.TLabel").pack(anchor="w")
        row = ttk.Frame(left)
        row.pack(fill="x")
        self.piece_query = tk.StringVar()
        q = ttk.Entry(row, textvariable=self.piece_query, width=26)
        q.pack(side="left")
        q.bind("<KeyRelease>", lambda e: self._filter_pieces())
        ttk.Button(row, text="Clear", command=lambda: (self.piece_query.set(""), self._filter_pieces())).pack(side="left", padx=4)

        self.piece_list = tk.Listbox(left, height=12, width=34, exportselection=False)
        self.piece_list.pack(pady=(4, 8))
        self.piece_list.bind("<Double-Button-1>", lambda e: self._add_piece())
        self._all_pieces = _pngs(PIECES_DIR)
        self._filter_pieces()

        self.count_label = ttk.Label(left, text=f"{len(self._all_pieces)} pieces", style="Muted.TLabel")
        self.count_label.pack(anchor="w")

        centre = ttk.Frame(self, padding=10)
        centre.grid(row=2, column=1, sticky="n")
        tw, th = TARGET
        ttk.Label(centre, text="Preview - drag pieces to place them").pack()
        self.canvas = tk.Canvas(
            centre, width=tw * ZOOM, height=th * ZOOM,
            background=theme.CANVAS_BG, highlightthickness=1, highlightbackground=theme.EDGE,
        )
        self.canvas.pack(pady=6)
        self.canvas.bind("<Button-1>", self._on_press)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", lambda e: setattr(self, "_drag", None))

        ctrl = ttk.Frame(centre)
        ctrl.pack(fill="x")
        ttk.Label(ctrl, text="Size:").pack(side="left")
        self.scale_var = tk.DoubleVar(value=1.0)
        self.scale_slider = ttk.Scale(
            ctrl, from_=0.2, to=3.0, variable=self.scale_var, orient="horizontal",
            length=180, command=lambda _v: self._on_scale(),
        )
        self.scale_slider.pack(side="left", padx=6)
        ttk.Button(ctrl, text="Remove", command=self._remove_selected).pack(side="left", padx=4)
        ttk.Button(ctrl, text="To front", command=self._raise_selected).pack(side="left")

        self.sel_label = ttk.Label(centre, text="No piece selected", style="Muted.TLabel")
        self.sel_label.pack(anchor="w", pady=(4, 0))

        name_row = ttk.Frame(centre)
        name_row.pack(fill="x", pady=(10, 0))
        ttk.Label(name_row, text="Picture name:").pack(side="left")
        self.name_var = tk.StringVar(value=suggested_name)
        ttk.Entry(name_row, textvariable=self.name_var, width=28, font=(theme.FACE_MONO, 9)).pack(side="left", padx=6)

        btns = ttk.Frame(centre)
        btns.pack(pady=10)
        ttk.Button(btns, text="Save picture", style="Accent.TButton", command=self._save).pack(side="left", padx=4)
        ttk.Button(btns, text="Cancel", command=self.destroy).pack(side="left", padx=4)

        ttk.Label(
            centre,
            text="Art from the Ultimate-HOI4-GFX community pack -\ncredit it in your mod page if you publish.",
            style="Muted.TLabel", justify="left",
        ).pack(anchor="w")

        self._render()

    def _filter_pieces(self):
        needle = self.piece_query.get().strip().lower()
        self.piece_list.delete(0, "end")
        self._filtered = [p for p in self._all_pieces if needle in os.path.basename(p).lower()]
        for p in self._filtered:
            self.piece_list.insert("end", os.path.splitext(os.path.basename(p))[0])

    def _pil(self, path):
        if path not in self._pil_cache:
            self._pil_cache[path] = Image.open(path).convert("RGBA")
        return self._pil_cache[path]

    def _on_bg(self):
        sel = self.bg_list.curselection()
        if not sel:
            return
        self.bg_path = None if sel[0] == 0 else self._bg_paths[sel[0] - 1]
        self._render()

    def _add_piece(self):
        sel = self.piece_list.curselection()
        if not sel:
            return
        path = self._filtered[sel[0]]
        tw, th = TARGET
        src = self._pil(path)
        fit = 0.55 * min(tw, th) / max(src.width, src.height)
        self.pieces.append({"path": path, "x": tw / 2, "y": th / 2, "scale": fit})
        self.selected = len(self.pieces) - 1
        self.scale_var.set(fit)
        self._render()

    def _compose(self):
        tw, th = TARGET
        out = Image.new("RGBA", (tw, th), (0, 0, 0, 255))
        if self.bg_path:
            bg = self._pil(self.bg_path)
            scale = max(tw / bg.width, th / bg.height)   # cover, not fit - fills the whole picture
            bg2 = bg.resize((max(1, round(bg.width * scale)), max(1, round(bg.height * scale))), Image.LANCZOS)
            out.paste(bg2.convert("RGB"), ((tw - bg2.width) // 2, (th - bg2.height) // 2))
        for piece in self.pieces:
            src = self._pil(piece["path"])
            w = max(1, round(src.width * piece["scale"]))
            h = max(1, round(src.height * piece["scale"]))
            resized = src.resize((w, h), Image.LANCZOS)
            out.paste(resized, (round(piece["x"] - w / 2), round(piece["y"] - h / 2)), resized)
        return out

    def _render(self):
        icon = self._compose()
        tw, th = TARGET
        shown = icon.resize((tw * ZOOM, th * ZOOM), Image.NEAREST)
        self._preview_ref = ImageTk.PhotoImage(shown)
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, image=self._preview_ref, anchor="nw")

        if self.selected is not None and self.selected < len(self.pieces):
            piece = self.pieces[self.selected]
            src = self._pil(piece["path"])
            w = src.width * piece["scale"] * ZOOM
            h = src.height * piece["scale"] * ZOOM
            cx, cy = piece["x"] * ZOOM, piece["y"] * ZOOM
            self.canvas.create_rectangle(
                cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2,
                outline=theme.AMBER, dash=(3, 2),
            )
            self.sel_label.config(text=f"Selected: {os.path.basename(piece['path'])}")
        else:
            self.sel_label.config(text="No piece selected")

    def _hit(self, x, y):
        for i in range(len(self.pieces) - 1, -1, -1):
            piece = self.pieces[i]
            src = self._pil(piece["path"])
            w = src.width * piece["scale"] / 2
            h = src.height * piece["scale"] / 2
            if abs(x - piece["x"]) <= w and abs(y - piece["y"]) <= h:
                return i
        return None

    def _on_press(self, event):
        x, y = event.x / ZOOM, event.y / ZOOM
        hit = self._hit(x, y)
        self.selected = hit
        if hit is not None:
            self._drag = (x - self.pieces[hit]["x"], y - self.pieces[hit]["y"])
            self.scale_var.set(self.pieces[hit]["scale"])
        self._render()

    def _on_drag(self, event):
        if self._drag is None or self.selected is None:
            return
        dx, dy = self._drag
        self.pieces[self.selected]["x"] = event.x / ZOOM - dx
        self.pieces[self.selected]["y"] = event.y / ZOOM - dy
        self._render()

    def _on_scale(self):
        if self.selected is not None and self.selected < len(self.pieces):
            self.pieces[self.selected]["scale"] = self.scale_var.get()
            self._render()

    def _remove_selected(self):
        if self.selected is not None and self.selected < len(self.pieces):
            del self.pieces[self.selected]
            self.selected = None
            self._render()

    def _raise_selected(self):
        if self.selected is not None and self.selected < len(self.pieces):
            self.pieces.append(self.pieces.pop(self.selected))
            self.selected = len(self.pieces) - 1
            self._render()

    def _save(self):
        if not self.mod_root:
            messagebox.showerror("No mod", "Load or create a mod first.")
            return
        if not self.bg_path and not self.pieces:
            messagebox.showerror("Empty picture", "Pick a background or add at least one piece.")
            return
        name = self.name_var.get().strip().replace(" ", "_")
        if not name:
            messagebox.showerror("No name", "Give the picture a name.")
            return

        image = self._compose()
        out_dir = os.path.join(self.mod_root, *OUT_FOLDER)
        os.makedirs(out_dir, exist_ok=True)
        dds_path = os.path.join(out_dir, f"{name}.dds")
        try:
            image.save(dds_path, "DDS")
        except Exception:
            dds_path = os.path.join(out_dir, f"{name}.png")
            image.save(dds_path, "PNG")

        sprite = f"{PREFIX}{name}"
        rel = os.path.relpath(dds_path, self.mod_root).replace("\\", "/")
        error = register_sprite(self.mod_root, sprite, rel)
        if error:
            messagebox.showerror("Name in use", error)
            return

        self.result = {"sprite": sprite, "path": dds_path}
        self.destroy()
