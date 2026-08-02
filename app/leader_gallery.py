"""Leader gallery: pick a country tag and see every character that country
has, as a grid of portraits. From here the user can add a brand new leader
(written to a separate additions file) or swap an existing leader's portrait.
"""

import os
import shutil
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from PIL import Image

from app import mod_loader as ml
from app import image_cache
from app import portrait_creator
from app import theme

CARD_W = 130
COLUMNS = 6


class NewLeaderDialog(tk.Toplevel):
    def __init__(self, master, tag):
        super().__init__(master)
        self.title(f"New Leader for {tag}")
        self.result = None
        self.tag = tag
        self.resizable(False, False)
        self._build()
        self.grab_set()

    def _build(self):
        ttk.Label(self, text="Character id (no spaces)").grid(row=0, column=0, sticky="w", padx=8, pady=4)
        self.id_var = tk.StringVar(value=f"{self.tag}_")
        ttk.Entry(self, textvariable=self.id_var, width=40).grid(row=0, column=1, padx=8, pady=4)

        ttk.Label(self, text="Display name").grid(row=1, column=0, sticky="w", padx=8, pady=4)
        self.name_var = tk.StringVar()
        ttk.Entry(self, textvariable=self.name_var, width=40).grid(row=1, column=1, padx=8, pady=4)

        ttk.Label(self, text="Ideology").grid(row=2, column=0, sticky="w", padx=8, pady=4)
        self.ideology_var = tk.StringVar(value="despotism")
        ttk.Combobox(
            self, textvariable=self.ideology_var, width=37,
            values=["despotism", "oligarchism", "conservatism", "liberalism", "socialism",
                    "fascism", "nazism", "marxism", "leninism", "stalinism", "anarchist_communism"],
        ).grid(row=2, column=1, padx=8, pady=4)

        ttk.Label(self, text="Portrait image").grid(row=3, column=0, sticky="w", padx=8, pady=4)
        frame = ttk.Frame(self)
        frame.grid(row=3, column=1, sticky="w", padx=8, pady=4)
        self.portrait_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.portrait_var, width=24).pack(side="left")
        ttk.Button(frame, text="Browse...", command=self._browse).pack(side="left", padx=3)
        ttk.Button(frame, text="Create...", command=self._create_portrait).pack(side="left", padx=3)

        ttk.Label(
            self,
            text="The portrait is copied into the mod's gfx/leaders folder.\n"
                 "HOI4 expects roughly 156x210 for large leader portraits.",
            style="Muted.TLabel",
        ).grid(row=4, column=0, columnspan=2, sticky="w", padx=8, pady=(4, 0))

        btns = ttk.Frame(self)
        btns.grid(row=5, column=0, columnspan=2, pady=10)
        ttk.Button(btns, text="Create", command=self._save).pack(side="left", padx=4)
        ttk.Button(btns, text="Cancel", command=self.destroy).pack(side="left", padx=4)

    def _browse(self):
        path = filedialog.askopenfilename(
            title="Pick a portrait image",
            filetypes=[("Images", "*.png *.dds *.tga *.jpg *.jpeg"), ("All files", "*.*")],
        )
        if path:
            self.portrait_var.set(path)

    def _create_portrait(self):
        if not portrait_creator.pack_available():
            messagebox.showerror("Pack missing", "The portrait template pack was not found.")
            return
        creator = portrait_creator.PortraitCreator(self, kind="leader")
        self.wait_window(creator)
        if creator.result:
            self.portrait_var.set(creator.result)

    def _save(self):
        cid = self.id_var.get().strip()
        if not cid or " " in cid:
            messagebox.showerror("Bad id", "Character id is required and cannot contain spaces.")
            return
        if not self.name_var.get().strip():
            messagebox.showerror("Missing name", "Display name is required.")
            return
        self.result = {
            "id": cid,
            "name": self.name_var.get().strip(),
            "ideology": self.ideology_var.get().strip() or "despotism",
            "portrait_source": self.portrait_var.get().strip(),
        }
        self.destroy()


