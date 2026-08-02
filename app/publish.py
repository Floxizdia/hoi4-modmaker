"""Workshop publish assistant: get the mod folder into the exact shape the
HOI4 launcher's upload flow expects, and hand the user a checklist for the
parts only they can click.

Uploading itself happens through Paradox's own launcher (there is no public
API a third-party tool should be poking), so this prepares: a 512x512
thumbnail.png, a description text with the asset-pack credit already in,
and a step-by-step guide file.
"""

import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from PIL import Image

from app import theme

DESCRIPTION_TEMPLATE = """[h1]{name}[/h1]

{summary}

[h2]Features[/h2]
[list]
[*] ...
[*] ...
[/list]

[h2]Compatibility[/h2]
Supported HOI4 version: {version}
{compat}

[h2]Credits[/h2]
Focus/portrait art pieces from the Ultimate-HOI4-GFX pack by Globvs & contributors
(https://github.com/Globvs/Ultimate-HOI4-GFX).
Built with HOI4 Mod Maker.
"""

GUIDE = """HOW TO PUBLISH THIS MOD TO THE STEAM WORKSHOP
=============================================

1. Make sure the mod is in your HOI4 user mod folder:
   Documents/Paradox Interactive/Hearts of Iron IV/mod/<folder>
   (the "Play in HOI4..." button in HOI4 Mod Maker puts it there for you)

2. Open the Paradox Launcher for Hearts of Iron IV.

3. Go to  All installed mods  ->  Mod tools  ->  Upload mod.

4. Pick this mod from the list. The launcher reads descriptor.mod for the
   name, tags and supported version, and thumbnail.png for the picture.

5. Paste the contents of workshop_description.txt into the description box
   (Steam BBCode like [h1] and [list] works there).

6. Set visibility (start with Friends-only or Unlisted to test), agree to
   the Workshop terms, and press Upload.

7. After the first upload the mod gets a Workshop ID; later updates are the
   same flow and keep the same page.

Notes
-----
- Keep the Ultimate-HOI4-GFX credit in the description if any composed
  icons or portraits are in the mod.
- If the upload button is greyed out, check that descriptor.mod has a
  supported_version matching the current game.
"""


def check_readiness(mod_root):
    """[(ok, label), ...] - the handful of things the Workshop upload flow
    itself silently depends on (descriptor.mod fields, thumbnail size, at
    least some actual content) so a modder finds out here instead of after
    the launcher already accepted a broken upload."""
    checks = []

    desc_path = os.path.join(mod_root, "descriptor.mod")
    if os.path.isfile(desc_path):
        with open(desc_path, "r", encoding="utf-8-sig", errors="ignore") as f:
            desc = f.read()
        checks.append(("name=" in desc, "descriptor.mod has a name"))
        checks.append(("supported_version=" in desc, "descriptor.mod declares a supported_version"))
        checks.append(("tags=" in desc or "tags = " in desc, "descriptor.mod has at least one tag"))
    else:
        checks.append((False, "descriptor.mod exists"))

    thumb_path = os.path.join(mod_root, "thumbnail.png")
    if os.path.isfile(thumb_path):
        try:
            with Image.open(thumb_path) as im:
                checks.append((im.size == (512, 512), f"thumbnail.png is 512x512 (currently {im.size[0]}x{im.size[1]})"))
        except Exception:
            checks.append((False, "thumbnail.png is a readable image"))
    else:
        checks.append((False, "thumbnail.png exists"))

    content_dirs = {
        "common/national_focus": "at least one focus tree file",
        "events": "at least one event file",
        "history/countries": "at least one country history file",
    }
    for rel, label in content_dirs.items():
        folder = os.path.join(mod_root, *rel.split("/"))
        has_files = os.path.isdir(folder) and any(
            name.endswith(".txt") for name in os.listdir(folder)
        )
        checks.append((has_files, label))

    loc_dir = os.path.join(mod_root, "localisation")
    has_loc = os.path.isdir(loc_dir) and any(
        name.endswith(".yml") for _, _, files in os.walk(loc_dir) for name in files
    )
    checks.append((has_loc, "at least one localisation file"))

    return checks


