"""Open Mod tab: load an existing (downloaded) HOI4 mod, render its focus
tree the way the in-game view lays it out (icons, titles, connector lines by
x/y grid position), walk the tree like the game does (completing a focus
hides its mutually exclusive rivals), inspect the country's leaders, and
append brand new focuses.

The original mod files are never rewritten by the focus exporter - new
focuses go to a separate "_additions.txt" that reuses the same focus_tree
id, which is how HOI4 lets multiple files extend one tree.
"""

import os
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from app.state import state
from app import ui_kit
from app import focus_sim
from app import layout as auto_layout_mod
from app import icon_library
from app import mod_export
from app.leader_gallery import LeaderGallery
from app.icon_creator import IconCreator
from app import piece_composer
from app.effect_wizard import EffectWizard
from app import focus_check
from app import searchable_combo
from app import theme
from app import focus_tree_theme
from app.focus_tree_controller import FocusTreeController
from app.focus_tree_theme import (
    NODE_HEIGHT, NODE_SPACING_X, NODE_SPACING_Y, NODE_WIDTH, ORIGIN,
    PLAQUE_SPRITES, STATE_COLORS,
)
from app.focus_tree_view import FocusTreeView

# HOI4's own focus node geometry: a 100x88 goal icon above a 164x50 plaque.
# Kept for reference/undo-safety, no longer used by the default renderer.
GAME_ICON_W, GAME_ICON_H = 100, 88
GAME_PLAQUE_W, GAME_PLAQUE_H = 164, 50
GAME_SPACING_X = 186
GAME_SPACING_Y = 176

DEFAULT_STEAM_WORKSHOP = r"C:\Program Files (x86)\Steam\steamapps\workshop\content\394360"
DEFAULT_BASE_GAME = r"C:\Program Files (x86)\Steam\steamapps\common\Hearts of Iron IV"


class NewFocusDialog(tk.Toplevel):
    def __init__(self, master, existing_ids, mod_root, library_getter=None):
        super().__init__(master)
        self.title("Add New Focus")
        self.result = None
        self.existing_ids = existing_ids
        self.mod_root = mod_root
        self.library_getter = library_getter
        self.resizable(False, False)
        self._build()
        self.grab_set()

    def _pick_from_library(self):
        if not self.library_getter:
            return
        library = self.library_getter()
        if not library:
            messagebox.showerror("No icons", "No focus icons were indexed.")
            return
        picker = icon_library.IconPicker(self, library)
        self.wait_window(picker)
        if picker.result:
            self.icon_var.set(picker.result)

    def _create_icon(self):
        creator = IconCreator(self, self.mod_root, suggested_name="my_custom_focus")
        self.wait_window(creator)
        if creator.result:
            self.icon_var.set(creator.result["sprite"])

    def _compose_icon(self):
        if not piece_composer.pack_available():
            messagebox.showerror(
                "Pack missing",
                "The Ultimate-HOI4-GFX asset pack was not found in the app's assets folder.",
            )
            return
        composer = piece_composer.PieceComposer(self, self.mod_root, kind="focus",
                                                suggested_name="my_custom_focus")
        self.wait_window(composer)
        if composer.result:
            self.icon_var.set(composer.result["sprite"])

    def _build(self):
        fields = [
            ("id", "Focus id"),
            ("title", "Title"),
            ("desc", "Description"),
            ("cost", "Cost (weeks, default 10)"),
        ]
        self.vars = {}
        row = 0
        for key, label in fields:
            ttk.Label(self, text=label).grid(row=row, column=0, sticky="w", padx=8, pady=4)
            var = tk.StringVar()
            ttk.Entry(self, textvariable=var, width=42).grid(row=row, column=1, padx=8, pady=4)
            self.vars[key] = var
            row += 1

        ttk.Label(self, text="Icon").grid(row=row, column=0, sticky="w", padx=8, pady=4)
        icon_frame = ttk.Frame(self)
        icon_frame.grid(row=row, column=1, sticky="w", padx=8, pady=4)
        self.icon_var = tk.StringVar()
        ttk.Entry(icon_frame, textvariable=self.icon_var, width=20).pack(side="left")
        ttk.Button(icon_frame, text="Library...", command=self._pick_from_library).pack(side="left", padx=3)
        ttk.Button(icon_frame, text="Create...", command=self._create_icon).pack(side="left", padx=3)
        ttk.Button(icon_frame, text="Compose...", command=self._compose_icon).pack(side="left", padx=3)
        ttk.Button(icon_frame, text="File...", command=self._browse_icon).pack(side="left", padx=3)
        row += 1

        ttk.Label(self, text="Prerequisites (select any, AND)").grid(row=row, column=0, sticky="nw", padx=8, pady=4)
        self.prereq_list = tk.Listbox(self, selectmode="multiple", height=8, exportselection=False)
        for fid in self.existing_ids:
            self.prereq_list.insert("end", fid)
        self.prereq_list.grid(row=row, column=1, padx=8, pady=4, sticky="w")
        row += 1

        ttk.Label(self, text="completion_reward (raw effect)").grid(row=row, column=0, sticky="nw", padx=8, pady=4)
        self.reward_txt = tk.Text(self, width=42, height=5)
        self.reward_txt.insert("1.0", "add_political_power = 100")
        self.reward_txt.grid(row=row, column=1, padx=8, pady=4)
        ttk.Button(self, text="Wizard...", command=lambda: EffectWizard(self, self.reward_txt, "effect")).grid(row=row, column=2, sticky="n", pady=4)
        row += 1

        ttk.Label(
            self,
            text="Position is set automatically, just under the prerequisite you picked.\n"
                 "Switch the view to \"Mod coordinates\" afterwards to drag it wherever you want.",
            foreground="#888", justify="left",
        ).grid(row=row, column=0, columnspan=2, sticky="w", padx=8, pady=(4, 0))
        row += 1

        btns = ttk.Frame(self)
        btns.grid(row=row, column=0, columnspan=2, pady=10)
        ttk.Button(btns, text="Save", command=self._save).pack(side="left", padx=4)
        ttk.Button(btns, text="Cancel", command=self.destroy).pack(side="left", padx=4)

    def _browse_icon(self):
        path = filedialog.askopenfilename(
            title="Pick an icon texture",
            initialdir=os.path.join(self.mod_root, "gfx") if self.mod_root else None,
            filetypes=[("Textures", "*.dds *.png *.tga"), ("All files", "*.*")],
        )
        if path:
            try:
                rel = os.path.relpath(path, self.mod_root)
            except ValueError:
                rel = path
            self.icon_var.set(rel.replace("\\", "/"))

    def _save(self):
        fid = self.vars["id"].get().strip()
        if not fid:
            messagebox.showerror("Missing id", "Focus id is required.")
            return
        try:
            cost = float(self.vars["cost"].get() or 10)
        except ValueError:
            messagebox.showerror("Bad number", "Cost must be a number.")
            return
        selected = [self.existing_ids[i] for i in self.prereq_list.curselection()]
        self.result = {
            "id": fid,
            "title": self.vars["title"].get().strip() or fid,
            "desc": self.vars["desc"].get().strip(),
            "icon": self.icon_var.get().strip(),
            "x": 0,
            "y": 0,
            "cost": cost,
            "prerequisite": selected,
            "prerequisite_groups": [[p] for p in selected],
            "mutually_exclusive": [],
            "completion_reward_raw": self.reward_txt.get("1.0", "end").strip() or "add_political_power = 100",
            "is_new": True,
        }
        self.destroy()


