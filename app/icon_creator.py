"""Focus icon creator.

HOI4 goal icons are 100x88 with a bronze bevelled frame and a darkened,
slightly desaturated interior. Rather than ripping and recolouring the
game's own art, the frame here is drawn procedurally to that same recipe,
so a user can drop in any picture and get something that sits next to the
vanilla icons without clashing.
"""

import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageTk

ICON_W, ICON_H = 100, 88
CORNER = 10

FRAME_LIGHT = (206, 170, 106)
FRAME_MID = (146, 111, 60)
FRAME_DARK = (74, 55, 30)
BACKDROP = (28, 26, 23)


def register_sprite(mod_root, sprite, texture_rel):
    """Append a SpriteType to the mod's interface/zz_custom_goals.gfx.
    Returns an error message, or None on success."""
    gfx_dir = os.path.join(mod_root, "interface")
    os.makedirs(gfx_dir, exist_ok=True)
    gfx_path = os.path.join(gfx_dir, "zz_custom_goals.gfx")

    entry = f'\tSpriteType = {{\n\t\tname = "{sprite}"\n\t\ttexturefile = "{texture_rel}"\n\t}}\n'
    if os.path.isfile(gfx_path):
        with open(gfx_path, "r", encoding="utf-8-sig", errors="ignore") as f:
            existing = f.read().rstrip()
        if sprite in existing:
            return f"{sprite} is already defined in zz_custom_goals.gfx."
        if existing.endswith("}"):
            existing = existing[:-1].rstrip("\n")
        content = existing + "\n" + entry + "}\n"
    else:
        content = "spriteTypes = {\n" + entry + "}\n"

    with open(gfx_path, "w", encoding="utf-8") as f:
        f.write(content)
    return None


def _rounded_mask(size, radius):
    mask = Image.new("L", size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, size[0] - 1, size[1] - 1], radius=radius, fill=255)
    return mask


def compose_icon(source_path, saturation=0.75, brightness=0.9, vignette=True, frame=True):
    """Return a 100x88 RGBA icon built from `source_path`."""
    src = Image.open(source_path)
    src.load()
    src = src.convert("RGBA")

    # cover-fit: fill the icon box, cropping the overflow
    scale = max(ICON_W / src.width, ICON_H / src.height)
    resized = src.resize((max(1, round(src.width * scale)), max(1, round(src.height * scale))), Image.LANCZOS)
    left = (resized.width - ICON_W) // 2
    top = (resized.height - ICON_H) // 2
    art = resized.crop((left, top, left + ICON_W, top + ICON_H))

    art = ImageEnhance.Color(art).enhance(saturation)
    art = ImageEnhance.Brightness(art).enhance(brightness)

    canvas = Image.new("RGBA", (ICON_W, ICON_H), BACKDROP + (255,))
    canvas.alpha_composite(art)

    if vignette:
        glow = Image.new("L", (ICON_W, ICON_H), 0)
        ImageDraw.Draw(glow).rounded_rectangle(
            [6, 6, ICON_W - 7, ICON_H - 7], radius=CORNER, fill=255
        )
        glow = glow.filter(ImageFilter.GaussianBlur(7))
        shade = Image.new("RGBA", (ICON_W, ICON_H), (0, 0, 0, 190))
        shade.putalpha(Image.eval(glow, lambda v: 190 - int(v * 190 / 255)))
        canvas.alpha_composite(shade)

    if frame:
        draw = ImageDraw.Draw(canvas)
        draw.rounded_rectangle([0, 0, ICON_W - 1, ICON_H - 1], radius=CORNER, outline=FRAME_DARK, width=4)
        draw.rounded_rectangle([2, 2, ICON_W - 3, ICON_H - 3], radius=CORNER - 2, outline=FRAME_MID, width=2)
        draw.rounded_rectangle([3, 3, ICON_W - 4, ICON_H - 4], radius=CORNER - 3, outline=FRAME_LIGHT, width=1)
        # bevel highlight along the top edge
        draw.line([(CORNER, 4), (ICON_W - CORNER, 4)], fill=FRAME_LIGHT, width=1)

    corners = _rounded_mask((ICON_W, ICON_H), CORNER)
    out = Image.new("RGBA", (ICON_W, ICON_H), (0, 0, 0, 0))
    out.paste(canvas, (0, 0), corners)
    return out


