"""Ideologies tab: define a brand-new ideology group (fascism/democratic/
communism are the vanilla three) with its own sub-ideologies, color and
icon - the same way the Country tab creates a new tag."""

import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, colorchooser

from app.state import state
from app import ideology_creator
from app import mod_export
from app import theme, ui_kit


class IdeologyTab(ttk.Frame):
    def __init__(self, master):
        super().__init__(master, padding=12)
        self.icon_path = None
        self.color = (140, 40, 40)
        self.sub_rows = []
        self._build()
        state.subscribe(self.on_mod_changed)

    def _build(self):
        self.header = ui_kit.PageHeader(
            self, "Ideologies",
            "Define a custom ideology or sub-ideology (beyond the base game's four) with its own colour, icon and the political parties that use it.", help_key="ideology")

        body = ttk.Frame(self)
        body.pack(fill="both", expand=True)

        row = 0
        ttk.Label(body, text="Ideology id (lowercase, no spaces)").grid(row=row, column=0, sticky="w", pady=4)
        self.id_var = tk.StringVar()
        ttk.Entry(body, textvariable=self.id_var, width=24).grid(row=row, column=1, sticky="w", padx=8)
        self.id_hint = ttk.Label(body, text="", style="Muted.TLabel")
        self.id_hint.grid(row=row, column=2, columnspan=2, sticky="w")
        self.id_var.trace_add("write", lambda *_: self._check_id())
        row += 1

        ttk.Label(body, text="Display name").grid(row=row, column=0, sticky="w", pady=4)
        self.name_var = tk.StringVar()
        ttk.Entry(body, textvariable=self.name_var, width=32).grid(row=row, column=1, columnspan=2, sticky="w", padx=8)
        row += 1

        ttk.Label(body, text="Colour").grid(row=row, column=0, sticky="w", pady=4)
        self.color_btn = tk.Button(body, width=8, command=self._pick_color,
                                    bg="#8c2828", activebackground="#8c2828", relief="flat")
        self.color_btn.grid(row=row, column=1, sticky="w", padx=8)
        row += 1

        ttk.Label(body, text="Icon (24-48px, square)").grid(row=row, column=0, sticky="w", pady=4)
        iframe = ttk.Frame(body)
        iframe.grid(row=row, column=1, columnspan=3, sticky="w", padx=8)
        ttk.Button(iframe, text="Browse...", command=self._pick_icon).pack(side="left")
        self.icon_label = ttk.Label(iframe, text="(optional)", style="Muted.TLabel")
        self.icon_label.pack(side="left", padx=6)
        row += 1

        self.boost_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(body, text="Can be boosted (political power spending unlocks it faster)",
                         variable=self.boost_var).grid(row=row, column=0, columnspan=3, sticky="w", pady=(4, 0))
        row += 1

        ttk.Separator(body).grid(row=row, column=0, columnspan=4, sticky="we", pady=8)
        row += 1
        ttk.Label(body, text="Sub-ideologies (ruling parties)", font=("Segoe UI", 10, "bold")).grid(
            row=row, column=0, columnspan=4, sticky="w")
        row += 1
        ttk.Label(
            body, text="Each row becomes a selectable party, e.g. vanilla fascism has despotism/plutocratic/etc.\n"
                       "Need at least one.",
            style="Muted.TLabel", justify="left",
        ).grid(row=row, column=0, columnspan=4, sticky="w", pady=(0, 4))
        row += 1

        self.sub_frame = ttk.Frame(body)
        self.sub_frame.grid(row=row, column=0, columnspan=4, sticky="w")
        row += 1
        ttk.Button(body, text="+ Add sub-ideology", command=self._add_sub_row).grid(
            row=row, column=0, sticky="w", pady=(2, 8))
        row += 1

        ttk.Button(body, text="Create Ideology", style="Accent.TButton",
                   command=self._create).grid(row=row, column=0, columnspan=2, sticky="w", pady=10)
        row += 1

        self.status = ttk.Label(body, text="", style="Status.TLabel", wraplength=900, justify="left")
        self.status.grid(row=row, column=0, columnspan=4, sticky="w")
        row += 1

        ttk.Label(
            body,
            text="Writes common/ideologies, localisation, and (if picked) the icon + GFX sprite into the open\n"
                 "mod. Reopen the mod (or restart) for the new ideology to show up in the Country tab's dropdown.\n"
                 "Party popularity for a country using this ideology is set from the Country tab or by editing\n"
                 "the country's history file directly.",
            style="Muted.TLabel", justify="left",
        ).grid(row=row, column=0, columnspan=4, sticky="w", pady=(10, 0))

        self._add_sub_row()
        self._add_sub_row()
        self.on_mod_changed()

    # ---- sub-ideology rows ----

    def _add_sub_row(self):
        i = len(self.sub_rows)
        r = ttk.Frame(self.sub_frame)
        r.grid(row=i, column=0, sticky="w", pady=2)
        ttk.Label(r, text="id:").pack(side="left")
        id_var = tk.StringVar()
        ttk.Entry(r, textvariable=id_var, width=18).pack(side="left", padx=(2, 10))
        ttk.Label(r, text="name:").pack(side="left")
        name_var = tk.StringVar()
        ttk.Entry(r, textvariable=name_var, width=24).pack(side="left", padx=2)
        remove_btn = ttk.Button(r, text="x", width=2, command=lambda: self._remove_sub_row(r))
        remove_btn.pack(side="left", padx=6)
        self.sub_rows.append((r, id_var, name_var))

    def _remove_sub_row(self, frame):
        self.sub_rows = [row for row in self.sub_rows if row[0] is not frame]
        frame.destroy()
        for i, (r, _, _) in enumerate(self.sub_rows):
            r.grid(row=i, column=0, sticky="w", pady=2)

    # ---- helpers ----

    def on_mod_changed(self):
        if state.is_loaded:
            self.header.set_status(True, state.mod_name)
            self._known_ids = None
        else:
            self.header.set_status(False, "no mod open")

    def _check_id(self):
        gid = self.id_var.get().strip().lower()
        if not gid or not gid.replace("_", "").isalnum() or not gid[0].isalpha():
            self.id_hint.config(text="lowercase letters/digits/underscore, starts with a letter",
                                 foreground=theme.MUTED)
            return
        if gid in ideology_creator.VANILLA_GROUPS:
            self.id_hint.config(text=f"{gid} is a vanilla ideology!", foreground=theme.RED)
            return
        if not state.is_loaded:
            return
        if getattr(self, "_known_ids", None) is None:
            self._known_ids = ideology_creator.existing_group_ids(state.mod_root)
        if gid in self._known_ids:
            self.id_hint.config(text=f"{gid} already exists in this mod!", foreground=theme.RED)
        else:
            self.id_hint.config(text=f"{gid} is free ✓", foreground=theme.GREEN)

    def _pick_color(self):
        rgb, _hex = colorchooser.askcolor(color=self.color, title="Ideology colour")
        if rgb:
            self.color = tuple(int(v) for v in rgb)
            hexcode = "#%02x%02x%02x" % self.color
            self.color_btn.configure(bg=hexcode, activebackground=hexcode)

    def _pick_icon(self):
        path = filedialog.askopenfilename(
            title="Pick an icon image", filetypes=[("Images", "*.png *.jpg *.jpeg *.bmp *.dds *.tga"), ("All", "*.*")],
        )
        if path:
            self.icon_path = path
            self.icon_label.config(text=os.path.basename(path))

    # ---- create ----

    def _create(self):
        if not state.is_loaded:
            messagebox.showerror("No mod", "Open or create a mod first.")
            return
        gid = self.id_var.get().strip().lower()
        name = self.name_var.get().strip()
        if not gid or not gid.replace("_", "").isalnum() or not gid[0].isalpha() or not name:
            messagebox.showerror("Missing info", "A valid id and a display name are required.")
            return
        if gid in ideology_creator.VANILLA_GROUPS:
            messagebox.showerror("Reserved id", f"'{gid}' is one of the vanilla ideologies.")
            return
        if getattr(self, "_known_ids", None) is None:
            self._known_ids = ideology_creator.existing_group_ids(state.mod_root)
        if gid in self._known_ids:
            messagebox.showerror("Id taken", f"'{gid}' already exists in this mod.")
            return

        subs = []
        for _, id_var, name_var in self.sub_rows:
            sid = id_var.get().strip().lower()
            sname = name_var.get().strip()
            if sid and sname:
                subs.append((sid, sname))
        if not subs:
            messagebox.showerror("No sub-ideologies", "Add at least one sub-ideology (id + name).")
            return
        sub_ids = [s[0] for s in subs]
        if len(sub_ids) != len(set(sub_ids)):
            messagebox.showerror("Duplicate id", "Sub-ideology ids must be unique.")
            return

        try:
            created = ideology_creator.create_group(
                state.mod_root, group_id=gid, display_name=name, color=self.color,
                can_be_boosted=self.boost_var.get(), sub_ideologies=subs, icon_path=self.icon_path,
            )
            mod_export.record_created(state.mod_root, [p for p in created if os.path.isfile(str(p))])
        except Exception as exc:
            messagebox.showerror("Failed", f"Ideology creation failed:\n{exc}")
            return

        self._known_ids.add(gid)
        state.add_loc(gid, name)
        for sid, sname in subs:
            state.add_loc(sid, sname)
        state.content_changed()
        self.status.config(
            text=f"Created ideology '{name}' ({gid}) with {len(subs)} sub-ideologies — {len(created)} files written."
        )
