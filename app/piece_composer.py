"""Compose a focus/national-spirit icon from the Ultimate-HOI4-GFX pack:
pick a hand-painted background, then stack symbol pieces on top, dragging
them into place on a zoomed preview. The output is saved and registered
exactly like the photo-based icon creator, so the sprite is immediately
usable in a focus or idea.

Pack: https://github.com/Globvs/Ultimate-HOI4-GFX (see its CREDITS.txt -
credit the pack in your mod description if you publish).
"""

import os
import glob
import tkinter as tk
from tkinter import ttk, messagebox

from PIL import Image, ImageTk

from app import theme
from app.icon_creator import register_sprite

ASSETS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "ultimate-gfx")

KINDS = {
    # target size, background folder, sprite prefix, output folder
    "focus": ((100, 88), "Focus Backgrounds", "GFX_goal_", ("gfx", "interface", "goals")),
    "spirit": ((60, 68), "National Spirit Backgrounds", "GFX_idea_", ("gfx", "interface", "ideas")),
}

PIECES_DIR = "Focus & National Spirits Pieces"
ZOOM = 3


def pack_available():
    return os.path.isdir(os.path.join(ASSETS, PIECES_DIR))


def _pngs(folder):
    return sorted(glob.glob(os.path.join(ASSETS, folder, "*.png")))