class EditFocusDialog(tk.Toplevel):
    """Edit the editable fields of an EXISTING focus. Changes go back into
    the original file through focus_surgery, touching only those fields."""

    def __init__(self, master, focus, library_getter=None):
        super().__init__(master)
        self.title(f"Edit focus — {focus['id']}")
        self.resizable(False, False)
        self.focus_data = focus
        self.library_getter = library_getter
        self.result = None
        self._build(focus)
        self.grab_set()

    def _build(self, f):
        row = 0
        ttk.Label(self, text=f"id: {f['id']}", style="Gold.TLabel").grid(
            row=row, column=0, columnspan=3, sticky="w", padx=8, pady=(8, 4))
        row += 1

        ttk.Label(self, text="Icon").grid(row=row, column=0, sticky="w", padx=8, pady=4)
        icon_frame = ttk.Frame(self)
        icon_frame.grid(row=row, column=1, sticky="w", padx=8, pady=4)
        self.icon_var = tk.StringVar(value=f.get("icon", ""))
        ttk.Entry(icon_frame, textvariable=self.icon_var, width=30).pack(side="left")
        ttk.Button(icon_frame, text="Library...", command=self._pick_icon).pack(side="left", padx=3)
        row += 1

        ttk.Label(self, text="Cost (weeks)").grid(row=row, column=0, sticky="w", padx=8, pady=4)
        self.cost_var = tk.StringVar(value=str(f.get("cost", 10)))
        ttk.Entry(self, textvariable=self.cost_var, width=10).grid(row=row, column=1, sticky="w", padx=8, pady=4)
        row += 1

        ttk.Label(self, text="available (raw trigger)").grid(row=row, column=0, sticky="nw", padx=8, pady=4)
        self.available_txt = tk.Text(self, width=46, height=4)
        self.available_txt.insert("1.0", f.get("available_raw", ""))
        self.available_txt.grid(row=row, column=1, padx=8, pady=4)
        ttk.Button(self, text="Wizard...", command=lambda: EffectWizard(self, self.available_txt, "trigger")).grid(
            row=row, column=2, sticky="n", pady=4)
        row += 1

        ttk.Label(self, text="completion_reward (raw effect)").grid(row=row, column=0, sticky="nw", padx=8, pady=4)
        self.reward_txt = tk.Text(self, width=46, height=6)
        self.reward_txt.insert("1.0", f.get("completion_reward_raw", ""))
        self.reward_txt.grid(row=row, column=1, padx=8, pady=4)
        ttk.Button(self, text="Wizard...", command=lambda: EffectWizard(self, self.reward_txt, "effect")).grid(
            row=row, column=2, sticky="n", pady=4)
        row += 1

        ttk.Label(
            self,
            text="Saved straight into the original file — only these fields are touched,\n"
                 "everything else stays byte-for-byte. A one-time .bak backup is kept.",
            style="Muted.TLabel", justify="left",
        ).grid(row=row, column=0, columnspan=3, sticky="w", padx=8, pady=(4, 0))
        row += 1

        btns = ttk.Frame(self)
        btns.grid(row=row, column=0, columnspan=3, pady=10)
        ttk.Button(btns, text="Save to file", style="Accent.TButton", command=self._save).pack(side="left", padx=4)
        ttk.Button(btns, text="Cancel", command=self.destroy).pack(side="left", padx=4)

    def _pick_icon(self):
        if not self.library_getter:
            return
        library = self.library_getter()
        picker = icon_library.IconPicker(self, library)
        self.wait_window(picker)
        if picker.result:
            self.icon_var.set(picker.result)

    def _save(self):
        try:
            cost = float(self.cost_var.get() or 10)
            cost = int(cost) if cost == int(cost) else cost
        except ValueError:
            messagebox.showerror("Bad number", "Cost must be a number.", parent=self)
            return
        self.result = {
            "scalars": {"icon": self.icon_var.get().strip(), "cost": cost},
            "blocks": {
                "completion_reward": self.reward_txt.get("1.0", "end").strip(),
                "available": self.available_txt.get("1.0", "end").strip(),
            },
        }
        self.destroy()