class PublishDialog(tk.Toplevel):
    def __init__(self, master, mod_root, mod_name, supported="1.16.*"):
        super().__init__(master)
        self.title("Prepare for the Steam Workshop")
        self.resizable(False, False)
        self.mod_root = mod_root
        self.thumb_source = None
        self._build(mod_name, supported)
        self.grab_set()

    def _build(self, mod_name, supported):
        pad = {"padx": 10, "pady": 4}
        ttk.Label(self, text="Mod title").grid(row=0, column=0, sticky="w", **pad)
        self.name_var = tk.StringVar(value=mod_name)
        ttk.Entry(self, textvariable=self.name_var, width=46).grid(row=0, column=1, **pad)

        ttk.Label(self, text="One-line summary").grid(row=1, column=0, sticky="w", **pad)
        self.summary_var = tk.StringVar(value="A Hearts of Iron IV mod.")
        ttk.Entry(self, textvariable=self.summary_var, width=46).grid(row=1, column=1, **pad)

        ttk.Label(self, text="Compatibility note").grid(row=2, column=0, sticky="w", **pad)
        self.compat_var = tk.StringVar(value="Should work alongside most mods that don't touch the same files.")
        ttk.Entry(self, textvariable=self.compat_var, width=46).grid(row=2, column=1, **pad)

        ttk.Label(self, text="Thumbnail image").grid(row=3, column=0, sticky="w", **pad)
        frame = ttk.Frame(self)
        frame.grid(row=3, column=1, sticky="w", **pad)
        ttk.Button(frame, text="Browse...", command=self._pick_thumb).pack(side="left")
        self.thumb_label = ttk.Label(frame, text="(any image — resized to 512x512)", style="Muted.TLabel")
        self.thumb_label.pack(side="left", padx=6)

        self.status = ttk.Label(self, text="", style="Status.TLabel", wraplength=480, justify="left")
        self.status.grid(row=4, column=0, columnspan=2, sticky="w", **pad)

        btns = ttk.Frame(self)
        btns.grid(row=5, column=0, columnspan=2, pady=10)
        ttk.Button(btns, text="Write publish files", style="Accent.TButton", command=self._write).pack(side="left", padx=4)
        ttk.Button(btns, text="Check Readiness", command=self._check_readiness).pack(side="left", padx=4)
        ttk.Button(btns, text="Close", command=self.destroy).pack(side="left", padx=4)

        ttk.Separator(self).grid(row=6, column=0, columnspan=2, sticky="ew", padx=10, pady=(0, 6))
        self.readiness = tk.Text(self, height=9, width=64, wrap="word", relief="flat",
                                  background=theme.SURFACE, foreground=theme.TEXT, borderwidth=0)
        self.readiness.grid(row=7, column=0, columnspan=2, sticky="ew", padx=10, pady=(0, 10))
        self.readiness.tag_configure("ok", foreground="#4caf50")
        self.readiness.tag_configure("bad", foreground="#e05a5a")
        self.readiness.insert("1.0", "Click \"Check Readiness\" to scan the mod for upload blockers.")
        self.readiness.configure(state="disabled")

        self.supported = supported

    def _check_readiness(self):
        checks = check_readiness(self.mod_root)
        self.readiness.configure(state="normal")
        self.readiness.delete("1.0", "end")
        for ok, label in checks:
            self.readiness.insert("end", ("OK  " if ok else "FIX "), ("ok" if ok else "bad"))
            self.readiness.insert("end", label + "\n")
        failing = sum(1 for ok, _ in checks if not ok)
        self.readiness.insert("end", "\n")
        if failing:
            self.readiness.insert("end", f"{failing} thing(s) to fix before uploading.", "bad")
        else:
            self.readiness.insert("end", "Everything checked out - ready to upload.", "ok")
        self.readiness.configure(state="disabled")

    def _pick_thumb(self):
        path = filedialog.askopenfilename(
            title="Pick a thumbnail image",
            filetypes=[("Images", "*.png *.jpg *.jpeg *.bmp *.webp"), ("All files", "*.*")],
        )
        if path:
            self.thumb_source = path
            self.thumb_label.config(text=os.path.basename(path))

    def _write(self):
        wrote = []
        if self.thumb_source:
            try:
                im = Image.open(self.thumb_source).convert("RGB")
                side = min(im.size)
                left = (im.width - side) // 2
                top = (im.height - side) // 2
                im = im.crop((left, top, left + side, top + side)).resize((512, 512), Image.LANCZOS)
                thumb_path = os.path.join(self.mod_root, "thumbnail.png")
                im.save(thumb_path, "PNG")
                wrote.append("thumbnail.png")
            except Exception as exc:
                messagebox.showerror("Thumbnail failed", str(exc), parent=self)
                return

        description = DESCRIPTION_TEMPLATE.format(
            name=self.name_var.get().strip() or "My Mod",
            summary=self.summary_var.get().strip(),
            version=self.supported,
            compat=self.compat_var.get().strip(),
        )
        desc_path = os.path.join(self.mod_root, "workshop_description.txt")
        with open(desc_path, "w", encoding="utf-8") as f:
            f.write(description)
        wrote.append("workshop_description.txt")

        guide_path = os.path.join(self.mod_root, "PUBLISH_GUIDE.txt")
        with open(guide_path, "w", encoding="utf-8") as f:
            f.write(GUIDE)
        wrote.append("PUBLISH_GUIDE.txt")

        self.status.config(
            text=f"Wrote {', '.join(wrote)} into the mod folder.\n"
                 "Open PUBLISH_GUIDE.txt and follow it — the actual upload happens in the Paradox launcher."
        )