class PieceComposer(tk.Toplevel):
    """`self.result` = {"sprite", "path"} once saved."""

    def __init__(self, master, mod_root, kind="focus", suggested_name="my_custom_icon"):
        super().__init__(master)
        self.title("Compose an icon from pieces")
        self.resizable(False, False)
        self.mod_root = mod_root
        self.kind = kind
        self.target, self.bg_folder, self.prefix, self.out_folder = (
            KINDS[kind][0], KINDS[kind][1], KINDS[kind][2], KINDS[kind][3]
        )
        self.result = None

        self.bg_path = None
        # each piece: {path, x, y (centre, target coords), scale}
        self.pieces = []
        self.selected = None
        self._drag = None
        self._preview_ref = None
        self._pil_cache = {}

        self._build(suggested_name)
        self.grab_set()

    # ---- UI ----

    def _build(self, suggested_name):
        left = ttk.Frame(self, padding=10)
        left.grid(row=0, column=0, sticky="n")

        ttk.Label(left, text="Background").pack(anchor="w")
        self.bg_list = tk.Listbox(left, height=8, width=34, exportselection=False)
        self.bg_list.insert("end", "(none)")
        self._bg_paths = _pngs(self.bg_folder)
        for p in self._bg_paths:
            self.bg_list.insert("end", os.path.splitext(os.path.basename(p))[0])
        self.bg_list.selection_set(0)
        self.bg_list.pack(pady=(2, 8))
        self.bg_list.bind("<<ListboxSelect>>", lambda e: self._on_bg())

        ttk.Label(left, text="Pieces (double-click to add)").pack(anchor="w")
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
        centre.grid(row=0, column=1, sticky="n")
        tw, th = self.target
        ttk.Label(centre, text="Preview — drag pieces to place them").pack()
        self.canvas = tk.Canvas(
            centre, width=tw * ZOOM, height=th * ZOOM,
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
        self.scale_slider = ttk.Scale(
            ctrl, from_=0.2, to=2.5, variable=self.scale_var, orient="horizontal",
            length=180, command=lambda _v: self._on_scale(),
        )
        self.scale_slider.pack(side="left", padx=6)
        ttk.Button(ctrl, text="Remove", command=self._remove_selected).pack(side="left", padx=4)
        ttk.Button(ctrl, text="To front", command=self._raise_selected).pack(side="left")

        self.sel_label = ttk.Label(centre, text="No piece selected", style="Muted.TLabel")
        self.sel_label.pack(anchor="w", pady=(4, 0))

        name_row = ttk.Frame(centre)
        name_row.pack(fill="x", pady=(10, 0))
        ttk.Label(name_row, text="Icon name:").pack(side="left")
        self.name_var = tk.StringVar(value=suggested_name)
        ttk.Entry(name_row, textvariable=self.name_var, width=28).pack(side="left", padx=6)

        btns = ttk.Frame(centre)
        btns.pack(pady=10)
        ttk.Button(btns, text="Save icon", style="Accent.TButton", command=self._save).pack(side="left", padx=4)
        ttk.Button(btns, text="Cancel", command=self.destroy).pack(side="left", padx=4)

        ttk.Label(
            centre,
            text="Art from the Ultimate-HOI4-GFX community pack —\ncredit it in your mod page if you publish.",
            style="Muted.TLabel", justify="left",
        ).pack(anchor="w")

        self._render()

    def _filter_pieces(self):
        needle = self.piece_query.get().strip().lower()
        self.piece_list.delete(0, "end")
        self._filtered = [p for p in self._all_pieces if needle in os.path.basename(p).lower()]
        for p in self._filtered:
            self.piece_list.insert("end", os.path.splitext(os.path.basename(p))[0])

    # ---- composition model ----

    def _pil(self, path):
        if path not in self._pil_cache:
            im = Image.open(path).convert("RGBA")
            self._pil_cache[path] = im
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
        tw, th = self.target
        src = self._pil(path)
        # start scaled so the piece fills ~65% of the icon's smaller side
        fit = 0.65 * min(tw, th) / max(src.width, src.height)
        self.pieces.append({"path": path, "x": tw / 2, "y": th / 2, "scale": fit})
        self.selected = len(self.pieces) - 1
        self.scale_var.set(fit)
        self._render()

    def _compose(self):
        tw, th = self.target
        out = Image.new("RGBA", (tw, th), (0, 0, 0, 0))
        if self.bg_path:
            bg = self._pil(self.bg_path)
            scale = min(tw / bg.width, th / bg.height)
            bg2 = bg.resize((max(1, round(bg.width * scale)), max(1, round(bg.height * scale))), Image.LANCZOS)
            out.alpha_composite(bg2, ((tw - bg2.width) // 2, (th - bg2.height) // 2))
        for piece in self.pieces:
            src = self._pil(piece["path"])
            w = max(1, round(src.width * piece["scale"]))
            h = max(1, round(src.height * piece["scale"]))
            resized = src.resize((w, h), Image.LANCZOS)
            out.alpha_composite(resized, (round(piece["x"] - w / 2), round(piece["y"] - h / 2)))
        return out

    def _render(self):
        icon = self._compose()
        tw, th = self.target
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

    # ---- interaction ----

    def _hit(self, x, y):
        """Topmost piece whose box contains the click, in target coords."""
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

    # ---- saving ----

    def _save(self):
        if not self.mod_root:
            messagebox.showerror("No mod", "Load or create a mod first.")
            return
        if not self.bg_path and not self.pieces:
            messagebox.showerror("Empty icon", "Pick a background or add at least one piece.")
            return
        name = self.name_var.get().strip().replace(" ", "_")
        if not name:
            messagebox.showerror("No name", "Give the icon a name.")
            return

        icon = self._compose()
        out_dir = os.path.join(self.mod_root, *self.out_folder)
        os.makedirs(out_dir, exist_ok=True)
        dds_path = os.path.join(out_dir, f"{name}.dds")
        try:
            icon.save(dds_path, "DDS")
        except Exception:
            dds_path = os.path.join(out_dir, f"{name}.png")
            icon.save(dds_path, "PNG")

        sprite = f"{self.prefix}{name}"
        rel = os.path.relpath(dds_path, self.mod_root).replace("\\", "/")
        error = register_sprite(self.mod_root, sprite, rel)
        if error:
            messagebox.showerror("Name in use", error)
            return

        self.result = {"sprite": sprite, "path": dds_path}
        self.destroy()
