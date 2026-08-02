"""Settings tab: shows whichever mod is currently open, and can create the
scaffold for a brand new one."""

import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from app.state import state
from app import theme, ui_kit

DESCRIPTOR_TEMPLATE = """version="1.0.0"
tags={{
{tags}
}}
name="{name}"
supported_version="1.16.*"
"""


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

        # ---- help ----
        ttk.Separator(body).grid(row=16, column=0, columnspan=3, sticky="we", pady=14)
        ttk.Label(body, text="Help", font=("Segoe UI", 11, "bold")).grid(
            row=17, column=0, columnspan=3, sticky="w")
        ttk.Button(body, text="Show Tour Again", command=self._show_tour).grid(
            row=18, column=0, sticky="w", pady=(4, 0))

        body.columnconfigure(1, weight=1)
        self.refresh()

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
        path, count = snapshots.create(state.mod_root, self.snap_note.get())
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
            "snapshot's versions. Taking a fresh snapshot first is recommended.",
        ):
            return
        count = snapshots.restore(state.mod_root, path)
        state._notify()
        self.status.config(text=f"Restored {count} files from {label}.")

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

        self.status.config(text=f"Mod scaffold ready at {root}")


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