class CopyBranchDialog(tk.Toplevel):
    def __init__(self, master, root_id, branch_size):
        super().__init__(master)
        self.title("Copy branch")
        self.resizable(False, False)
        self.result = None
        pad = {"padx": 10, "pady": 4}
        ttk.Label(self, text=f"Copying '{root_id}' + its whole branch ({branch_size} focuses).").grid(
            row=0, column=0, columnspan=2, sticky="w", **pad)
        ttk.Label(self, text="Replace prefix").grid(row=1, column=0, sticky="w", **pad)
        prefix = root_id.split("_")[0] + "_" if "_" in root_id else ""
        self.from_var = tk.StringVar(value=prefix)
        ttk.Entry(self, textvariable=self.from_var, width=16).grid(row=1, column=1, sticky="w", **pad)
        ttk.Label(self, text="with prefix").grid(row=2, column=0, sticky="w", **pad)
        self.to_var = tk.StringVar(value="MYX_")
        ttk.Entry(self, textvariable=self.to_var, width=16).grid(row=2, column=1, sticky="w", **pad)
        ttk.Label(self, text="Copied focuses become new (green) and export via the additions file.",
                  style="Muted.TLabel").grid(row=3, column=0, columnspan=2, sticky="w", **pad)
        btns = ttk.Frame(self)
        btns.grid(row=4, column=0, columnspan=2, pady=10)
        ttk.Button(btns, text="Copy", style="Accent.TButton", command=self._ok).pack(side="left", padx=4)
        ttk.Button(btns, text="Cancel", command=self.destroy).pack(side="left", padx=4)
        self.grab_set()

    def _ok(self):
        self.result = (self.from_var.get(), self.to_var.get())
        self.destroy()


def _folder_size(path):
    total = 0
    for dirpath, _dirs, files in os.walk(path):
        for name in files:
            try:
                total += os.path.getsize(os.path.join(dirpath, name))
            except OSError:
                pass
    return total


def _fmt_size(num_bytes):
    if num_bytes >= 1024 ** 3:
        return f"{num_bytes / 1024 ** 3:.1f} GB"
    if num_bytes >= 1024 ** 2:
        return f"{num_bytes / 1024 ** 2:.0f} MB"
    return f"{num_bytes / 1024:.0f} KB"