class LeaderGallery(tk.Toplevel):
    def __init__(self, master, mod_root, gfx_index, loc, characters_by_tag, tag):
        super().__init__(master)
        self.title(f"Leaders — {tag}")
        self.geometry("900x620")
        self.mod_root = mod_root
        self.gfx_index = gfx_index
        self.loc = loc
        self.characters_by_tag = characters_by_tag
        self.tag = tag
        self.image_refs = []
        self.selected = None
        self._build()
        self._render()

    def _build(self):
        head = ttk.Frame(self, padding=(16, 14, 16, 8))
        head.pack(fill="x")
        ttk.Label(head, text="LEADER GALLERY", style="PageTitle.TLabel").pack(anchor="w")
        ttk.Label(
            head, text="Every character this country has, with portraits — swap one, add a new "
                       "leader, or bulk-import a folder of art at once.",
            style="Muted.TLabel", wraplength=860, justify="left",
        ).pack(anchor="w", pady=(2, 0))
        ttk.Separator(self).pack(fill="x", padx=16, pady=(8, 0))

        top = ttk.Frame(self, padding=(16, 10, 16, 8))
        top.pack(fill="x")
        ttk.Label(top, text="Country tag", style="FieldLabel.TLabel").pack(side="left")
        self.tag_var = tk.StringVar(value=self.tag)
        ttk.Entry(top, textvariable=self.tag_var, width=6, font=(theme.FACE_MONO, 10)).pack(side="left", padx=4)
        ttk.Button(top, text="Show", command=self._on_tag_change).pack(side="left")

        ttk.Label(top, text="   Filter", style="FieldLabel.TLabel").pack(side="left", padx=(12, 0))
        self.filter_var = tk.StringVar()
        entry = ttk.Entry(top, textvariable=self.filter_var, width=22, font=(theme.FACE_MONO, 10))
        entry.pack(side="left", padx=4)
        entry.bind("<KeyRelease>", lambda e: self._render())

        self.only_leaders_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            top, text="Only country leaders", variable=self.only_leaders_var, command=self._render
        ).pack(side="left", padx=12)

        self.count_label = ttk.Label(top, text="", style="Muted.TLabel")
        self.count_label.pack(side="left", padx=8)

        wrap = ttk.Frame(self, padding=(16, 0))
        wrap.pack(fill="both", expand=True)
        self.canvas = tk.Canvas(wrap, background=theme.CANVAS_BG, highlightthickness=0)
        bar = ttk.Scrollbar(wrap, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=bar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        bar.pack(side="right", fill="y")
        self.canvas.bind("<MouseWheel>", lambda e: self.canvas.yview_scroll(-1 * (e.delta // 120), "units"))

        bottom = ttk.Frame(self, padding=16)
        bottom.pack(fill="x")
        ttk.Button(bottom, text="Add New Leader", command=self._add_leader).pack(side="left")
        ttk.Button(bottom, text="Replace Selected Portrait", command=self._replace_portrait).pack(side="left", padx=6)
        ttk.Button(bottom, text="Bulk Import Portraits...", style="Accent.TButton",
                   command=self._bulk_import_portraits).pack(side="left", padx=6)
        self.status = ttk.Label(bottom, text="Click a portrait to select it.", style="Status.TLabel")
        self.status.pack(side="left", padx=10)

    def _on_tag_change(self):
        self.tag = self.tag_var.get().strip().upper()
        self.title(f"Leaders — {self.tag}")
        self.selected = None
        self._render()

    def _visible_characters(self):
        chars = self.characters_by_tag.get(self.tag, [])
        needle = self.filter_var.get().strip().lower()
        out = []
        for c in chars:
            if self.only_leaders_var.get() and "country_leader" not in c["roles"]:
                continue
            label = self._display_name(c).lower()
            if needle and needle not in label and needle not in c["id"].lower():
                continue
            out.append(c)
        return out

    def _display_name(self, c):
        return self.loc.get(c["name_key"], self.loc.get(c["id"], c["name_key"]))

    def _portrait_path(self, c):
        for value in c["portraits"]:
            path = ml.resolve_texture(value, self.mod_root, self.gfx_index)
            if path and os.path.isfile(path):
                return path
        return None

    def _render(self):
        self.canvas.delete("all")
        self.image_refs = []
        chars = self._visible_characters()
        self.count_label.config(text=f"{len(chars)} shown")

        for i, c in enumerate(chars):
            col = i % COLUMNS
            row = i // COLUMNS
            x = 20 + col * CARD_W
            y = 20 + row * 190
            tag_name = f"char_{i}"

            is_sel = self.selected is not None and self.selected["id"] == c["id"]
            self.canvas.create_rectangle(
                x, y, x + CARD_W - 14, y + 170,
                fill=theme.RAISED, outline=theme.GOLD if is_sel else theme.EDGE,
                width=2 if is_sel else 1, tags=(tag_name,),
            )

            path = self._portrait_path(c)
            thumb = image_cache.get_thumbnail(path, (100, 120)) if path else None
            if thumb:
                self.image_refs.append(thumb)
                self.canvas.create_image(x + (CARD_W - 14) / 2, y + 65, image=thumb, tags=(tag_name,))
            else:
                self.canvas.create_text(
                    x + (CARD_W - 14) / 2, y + 65, text="(no image)", fill=theme.MUTED,
                    font=(theme.FACE_UI, 8), tags=(tag_name,),
                )

            self.canvas.create_text(
                x + (CARD_W - 14) / 2, y + 138, text=self._display_name(c), fill=theme.TEXT,
                width=CARD_W - 22, font=(theme.FACE_UI, 8, "bold"), tags=(tag_name,),
            )
            self.canvas.create_text(
                x + (CARD_W - 14) / 2, y + 160, text=c["ideology"], fill=theme.AMBER,
                width=CARD_W - 22, font=(theme.FACE_MONO, 7), tags=(tag_name,),
            )

            self.canvas.tag_bind(tag_name, "<Button-1>", lambda e, ch=c: self._select(ch))

        bbox = self.canvas.bbox("all")
        if bbox:
            self.canvas.configure(scrollregion=(0, 0, bbox[2] + 20, bbox[3] + 20))

    def _select(self, c):
        self.selected = c
        self.status.config(text=f"Selected: {self._display_name(c)}  ({c['id']})")
        self._render()

    # ---- editing ----

    def _copy_portrait_into_mod(self, source, dest_name):
        dest_dir = os.path.join(self.mod_root, "gfx", "leaders", self.tag)
        os.makedirs(dest_dir, exist_ok=True)
        ext = os.path.splitext(source)[1] or ".png"
        dest = os.path.join(dest_dir, dest_name + ext)
        shutil.copy2(source, dest)
        rel = os.path.relpath(dest, self.mod_root).replace("\\", "/")
        return dest, rel

    def _add_leader(self):
        if not self.mod_root:
            messagebox.showerror("No mod", "Load a mod first.")
            return
        dlg = NewLeaderDialog(self, self.tag)
        self.wait_window(dlg)
        if not dlg.result:
            return

        r = dlg.result
        portrait_rel = ""
        if r["portrait_source"]:
            if not os.path.isfile(r["portrait_source"]):
                messagebox.showerror("Missing image", "The chosen portrait file does not exist.")
                return
            _, portrait_rel = self._copy_portrait_into_mod(r["portrait_source"], r["id"])

        portrait_line = f'\t\t\t\t\tlarge = "{portrait_rel}"' if portrait_rel else "\t\t\t\t\tlarge = GFX_portrait_unknown"
        entry = (
            f'\t\t{r["id"]} = {{\n'
            f'\t\t\tname = {r["id"]}\n'
            f'\t\t\tportraits = {{\n'
            f'\t\t\t\tcivilian = {{\n'
            f'{portrait_line}\n'
            f'\t\t\t\t}}\n'
            f'\t\t\t}}\n'
            f'\t\t\tcountry_leader = {{\n'
            f'\t\t\t\tideology = {r["ideology"]}\n'
            f'\t\t\t\texpire = "1965.1.1.1"\n'
            f'\t\t\t\tid = -1\n'
            f'\t\t\t}}\n'
            f'\t\t}}\n'
        )

        out_dir = os.path.join(self.mod_root, "common", "characters")
        os.makedirs(out_dir, exist_ok=True)
        out_path = os.path.join(out_dir, f"zz_{self.tag}_additions.txt")

        # Append inside the existing characters block if our additions file
        # already exists, otherwise start a fresh one.
        if os.path.isfile(out_path):
            with open(out_path, "r", encoding="utf-8-sig", errors="ignore") as f:
                existing = f.read().rstrip()
            if existing.endswith("}"):
                existing = existing[:-1].rstrip("\n")
            content = existing + "\n" + entry + "}\n"
        else:
            content = "characters = {\n" + entry + "}\n"

        with open(out_path, "w", encoding="utf-8") as f:
            f.write(content)

        loc_dir = os.path.join(self.mod_root, "localisation", "english")
        os.makedirs(loc_dir, exist_ok=True)
        loc_path = os.path.join(loc_dir, f"zz_{self.tag}_additions_l_english.yml")
        existing_lines = []
        if os.path.isfile(loc_path):
            with open(loc_path, "r", encoding="utf-8-sig", errors="ignore") as f:
                existing_lines = [ln.rstrip("\n") for ln in f if ln.strip() and not ln.startswith("l_english")]
        existing_lines.append(f' {r["id"]}:0 "{r["name"]}"')
        with open(loc_path, "w", encoding="utf-8-sig") as f:
            f.write("l_english:\n" + "\n".join(existing_lines) + "\n")

        self.characters_by_tag.setdefault(self.tag, []).append({
            "id": r["id"],
            "name_key": r["id"],
            "portraits": [portrait_rel] if portrait_rel else [],
            "roles": ["country_leader"],
            "ideology": r["ideology"],
            "source_file": out_path,
        })
        self.loc[r["id"]] = r["name"]
        self._render()
        self.status.config(text=f"Created {r['id']} in {os.path.basename(out_path)}")

    def _replace_portrait(self):
        if not self.selected:
            messagebox.showerror("Nothing selected", "Click a portrait first.")
            return

        source = filedialog.askopenfilename(
            title="Pick the new portrait image",
            filetypes=[("Images", "*.png *.dds *.tga *.jpg *.jpeg"), ("All files", "*.*")],
        )
        if not source:
            return

        current = self._portrait_path(self.selected)
        if not current:
            messagebox.showerror(
                "No current portrait",
                "Couldn't locate this character's existing portrait file, so there is nothing to replace.",
            )
            return

        confirm = messagebox.askyesno(
            "Overwrite portrait file?",
            "This will overwrite an image file inside the mod:\n\n"
            f"{current}\n\n"
            "A backup copy will be saved next to it with a .bak extension.\n\nContinue?",
        )
        if not confirm:
            self.status.config(text="Portrait replacement cancelled.")
            return

        backup = current + ".bak"
        try:
            if not os.path.exists(backup):
                shutil.copy2(current, backup)
            shutil.copy2(source, current)
        except OSError as exc:
            messagebox.showerror("Failed", f"Could not replace the portrait:\n{exc}")
            return

        image_cache.clear()
        self._render()
        self.status.config(text=f"Portrait replaced. Backup saved as {os.path.basename(backup)}")

    def _bulk_import_portraits(self):
        """Pick many images at once, matched to characters by filename - the
        id (TUR_ataturk.png -> TUR_ataturk) or a filename containing the id.
        One-at-a-time replace is fine for a single leader, but a real mod's
        art pass usually lands as a folder of files named after who they are."""
        if not self.mod_root:
            messagebox.showerror("No mod", "Load a mod first.")
            return

        paths = filedialog.askopenfilenames(
            title="Pick portrait images to import",
            filetypes=[("Images", "*.png *.jpg *.jpeg *.bmp *.webp *.dds *.tga"), ("All files", "*.*")],
        )
        if not paths:
            return

        chars = self.characters_by_tag.get(self.tag, [])
        by_id = {c["id"].lower(): c for c in chars}

        matched, unmatched = [], []
        for src in paths:
            stem = os.path.splitext(os.path.basename(src))[0].lower()
            c = by_id.get(stem) or next((ch for ch in chars if ch["id"].lower() in stem), None)
            if c:
                matched.append((src, c))
            else:
                unmatched.append(src)

        if not matched:
            messagebox.showinfo(
                "No matches",
                "None of the picked filenames matched a character id for this country.\n\n"
                "Rename the file to match the character's id (e.g. TUR_ataturk.png) and try again.",
            )
            return

        preview = "\n".join(f"  {os.path.basename(s)}  ->  {c['id']}" for s, c in matched)
        extra = f"\n\n{len(unmatched)} file(s) matched no character and will be skipped." if unmatched else ""
        if not messagebox.askyesno(
            "Import portraits?",
            f"Match {len(matched)} image(s) to characters by filename:\n\n{preview}{extra}\n\n"
            "Each replaced portrait keeps a one-time .bak backup. Continue?",
        ):
            return

        done, failed = 0, []
        for src, c in matched:
            try:
                current = self._portrait_path(c)
                if current:
                    backup = current + ".bak"
                    if not os.path.exists(backup):
                        shutil.copy2(current, backup)
                    dest = current
                else:
                    dest, rel = self._copy_portrait_into_mod(src, c["id"])
                    c["portraits"] = list(c.get("portraits", [])) + [rel]
                im = Image.open(src).convert("RGBA")
                im = im.resize((156, 210), Image.LANCZOS)
                im.save(dest, "PNG" if dest.lower().endswith(".png") else None)
                done += 1
            except Exception:
                failed.append(os.path.basename(src))

        image_cache.clear()
        self._render()
        msg = f"Imported {done} portrait(s), resized to 156x210."
        if unmatched:
            msg += f" {len(unmatched)} skipped (no match)."
        if failed:
            msg += f" {len(failed)} failed: {', '.join(failed)}."
        self.status.config(text=msg)