class IconCreator(tk.Toplevel):
    """Live preview editor. On success `self.result` is the sprite name that
    was registered, ready to drop into a focus definition."""

    def __init__(self, master, mod_root, suggested_name="my_custom_focus"):
        super().__init__(master)
        self.title("Create a focus icon")
        self.resizable(False, False)
        self.mod_root = mod_root
        self.result = None
        self.source_path = None
        self._preview_ref = None
        self._build(suggested_name)
        self.grab_set()

    def _build(self, suggested_name):
        left = ttk.Frame(self, padding=12)
        left.grid(row=0, column=0, sticky="n")

        ttk.Label(left, text="Source image").grid(row=0, column=0, sticky="w")
        row = ttk.Frame(left)
        row.grid(row=1, column=0, sticky="w", pady=(2, 10))
        self.path_var = tk.StringVar()
        ttk.Entry(row, textvariable=self.path_var, width=34).pack(side="left")
        ttk.Button(row, text="Browse...", command=self._browse).pack(side="left", padx=4)

        ttk.Label(left, text="Icon name (sprite becomes GFX_goal_<name>)").grid(row=2, column=0, sticky="w")
        self.name_var = tk.StringVar(value=suggested_name)
        ttk.Entry(left, textvariable=self.name_var, width=42).grid(row=3, column=0, sticky="w", pady=(2, 10))

        self.saturation = tk.DoubleVar(value=0.75)
        self.brightness = tk.DoubleVar(value=0.9)
        self.vignette = tk.BooleanVar(value=True)
        self.frame = tk.BooleanVar(value=True)

        self._slider(left, 4, "Colour (lower = more vanilla)", self.saturation, 0.0, 1.4)
        self._slider(left, 6, "Brightness", self.brightness, 0.4, 1.4)

        ttk.Checkbutton(left, text="Darkened edges (vignette)", variable=self.vignette,
                        command=self._refresh).grid(row=8, column=0, sticky="w", pady=2)
        ttk.Checkbutton(left, text="Bronze frame", variable=self.frame,
                        command=self._refresh).grid(row=9, column=0, sticky="w", pady=2)

        ttk.Label(
            left,
            text="Saved as a 100x88 .dds into the mod's gfx/interface/goals folder,\n"
                 "and registered in interface/zz_custom_goals.gfx.",
            foreground="#888", justify="left",
        ).grid(row=10, column=0, sticky="w", pady=(10, 0))

        right = ttk.Frame(self, padding=12)
        right.grid(row=0, column=1, sticky="n")
        ttk.Label(right, text="Preview", font=("Segoe UI", 10, "bold")).pack()
        self.preview = tk.Label(right, background="#161616", width=220, height=200)
        self.preview.pack(pady=8)

        btns = ttk.Frame(self, padding=12)
        btns.grid(row=1, column=0, columnspan=2)
        ttk.Button(btns, text="Save icon", command=self._save).pack(side="left", padx=4)
        ttk.Button(btns, text="Cancel", command=self.destroy).pack(side="left", padx=4)

    def _slider(self, parent, row, label, var, lo, hi):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w")
        ttk.Scale(parent, from_=lo, to=hi, variable=var, orient="horizontal", length=280,
                  command=lambda _v: self._refresh()).grid(row=row + 1, column=0, sticky="w", pady=(0, 8))

    def _browse(self):
        path = filedialog.askopenfilename(
            title="Pick an image",
            filetypes=[("Images", "*.png *.jpg *.jpeg *.dds *.tga *.bmp *.webp"), ("All files", "*.*")],
        )
        if path:
            self.source_path = path
            self.path_var.set(path)
            self._refresh()

    def _current_icon(self):
        if not self.source_path:
            return None
        return compose_icon(
            self.source_path,
            saturation=self.saturation.get(),
            brightness=self.brightness.get(),
            vignette=self.vignette.get(),
            frame=self.frame.get(),
        )

    def _refresh(self):
        if not self.source_path:
            return
        try:
            icon = self._current_icon()
        except Exception as exc:
            self.preview.configure(image="", text=f"Cannot read image:\n{exc}")
            return
        shown = icon.resize((ICON_W * 2, ICON_H * 2), Image.NEAREST)
        self._preview_ref = ImageTk.PhotoImage(shown)
        self.preview.configure(image=self._preview_ref, text="")

    def _save(self):
        if not self.source_path:
            messagebox.showerror("No image", "Pick a source image first.")
            return
        if not self.mod_root:
            messagebox.showerror("No mod", "Load or create a mod first.")
            return

        name = self.name_var.get().strip().replace(" ", "_")
        if not name:
            messagebox.showerror("No name", "Give the icon a name.")
            return

        try:
            icon = self._current_icon()
        except Exception as exc:
            messagebox.showerror("Bad image", f"Could not process that image:\n{exc}")
            return

        out_dir = os.path.join(self.mod_root, "gfx", "interface", "goals")
        os.makedirs(out_dir, exist_ok=True)
        dds_path = os.path.join(out_dir, f"{name}.dds")
        try:
            icon.save(dds_path, "DDS")
        except Exception:
            dds_path = os.path.join(out_dir, f"{name}.png")
            icon.save(dds_path, "PNG")

        sprite = f"GFX_goal_{name}"
        rel = os.path.relpath(dds_path, self.mod_root).replace("\\", "/")
        error = register_sprite(self.mod_root, sprite, rel)
        if error:
            messagebox.showerror("Name in use", error)
            return

        self.result = {"sprite": sprite, "path": dds_path}
        self.destroy()
