"""New Mod wizard: everything a from-scratch mod needs, decided on one
screen and created in one click.

The conveniences that matter:
  - the mod is created straight inside the HOI4 user mod folder with its
    launcher .mod entry, so it appears in the Paradox launcher immediately,
    playable with zero export steps
  - supported_version is read from the installed game, not guessed
  - Workshop tags are real checkboxes instead of remembered strings
  - optional starter content writes a wired focus tree / event / decision /
    spirit example so the mod isn't a maze of empty folders
"""

import json
import os
import re
import shutil
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from app.state import state
from app import mod_export
from app import mod_loader
from app import starter
from app import theme

BASE_GAME = r"C:\Program Files (x86)\Steam\steamapps\common\Hearts of Iron IV"

WORKSHOP_TAGS = [
    "Alternative History", "Balance", "Events", "Fixes", "Gameplay",
    "Graphics", "Historical", "Ideologies", "Map", "Military",
    "National Focuses", "Sound", "Technologies", "Translation", "Utilities",
]

SCAFFOLD_DIRS = [
    "common/national_focus", "common/decisions", "common/ideas",
    "common/characters", "events", "localisation/english",
    "interface", "gfx/interface/goals", "gfx/leaders",
]

SAFE_FOLDER = re.compile(r"[^A-Za-z0-9_\- ]+")


def detect_game_version():
    """'1.19.*' from the installed game's launcher-settings.json."""
    path = os.path.join(BASE_GAME, "launcher-settings.json")
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            raw = json.load(f).get("rawVersion", "")
        parts = raw.split(".")
        if len(parts) >= 2:
            return f"{parts[0]}.{parts[1]}.*"
    except (OSError, ValueError):
        pass
    return "1.16.*"


def copy_vanilla_focus_tree(base_game, mod_root, tag):
    """Copy the largest vanilla focus tree assigned to ``tag`` into a mod.

    The copy retains the base game's relative path, so Paradox's virtual
    filesystem uses it as the editable version while the installed game files
    remain untouched.  This is the safe way to extend a vanilla country tree:
    all original focuses are present before the user adds or edits anything.
    """
    tag = tag.strip().upper()
    candidates = []
    for source_path in mod_loader.find_focus_tree_files(base_game):
        for tree in mod_loader.parse_focus_trees(source_path):
            if tag in tree["country_tags"]:
                candidates.append((len(tree["focuses"]), source_path))
    if not candidates:
        raise ValueError(f"No vanilla focus tree could be found for country tag '{tag}'.")

    _count, source_path = max(candidates, key=lambda item: item[0])
    relative_path = os.path.relpath(source_path, base_game)
    destination = os.path.join(mod_root, relative_path)
    os.makedirs(os.path.dirname(destination), exist_ok=True)
    shutil.copy2(source_path, destination)
    return destination


def create_mod(*, name, folder, location, tags, supported, version="1.0.0",
               launcher_entry=True, starter_prefix=None, starter_tag="TUR",
               content_mode="country_starter", base_game=BASE_GAME):
    """Create the whole mod. Returns its root path."""
    root = os.path.join(location, folder)
    os.makedirs(root, exist_ok=True)

    for sub in SCAFFOLD_DIRS:
        os.makedirs(os.path.join(root, *sub.split("/")), exist_ok=True)

    tags_block = "\n".join(f'\t"{t}"' for t in (tags or ["Gameplay"]))
    descriptor = (
        f'version="{version}"\n'
        f"tags={{\n{tags_block}\n}}\n"
        f'name="{name}"\n'
        f'supported_version="{supported}"\n'
    )
    with open(os.path.join(root, "descriptor.mod"), "w", encoding="utf-8") as f:
        f.write(descriptor)

    if launcher_entry:
        mod_dir = os.path.dirname(root)
        with open(os.path.join(mod_dir, f"{folder}.mod"), "w", encoding="utf-8") as f:
            f.write(descriptor + f'path="{root.replace(os.sep, "/")}"\n')

    if content_mode == "vanilla_clone":
        copy_vanilla_focus_tree(base_game, root, starter_tag)

    if starter_prefix:
        starter.write_starter(
            root,
            starter_prefix,
            starter_tag,
            country_setup=content_mode == "country_starter",
            include_focus_tree=content_mode != "vanilla_clone",
        )

    return root


