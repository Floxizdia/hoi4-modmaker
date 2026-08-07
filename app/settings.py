"""Settings tab: shows whichever mod is currently open, and can create the
scaffold for a brand new one."""

import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from app.state import state
from app import mod_export, theme, ui_kit
from app import game_paths

DESCRIPTOR_TEMPLATE = """version="1.0.0"
tags={{
{tags}
}}
name="{name}"
supported_version="1.16.*"
"""


def scaffold_status(root, user_mod_dir):
    """Status text for the scaffold button, given the folder just scaffolded
    and (if found) the game's own mod directory (Documents/Paradox
    Interactive/Hearts of Iron IV/mod).

    Scaffolding only writes descriptor.mod + the folder structure - it does
    not create the separate <name>.mod launcher-entry file, since a folder
    already living under the game's mod directory may already have one (or
    the user is about to make one via Export). But that means the Paradox
    Launcher won't list this mod at all until it's actually inside that
    directory, and that gap is invisible unless the status line says so.
    """
    mod_dir = os.path.join(user_mod_dir, "mod") if user_mod_dir else None
    inside_mod_dir = mod_dir and os.path.normcase(os.path.abspath(root)).startswith(
        os.path.normcase(os.path.abspath(mod_dir)) + os.sep)

    if inside_mod_dir:
        return (
            f"Mod scaffold ready at {root}. "
            "It should now show up in the Paradox Launcher's mod list - if the "
            "Launcher was already open, close and reopen it (or use its own "
            "refresh) to see it."
        )
    return (
        f"Mod scaffold ready at {root} - but this folder is outside your HOI4 "
        f"mod folder ({mod_dir or 'not found - is HOI4 installed?'}), so the "
        "Paradox Launcher will not list it. Move it there, or use \"Create a new "
        "mod\" from the Home screen instead, which sets this up for you."
    )