class PlayExportDialog(tk.Toplevel):
    """Write the edits somewhere the HOI4 launcher will pick them up."""

    def __init__(self, master, mod_root, own_files):
        super().__init__(master)
        self.title("Play your version in HOI4")
        self.resizable(False, False)
        self.mod_root = mod_root
        self.own_files = own_files
        self._build()
        self.grab_set()
        self._measure_copy_size()

    def _build(self):
        source_name = os.path.basename(self.mod_root)
        ttk.Label(
            self,
            text="This writes straight to your HOI4 mod folder so you can launch it - no "
                 "Steam Workshop upload needed. Workshop is only for sharing the mod publicly.",
            foreground="#888", wraplength=520, justify="left",
        ).grid(row=0, column=0, columnspan=2, sticky="w", padx=10, pady=(10, 0))
        ttk.Label(self, text="Mod name shown in the launcher").grid(row=1, column=0, sticky="w", padx=10, pady=6)
        self.name_var = tk.StringVar(value=f"{source_name} - My Edits")
        ttk.Entry(self, textvariable=self.name_var, width=46).grid(row=1, column=1, padx=10, pady=6)

        ttk.Label(self, text="What to export").grid(row=2, column=0, sticky="nw", padx=10, pady=6)
        self.mode = tk.StringVar(value="submod")
        box = ttk.Frame(self)
        box.grid(row=2, column=1, sticky="w", padx=10, pady=6)
        ttk.Radiobutton(
            box, text=f"Submod — only your {len(self.own_files)} own files (recommended)",
            variable=self.mode, value="submod",
        ).pack(anchor="w")
        ttk.Label(
            box,
            text="Small and instant. In the launcher enable the original mod AND this one,\n"
                 "with this one ordered after it.",
            foreground="#888", justify="left",
        ).pack(anchor="w", padx=22, pady=(0, 6))
        ttk.Radiobutton(
            box, text="Full copy — duplicate the entire mod with your edits baked in",
            variable=self.mode, value="copy",
        ).pack(anchor="w")
        self.copy_size_label = ttk.Label(
            box,
            text="Self-contained, but this duplicates every file in the source mod "
                 "(measuring size...) and it will not\nreceive Workshop updates. Enable only "
                 "this one in the launcher.",
            foreground="#888", justify="left",
        )
        self.copy_size_label.pack(anchor="w", padx=22)

        user_dir = mod_export.find_user_dir()
        ttk.Label(
            self,
            text=f"Destination: {os.path.join(user_dir, 'mod') if user_dir else 'HOI4 user folder NOT FOUND'}",
            foreground="#888" if user_dir else "#c05050", wraplength=520, justify="left",
        ).grid(row=3, column=0, columnspan=2, sticky="w", padx=10, pady=(4, 0))

        self.status = ttk.Label(self, text="", foreground="#2a7a2a", wraplength=520, justify="left")
        self.status.grid(row=4, column=0, columnspan=2, sticky="w", padx=10, pady=6)

        btns = ttk.Frame(self)
        btns.grid(row=5, column=0, columnspan=2, pady=10)
        self.export_btn = ttk.Button(btns, text="Export", command=self._export)
        self.export_btn.pack(side="left", padx=4)
        ttk.Button(btns, text="Close", command=self.destroy).pack(side="left", padx=4)

        self._size_measured = None

    def _measure_copy_size(self):
        """Walking the whole source mod to size it is exactly the kind of
        filesystem scan that shouldn't happen on the UI thread - do it in
        the background and fill in the real number once it's known, so the
        warning says "this will copy 1.8 GB" instead of a vague guess."""
        mod_root = self.mod_root

        def work():
            try:
                nbytes = _folder_size(mod_root)
            except OSError:
                return
            self.after(0, lambda: self._apply_copy_size(nbytes))

        threading.Thread(target=work, daemon=True).start()

    def _apply_copy_size(self, nbytes):
        if not self.copy_size_label.winfo_exists():
            return
        self._size_measured = f"~{_fmt_size(nbytes)}"
        self.copy_size_label.config(
            text=f"Self-contained, but this duplicates every file in the source mod "
                 f"({self._size_measured}) and it will not\n"
                 "receive Workshop updates. Enable only this one in the launcher."
        )

    def _export(self):
        name = self.name_var.get().strip()
        if not name:
            messagebox.showerror("No name", "Give the mod a name.")
            return

        mode = self.mode.get()
        if mode == "submod" and not self.own_files:
            messagebox.showerror(
                "Nothing of your own",
                "No files created by this tool were found in the mod.\n"
                "Add a focus or leader and export it first, or choose Full copy.",
            )
            return

        if mode == "copy":
            size_note = (self._size_measured or "size still being measured")
            if not messagebox.askyesno(
                "Copy the whole mod?",
                f"This duplicates every file in the mod ({size_note}), "
                "which can take a few minutes.\n\nContinue?",
            ):
                return

        self.export_btn.state(["disabled"])
        self.status.config(text="Exporting...")
        self.update_idletasks()

        try:
            dest, mod_file, copied = mod_export.export(
                self.mod_root, name, mode=mode, own_files=self.own_files,
                progress=lambda msg: (self.status.config(text=msg), self.update_idletasks()),
            )
        except Exception as exc:
            self.status.config(text=f"Failed: {exc}", foreground="#c05050")
            self.export_btn.state(["!disabled"])
            return

        order = ("Enable the original mod first, then this one." if mode == "submod"
                 else "Enable only this mod (not the original).")
        self.status.config(
            text=f"Done — {copied} files written to {dest}\n"
                 f"Descriptor: {os.path.basename(mod_file)}\n"
                 "If the Paradox Launcher was already open, close and reopen it (or use its "
                 f"own refresh) to see this mod. No Workshop upload needed. {order}",
            foreground="#2a7a2a",
        )
        self.export_btn.state(["!disabled"])


class ShiftBranchDialog(tk.Toplevel):
    """`self.result` = (dx, dy) grid offset, or None if cancelled."""

    def __init__(self, master, root_id, branch_size):
        super().__init__(master)
        self.title("Shift branch")
        self.resizable(False, False)
        self.result = None
        pad = {"padx": 10, "pady": 4}

        ttk.Label(self, text=f"Moving '{root_id}' + its whole branch ({branch_size} focuses).").grid(
            row=0, column=0, columnspan=2, sticky="w", **pad)
        ttk.Label(self, text="Shift X by", style="FieldLabel.TLabel").grid(row=1, column=0, sticky="w", **pad)
        self.dx_var = tk.StringVar(value="1")
        ttk.Spinbox(self, from_=-99, to=99, textvariable=self.dx_var, width=6).grid(row=1, column=1, sticky="w", **pad)
        ttk.Label(self, text="Shift Y by", style="FieldLabel.TLabel").grid(row=2, column=0, sticky="w", **pad)
        self.dy_var = tk.StringVar(value="0")
        ttk.Spinbox(self, from_=-99, to=99, textvariable=self.dy_var, width=6).grid(row=2, column=1, sticky="w", **pad)
        ttk.Label(self, text="Positive X moves right, positive Y moves down.",
                  style="Muted.TLabel").grid(row=3, column=0, columnspan=2, sticky="w", **pad)

        btns = ttk.Frame(self)
        btns.grid(row=4, column=0, columnspan=2, pady=10)
        ttk.Button(btns, text="Shift", style="Accent.TButton", command=self._ok).pack(side="left", padx=4)
        ttk.Button(btns, text="Cancel", command=self.destroy).pack(side="left", padx=4)
        self.grab_set()

    def _ok(self):
        try:
            self.result = (int(self.dx_var.get()), int(self.dy_var.get()))
        except ValueError:
            messagebox.showerror("Bad number", "X and Y offsets must be whole numbers.", parent=self)
            return
        self.destroy()


