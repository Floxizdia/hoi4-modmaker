"""Flag Creator tab: procedural flag patterns (tricolors, cross, canton...)
plus an optional emblem image you supply, rendered at the exact large/
medium/small sizes HOI4 expects - gfx/flags/."""

import os
import tkinter as tk
from tkinter import ttk, messagebox, colorchooser, filedialog

from PIL import Image, ImageTk

from app.state import state
from app import flag_creator as fc
from app import theme, ui_kit


class FlagTab(ttk.Frame):
    def __init__(self, master):
        super().__init__(master, padding=12)
        self._colors = [(200, 20, 20), (255, 255, 255), (10, 10, 10)]
        self._emblem_path = ""
        self._preview_img = None
        self._build()
        state.subscribe(self.on_mod_changed)

    def _build(self):
        self.header = ui_kit.PageHeader(
            self, "Flags",
            "Draws a country flag (tricolor, cross, canton...) from colours you pick, optionally layers your own emblem PNG on top, and writes the real large/medium/small .tga sizes the game expects.", help_key="flags")
        ttk.Label(
            self, text="No reusable flag-parts library ships with the game or the bundled asset pack, so "
                       "this draws the pattern itself with the colors you pick, then layers an emblem PNG "
                       "you supply on top — output at the real large/medium/small sizes (82x52 / 41x26 / 10x7).",
            style="Muted.TLabel", wraplength=980, justify="left",
        ).pack(anchor="w", pady=(0, 8))

        body = ttk.Frame(self)
        body.pack(fill="both", expand=True)

        left = ttk.Frame(body)
        left.pack(side="left", fill="both", expand=True, padx=(0, 20))

        row = ttk.Frame(left)
        row.pack(fill="x", pady=2)
        ttk.Label(row, text="Country tag").pack(side="left")
        self.tag_var = tk.StringVar()
        ttk.Entry(row, textvariable=self.tag_var, width=8).pack(side="left", padx=(4, 16))
        ttk.Label(row, text="Ideology suffix").pack(side="left")
        self.ideology_var = tk.StringVar(value="")
        ttk.Combobox(row, textvariable=self.ideology_var, state="readonly", width=14,
                     values=fc.IDEOLOGY_SUFFIXES).pack(side="left", padx=4)

        row2 = ttk.Frame(left)
        row2.pack(fill="x", pady=(8, 2))
        ttk.Label(row2, text="Pattern").pack(side="left")
        self.pattern_var = tk.StringVar(value="horizontal_tricolor")
        pattern_combo = ttk.Combobox(row2, textvariable=self.pattern_var, state="readonly", width=20,
                                      values=fc.PATTERNS)
        pattern_combo.pack(side="left", padx=4)
        pattern_combo.bind("<<ComboboxSelected>>", lambda e: self._update_preview())

        ttk.Label(left, text="Colors (pattern uses as many as it needs)",
                  font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(10, 2))
        self.color_swatches = []
        color_row = ttk.Frame(left)
        color_row.pack(fill="x")
        for i in range(3):
            btn = tk.Button(color_row, width=6, height=2, command=lambda i=i: self._pick_color(i))
            btn.pack(side="left", padx=(0, 8))
            self.color_swatches.append(btn)
        self._refresh_swatches()

        row3 = ttk.Frame(left)
        row3.pack(fill="x", pady=(10, 2))
        ttk.Label(row3, text="Emblem (optional PNG, transparent background)").pack(side="left")
        ttk.Button(row3, text="Browse...", command=self._pick_emblem).pack(side="left", padx=6)
        self.emblem_lbl = ttk.Label(left, text="No emblem selected.", style="Muted.TLabel")
        self.emblem_lbl.pack(anchor="w")

        ttk.Button(left, text="Update Preview", command=self._update_preview).pack(anchor="w", pady=(10, 4))
        ttk.Button(left, text="Create Flag", style="Accent.TButton", command=self._create).pack(anchor="w", pady=4)
        self.status = ttk.Label(left, text="", style="Status.TLabel", wraplength=560, justify="left")
        self.status.pack(anchor="w")

        right = ttk.Frame(body, width=260)
        right.pack(side="left", fill="y")
        right.pack_propagate(False)
        ttk.Label(right, text="Preview (large, 4x)", font=("Segoe UI", 10, "bold")).pack(anchor="w")
        self.preview_canvas = tk.Canvas(right, width=82 * 4, height=52 * 4, highlightthickness=1,
                                         highlightbackground="#555")
        self.preview_canvas.pack(anchor="w", pady=6)

        self._update_preview()
        self.on_mod_changed()

    def _refresh_swatches(self):
        for btn, rgb in zip(self.color_swatches, self._colors):
            hex_c = "#%02x%02x%02x" % rgb
            btn.config(bg=hex_c, activebackground=hex_c)

    def _pick_color(self, i):
        rgb, hex_c = colorchooser.askcolor(color="#%02x%02x%02x" % self._colors[i])
        if rgb is None:
            return
        self._colors[i] = tuple(int(c) for c in rgb)
        self._refresh_swatches()
        self._update_preview()

    def _pick_emblem(self):
        path = filedialog.askopenfilename(filetypes=[("PNG image", "*.png"), ("All files", "*.*")])
        if not path:
            return
        self._emblem_path = path
        self.emblem_lbl.config(text=os.path.basename(path))
        self._update_preview()

    def _update_preview(self):
        im = fc._draw_pattern(self.pattern_var.get(), fc.LARGE_SIZE, self._colors).convert("RGBA")
        if self._emblem_path and os.path.isfile(self._emblem_path):
            try:
                emblem = Image.open(self._emblem_path).convert("RGBA")
                target_h = int(fc.LARGE_SIZE[1] * 0.7)
                ratio = target_h / emblem.height
                target_w = max(1, int(emblem.width * ratio))
                emblem = emblem.resize((target_w, target_h), Image.LANCZOS)
                pos = ((fc.LARGE_SIZE[0] - target_w) // 2, (fc.LARGE_SIZE[1] - target_h) // 2)
                im.alpha_composite(emblem, pos)
            except Exception:
                pass
        big = im.resize((fc.LARGE_SIZE[0] * 4, fc.LARGE_SIZE[1] * 4), Image.NEAREST)
        self._preview_img = ImageTk.PhotoImage(big)
        self.preview_canvas.delete("all")
        self.preview_canvas.create_image(0, 0, anchor="nw", image=self._preview_img)

    def on_mod_changed(self):
        if state.is_loaded:
            self.header.set_status(True, state.mod_name)
        else:
            self.header.set_status(False, "no mod open")

    def on_show(self):
        self.on_mod_changed()

    def _create(self):
        if not state.is_loaded:
            messagebox.showerror("No mod", "Open or create a mod first.")
            return
        tag = self.tag_var.get().strip().upper()
        if len(tag) < 2:
            messagebox.showerror("Missing info", "Enter a country tag (e.g. GKL).")
            return

        try:
            paths = fc.create_flag(
                state.mod_root, tag=tag, ideology=self.ideology_var.get(), pattern=self.pattern_var.get(),
                colors=self._colors, emblem_path=self._emblem_path or None,
            )
        except Exception as exc:
            messagebox.showerror("Failed", f"Flag creation failed:\n{exc}")
            return

        self.status.config(text="Created:\n" + "\n".join(paths), foreground=theme.GREEN)
