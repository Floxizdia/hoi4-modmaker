"""Command Table toolbar and action bars for the Focus Tree screen."""

import tkinter as tk
from tkinter import ttk

from app import focus_tree_theme as ft
from app import searchable_combo


class FocusTreeToolbar(ttk.Frame):
    """Build the existing Focus Tree controls with scoped visual styles."""

    def __init__(self, parent, *, tree_labels, on_refresh_mods, on_load_mod,
                 on_browse_mod, on_load_tree, on_leaders, on_find_next,
                 on_find_changed, on_sim_toggle, on_reset_progress, on_layout_changed,
                 on_zoom, on_mode_changed, on_help):
        super().__init__(parent, style="FocusTree.Toolbar.TFrame", padding=(12, 8))
        self._tree_labels = tree_labels
        self._on_find_changed = on_find_changed
        self._build(
            on_refresh_mods, on_load_mod, on_browse_mod, on_load_tree, on_leaders,
            on_find_next, on_sim_toggle, on_reset_progress, on_layout_changed,
            on_zoom, on_mode_changed, on_help,
        )

    @staticmethod
    def _separator(parent):
        ttk.Frame(parent, style="FocusTree.Sash.TFrame", width=1).pack(
            side="left", fill="y", padx=10, pady=2
        )

    def _build(self, on_refresh_mods, on_load_mod, on_browse_mod, on_load_tree,
               on_leaders, on_find_next, on_sim_toggle, on_reset_progress,
               on_layout_changed, on_zoom, on_mode_changed, on_help):
        top = ttk.Frame(self, style="FocusTree.ToolbarRow.TFrame")
        top.pack(fill="x")
        ttk.Label(top, text="MOD", style="FocusTree.Eyebrow.TLabel", width=5).pack(side="left")
        self.mod_combo = ttk.Combobox(top, state="readonly", width=38, style="FocusTree.TCombobox")
        self.mod_combo.pack(side="left", padx=(0, 4))
        ttk.Button(top, text="↻", width=3, style="FocusTree.Ghost.TButton",
                   command=on_refresh_mods).pack(side="left")
        ttk.Button(top, text="Load", style="FocusTree.Primary.TButton", command=on_load_mod).pack(
            side="left", padx=4
        )
        ttk.Button(top, text="Folder...", style="FocusTree.Secondary.TButton",
                   command=on_browse_mod).pack(side="left")
        self.mod_label = ttk.Label(top, text="No mod loaded", style="FocusTree.ToolbarMuted.TLabel")
        self.mod_label.pack(side="right")
        ttk.Button(top, text="?", style="FocusTree.Ghost.TButton", width=2, command=on_help).pack(
            side="right", padx=(0, 8)
        )

        picker = ttk.Frame(self, style="FocusTree.ToolbarRow.TFrame")
        picker.pack(fill="x", pady=(7, 0))
        ttk.Label(picker, text="TREE", style="FocusTree.Eyebrow.TLabel", width=5).pack(side="left")
        self.tree_combo = ttk.Combobox(picker, width=38, style="FocusTree.TCombobox")
        self.tree_combo.pack(side="left", padx=(0, 4))
        searchable_combo.enable_filter(self.tree_combo, self._tree_labels)
        ttk.Button(picker, text="Load", style="FocusTree.Primary.TButton", command=on_load_tree).pack(
            side="left"
        )
        self._separator(picker)
        ttk.Label(picker, text="COUNTRY", style="FocusTree.Eyebrow.TLabel").pack(side="left")
        self.tag_var = tk.StringVar()
        ttk.Entry(picker, textvariable=self.tag_var, width=5, style="FocusTree.TEntry").pack(
            side="left", padx=4
        )
        ttk.Button(picker, text="Leaders...", style="FocusTree.Secondary.TButton",
                   command=on_leaders).pack(side="left")

        self.find_label = ttk.Label(picker, text="", style="FocusTree.ToolbarMuted.TLabel")
        self.find_label.pack(side="right", padx=(6, 0))
        ttk.Button(picker, text="Next", style="FocusTree.Secondary.TButton",
                   command=on_find_next).pack(side="right", padx=(4, 0))
        self.find_var = tk.StringVar()
        find_entry = ttk.Entry(picker, textvariable=self.find_var, width=22, style="FocusTree.TEntry")
        find_entry.pack(side="right")
        find_entry.bind("<Return>", lambda _event: on_find_next())
        find_entry.bind("<KeyRelease>", lambda _event: self._on_find_changed())
        ttk.Label(picker, text="SEARCH", style="FocusTree.Eyebrow.TLabel").pack(
            side="right", padx=(0, 4)
        )

        tools = ttk.Frame(self, style="FocusTree.ToolbarRow.TFrame")
        tools.pack(fill="x", pady=(7, 0))
        ttk.Label(tools, text="VIEW", style="FocusTree.Eyebrow.TLabel", width=5).pack(side="left")
        self.sim_mode = tk.BooleanVar(value=False)
        ttk.Checkbutton(tools, text="Play mode", variable=self.sim_mode,
                        style="FocusTree.TCheckbutton", command=on_sim_toggle).pack(side="left")
        ttk.Button(tools, text="Reset", style="FocusTree.Ghost.TButton",
                   command=on_reset_progress).pack(side="left", padx=4)
        self._separator(tools)
        ttk.Label(tools, text="LAYOUT", style="FocusTree.Eyebrow.TLabel").pack(side="left")
        self.layout_mode = tk.StringVar(value="auto")
        ttk.Combobox(tools, textvariable=self.layout_mode, state="readonly", width=15,
                     values=["auto", "mod coordinates"], style="FocusTree.TCombobox").pack(
            side="left", padx=4
        )
        self.layout_mode.trace_add("write", lambda *_args: on_layout_changed())
        self._separator(tools)
        # Whole focus branches are gated on expansions with
        # `allow_branch = { has_dlc = ... }`, so editing a tree without an
        # expansion means seeing what that player actually gets.
        self.dlc_button = ttk.Menubutton(tools, text="DLC", width=10,
                                         style="FocusTree.Ghost.TButton")
        self.dlc_menu = tk.Menu(self.dlc_button, tearoff=False)
        self.dlc_button["menu"] = self.dlc_menu
        self.dlc_button.pack(side="left", padx=4)
        self._separator(tools)
        ttk.Button(tools, text="-", width=3, style="FocusTree.Ghost.TButton",
                   command=lambda: on_zoom(1 / 1.25)).pack(side="left")
        ttk.Button(tools, text="100%", width=5, style="FocusTree.Ghost.TButton",
                   command=lambda: on_zoom(None)).pack(side="left", padx=2)
        ttk.Button(tools, text="+", width=3, style="FocusTree.Ghost.TButton",
                   command=lambda: on_zoom(1.25)).pack(side="left")
        self.progress_label = ttk.Label(tools, text="", style="FocusTree.ToolbarMuted.TLabel")
        self.progress_label.pack(side="right")

        modes = ttk.Frame(self, style="FocusTree.ToolbarRow.TFrame")
        modes.pack(fill="x", pady=(7, 0))
        ttk.Label(modes, text="MODE", style="FocusTree.Eyebrow.TLabel", width=5).pack(side="left")
        self.canvas_mode = tk.StringVar(value="select")
        self.mode_buttons = {}
        for value, label in (("select", "SELECT"), ("link", "LINK"), ("add", "ADD"), ("pan", "PAN")):
            button = tk.Button(
                modes, text=label, relief="flat", font=(ft.theme.FACE_MONO, 8, "bold"),
                padx=10, pady=3, bd=0, command=lambda mode=value: on_mode_changed(mode),
                background=ft.RAISED, foreground=ft.TEXT_MID,
                activebackground=ft.HOVER, activeforeground=ft.TEXT_HI,
                highlightthickness=1, highlightbackground=ft.LINE_STRONG,
            )
            button.pack(side="left", padx=(0, 4))
            self.mode_buttons[value] = button
        self.mode_hint = ttk.Label(modes, text="", style="FocusTree.ToolbarMuted.TLabel")
        self.mode_hint.pack(side="left", padx=10)


