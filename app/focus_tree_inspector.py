"""Command Table inspector widgets for the Focus Tree screen."""

import os
import tkinter as tk
from tkinter import ttk

from app import focus_tree_theme as ft
from app import image_cache
from app import mod_loader as ml


class FocusTreeInspector(ttk.Frame):
    """Focus properties and tree-settings panels with a stable widget API."""

    def __init__(self, parent, *, on_pick_icon, on_complete, on_save,
                 on_more_options, on_show_references):
        super().__init__(parent, width=340, style="FocusTree.Inspector.TFrame")
        self.pack_propagate(False)
        self.icon_refs = []
        self._build(on_pick_icon, on_complete, on_save, on_more_options, on_show_references)

    def _build(self, on_pick_icon, on_complete, on_save, on_more_options, on_show_references):
        self.notebook = ttk.Notebook(self, style="FocusTree.TNotebook")
        self.notebook.pack(fill="both", expand=True)
        self._build_focus_panel(on_pick_icon, on_complete, on_save, on_more_options, on_show_references)
        self._build_tree_settings_panel()

    def _build_focus_panel(self, on_pick_icon, on_complete, on_save, on_more_options, on_show_references):
        page = ttk.Frame(self.notebook, style="FocusTree.Inspector.TFrame", padding=12)
        self.notebook.add(page, text="Focus")
        self.detail_placeholder = ttk.Label(
            page, text="Click a focus on the canvas to edit its properties.",
            style="FocusTree.SurfaceMuted.TLabel", wraplength=300, justify="left",
        )
        self.detail_placeholder.pack(anchor="w", pady=(4, 0))

        self.detail_form = ttk.Frame(page, style="FocusTree.Inspector.TFrame")
        ttk.Label(self.detail_form, text="FOCUS PROPERTIES",
                  style="FocusTree.SurfaceEyebrow.TLabel").pack(anchor="w")

        ttk.Label(self.detail_form, text="DISPLAY NAME", style="FocusTree.SurfaceEyebrow.TLabel").pack(
            anchor="w", pady=(10, 0)
        )
        self.name_var = tk.StringVar()
        ttk.Entry(self.detail_form, textvariable=self.name_var, style="FocusTree.TEntry").pack(
            fill="x", pady=(3, 0)
        )

        ttk.Label(self.detail_form, text="SCRIPT ID", style="FocusTree.SurfaceEyebrow.TLabel").pack(
            anchor="w", pady=(10, 0)
        )
        self.id_label = ttk.Label(self.detail_form, text="", style="FocusTree.SurfaceMuted.TLabel",
                                  font=(ft.theme.FACE_MONO, 10))
        self.id_label.pack(anchor="w")

        ttk.Label(self.detail_form, text="DESCRIPTION", style="FocusTree.SurfaceEyebrow.TLabel").pack(
            anchor="w", pady=(10, 0)
        )
        self.desc_txt = tk.Text(
            self.detail_form, height=4, wrap="word", font=(ft.theme.FACE_MONO, 9),
            background=ft.CANVAS, foreground=ft.TEXT_HI, insertbackground=ft.ACCENT,
            highlightthickness=1, highlightbackground=ft.LINE_STRONG, highlightcolor=ft.ACCENT,
            relief="flat", padx=7, pady=5,
        )
        self.desc_txt.pack(fill="x", pady=(3, 0))

        icon_row = ttk.Frame(self.detail_form, style="FocusTree.Inspector.TFrame")
        icon_row.pack(fill="x", pady=(10, 0))
        self.detail_icon_label = ttk.Label(icon_row, style="FocusTree.Surface.TLabel")
        self.detail_icon_label.pack(side="left", padx=(0, 8))
        icon_col = ttk.Frame(icon_row, style="FocusTree.Inspector.TFrame")
        icon_col.pack(side="left", fill="x", expand=True)
        ttk.Label(icon_col, text="ICON SPRITE", style="FocusTree.SurfaceEyebrow.TLabel").pack(anchor="w")
        self.icon_var = tk.StringVar()
        icon_entry_row = ttk.Frame(icon_col, style="FocusTree.Inspector.TFrame")
        icon_entry_row.pack(fill="x")
        ttk.Entry(icon_entry_row, textvariable=self.icon_var, style="FocusTree.TEntry").pack(
            side="left", fill="x", expand=True, pady=(3, 0)
        )
        ttk.Button(icon_entry_row, text="...", width=3, style="FocusTree.Secondary.TButton",
                   command=on_pick_icon).pack(side="left", padx=(4, 0), pady=(3, 0))

        pos_row = ttk.Frame(self.detail_form, style="FocusTree.Inspector.TFrame")
        pos_row.pack(fill="x", pady=(10, 0))
        cost_col = ttk.Frame(pos_row, style="FocusTree.Inspector.TFrame")
        cost_col.pack(side="left")
        ttk.Label(cost_col, text="COST", style="FocusTree.SurfaceEyebrow.TLabel").pack(anchor="w")
        self.cost_var = tk.StringVar(value="10")
        ttk.Spinbox(cost_col, from_=1, to=999, textvariable=self.cost_var,
                    width=6, style="FocusTree.TSpinbox").pack(pady=(3, 0))
        grid_col = ttk.Frame(pos_row, style="FocusTree.Inspector.TFrame")
        grid_col.pack(side="left", padx=(16, 0))
        ttk.Label(grid_col, text="GRID POSITION (X / Y)",
                  style="FocusTree.SurfaceEyebrow.TLabel").pack(anchor="w")
        xy_row = ttk.Frame(grid_col, style="FocusTree.Inspector.TFrame")
        xy_row.pack()
        self.x_var = tk.StringVar(value="0")
        self.y_var = tk.StringVar(value="0")
        ttk.Spinbox(xy_row, from_=-99, to=99, textvariable=self.x_var,
                    width=5, style="FocusTree.TSpinbox").pack(side="left", pady=(3, 0))
        ttk.Spinbox(xy_row, from_=-99, to=99, textvariable=self.y_var,
                    width=5, style="FocusTree.TSpinbox").pack(side="left", padx=(4, 0), pady=(3, 0))

        ttk.Label(self.detail_form, text="PREREQUISITE BEHAVIOR",
                  style="FocusTree.SurfaceEyebrow.TLabel").pack(anchor="w", pady=(10, 0))
        self.prereq_mode_label = ttk.Label(self.detail_form, text="", style="FocusTree.SurfaceMuted.TLabel",
                                           wraplength=300, justify="left")
        self.prereq_mode_label.pack(anchor="w")
        ttk.Label(self.detail_form, text="PREREQUISITES", style="FocusTree.SurfaceEyebrow.TLabel").pack(
            anchor="w", pady=(8, 0)
        )
        self.prereq_list_label = ttk.Label(self.detail_form, text="", style="FocusTree.SurfaceMuted.TLabel",
                                           wraplength=300, justify="left", font=(ft.theme.FACE_MONO, 9))
        self.prereq_list_label.pack(anchor="w")
        ttk.Label(self.detail_form, text="MUTUALLY EXCLUSIVE WITH",
                  style="FocusTree.SurfaceEyebrow.TLabel").pack(anchor="w", pady=(8, 0))
        self.mutex_list_label = ttk.Label(self.detail_form, text="", style="FocusTree.SurfaceMuted.TLabel",
                                          wraplength=300, justify="left", font=(ft.theme.FACE_MONO, 9))
        self.mutex_list_label.pack(anchor="w")
        ttk.Label(
            self.detail_form,
            text="Use Link mode on the canvas to add a prerequisite; Save writes staged links to the focus file.",
            style="FocusTree.SurfaceMuted.TLabel", wraplength=300, justify="left",
        ).pack(anchor="w", pady=(3, 0))

        self.detail_state = ttk.Label(self.detail_form, text="", style="FocusTree.SurfaceMuted.TLabel")
        self.detail_state.pack(fill="x", pady=(8, 0))
        self.complete_btn = ttk.Button(self.detail_form, text="Complete this focus",
                                       style="FocusTree.Primary.TButton", command=on_complete)

        button_row = ttk.Frame(self.detail_form, style="FocusTree.Inspector.TFrame")
        button_row.pack(fill="x", pady=(10, 0))
        ttk.Button(button_row, text="Save", style="FocusTree.Primary.TButton", command=on_save).pack(side="left")
        ttk.Button(button_row, text="Triggers/effects...", style="FocusTree.Secondary.TButton",
                   command=on_more_options).pack(side="left", padx=6)
        ttk.Button(button_row, text="Used by...", style="FocusTree.Ghost.TButton",
                   command=on_show_references).pack(side="left")

    def _build_tree_settings_panel(self):
        page = ttk.Frame(self.notebook, style="FocusTree.Inspector.TFrame", padding=12)
        self.notebook.add(page, text="Tree settings")
        ttk.Label(page, text="TREE SETTINGS", style="FocusTree.SurfaceEyebrow.TLabel").pack(anchor="w")
        self.tree_info_label = ttk.Label(
            page, text="Load a focus tree to see its settings.",
            style="FocusTree.SurfaceMuted.TLabel", wraplength=300, justify="left",
        )
        self.tree_info_label.pack(anchor="w", pady=(8, 0))

    def show_tree_settings(self, tree):
        """Display metadata for the newly loaded focus tree."""
        self.tree_info_label.configure(
            text=f"Tree id: {tree['id']}\n"
                 f"File: {os.path.basename(tree['source_file'])}\n"
                 f"Focuses: {len(tree['focuses'])}\n"
                 f"Default tree: {tree.get('default', 'yes')}"
        )

    def show_focus(self, focus_id, focus, *, localisation, mod_root, gfx_index,
                   simulating, completed, available):
        """Populate the inspector from the current focus model."""
        is_new = bool(focus.get("is_new"))
        title = focus.get("title", focus_id) if is_new else localisation.get(focus_id, focus_id)
        description = focus.get("desc", "") if is_new else localisation.get(focus_id + "_desc", "")

        self.detail_placeholder.pack_forget()
        self.detail_form.pack(fill="both", expand=True)
        icon_path = ml.resolve_texture(focus.get("icon", ""), mod_root, gfx_index)
        thumbnail = image_cache.get_thumbnail(icon_path, (48, 48)) if icon_path else None
        self.icon_refs = [thumbnail] if thumbnail else []
        if thumbnail:
            self.detail_icon_label.configure(image=thumbnail, text="")
        else:
            self.detail_icon_label.configure(image="", text="(no icon)")

        self.name_var.set(title)
        self.id_label.configure(text=focus_id)
        self.desc_txt.delete("1.0", "end")
        self.desc_txt.insert("1.0", description)
        self.icon_var.set(focus.get("icon", ""))
        self.cost_var.set(str(focus.get("cost", 10)))
        self.x_var.set(str(focus.get("x", 0)))
        self.y_var.set(str(focus.get("y", 0)))

        groups = focus.get("prerequisite_groups") or []
        if len(groups) <= 1:
            self.prereq_mode_label.configure(text="Require all selected focuses (AND)")
        else:
            self.prereq_mode_label.configure(text=f"Require any one of {len(groups)} groups (OR)")
        self.prereq_list_label.configure(text=", ".join(focus.get("prerequisite", [])) or "(none)")
        self.mutex_list_label.configure(text=", ".join(focus.get("mutually_exclusive", [])) or "(none)")

        if simulating:
            if focus_id in completed:
                self.detail_state.configure(text="Completed", foreground="#4caf50")
                self.complete_btn.pack_forget()
            elif focus_id in available:
                self.detail_state.configure(text="Available - double-click it to complete", foreground="#e0b23c")
                self.complete_btn.pack(fill="x", pady=4)
            else:
                self.detail_state.configure(text="Locked (prerequisites not met)", foreground="#888")
                self.complete_btn.pack_forget()
        else:
            self.detail_state.configure(text="")
            self.complete_btn.pack_forget()