class SettingsTab(ttk.Frame):
    def __init__(self, master):
        super().__init__(master, padding=12)
        self._build()
        state.subscribe(self.refresh)

    def _build(self):
        self.header = ui_kit.PageHeader(
            self, "Settings",
            "The mod's descriptor.mod (name, version, supported game version, tags) plus "
            "snapshots (save points you can roll back to) and auto-snapshot timing.", help_key="settings")

        body = ttk.Frame(self)
        body.pack(fill="both", expand=True)

        ttk.Label(body, text="Mod name").grid(row=0, column=0, sticky="w")
        self.name_var = tk.StringVar(value=state.mod_name)
        ttk.Entry(body, textvariable=self.name_var, width=40).grid(row=0, column=1, sticky="we", padx=6)

        ttk.Label(body, text="Mod folder").grid(row=1, column=0, sticky="w", pady=(8, 0))
        self.root_var = tk.StringVar(value=state.mod_root)
        ttk.Entry(body, textvariable=self.root_var, width=40).grid(row=1, column=1, sticky="we", padx=6, pady=(8, 0))
        ttk.Button(body, text="Browse...", command=self._browse).grid(row=1, column=2, pady=(8, 0))

        ttk.Label(body, text="Tags (comma-separated, e.g. Alternate History, Events)").grid(
            row=2, column=0, columnspan=2, sticky="w", pady=(8, 0)
        )
        self.tags_var = tk.StringVar(value=", ".join(state.mod_tags))
        ttk.Entry(body, textvariable=self.tags_var, width=50).grid(
            row=3, column=0, columnspan=2, sticky="we", pady=(0, 8)
        )

        ttk.Button(body, text="Create / Update Mod Scaffold", command=self._scaffold).grid(
            row=4, column=0, columnspan=3, pady=12
        )

        self.summary = ttk.Label(body, text="", foreground="#888", justify="left")
        self.summary.grid(row=5, column=0, columnspan=3, sticky="w")

        self.status = ttk.Label(body, text="", foreground="#2a7a2a")
        self.status.grid(row=6, column=0, columnspan=3, sticky="w", pady=(8, 0))

        # ---- starter template ----
        ttk.Separator(body).grid(row=7, column=0, columnspan=3, sticky="we", pady=14)
        ttk.Label(body, text="Starter content", font=("Segoe UI", 11, "bold")).grid(
            row=8, column=0, columnspan=3, sticky="w")
        ttk.Label(
            body,
            text="Writes a small wired-together example: a 3-focus tree that fires an event, a decision\n"
                 "and a national spirit — the fastest way to see how the pieces reference each other.",
            foreground="#8f8875", justify="left",
        ).grid(row=9, column=0, columnspan=3, sticky="w", pady=(2, 6))
        starter_row = ttk.Frame(body)
        starter_row.grid(row=10, column=0, columnspan=3, sticky="w")
        ttk.Label(starter_row, text="Prefix:").pack(side="left")
        self.starter_prefix = tk.StringVar(value="my")
        ttk.Entry(starter_row, textvariable=self.starter_prefix, width=12).pack(side="left", padx=4)
        ttk.Label(starter_row, text="Country tag:").pack(side="left", padx=(10, 0))
        self.starter_tag = tk.StringVar(value="TUR")
        ttk.Entry(starter_row, textvariable=self.starter_tag, width=6).pack(side="left", padx=4)
        ttk.Button(starter_row, text="Add Starter Content", command=self._starter).pack(side="left", padx=8)

        # ---- snapshots ----
        ttk.Separator(body).grid(row=11, column=0, columnspan=3, sticky="we", pady=14)
        ttk.Label(body, text="Snapshots (version history)", font=("Segoe UI", 11, "bold")).grid(
            row=12, column=0, columnspan=3, sticky="w")
        snap_row = ttk.Frame(body)
        snap_row.grid(row=13, column=0, columnspan=3, sticky="we", pady=(4, 0))
        ttk.Button(snap_row, text="Take Snapshot", command=self._snap_create).pack(side="left")
        ttk.Button(snap_row, text="Restore Selected", command=self._snap_restore).pack(side="left", padx=6)
        ttk.Button(snap_row, text="Changelog vs Selected...", command=self._snap_changelog).pack(side="left", padx=6)
        ttk.Button(snap_row, text="Export mod as .zip...", command=self._export_archive).pack(side="left", padx=6)
        self.snap_note = tk.StringVar()
        ttk.Entry(snap_row, textvariable=self.snap_note, width=24).pack(side="left", padx=6)
        ttk.Label(snap_row, text="note (optional)", foreground="#8f8875").pack(side="left")
        self.snap_list = tk.Listbox(body, height=5)
        self.snap_list.grid(row=14, column=0, columnspan=3, sticky="we", pady=(6, 0))

        auto_row = ttk.Frame(body)
        auto_row.grid(row=15, column=0, columnspan=3, sticky="w", pady=(6, 0))
        self.auto_snap_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            auto_row, text="Auto-snapshot every", variable=self.auto_snap_var,
            command=self._auto_snap_toggle,
        ).pack(side="left")
        self.auto_snap_minutes = tk.StringVar(value="15")
        ttk.Entry(auto_row, textvariable=self.auto_snap_minutes, width=4).pack(side="left", padx=4)
        ttk.Label(auto_row, text="minutes (keeps the last 8)").pack(side="left")

        # ---- game folders ----
        ttk.Separator(body).grid(row=16, column=0, columnspan=3, sticky="we", pady=14)
        ttk.Label(body, text="Game folders", font=("Segoe UI", 11, "bold")).grid(
            row=17, column=0, columnspan=3, sticky="w")
        ttk.Label(
            body,
            text="Found automatically from your Steam libraries. Set them by hand if the game "
                 "lives somewhere the search can't reach - another drive, a non-Steam copy, or "
                 "a Windows install being edited from Linux.",
            foreground="#888", wraplength=620, justify="left",
        ).grid(row=18, column=0, columnspan=3, sticky="w", pady=(2, 6))

        ttk.Label(body, text="HOI4 game folder").grid(row=19, column=0, sticky="w")
        self.base_game_var = tk.StringVar()
        ttk.Entry(body, textvariable=self.base_game_var, width=40).grid(
            row=19, column=1, sticky="we", padx=6)
        ttk.Button(body, text="Browse...",
                   command=lambda: self._browse_game_dir(self.base_game_var,
                                                         "Select the Hearts of Iron IV folder")
                   ).grid(row=19, column=2)

        ttk.Label(body, text="Workshop folder").grid(row=20, column=0, sticky="w", pady=(6, 0))
        self.workshop_var = tk.StringVar()
        ttk.Entry(body, textvariable=self.workshop_var, width=40).grid(
            row=20, column=1, sticky="we", padx=6, pady=(6, 0))
        ttk.Button(body, text="Browse...",
                   command=lambda: self._browse_game_dir(self.workshop_var,
                                                         "Select the Workshop content folder")
                   ).grid(row=20, column=2, pady=(6, 0))

        paths_row = ttk.Frame(body)
        paths_row.grid(row=21, column=0, columnspan=3, sticky="w", pady=(8, 0))
        ttk.Button(paths_row, text="Save Folders", style="Accent.TButton",
                   command=self._save_game_paths).pack(side="left")
        ttk.Button(paths_row, text="Detect Again",
                   command=self._detect_game_paths).pack(side="left", padx=6)
        self.paths_status = ttk.Label(body, text="", foreground="#888",
                                      wraplength=620, justify="left")
        self.paths_status.grid(row=22, column=0, columnspan=3, sticky="w", pady=(6, 0))

        # ---- help ----
        ttk.Separator(body).grid(row=23, column=0, columnspan=3, sticky="we", pady=14)
        ttk.Label(body, text="Help", font=("Segoe UI", 11, "bold")).grid(
            row=24, column=0, columnspan=3, sticky="w")
        ttk.Button(body, text="Show Tour Again", command=self._show_tour).grid(
            row=25, column=0, sticky="w", pady=(4, 0))

        body.columnconfigure(1, weight=1)
        self._load_game_paths()
        self.refresh()

    # ---- game folders ----

    def _load_game_paths(self):
        self.base_game_var.set(game_paths.find_base_game())
        self.workshop_var.set(game_paths.find_workshop())
        self._describe_game_paths()

    def _describe_game_paths(self):
        missing = [label for label, value in (("game", self.base_game_var.get()),
                                              ("Workshop", self.workshop_var.get()))
                   if not value or not os.path.isdir(value)]
        if missing:
            self.paths_status.config(
                text="Not found: " + ", ".join(missing) +
                     ". Most screens need the game folder to show vanilla content.")
        else:
            self.paths_status.config(text="Both folders found.")

    def _browse_game_dir(self, var, title):
        path = filedialog.askdirectory(title=title, initialdir=var.get() or None)
        if path:
            var.set(path)
            self._describe_game_paths()

    def _detect_game_paths(self):
        """Re-run the search, ignoring anything pinned earlier."""
        game_paths.save_pinned(base_game="", workshop="")
        self._load_game_paths()

    def _save_game_paths(self):
        """Paths are read into module-level constants when each screen is
        first imported, so a change only takes hold on the next run - say so
        rather than leaving half the app pointing at the old folder."""
        base = self.base_game_var.get().strip()
        workshop = self.workshop_var.get().strip()
        for label, value in (("game", base), ("Workshop", workshop)):
            if value and not os.path.isdir(value):
                messagebox.showerror("No such folder",
                                     f"That {label} folder doesn't exist:\n{value}")
                return
        game_paths.save_pinned(base_game=base, workshop=workshop)
        self.paths_status.config(
            text="Saved. Restart HOI4 Mod Maker for the new folders to take effect everywhere.")

    def _show_tour(self):
        from app import onboarding
        onboarding.show_now(self.winfo_toplevel())

    def _auto_snap_toggle(self):
        app = self.winfo_toplevel()
        if hasattr(app, "set_auto_snapshot"):
            try:
                minutes = max(1, int(self.auto_snap_minutes.get()))
            except ValueError:
                minutes = 15
                self.auto_snap_minutes.set("15")
            app.set_auto_snapshot(self.auto_snap_var.get(), minutes)

    def _starter(self):
        from app import starter
        if not state.is_loaded:
            messagebox.showerror("No mod", "Create or open a mod first.")
            return
        created = starter.write_starter(state.mod_root, self.starter_prefix.get(), self.starter_tag.get())
        state._notify()  # let the other tabs pick up the new files
        self.status.config(text=f"Starter content written: {len(created)} files. "
                                "See the Focus Tree / Events / Decisions / Ideas tabs.")

    def _snap_refresh(self):
        from app import snapshots
        self.snap_list.delete(0, "end")
        self._snaps = snapshots.list_snapshots(state.mod_root) if state.is_loaded else []
        for _, label, size in self._snaps:
            self.snap_list.insert("end", f"  {label}   ({size:.1f} MB)")

    def _snap_create(self):
        from app import snapshots
        if not state.is_loaded:
            messagebox.showerror("No mod", "Open a mod first.")
            return
        self.status.config(text="Creating snapshot...")
        self.update_idletasks()
        try:
            path, count = snapshots.create(state.mod_root, self.snap_note.get())
        except OSError as exc:
            self.status.config(text=f"Snapshot failed: {exc}")
            return
        self._snap_refresh()
        self.status.config(text=f"Snapshot saved: {count} script files -> {os.path.basename(path)}")

    def _snap_restore(self):
        from app import snapshots
        sel = self.snap_list.curselection()
        if not sel or not getattr(self, "_snaps", None):
            messagebox.showerror("Nothing selected", "Pick a snapshot from the list first.")
            return
        path, label, _ = self._snaps[sel[0]]
        if not messagebox.askyesno(
            "Restore snapshot?",
            f"Restore '{label}'?\n\nThis overwrites the mod's current script files with the "
            "snapshot's versions.\n\nThe mod's current state is snapshotted first as "
            "'before-restore', so this is reversible.",
        ):
            return
        try:
            count, safety = snapshots.restore(state.mod_root, path)
        except OSError as exc:
            self.status.config(text=f"Restore failed partway through: {exc}. "
                                     "Some files may already have been overwritten - "
                                     "take a new snapshot to check the mod's current state.")
            state._notify()
            return
        state._notify()
        self._snap_refresh()
        undo_hint = (" Your previous state is the 'before-restore' snapshot in this list."
                     if safety else "")
        self.status.config(text=f"Restored {count} files from {label}.{undo_hint}")

    def _export_archive(self):
        """A full, self-contained copy of the mod - textures and all - for
        sending to someone, moving machines, or archiving a release. This is
        deliberately separate from snapshots, which are script-only and live
        inside the mod folder."""
        from app import snapshots
        if not state.is_loaded:
            messagebox.showerror("No mod", "Open a mod first.")
            return
        safe = "".join(c for c in state.mod_name if c.isalnum() or c in "-_ ").strip().replace(" ", "_")
        out_path = filedialog.asksaveasfilename(
            title="Save the mod archive",
            defaultextension=".zip",
            initialfile=f"{safe or 'mod'}.zip",
            filetypes=[("Zip archive", "*.zip")],
        )
        if not out_path:
            return
        self.status.config(text="Packing the mod...")
        self.update_idletasks()
        try:
            count, total = snapshots.export_archive(
                state.mod_root, out_path,
                progress=lambda m: (self.status.config(text=m), self.update_idletasks()),
            )
        except OSError as exc:
            messagebox.showerror("Export failed", str(exc))
            self.status.config(text="")
            return
        size_mb = os.path.getsize(out_path) / (1024 * 1024)
        self.status.config(
            text=f"Packed {count} file(s) ({total / (1024 * 1024):.1f} MB of content) "
                 f"into {os.path.basename(out_path)} — {size_mb:.1f} MB compressed."
        )

    def _snap_changelog(self):
        if not state.is_loaded:
            messagebox.showerror("No mod", "Open a mod first.")
            return
        sel = self.snap_list.curselection()
        if not sel or not getattr(self, "_snaps", None):
            messagebox.showerror("Nothing selected", "Pick a snapshot from the list first - the "
                                  "changelog compares the mod's current state against it.")
            return
        path, label, _ = self._snaps[sel[0]]
        self.status.config(text="Comparing against snapshot...")
        self.update_idletasks()
        from app import changelog
        text = changelog.build(state.mod_root, path, title=f"{state.mod_name} - changes since {label}")
        self.status.config(text="")
        _ChangelogDialog(self, text)

    def refresh(self):
        if hasattr(self, "snap_list"):
            self._snap_refresh()
        if state.is_loaded:
            self.header.set_status(True, state.mod_name)
            self.name_var.set(state.mod_name)
            self.root_var.set(state.mod_root)
            self.tags_var.set(", ".join(state.mod_tags))
            self.summary.config(
                text=f"{len(state.gfx_index)} sprites indexed · {len(state.mod_loc)} localisation keys · "
                     f"{len(state.characters)} countries with characters\n"
                     "The other tabs are all working on this mod."
            )
        else:
            self.header.set_status(False, "no mod open")
            self.summary.config(text="Open a mod from the Home screen or the Open Mod tab, or create a new one below.")

    def _browse(self):
        path = filedialog.askdirectory(title="Choose or create the mod folder")
        if path:
            self.root_var.set(path)

    def _scaffold(self):
        root = self.root_var.get().strip()
        name = self.name_var.get().strip()
        if not root or not name:
            messagebox.showerror("Missing info", "Mod folder and mod name are both required.")
            return

        os.makedirs(root, exist_ok=True)
        tags = [t.strip() for t in self.tags_var.get().split(",") if t.strip()]
        state.set_mod(root, name=name, tags=tags)

        for sub in (
            "common/national_focus",
            "common/decisions",
            "common/characters",
            "events",
            "localisation/english",
            "interface",
            "gfx/interface/goals",
        ):
            state.ensure_dir(*sub.split("/"))

        tags_block = "\n".join(f'\t"{t}"' for t in tags) if tags else '\t"Alternate History"'
        descriptor = DESCRIPTOR_TEMPLATE.format(tags=tags_block, name=name)
        with open(state.path("descriptor.mod"), "w", encoding="utf-8") as f:
            f.write(descriptor)

        user_dir = mod_export.find_user_dir()
        self.status.config(text=scaffold_status(root, user_dir))


class _ChangelogDialog(tk.Toplevel):
    def __init__(self, master, text):
        super().__init__(master)
        self.title("Changelog")
        self.geometry("640x480")
        outer = ttk.Frame(self, padding=12)
        outer.pack(fill="both", expand=True)
        ttk.Label(outer, text="Paste this into your Workshop update description.",
                  style="Muted.TLabel").pack(anchor="w", pady=(0, 6))
        box = tk.Text(outer, wrap="word", font=(theme.FACE_MONO, 9))
        box.insert("1.0", text)
        box.pack(fill="both", expand=True)
        btns = ttk.Frame(outer)
        btns.pack(fill="x", pady=(8, 0))
        ttk.Button(btns, text="Copy to Clipboard", style="Accent.TButton",
                   command=lambda: self._copy(text)).pack(side="left")
        ttk.Button(btns, text="Close", command=self.destroy).pack(side="left", padx=6)

    def _copy(self, text):
        self.clipboard_clear()
        self.clipboard_append(text)
