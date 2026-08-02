"""Icon Coverage tab: every icon/picture reference in the mod's focuses,
ideas, decisions and events, cross-checked against sprites actually
registered in .gfx files - flags exactly what would render as a blank or
red-X icon in game, before you find out the hard way."""

import tkinter as tk
from tkinter import ttk

from app.state import state
from app import icon_coverage
from app import theme, ui_kit


class IconCoverageTab(ttk.Frame):
    def __init__(self, master):
        super().__init__(master, padding=12)
        self._build()
        state.subscribe(self.on_mod_changed)

    def _build(self):
        self.header = ui_kit.PageHeader(
            self, "Icon Coverage",
            "Every icon/picture reference in focuses/ideas/decisions/events, checked against sprites actually registered in .gfx files - flags exactly what would render as a blank or red-X icon in game.", help_key="icon_coverage")
        ttk.Label(
            self, text="Checks icon/picture/large_picture/small_icon references in common/national_focus, "
                       "common/ideas, common/decisions and events against every sprite name registered in "
                       ".gfx files (base game + this mod).",
            style="Muted.TLabel", wraplength=980, justify="left",
        ).pack(anchor="w", pady=(0, 8))

        top = ttk.Frame(self)
        top.pack(fill="x", pady=(0, 8))
        ttk.Button(top, text="Scan Now", style="Accent.TButton", command=self._scan).pack(side="left")
        ttk.Button(top, text="Clean Dead Sprite Entries...",
                   command=self._clean_dead).pack(side="left", padx=8)
        self.summary = ttk.Label(top, text="", style="Status.TLabel")
        self.summary.pack(side="left", padx=12)

        self.tree = ttk.Treeview(self, columns=("token", "field", "context", "file"), show="headings", height=26)
        self.tree.heading("token", text="missing icon token")
        self.tree.heading("field", text="field")
        self.tree.heading("context", text="found in (id)")
        self.tree.heading("file", text="file")
        self.tree.column("token", width=220)
        self.tree.column("field", width=90)
        self.tree.column("context", width=200)
        self.tree.column("file", width=320)
        self.tree.pack(fill="both", expand=True)

    def on_mod_changed(self):
        if state.is_loaded:
            self.header.set_status(True, state.mod_name)
        else:
            self.header.set_status(False, "no mod open")
        self.tree.delete(*self.tree.get_children())
        self.summary.config(text="")

    def on_show(self):
        self.on_mod_changed()

    def _clean_dead(self):
        """The other half of the icon problem: a .gfx entry that *is*
        registered but whose texture file isn't on disk. The reference looks
        satisfied to every id check, yet renders blank in game."""
        if not state.is_loaded:
            messagebox.showerror("No mod", "Open a mod first.")
            return
        from app import sprite_cleanup
        self.summary.config(text="Looking for sprites whose texture file is missing...")
        self.update_idletasks()
        dead = sprite_cleanup.find_dead_sprites(state.mod_root)
        self.summary.config(text="")
        if not dead:
            messagebox.showinfo(
                "Nothing to clean",
                "Every sprite this mod declares has its texture file present.")
            return

        plan = sprite_cleanup.plan_removal(state.mod_root, dead)
        sample = chr(10).join(
            f"  {name}   ->   {rel}" for name, rel in sorted(dead.items())[:10])
        if len(dead) > 10:
            sample += chr(10) + f"  ... and {len(dead) - 10} more"

        if not messagebox.askyesno(
            "Remove dead sprite entries?",
            f"{len(dead)} sprite(s) across {len(plan)} .gfx file(s) point at a texture that "
            "exists in neither this mod nor the base game:" + chr(10) * 2 + sample + chr(10) * 2 +
            "Their SpriteType blocks will be removed. The entries are removed rather than "
            "repointed at a placeholder, because guessing which image you meant would turn a "
            "visible broken icon into an invisible wrong one." + chr(10) * 2 +
            "Each edited .gfx keeps a one-time .bak. Continue?"):
            return

        files_changed, removed = sprite_cleanup.remove_sprites(state.mod_root, dead)
        self.summary.config(
            text=f"Removed {removed} dead sprite entr(ies) from {files_changed} .gfx file(s). "
                 "Anything that referenced them now shows up here as a missing icon, which is "
                 "what it actually was all along.")

    def _scan(self):
        self.tree.delete(*self.tree.get_children())
        if not state.is_loaded:
            self.summary.config(text="Open a mod first.", foreground=theme.RED)
            return
        missing = icon_coverage.missing_icons(state.mod_root, state.gfx_index)
        total_refs = 0
        for token, hits in sorted(missing.items()):
            for field, context, rel in hits:
                self.tree.insert("", "end", values=(token, field, context, rel))
                total_refs += 1
        if not missing:
            self.summary.config(text="No missing icons found — every reference resolves to a real sprite.",
                                 foreground=theme.GREEN)
        else:
            self.summary.config(
                text=f"{len(missing)} distinct missing icon token(s), {total_refs} reference(s) affected.",
                foreground=theme.RED)