class FocusTreeActionBar(ttk.Frame):
    """Dense command strip and status bar, without changing its actions."""

    def __init__(self, parent, *, on_add, on_copy_branch, on_shift_branch, on_tidy,
                 on_export_png, on_save_moved, on_icon_library, on_export_additions,
                 on_play_export, on_publish):
        super().__init__(parent, style="FocusTree.ActionBar.TFrame", padding=(12, 7, 12, 0))
        self._build(
            on_add, on_copy_branch, on_shift_branch, on_tidy, on_export_png,
            on_save_moved, on_icon_library, on_export_additions, on_play_export, on_publish,
        )

    def _build(self, on_add, on_copy_branch, on_shift_branch, on_tidy, on_export_png,
               on_save_moved, on_icon_library, on_export_additions, on_play_export, on_publish):
        commands = ttk.Frame(self, style="FocusTree.ActionBar.TFrame")
        commands.pack(fill="x")
        for text, callback, padx in (
            ("Add New Focus", on_add, 0), ("Copy Branch...", on_copy_branch, 6),
            ("Shift Branch...", on_shift_branch, 0), ("Tidy Tree", on_tidy, 6),
            ("Export PNG", on_export_png, 0), ("Save Moved", on_save_moved, 0),
            ("Icon Library", on_icon_library, 6), ("Export New Focuses", on_export_additions, 0),
            ("Play in HOI4...", on_play_export, 6), ("Publish Prep...", on_publish, 0),
        ):
            ttk.Button(commands, text=text, style="FocusTree.Action.TButton", command=callback).pack(
                side="left", padx=(padx, 0)
            )
        self.status = ttk.Label(commands, text="", style="FocusTree.StatusOk.TLabel", wraplength=560)
        self.status.pack(side="left", padx=10)
        self.warning_label = ttk.Label(commands, text="", style="FocusTree.ToolbarMuted.TLabel")
        self.warning_label.pack(side="right", padx=(0, 4))
        ttk.Label(commands, text="Ctrl+S Save Moved | F6 Validate | F7 Play mode | F8 Export",
                  style="FocusTree.ToolbarMuted.TLabel").pack(side="right", padx=10)

        status_bar = ttk.Frame(self, style="FocusTree.Status.TFrame", padding=(8, 4))
        status_bar.pack(fill="x", pady=(5, 0))
        ttk.Label(status_bar, text="Drag node to move | Add mode: click empty canvas to place a focus | "
                                   "Link mode: click a focus, then a second focus, to link them",
                  style="FocusTree.SurfaceMuted.TLabel").pack(side="left")
        self.unsaved_label = ttk.Label(status_bar, text="", style="FocusTree.StatusWarn.TLabel")
        self.unsaved_label.pack(side="right")