class ModBrowserTab(ttk.Frame):
    def __init__(self, master):
        focus_tree_theme.install(master)
        super().__init__(master, style="FocusTree.TFrame", padding=0)
        self.controller = FocusTreeController(self, DEFAULT_BASE_GAME, DEFAULT_STEAM_WORKSHOP)
        self.focus_tree_data = self.controller.data  # temporary compatibility alias
        self.mod_root = ""
        self.gfx_index = {}
        self.loc = {}
        self.characters = {}
        self.tree_files = []
        self._tree_items = []
        self.current_tree = None
        self.new_focuses = []
        self.node_pos = {}
        self.icon_refs = []
        self.zoom = 1.0
        self.completed = set()
        self.sim_mode = tk.BooleanVar(value=False)
        self._build()

    # ---- layout ----

    def _build(self):
        callbacks = {
            "refresh_mods": self._refresh_workshop_mods,
            "load_mod": self._load_selected_workshop_mod,
            "browse_mod": self._browse_mod,
            "load_tree": self._load_selected_tree,
            "leaders": self._open_leader_gallery,
            "find_next": self._find_next,
            "find_changed": self._update_matches,
            "sim_toggle": self._on_sim_toggle,
            "reset_progress": self._reset_progress,
            "layout_changed": self._render_tree,
            "zoom": self._toolbar_zoom,
            "mode_changed": self._set_canvas_mode,
            "help": lambda: ui_kit.open_help(self, "open_mod"),
            "outline_select": self._on_outline_select,
            "canvas_zoom": lambda factor: self._set_zoom(self.zoom * factor),
            "canvas_press": self._on_canvas_press,
            "canvas_drag": self._on_canvas_drag,
            "pick_icon": self._pick_detail_icon,
            "complete": self._complete_selected,
            "save": self._save_focus_properties,
            "more_options": self._open_more_options,
            "show_references": self._show_references,
            "add": self._add_focus,
            "copy_branch": self._copy_branch,
            "shift_branch": self._shift_branch,
            "tidy": self._tidy_tree,
            "export_png": self._export_png,
            "save_moved": self._save_moved,
            "icon_library": self._open_icon_library,
            "export_additions": self._export_additions,
            "play_export": self._open_play_export,
            "publish": self._open_publish,
        }
        self.focus_tree_view = FocusTreeView(
            self, tree_labels=lambda: [item[0] for item in self._tree_items], callbacks=callbacks,
        )
        self.focus_tree_view.pack(fill="both", expand=True)
        self.toolbar = self.focus_tree_view.toolbar
        self.sidebar = self.focus_tree_view.sidebar
        self.tree_canvas = self.focus_tree_view.tree_canvas
        self.inspector = self.focus_tree_view.inspector
        self.action_bar = self.focus_tree_view.action_bar
        for name in (
            "mod_combo", "mod_label", "tree_combo", "tag_var", "find_var", "find_label",
            "sim_mode", "layout_mode", "progress_label", "canvas_mode", "mode_buttons", "mode_hint",
        ):
            setattr(self, name, getattr(self.toolbar, name))
        for name in ("outline_tree", "outline_count"):
            setattr(self, name, getattr(self.sidebar, "tree" if name == "outline_tree" else "count_label"))
        self.canvas = self.tree_canvas.canvas
        self.minimap = self.tree_canvas.minimap
        for name in (
            "side_notebook", "detail_placeholder", "detail_form", "name_var", "id_label", "desc_txt",
            "detail_icon_label", "icon_var", "cost_var", "x_var", "y_var", "prereq_mode_label",
            "prereq_list_label", "mutex_list_label", "detail_state", "complete_btn", "tree_info_label",
        ):
            setattr(self, name, getattr(self.inspector, name.replace("side_notebook", "notebook")))
        self.status = self.action_bar.status
        self.warning_label = self.action_bar.warning_label
        self.unsaved_label = self.action_bar.unsaved_label
        self._link_from = None
        self._set_canvas_mode("select")
        self.bind_all("<F6>", self._on_f6)
        self.bind_all("<F7>", self._on_f7)
        self.bind_all("<F8>", self._on_f8)

        self.selected_id = None
        self._editing_id = None
        self._workshop_mods = []
        self._refresh_workshop_mods()

    # ---- mod loading ----

    def _refresh_workshop_mods(self):
        self.controller.refresh_workshop_mods()

    def _load_selected_workshop_mod(self):
        idx = self.mod_combo.current()
        if idx < 0 or not self._workshop_mods:
            messagebox.showerror("No mod selected", "Pick a mod from the list first (or use Browse Folder).")
            return
        self.load_mod_async(self._workshop_mods[idx]["path"])

    def _browse_mod(self):
        initial = DEFAULT_STEAM_WORKSHOP if os.path.isdir(DEFAULT_STEAM_WORKSHOP) else None
        path = filedialog.askdirectory(title="Select the mod's root folder", initialdir=initial)
        if path:
            self.load_mod_async(path)

    def load_mod_async(self, path):
        self.controller.load_mod_async(path)
    def _poll_load(self):
        self.controller.poll_load()

    def _apply_load(self, result):
        self.controller.apply_load(result)

    def _load_mod(self, path):
        """Synchronous variant, kept for tests and simple callers."""
        self.controller.load_mod_sync(path)
    def _load_selected_tree(self):
        self.controller.load_selected_tree()

    # ---- view controls ----

    def _on_wheel(self, event):
        self.canvas.yview_scroll(-1 * (event.delta // 120), "units")
        self._render_minimap()

    def _on_ctrl_wheel(self, event):
        self._set_zoom(self.zoom * (1.1 if event.delta > 0 else 1 / 1.1))

    def _set_zoom(self, value):
        self.zoom = max(0.3, min(2.5, value))
        self._render_tree()

    def _toolbar_zoom(self, factor):
        self._set_zoom(1.0 if factor is None else self.zoom * factor)

    def _on_sim_toggle(self):
        self.controller.on_simulation_toggled()

    def _reset_progress(self):
        self.controller.reset_simulation()

    # ---- find ----

    def _find_matches(self):
        return self.controller.find_matches()

    def _update_matches(self):
        self.controller.update_matches()

    def _clear_find(self):
        self.controller.clear_find()

    def _find_next(self):
        self.controller.find_next()

    def _scroll_to(self, focus_id):
        self.tree_canvas.scroll_to_node(self.node_pos, focus_id)

    # ---- positioning ----

    def _all_focuses(self):
        return list(self.current_tree["focuses"]) + list(self.new_focuses) if self.current_tree else []

    def _mod_grid(self, focuses):
        """Grid coords as authored, honouring relative_position_id chains.
        An anchor that lives in another file can't be resolved, so those
        focuses fall back to their raw offsets - which is exactly why the
        auto layout exists."""
        by_id = {f["id"]: f for f in focuses}
        grid = {}
        pending = list(focuses)

        for _ in range(len(focuses) + 1):
            still = []
            for f in pending:
                rel = f.get("relative_position_id")
                if rel and rel in by_id and rel != f["id"]:
                    if rel in grid:
                        bx, by = grid[rel]
                        grid[f["id"]] = (bx + f["x"], by + f["y"])
                    else:
                        still.append(f)
                else:
                    grid[f["id"]] = (f["x"], f["y"])
            pending = still
            if not pending:
                break
        for f in pending:
            grid[f["id"]] = (f["x"], f["y"])
        return grid

    def _resolve_positions(self, focuses):
        if self.layout_mode.get() == "auto":
            grid = auto_layout_mod.auto_layout(focuses)
        else:
            grid = self._mod_grid(focuses)
            # only the authored view can collide, so spread exact duplicates
            seen = {}
            spread = {}
            for fid, cell in grid.items():
                n = seen.get(cell, 0)
                seen[cell] = n + 1
                spread[fid] = (cell[0] + n * 0.35, cell[1])
            grid = spread

        self._grid = grid
        sx = NODE_SPACING_X * self.zoom
        sy = NODE_SPACING_Y * self.zoom
        return {fid: (ORIGIN + gx * sx, ORIGIN + gy * sy) for fid, (gx, gy) in grid.items()}

    def _plaque_path(self, state):
        """The game's own titlebar texture for a focus in the given state."""
        sprite = PLAQUE_SPRITES.get(state, PLAQUE_SPRITES["locked"])
        path = os.path.join(
            DEFAULT_BASE_GAME, "gfx", "interface", "focusview", "titlebar", sprite + ".dds"
        )
        return path if os.path.isfile(path) else None

    # ---- node drawing ----

    def _render_tree(self):
        self.canvas.delete("all")
        self.icon_refs = []
        if not self.current_tree:
            return

        focuses = self._all_focuses()
        playing = self.sim_mode.get()
        if playing:
            hidden, available = focus_sim.compute_states(focuses, self.completed)
        else:
            hidden, available = set(), set()

        visible = [focus for focus in focuses if focus["id"] not in hidden]
        self.node_pos = self._resolve_positions(visible)
        self._by_id = {focus["id"]: focus for focus in focuses}
        node_states = {
            focus["id"]: (focus_sim.state_of(focus["id"], self.completed, hidden, available)
                          if playing else "available")
            for focus in visible
        }
        self.icon_refs = self.tree_canvas.render_scene(
            focuses=focuses,
            visible=visible,
            node_positions=self.node_pos,
            focus_by_id=self._by_id,
            node_states=node_states,
            playing=playing,
            completed=self.completed,
            selected_id=self.selected_id,
            matches=getattr(self, "_matches", ()),
            mod_root=self.mod_root,
            gfx_index=self.gfx_index,
            localisation=self.loc,
            node_width=NODE_WIDTH,
            node_height=NODE_HEIGHT,
            zoom=self.zoom,
            state_colors=STATE_COLORS,
            on_node_press=self._on_node_press,
            on_node_drag=self._on_node_drag,
            on_node_release=self._on_node_release,
            on_node_double=self._on_node_double,
        )

        if playing:
            self.progress_label.config(
                text=f"{len(self.completed)} completed · {len(available)} available · {len(hidden)} closed off"
            )
        else:
            self.progress_label.config(text=f"{len(focuses)} focuses")

        self._available_now = available
        self._render_outline(focuses, self._by_id)
        self._update_warning_label(focus_check.check(focuses))
        self._update_unsaved_label()
    def _update_unsaved_label(self):
        if not hasattr(self, "unsaved_label"):
            return
        moved = len(getattr(self, "_moved", ()))
        added = len(self.new_focuses)
        if not moved and not added:
            self.unsaved_label.config(text="")
            return
        parts = []
        if moved:
            parts.append(f"{moved} moved")
        if added:
            parts.append(f"{added} new")
        self.unsaved_label.config(text=f"unsaved changes: {', '.join(parts)}")

    def _render_outline(self, focuses, by_id):
        self.sidebar.render(focuses, by_id, self.selected_id)

    def _on_outline_select(self, event):
        self.controller.on_outline_selected()

    def _center_on_node(self, fid):
        self.tree_canvas.center_on_node(self.node_pos, fid)

    # ---- minimap ----

    def _render_minimap(self):
        self.tree_canvas.set_minimap_data(self.node_pos, getattr(self, "_by_id", {}))
        self.tree_canvas.render_minimap()
    # ---- interaction ----

    def _can_drag(self, focus_id):
        return self.controller.can_drag(focus_id)

    def _set_canvas_mode(self, mode):
        self.controller.set_canvas_mode(mode)

    def _on_canvas_press(self, event):
        self.controller.on_canvas_press(event)

    def _on_canvas_drag(self, event):
        self.controller.on_canvas_drag(event)

    def _on_node_press(self, event, focus_id):
        self.controller.on_node_press(event, focus_id)

    def _on_node_drag(self, event, focus_id):
        self.controller.on_node_drag(event, focus_id)

    def _on_node_release(self, event, focus_id):
        self.controller.on_node_release(event, focus_id)
    def _save_moved(self):
        self.controller.save_moved()
    def _on_node_double(self, focus_id):
        self.controller.on_node_double(focus_id)
    def _edit_focus(self, focus_id):
        f = self._by_id.get(focus_id)
        if not f:
            return
        if f.get("is_new"):
            # our own pending focus - edit the dict directly
            dlg = EditFocusDialog(self, {
                "id": f["id"], "icon": f.get("icon", ""), "cost": f.get("cost", 10),
                "available_raw": "", "completion_reward_raw": f.get("completion_reward_raw", ""),
            }, library_getter=self._get_icon_library)
            self.wait_window(dlg)
            if dlg.result:
                self.controller.apply_focus_edit(focus_id, dlg.result)
            return

        dlg = EditFocusDialog(self, f, library_getter=self._get_icon_library)
        self.wait_window(dlg)
        if not dlg.result:
            return
        self.controller.apply_focus_edit(focus_id, dlg.result)

    def _show_references(self):
        """Everything that mentions this focus - other focuses requiring it,
        events/decisions that check or complete it. Right-click on the canvas
        is already pan, so this lives on the properties panel instead."""
        if not self.selected_id:
            messagebox.showerror("Nothing selected", "Click a focus on the canvas first.")
            return
        if not state.is_loaded:
            messagebox.showerror("No mod", "Open a mod first.")
            return
        from app import references
        references.open_dialog(self, state.mod_root, self.selected_id)

    def _export_png(self):
        if not self.current_tree:
            messagebox.showerror("No tree", "Load a focus tree first.")
            return
        path = filedialog.asksaveasfilename(
            title="Save focus tree image",
            defaultextension=".png",
            initialfile=f"{self.current_tree.get('id', 'focus_tree')}.png",
            filetypes=[("PNG image", "*.png")],
        )
        if not path:
            return
        self.controller.export_png(path)

    def _tidy_tree(self):
        self.controller.tidy_tree()

    def _branch_ids(self, root_id, focuses):
        return self.controller.branch_ids(root_id, focuses)
    def _shift_branch(self):
        """Move a whole branch by a grid offset in one go. Inserting a new
        column into an existing tree otherwise means dragging every focus to
        the right of it by hand, one at a time."""
        if not self.selected_id or not self.current_tree:
            messagebox.showerror("Nothing selected", "Click the branch's root focus first.")
            return
        if self.layout_mode.get() == "auto":
            messagebox.showerror(
                "Switch layout first",
                "Shifting edits the authored x/y, so set Layout to \"mod coordinates\" "
                "first - in auto layout the positions on screen aren't the ones in the file.")
            return
        focuses = self._all_focuses()
        if self.selected_id not in {focus["id"] for focus in focuses}:
            return
        branch = self._branch_ids(self.selected_id, focuses)

        dlg = ShiftBranchDialog(self, self.selected_id, len(branch))
        self.wait_window(dlg)
        if not dlg.result:
            return
        dx, dy = dlg.result
        if not dx and not dy:
            return

        self.controller.shift_branch(self.selected_id, dx, dy)

    def _copy_branch(self):
        if not self.selected_id or not self.current_tree:
            messagebox.showerror("Nothing selected", "Click the branch's root focus first.")
            return
        root_id = self.selected_id
        focuses = self._all_focuses()
        if root_id not in {focus["id"] for focus in focuses}:
            return

        branch = self._branch_ids(root_id, focuses)

        dlg = CopyBranchDialog(self, root_id, len(branch))
        self.wait_window(dlg)
        if not dlg.result:
            return
        old_prefix, new_prefix = dlg.result

        self.controller.copy_branch(root_id, old_prefix, new_prefix)

    def _complete_selected(self):
        self.controller.complete_selected()

    def _show_details(self, focus_id):
        f = self._by_id.get(focus_id)
        if not f:
            return
        self._editing_id = focus_id
        self.inspector.show_focus(
            focus_id, f,
            localisation=self.loc,
            mod_root=self.mod_root,
            gfx_index=self.gfx_index,
            simulating=self.sim_mode.get(),
            completed=self.completed,
            available=getattr(self, "_available_now", set()),
        )

    def _pick_detail_icon(self):
        library = self._get_icon_library()
        if not library:
            messagebox.showerror("No icons", "No focus icons were indexed.")
            return
        picker = icon_library.IconPicker(self, library)
        self.wait_window(picker)
        if picker.result:
            self.icon_var.set(picker.result)

    def _open_more_options(self):
        if self._editing_id:
            self._edit_focus(self._editing_id)

    def _save_focus_properties(self):
        fid = self._editing_id
        f = self._by_id.get(fid) if fid else None
        if not f:
            messagebox.showerror("Nothing selected", "Click a focus on the canvas first.")
            return
        try:
            cost = float(self.cost_var.get() or 10)
            cost = int(cost) if cost == int(cost) else cost
            x = int(self.x_var.get() or 0)
            y = int(self.y_var.get() or 0)
        except ValueError:
            messagebox.showerror("Bad number", "Cost and grid position must be numbers.")
            return
        icon = self.icon_var.get().strip()
        name = self.name_var.get().strip() or fid
        desc = self.desc_txt.get("1.0", "end").strip()

        self.controller.save_focus_properties(
            fid, icon=icon, cost=cost, x=x, y=y, name=name, desc=desc
        )

    def _on_f6(self, event=None):
        if not self.winfo_ismapped():
            return
        self._run_validate()
        return "break"

    def _on_f7(self, event=None):
        if not self.winfo_ismapped():
            return
        self.controller.toggle_simulation()
        return "break"

    def _on_f8(self, event=None):
        if not self.winfo_ismapped():
            return
        self._export_additions()
        return "break"

    def _run_validate(self):
        self.controller.run_tree_validation()

    def _update_warning_label(self, issues):
        self.controller.update_warning_label(issues)

    def _get_icon_library(self):
        """Built once on demand - scanning every mod's .gfx takes a moment."""
        if getattr(self, "_icon_library", None) is None:
            self.status.config(text="Indexing focus icons from the base game and every installed mod...")
            self.update_idletasks()
            self._icon_library = icon_library.build_library(
                DEFAULT_BASE_GAME, DEFAULT_STEAM_WORKSHOP,
                extra_roots=[self.mod_root] if self.mod_root else (),
            )
            self.status.config(text=f"Indexed {len(self._icon_library)} focus icons.")
        return self._icon_library

    def _open_icon_library(self):
        library = self._get_icon_library()
        if not library:
            messagebox.showerror("No icons", "No focus icons were found.")
            return
        picker = icon_library.IconPicker(self, library)
        self.wait_window(picker)
        if picker.result and self.selected_id:
            f = self._by_id.get(self.selected_id)
            if f and f.get("is_new"):
                f["icon"] = picker.result
                self._render_tree()
                self.status.config(text=f"Set icon of {self.selected_id} to {picker.result}")
            else:
                self.status.config(text=f"Copied icon name: {picker.result} (select one of your own focuses to apply it)")

    def _open_publish(self):
        if not self.mod_root:
            messagebox.showerror("No mod", "Load a mod first.")
            return
        if not self._precheck_before_export():
            return
        from app.publish import PublishDialog
        PublishDialog(self, state.mod_root, state.mod_name)

    def _open_play_export(self):
        if not self.mod_root:
            messagebox.showerror("No mod", "Load a mod first.")
            return
        if not self._precheck_before_export():
            return
        PlayExportDialog(self, self.mod_root, self._own_files())

    def _precheck_before_export(self):
        return self.controller.precheck_before_export()

    def _own_files(self):
        """Absolute paths this tool wrote into the mod, so a submod can ship
        exactly those and nothing else."""
        out = set()
        if not self.mod_root:
            return out
        candidates = [
            os.path.join(self.mod_root, "common", "national_focus"),
            os.path.join(self.mod_root, "common", "characters"),
            os.path.join(self.mod_root, "common", "decisions"),
            os.path.join(self.mod_root, "common", "ideas"),
            os.path.join(self.mod_root, "common", "country_tags"),
            os.path.join(self.mod_root, "common", "countries"),
            os.path.join(self.mod_root, "history", "countries"),
            os.path.join(self.mod_root, "gfx", "flags"),
            os.path.join(self.mod_root, "localisation", "english"),
            os.path.join(self.mod_root, "interface"),
            os.path.join(self.mod_root, "gfx", "interface", "goals"),
            os.path.join(self.mod_root, "gfx", "leaders"),
        ]
        for folder in candidates:
            if not os.path.isdir(folder):
                continue
            for dirpath, _, filenames in os.walk(folder):
                for filename in filenames:
                    if "_additions" in filename or filename.startswith("zz_"):
                        out.add(os.path.join(dirpath, filename))
        # plus everything the manifest remembers (country files, flags,
        # colors.txt - names that carry no recognisable marker)
        out |= mod_export.recorded_files(self.mod_root)
        return out

    def _open_leader_gallery(self):
        if not self.mod_root:
            messagebox.showerror("No mod", "Load a mod first.")
            return
        tag = self.tag_var.get().strip().upper()
        if not tag:
            messagebox.showerror("No country", "Type a 3-letter country tag first (e.g. TUR).")
            return
        LeaderGallery(self, self.mod_root, self.gfx_index, self.loc, self.characters, tag)

    # ---- adding new content ----

    def _add_focus(self):
        if not self.current_tree:
            messagebox.showerror("No tree loaded", "Load a focus tree first.")
            return
        existing_ids = [f["id"] for f in self._all_focuses()]
        dlg = NewFocusDialog(self, existing_ids, self.mod_root, library_getter=self._get_icon_library)
        self.wait_window(dlg)
        if dlg.result:
            self.controller.add_focus(dlg.result)

    def _auto_place(self, focus):
        self.controller.auto_place_focus(focus)

    def _export_additions(self):
        self.controller.export_additions()
