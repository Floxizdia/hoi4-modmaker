"""Composition root for the Focus Tree screen's visible widgets.

The screen keeps its current callbacks and public widget aliases during the
migration, while this module owns the stable toolbar/sidebar/canvas/inspector
layout used by the Focus Tree editor.
"""

from tkinter import ttk

from app.focus_tree_canvas import FocusTreeCanvas
from app.focus_tree_inspector import FocusTreeInspector
from app.focus_tree_sidebar import FocusTreeSidebar
from app.focus_tree_toolbar import FocusTreeActionBar, FocusTreeToolbar


class FocusTreeView(ttk.Frame):
    """Build the complete Focus Tree layout from focused reusable widgets."""

    def __init__(self, parent, *, tree_labels, callbacks):
        super().__init__(parent, style="FocusTree.TFrame")
        self._build(tree_labels, callbacks)

    def _build(self, tree_labels, callbacks):
        self.toolbar = FocusTreeToolbar(
            self,
            tree_labels=tree_labels,
            on_refresh_mods=callbacks["refresh_mods"],
            on_load_mod=callbacks["load_mod"],
            on_browse_mod=callbacks["browse_mod"],
            on_load_tree=callbacks["load_tree"],
            on_leaders=callbacks["leaders"],
            on_find_next=callbacks["find_next"],
            on_find_changed=callbacks["find_changed"],
            on_sim_toggle=callbacks["sim_toggle"],
            on_reset_progress=callbacks["reset_progress"],
            on_layout_changed=callbacks["layout_changed"],
            on_zoom=callbacks["zoom"],
            on_mode_changed=callbacks["mode_changed"],
            on_help=callbacks["help"],
        )
        self.toolbar.pack(fill="x")
        ttk.Frame(self, style="FocusTree.Sash.TFrame", height=1).pack(fill="x", pady=(8, 0))

        body = ttk.Frame(self, style="FocusTree.Workspace.TFrame", padding=(0, 10, 0, 8))
        body.pack(fill="both", expand=True)
        body.rowconfigure(0, weight=1)
        body.columnconfigure(2, weight=1)
        self.sidebar = FocusTreeSidebar(body, on_select=callbacks["outline_select"])
        self.sidebar.grid(row=0, column=0, sticky="ns")
        ttk.Frame(body, style="FocusTree.Sash.TFrame", width=1).grid(row=0, column=1, sticky="ns", padx=10)

        self.tree_canvas = FocusTreeCanvas(
            body,
            on_zoom=callbacks["canvas_zoom"],
            on_canvas_press=callbacks["canvas_press"],
            on_canvas_drag=callbacks["canvas_drag"],
        )
        self.tree_canvas.grid(row=0, column=2, sticky="nsew")
        ttk.Frame(body, style="FocusTree.Sash.TFrame", width=1).grid(row=0, column=3, sticky="ns", padx=10)

        self.inspector = FocusTreeInspector(
            body,
            on_pick_icon=callbacks["pick_icon"],
            on_complete=callbacks["complete"],
            on_save=callbacks["save"],
            on_more_options=callbacks["more_options"],
            on_show_references=callbacks["show_references"],
        )
        self.inspector.grid(row=0, column=4, sticky="ns")

        self.action_bar = FocusTreeActionBar(
            self,
            on_add=callbacks["add"],
            on_copy_branch=callbacks["copy_branch"],
            on_shift_branch=callbacks["shift_branch"],
            on_tidy=callbacks["tidy"],
            on_export_png=callbacks["export_png"],
            on_save_moved=callbacks["save_moved"],
            on_icon_library=callbacks["icon_library"],
            on_export_additions=callbacks["export_additions"],
            on_import_drawio=callbacks["import_drawio"],
            on_play_export=callbacks["play_export"],
            on_publish=callbacks["publish"],
        )
        self.action_bar.pack(fill="x")