class NewModWizard(tk.Toplevel):
    """`self.result` is the created mod's root path."""

    def __init__(self, master):
        super().__init__(master)
        self.title("Create a new mod")
        self.resizable(False, False)
        self.result = None
        self._build()
        self.grab_set()

    def _build(self):
        pad = {"padx": 12, "pady": 4}
        row = 0

        ttk.Label(self, text="Create a new mod", style="Gold.TLabel",
                  font=("Segoe UI", 14, "bold")).grid(row=row, column=0, columnspan=3, sticky="w", **pad)
        row += 1

        ttk.Label(self, text="Mod name").grid(row=row, column=0, sticky="w", **pad)
        self.name_var = tk.StringVar(value="My HOI4 Mod")
        entry = ttk.Entry(self, textvariable=self.name_var, width=40)
        entry.grid(row=row, column=1, columnspan=2, sticky="w", **pad)
        self.name_var.trace_add("write", lambda *_: self._suggest_folder())
        row += 1

        ttk.Label(self, text="Folder name").grid(row=row, column=0, sticky="w", **pad)
        self.folder_var = tk.StringVar(value="my_hoi4_mod")
        ttk.Entry(self, textvariable=self.folder_var, width=40).grid(row=row, column=1, columnspan=2, sticky="w", **pad)
        row += 1

        ttk.Label(self, text="Location").grid(row=row, column=0, sticky="w", **pad)
        user_dir = mod_export.find_user_dir()
        self.default_location = os.path.join(user_dir, "mod") if user_dir else ""
        self.location_var = tk.StringVar(value="game" if user_dir else "custom")
        loc_frame = ttk.Frame(self)
        loc_frame.grid(row=row, column=1, columnspan=2, sticky="w", **pad)
        ttk.Radiobutton(
            loc_frame, variable=self.location_var, value="game",
            text="HOI4 mod folder — appears in the launcher instantly (recommended)",
            state="normal" if user_dir else "disabled",
        ).pack(anchor="w")
        custom_row = ttk.Frame(loc_frame)
        custom_row.pack(anchor="w")
        ttk.Radiobutton(custom_row, variable=self.location_var, value="custom", text="Custom folder:").pack(side="left")
        self.custom_var = tk.StringVar()
        ttk.Entry(custom_row, textvariable=self.custom_var, width=28).pack(side="left", padx=4)
        ttk.Button(custom_row, text="...", width=3, command=self._browse).pack(side="left")
        row += 1

        ttk.Label(self, text="Game version").grid(row=row, column=0, sticky="w", **pad)
        self.version_var = tk.StringVar(value=detect_game_version())
        ttk.Entry(self, textvariable=self.version_var, width=10).grid(row=row, column=1, sticky="w", **pad)
        ttk.Label(self, text="detected from your installed game", style="Muted.TLabel").grid(
            row=row, column=2, sticky="w")
        row += 1

        ttk.Label(self, text="Workshop tags").grid(row=row, column=0, sticky="nw", **pad)
        tag_frame = ttk.Frame(self)
        tag_frame.grid(row=row, column=1, columnspan=2, sticky="w", **pad)
        self.tag_vars = {}
        for i, tag in enumerate(WORKSHOP_TAGS):
            var = tk.BooleanVar(value=tag in ("Gameplay", "National Focuses"))
            ttk.Checkbutton(tag_frame, text=tag, variable=var).grid(
                row=i // 3, column=i % 3, sticky="w", padx=4, pady=1)
            self.tag_vars[tag] = var
        row += 1

        ttk.Separator(self).grid(row=row, column=0, columnspan=3, sticky="we", pady=8)
        row += 1

        self.starter_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            self, variable=self.starter_var,
            text="Add starter content — a wired example (3 focuses → event → national spirit + a decision)",
        ).grid(row=row, column=0, columnspan=3, sticky="w", **pad)
        row += 1

        starter_row = ttk.Frame(self)
        starter_row.grid(row=row, column=0, columnspan=3, sticky="w", padx=32)
        ttk.Label(starter_row, text="Prefix:").pack(side="left")
        self.prefix_var = tk.StringVar(value="my")
        ttk.Entry(starter_row, textvariable=self.prefix_var, width=10).pack(side="left", padx=4)
        ttk.Label(starter_row, text="For country tag:").pack(side="left", padx=(10, 0))
        self.tag_var = tk.StringVar(value="TUR")
        ttk.Entry(starter_row, textvariable=self.tag_var, width=6).pack(side="left", padx=4)
        row += 1

        ttk.Label(self, text="Vanilla integration").grid(row=row, column=0, sticky="nw", **pad)
        mode_frame = ttk.Frame(self)
        mode_frame.grid(row=row, column=1, columnspan=2, sticky="w", **pad)
        self.content_mode_var = tk.StringVar(value="safe_addon")
        ttk.Radiobutton(
            mode_frame, variable=self.content_mode_var, value="safe_addon",
            text="Vanilla-safe add-on — does not replace a country tree or starting history (recommended)",
        ).pack(anchor="w")
        ttk.Radiobutton(
            mode_frame, variable=self.content_mode_var, value="vanilla_clone",
            text="Edit a vanilla country tree — copy its complete focus tree into this mod first",
        ).pack(anchor="w")
        ttk.Radiobutton(
            mode_frame, variable=self.content_mode_var, value="country_starter",
            text="Custom country starter — replace selected country's starting tree and history",
        ).pack(anchor="w")
        ttk.Label(
            mode_frame,
            text="The game installation is never changed. The selected country tag is used for the last two options.",
            style="Muted.TLabel", wraplength=510, justify="left",
        ).pack(anchor="w", pady=(2, 0))
        row += 1

        self.status = ttk.Label(self, text="", style="Warn.TLabel", wraplength=520, justify="left")
        self.status.grid(row=row, column=0, columnspan=3, sticky="w", **pad)
        row += 1

        btns = ttk.Frame(self)
        btns.grid(row=row, column=0, columnspan=3, pady=12)
        ttk.Button(btns, text="Create Mod", style="Accent.TButton", command=self._create).pack(side="left", padx=4)
        ttk.Button(btns, text="Cancel", command=self.destroy).pack(side="left", padx=4)

        self._suggest_folder()

    def _suggest_folder(self):
        name = self.name_var.get()
        folder = SAFE_FOLDER.sub("", name).strip().lower().replace(" ", "_")
        self.folder_var.set(folder or "my_mod")

    def _browse(self):
        path = filedialog.askdirectory(title="Where should the mod folder be created?")
        if path:
            self.custom_var.set(path)
            self.location_var.set("custom")

    def _create(self):
        name = self.name_var.get().strip()
        folder = SAFE_FOLDER.sub("", self.folder_var.get()).strip().replace(" ", "_")
        if not name or not folder:
            self.status.config(text="Mod name and folder name are required.")
            return

        if self.location_var.get() == "game":
            location = self.default_location
            launcher_entry = True
        else:
            location = self.custom_var.get().strip()
            launcher_entry = False
            if not location:
                self.status.config(text="Pick a custom folder or choose the HOI4 mod folder.")
                return

        root = os.path.join(location, folder)
        if os.path.isdir(root) and os.listdir(root):
            self.status.config(text=f"'{root}' already exists and is not empty — pick another folder name.")
            return

        tags = [t for t, v in self.tag_vars.items() if v.get()]
        try:
            root = create_mod(
                name=name, folder=folder, location=location, tags=tags,
                supported=self.version_var.get().strip() or "1.16.*",
                launcher_entry=launcher_entry,
                starter_prefix=self.prefix_var.get() if self.starter_var.get() else None,
                starter_tag=self.tag_var.get(),
                content_mode=self.content_mode_var.get(),
            )
        except (OSError, ValueError) as exc:
            self.status.config(text=f"Creation failed: {exc}")
            return

        state.mod_tags = tags
        self.result = root
        self.destroy()
