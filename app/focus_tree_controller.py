"""Controller for the Focus Tree screen's mod and tree loading lifecycle.

Stage 2 keeps ``ModBrowserTab`` as the visible screen.  The controller owns
the data service and coordinates loading results into that existing view;
canvas, inspector, editing, and export behaviours remain in the screen until
their later extraction stages.
"""

import copy
import os
import shutil
from tkinter import messagebox

from app import focus_surgery
from app import focus_check
from app import focus_tree_theme as ft
from app import layout as auto_layout_mod
from app import loc_surgery
from app import pds
from app import searchable_combo
from app import theme
from app import undo
from app import validator
from app.focus_tree_data import FocusTreeData
from app.state import state


class FocusTreeController:
    """Drive loading state without making the current UI depend on new widgets."""

    def __init__(self, view, base_game, workshop_root):
        self.view = view
        self.data = FocusTreeData(base_game)
        self.workshop_root = workshop_root
        self._link_from = None
        self._drag_state = None

    # ---- staged-editor undo -------------------------------------------------

    def _model_snapshot(self):
        """Capture only the Focus Tree state that may exist before a save."""
        view = self.view
        return {
            "focuses": copy.deepcopy(view.current_tree.get("focuses", [])),
            "new_focuses": copy.deepcopy(view.new_focuses),
            "moved": set(getattr(view, "_moved", set())),
            "relationship_dirty": set(getattr(view, "_relationship_dirty", set())),
            "selected_id": view.selected_id,
        }

    def _restore_model_snapshot(self, snapshot, status):
        view = self.view
        if not view.current_tree:
            return
        view.current_tree["focuses"] = copy.deepcopy(snapshot["focuses"])
        view.new_focuses = copy.deepcopy(snapshot["new_focuses"])
        view._moved = set(snapshot["moved"])
        view._relationship_dirty = set(snapshot["relationship_dirty"])
        view.selected_id = snapshot["selected_id"]
        view._render_tree()
        if view.selected_id in view._by_id:
            view._show_details(view.selected_id)
        view.status.config(text=status)

    def _record_model_change(self, description, before):
        """Add a reversible staged command to the app-wide Ctrl+Z history."""
        after = self._model_snapshot()
        undo.record_action(
            lambda: self._restore_model_snapshot(before, f"Reverted {description}."),
            lambda: self._restore_model_snapshot(after, f"Re-applied {description}."),
            description,
        )

    def refresh_workshop_mods(self):
        view = self.view
        view._workshop_mods = self.data.list_workshop_mods(self.workshop_root)
        view.mod_combo["values"] = [
            f"{mod['name']}  ({mod['workshop_id']})" for mod in view._workshop_mods
        ]
        if view._workshop_mods:
            view.mod_combo.current(0)

    def load_mod_async(self, path):
        view = self.view
        if getattr(view, "_loading", False):
            return
        view._loading = True
        view.status.config(text="Scanning mod in the background (icons, localisation, characters)...")
        view.mod_label.config(text="Loading...")
        view._load_request_id = self.data.load_mod_async(path)
        self.poll_load()

    def poll_load(self):
        view = self.view
        request_id = getattr(view, "_load_request_id", None)
        result = self.data.take_load_result(request_id) if request_id else None
        if result is not None:
            self.apply_load(result)
        elif getattr(view, "_loading", False):
            view.after(60, self.poll_load)

    def apply_load(self, result):
        view = self.view
        view._loading = False
        if "error" in result:
            view.status.config(text=f"Load failed: {result['error']}")
            view.mod_label.config(text="Load failed")
            return

        view.mod_root = result["path"]
        view.tree_files = result["tree_files"]
        view.gfx_index = result["gfx_index"]
        view.loc = result["loc"]
        view.characters = result["characters"]
        view._icon_library = None
        view._tree_items = result["items"]
        view.tree_combo["values"] = [item[0] for item in result["items"]]
        if result["items"]:
            view.tree_combo.current(0)

        state.set_mod(
            view.mod_root,
            name=result["mod_name"],
            gfx_index=view.gfx_index,
            mod_loc=view.loc,
            characters=view.characters,
            tags=result["tags"],
        )
        view.mod_label.config(
            text=f"Loaded: {os.path.basename(view.mod_root)}  "
                 f"({len(view.gfx_index)} icons, {len(view.characters)} countries)"
        )
        view.status.config(text="Mod loaded. Pick a focus tree and click Load Tree.")

    def load_mod_sync(self, path):
        self.apply_load(self.data.load_mod(path))

    def load_selected_tree(self):
        view = self.view
        item = searchable_combo.resolve(view.tree_combo, view._tree_items)
        if item is None:
            return
        _, _, tree = item
        view.current_tree = tree
        view.new_focuses = []
        view._relationship_dirty = set()
        view.completed = set()
        view.selected_id = None
        view._editing_id = None
        view.detail_form.pack_forget()
        view.detail_placeholder.pack(anchor="w", pady=(4, 0))
        if tree["country_tags"]:
            view.tag_var.set(tree["country_tags"][0])
        view.inspector.show_tree_settings(tree)
        view._render_tree()

    def ensure_editable_tree(self):
        """Copy a selected vanilla tree into the mod before its first write."""
        view = self.view
        tree = view.current_tree
        if not tree:
            return None
        source_path = tree.get("source_file", "")
        if not tree.get("is_vanilla"):
            return source_path
        try:
            relative_path = os.path.relpath(source_path, self.data.base_game)
        except ValueError:
            return None
        if relative_path.startswith("..") or os.path.isabs(relative_path):
            return None
        destination = os.path.join(view.mod_root, relative_path)
        try:
            os.makedirs(os.path.dirname(destination), exist_ok=True)
            shutil.copy2(source_path, destination)
        except OSError as exc:
            messagebox.showerror("Couldn't create editable copy", str(exc))
            return None
        tree["source_file"] = destination
        tree["is_vanilla"] = False
        return destination

    # ---- canvas interaction ----

    def can_drag(self, focus_id):
        view = self.view
        return (
            not view.sim_mode.get()
            and view.layout_mode.get() != "auto"
            and focus_id in view._by_id
        )

    def set_canvas_mode(self, mode):
        view = self.view
        view.canvas_mode.set(mode)
        self._link_from = None
        hints = {
            "select": "click a node to select it, drag to move it",
            "link": "click a focus, then a second focus, to add the first as its prerequisite",
            "add": "click empty canvas to place a new focus there",
            "pan": "click-drag anywhere to pan the view",
        }
        view.mode_hint.config(text=hints[mode])
        for value, button in view.mode_buttons.items():
            active = value == mode
            button.configure(
                bg=ft.ACCENT if active else ft.RAISED,
                fg=ft.ACCENT_ON if active else ft.TEXT_MID,
                activebackground=ft.ACCENT_HI if active else ft.HOVER,
                activeforeground=ft.ACCENT_ON if active else ft.TEXT_HI,
                highlightbackground=ft.ACCENT if active else ft.LINE_STRONG,
                highlightcolor=ft.ACCENT if active else ft.LINE_STRONG,
            )

    def on_canvas_press(self, event):
        view = self.view
        mode = view.canvas_mode.get()
        canvas_x = view.canvas.canvasx(event.x)
        canvas_y = view.canvas.canvasy(event.y)
        hit_items = view.canvas.find_overlapping(canvas_x, canvas_y, canvas_x, canvas_y)
        on_node = any(
            tag.startswith("focus_")
            for item in hit_items
            for tag in view.canvas.gettags(item)
        )
        if mode == "pan":
            view.canvas.scan_mark(event.x, event.y)
        elif on_node:
            return
        elif mode == "add":
            view._add_focus()
        elif mode == "link":
            self._link_from = None
            view.mode_hint.config(text="link cancelled — click a focus to start again")
        elif mode == "select":
            view.selected_id = None
            view._render_tree()

    def on_canvas_drag(self, event):
        view = self.view
        if view.canvas_mode.get() == "pan":
            view.canvas.scan_dragto(event.x, event.y, gain=1)
            view._render_minimap()

    def on_outline_selected(self):
        """Apply a sidebar selection to the canvas and inspector."""
        view = self.view
        focus_id = view.sidebar.selected_focus_id()
        if not focus_id or focus_id not in view._by_id:
            return
        view.selected_id = focus_id
        view._show_details(focus_id)
        view._center_on_node(focus_id)
        view._render_tree()

    def on_node_press(self, event, focus_id):
        view = self.view
        mode = view.canvas_mode.get()
        if mode == "link":
            self._handle_link_click(focus_id)
            return
        if mode == "pan":
            view.canvas.scan_mark(event.x, event.y)
            return
        if mode == "add":
            return
        view.selected_id = focus_id
        view._show_details(focus_id)
        self._drag_state = None
        if self.can_drag(focus_id):
            self._drag_state = {
                "id": focus_id,
                "x": view.canvas.canvasx(event.x),
                "y": view.canvas.canvasy(event.y),
                "moved": False,
                "before": self._model_snapshot(),
            }
        else:
            view._render_tree()

    def on_node_drag(self, event, focus_id):
        view = self.view
        state = self._drag_state
        if not state or state["id"] != focus_id:
            return
        canvas_x = view.canvas.canvasx(event.x)
        canvas_y = view.canvas.canvasy(event.y)
        dx, dy = canvas_x - state["x"], canvas_y - state["y"]
        if not state["moved"] and abs(dx) < 4 and abs(dy) < 4:
            return
        state["moved"] = True
        view.canvas.move(f"focus_{focus_id}", dx, dy)
        state["x"], state["y"] = canvas_x, canvas_y

    def on_node_release(self, event, focus_id):
        view = self.view
        state, self._drag_state = self._drag_state, None
        if not state or not state["moved"]:
            return
        focus = view._by_id.get(focus_id)
        if not focus:
            return
        canvas_x = view.canvas.canvasx(event.x)
        canvas_y = view.canvas.canvasy(event.y)
        abs_x = int(round((canvas_x - 80) / (210 * view.zoom)))
        abs_y = int(round((canvas_y - 80) / (96 * view.zoom)))
        relative_to = focus.get("relative_position_id")
        grid = getattr(view, "_grid", {})
        if relative_to and relative_to in grid:
            anchor_x, anchor_y = grid[relative_to]
            focus["x"], focus["y"] = int(abs_x - anchor_x), int(abs_y - anchor_y)
        else:
            focus["x"], focus["y"] = abs_x, abs_y
        if not focus.get("is_new"):
            if not hasattr(view, "_moved"):
                view._moved = set()
            view._moved.add(focus_id)
        self._record_model_change(f"moving {focus_id}", state["before"])
        view._render_tree()
        view._show_details(focus_id)
        pending = len(getattr(view, "_moved", ()))
        note = f"  ({pending} moved focus(es) pending — use Save Moved)" if pending else ""
        view.status.config(text=f"Moved {focus_id} to x={focus['x']} y={focus['y']}.{note}")

    def on_node_double(self, focus_id):
        view = self.view
        if view.sim_mode.get():
            if focus_id in getattr(view, "_available_now", set()):
                self.complete_selected(focus_id)
            return
        view._edit_focus(focus_id)

    def _handle_link_click(self, focus_id):
        view = self.view
        if self._link_from is None:
            self._link_from = focus_id
            view.mode_hint.config(text=f"linking from {focus_id} — click the focus that should require it")
            return
        if self._link_from == focus_id:
            self.set_canvas_mode("link")
            return
        target = view._by_id.get(focus_id)
        if target is None:
            return
        prerequisites = target.setdefault("prerequisite", [])
        if self._link_from in prerequisites:
            view.status.config(text=f"{focus_id} already requires {self._link_from}.")
        else:
            before = self._model_snapshot()
            prerequisites.append(self._link_from)
            target.setdefault("prerequisite_groups", []).append([self._link_from])
            if not target.get("is_new"):
                view._relationship_dirty = set(getattr(view, "_relationship_dirty", set()))
                view._relationship_dirty.add(focus_id)
            self._record_model_change(f"linking {focus_id} to {self._link_from}", before)
            view.status.config(
                text=f"Linked: {focus_id} now requires {self._link_from}. Click Save to write it to the mod."
            )
        self.set_canvas_mode("link")
        view._render_tree()

    # ---- coordinate commands ----

    def save_moved(self):
        view = self.view
        moved = getattr(view, "_moved", set())
        if not moved:
            messagebox.showerror("Nothing moved", "Drag an existing focus first (Layout: mod coordinates).")
            return
        path = view.current_tree["source_file"]
        if not messagebox.askyesno(
            "Write new positions?",
            f"Update x/y of {len(moved)} focus(es) inside {os.path.basename(path)}?\n"
            "Vanilla trees are copied into your mod first; the game installation is never changed.",
        ):
            return
        path = self.ensure_editable_tree()
        if not path:
            return
        done = 0
        for focus_id in sorted(moved):
            focus = view._by_id.get(focus_id)
            if focus and focus_surgery.apply_edits(path, focus_id, scalars={"x": focus["x"], "y": focus["y"]}):
                done += 1
        view._moved = set()
        view._update_unsaved_label()
        view.status.config(text=f"Saved new positions of {done} focus(es) into {os.path.basename(path)}.")

    def tidy_tree(self):
        view = self.view
        if not view.current_tree:
            return
        focuses = view._all_focuses()
        if not focuses:
            return
        positions = auto_layout_mod.auto_layout(focuses)
        if not positions:
            return
        moved_preview = sum(
            1 for focus in focuses
            if positions.get(focus["id"])
            and (int(round(positions[focus["id"]][0])) != int(focus.get("x", 0) or 0)
                 or int(round(positions[focus["id"]][1])) != int(focus.get("y", 0) or 0))
        )
        if not moved_preview:
            view.status.config(text="Already tidy — the computed layout matches the current coordinates.")
            return
        if not messagebox.askyesno(
            "Tidy the whole tree?",
            f"Recompute x/y for all {len(focuses)} focus(es) from their prerequisite structure?\n\n"
            f"{moved_preview} focus(es) would move. Branch shape and ordering are preserved; this removes "
            "overlaps and evens out the spacing.\n\nNothing is written until you click 'Save Moved' afterwards.",
        ):
            return
        if not hasattr(view, "_moved"):
            view._moved = set()
        before = self._model_snapshot()
        changed = 0
        for focus in focuses:
            position = positions.get(focus["id"])
            if position is None:
                continue
            new_x, new_y = int(round(position[0])), int(round(position[1]))
            if int(focus.get("x", 0) or 0) == new_x and int(focus.get("y", 0) or 0) == new_y:
                continue
            focus["x"], focus["y"] = new_x, new_y
            if focus["id"] in view._by_id:
                view._moved.add(focus["id"])
            changed += 1
        view.layout_mode.set("mod coordinates")
        self._record_model_change("tidying the tree", before)
        view._render_tree()
        view.status.config(text=f"Tidied {changed} focus(es). Click 'Save Moved' to write the new coordinates to the file.")

    def shift_branch(self, root_id, dx, dy):
        """Apply a confirmed grid offset to an authored focus branch."""
        view = self.view
        focuses = view._all_focuses()
        by_id = {focus["id"]: focus for focus in focuses}
        if root_id not in by_id:
            return

        branch = self.branch_ids(root_id, focuses)
        if not hasattr(view, "_moved"):
            view._moved = set()
        before = self._model_snapshot()
        shifted = 0
        for focus_id in branch:
            focus = by_id.get(focus_id)
            if focus is None:
                continue
            try:
                focus["x"] = int(focus.get("x", 0)) + dx
                focus["y"] = int(focus.get("y", 0)) + dy
            except (TypeError, ValueError):
                continue
            # New focuses are persisted by Export, not Save Moved.
            if focus_id in view._by_id:
                view._moved.add(focus_id)
            shifted += 1

        self._record_model_change(f"shifting the {root_id} branch", before)
        view._render_tree()
        view.status.config(
            text=f"Shifted {shifted} focus(es) in the '{root_id}' branch by "
                 f"x{dx:+d} y{dy:+d}. Click 'Save Moved' to write it to the file."
        )

    def copy_branch(self, root_id, old_prefix, new_prefix):
        """Create in-memory copies of a branch after the view confirms naming."""
        view = self.view
        focuses = view._all_focuses()
        by_id = {focus["id"]: focus for focus in focuses}
        if root_id not in by_id:
            return

        branch = self.branch_ids(root_id, focuses)

        def rename(focus_id):
            if old_prefix and focus_id.startswith(old_prefix):
                return new_prefix + focus_id[len(old_prefix):]
            return new_prefix + focus_id

        grid = view._mod_grid(focuses)
        root_cell = grid.get(root_id, (0, 0))
        max_y = max((cell[1] for cell in grid.values()), default=0)
        existing_ids = set(by_id) | {focus["id"] for focus in view.new_focuses}
        before = self._model_snapshot()

        added = 0
        for focus_id in branch:
            source = by_id[focus_id]
            new_id = rename(focus_id)
            if new_id in existing_ids:
                continue
            cell = grid.get(focus_id, root_cell)
            clone = {
                "id": new_id,
                "title": view.loc.get(focus_id, focus_id) + " (copy)",
                "desc": view.loc.get(focus_id + "_desc", ""),
                "icon": source.get("icon", ""),
                "x": cell[0] - root_cell[0] + root_cell[0],
                "y": cell[1] - root_cell[1] + max_y + 2,
                "cost": source.get("cost", 10),
                "prerequisite": [rename(prerequisite) if prerequisite in branch else prerequisite
                                   for prerequisite in source.get("prerequisite", [])],
                "prerequisite_groups": [
                    [rename(prerequisite) if prerequisite in branch else prerequisite for prerequisite in group]
                    for group in (source.get("prerequisite_groups") or [])
                ],
                "mutually_exclusive": [rename(mutex) for mutex in source.get("mutually_exclusive", [])
                                       if mutex in branch],
                "completion_reward_raw": source.get("completion_reward_raw", "add_political_power = 100"),
                "is_new": True,
            }
            view.new_focuses.append(clone)
            existing_ids.add(new_id)
            added += 1

        if added:
            self._record_model_change(f"copying the {root_id} branch", before)
        view._render_tree()
        view.status.config(
            text=f"Copied {added} focuses as '{new_prefix}...' - they're green now; "
                 "use Export New Focuses to write them to the additions file."
        )

    def apply_focus_edit(self, focus_id, result):
        """Persist a confirmed full-editor dialog result and refresh the view."""
        view = self.view
        focus = view._by_id.get(focus_id)
        if focus is None:
            return
        scalars = result["scalars"]
        blocks = result["blocks"]
        if focus.get("is_new"):
            before = self._model_snapshot()
            focus["icon"] = scalars["icon"]
            focus["cost"] = scalars["cost"]
            focus["completion_reward_raw"] = blocks["completion_reward"]
            focus["available_raw"] = blocks["available"]
            self._record_model_change(f"editing {focus_id}", before)
            view._render_tree()
            return

        path = self.ensure_editable_tree()
        if not path:
            return
        relationship_dirty = focus_id in getattr(view, "_relationship_dirty", set())
        persisted_blocks = dict(blocks)
        if relationship_dirty:
            persisted_blocks["prerequisite_groups"] = focus.get("prerequisite_groups", [])
            persisted_blocks["mutually_exclusive"] = focus.get("mutually_exclusive", [])
        if not focus_surgery.apply_edits(path, focus_id, scalars=scalars, blocks=persisted_blocks):
            messagebox.showerror("Not found", f"Couldn't locate '{focus_id}' in {os.path.basename(path)}.")
            return
        # Keep the active canvas model synchronized with the edited file.
        focus["icon"] = scalars["icon"]
        focus["cost"] = scalars["cost"]
        focus["completion_reward_raw"] = blocks["completion_reward"]
        focus["available_raw"] = blocks["available"]
        if relationship_dirty:
            view._relationship_dirty.discard(focus_id)
        view._render_tree()
        view._show_details(focus_id)
        view.status.config(text=f"Edited '{focus_id}' in {os.path.basename(path)} (backup kept as .bak).")

    def save_focus_properties(self, focus_id, *, icon, cost, x, y, name, desc):
        """Persist inspector edits while retaining the existing dictionary shape."""
        view = self.view
        focus = view._by_id.get(focus_id)
        if focus is None:
            return

        if focus.get("is_new"):
            before = self._model_snapshot()
            focus["icon"], focus["cost"], focus["x"], focus["y"] = icon, cost, x, y
            focus["title"], focus["desc"] = name, desc
            self._record_model_change(f"editing {focus_id}", before)
        else:
            path = self.ensure_editable_tree()
            if not path:
                return
            blocks = {}
            if focus_id in getattr(view, "_relationship_dirty", set()):
                blocks["prerequisite_groups"] = focus.get("prerequisite_groups", [])
                blocks["mutually_exclusive"] = focus.get("mutually_exclusive", [])
            if not focus_surgery.apply_edits(
                path, focus_id, scalars={"icon": icon, "cost": cost, "x": x, "y": y}, blocks=blocks
            ):
                messagebox.showerror("Not found", f"Couldn't locate '{focus_id}' in {os.path.basename(path)}.")
                return
            focus["icon"], focus["cost"], focus["x"], focus["y"] = icon, cost, x, y
            if name != view.loc.get(focus_id, focus_id):
                loc_surgery.set_key(view.mod_root, focus_id, name)
                view.loc[focus_id] = name
            if desc != view.loc.get(focus_id + "_desc", ""):
                loc_surgery.set_key(view.mod_root, focus_id + "_desc", desc)
                view.loc[focus_id + "_desc"] = desc
            getattr(view, "_moved", set()).discard(focus_id)
            getattr(view, "_relationship_dirty", set()).discard(focus_id)

        view._render_tree()
        view._show_details(focus_id)
        view.status.config(text=f"Saved '{focus_id}'.")

    def export_png(self, path):
        """Render the current focus tree directly to a complete PNG image."""
        view = self.view
        if not view.current_tree:
            messagebox.showerror("No tree", "Load a focus tree first.")
            return
        focuses = view._all_focuses()
        if not focuses:
            return

        from PIL import Image, ImageDraw

        cell_w, cell_h = 190, 130
        node_w, node_h = 168, 54
        margin = 40
        grid = view._mod_grid(focuses)
        if not grid:
            messagebox.showerror("No positions", "This tree has no usable coordinates to draw.")
            return
        xs = [cell[0] for cell in grid.values()]
        ys = [cell[1] for cell in grid.values()]
        min_x, min_y = min(xs), min(ys)
        width = (max(xs) - min_x + 1) * cell_w + margin * 2
        height = (max(ys) - min_y + 1) * cell_h + margin * 2

        def centre(focus_id):
            grid_x, grid_y = grid[focus_id]
            return (
                margin + (grid_x - min_x) * cell_w + cell_w / 2,
                margin + (grid_y - min_y) * cell_h + node_h / 2,
            )

        image = Image.new("RGB", (int(width), int(height)), theme.BG)
        draw = ImageDraw.Draw(image)
        for focus in focuses:
            if focus["id"] not in grid:
                continue
            center_x, center_y = centre(focus["id"])
            for prerequisite in focus.get("prerequisite", []):
                if prerequisite not in grid:
                    continue
                previous_x, previous_y = centre(prerequisite)
                middle_y = (previous_y + node_h / 2 + center_y - node_h / 2) / 2
                draw.line([(previous_x, previous_y + node_h / 2), (previous_x, middle_y)],
                          fill=theme.GOLD_DIM, width=2)
                draw.line([(previous_x, middle_y), (center_x, middle_y)], fill=theme.GOLD_DIM, width=2)
                draw.line([(center_x, middle_y), (center_x, center_y - node_h / 2)],
                          fill=theme.GOLD_DIM, width=2)

        for focus in focuses:
            if focus["id"] not in grid:
                continue
            center_x, center_y = centre(focus["id"])
            box = [
                center_x - node_w / 2, center_y - node_h / 2,
                center_x + node_w / 2, center_y + node_h / 2,
            ]
            draw.rectangle(box, fill=theme.RAISED, outline=theme.EDGE, width=1)
            title = view.loc.get(focus["id"], focus.get("title", focus["id"]))
            if len(title) > 26:
                title = title[:24] + "..."
            draw.text((box[0] + 10, box[1] + 12), title, fill=theme.TEXT)
            draw.text((box[0] + 10, box[1] + 32), f"cost {focus.get('cost', 10)}", fill=theme.AMBER)

        try:
            image.save(path, "PNG")
        except OSError as exc:
            messagebox.showerror("Save failed", str(exc))
            return
        view.status.config(
            text=f"Saved {len(grid)} focus(es) to {os.path.basename(path)} ({int(width)}x{int(height)})."
        )

    def export_additions(self):
        """Persist pending new focuses in the selected tree and write locale."""
        view = self.view
        if not view.current_tree or not view.new_focuses:
            messagebox.showerror("Nothing to export", "Add at least one new focus first.")
            return

        issues = focus_check.check(view._all_focuses())
        if issues and not messagebox.askyesno(
            "Check this before saving",
            focus_check.format_issues(issues) +
            "\n\nSave anyway? (errors mean the game will refuse to load this tree)",
        ):
            return

        tree_id = view.current_tree["id"]
        focus_blocks = []
        for focus in view.new_focuses:
            body = [
                pds.kv("id", focus["id"]),
                pds.kv("icon", focus["icon"] or "GFX_goal_generic_more_territorial_claims"),
                pds.kv("x", focus["x"]),
                pds.kv("y", focus["y"]),
                pds.kv("cost", focus["cost"]),
            ]
            prerequisite_groups = focus.get("prerequisite_groups") or [
                [prerequisite] for prerequisite in focus.get("prerequisite", [])
            ]
            for group in prerequisite_groups:
                body.append(pds.block("prerequisite", "\n".join(
                    pds.kv("focus", prerequisite) for prerequisite in group
                )))
            mutexes = focus.get("mutually_exclusive", [])
            if mutexes:
                body.append(pds.block("mutually_exclusive", "\n".join(
                    pds.kv("focus", mutex) for mutex in mutexes
                )))
            if focus.get("available_raw", "").strip():
                body.append(pds.block("available", focus["available_raw"]))
            body.append(pds.block("completion_reward", focus["completion_reward_raw"]))
            focus_blocks.append(pds.block("focus", "\n".join(body)))

        source_path = self.ensure_editable_tree()
        if not source_path or not focus_surgery.append_focus_blocks(
            source_path, tree_id, "\n".join(focus_blocks)
        ):
            messagebox.showerror(
                "Export failed",
                "Could not add the new focuses to the loaded focus-tree file. "
                "The original file was not changed.",
            )
            return

        exported_focuses = list(view.new_focuses)
        localisation_lines = ["l_english:"]
        for focus in exported_focuses:
            localisation_lines.append(f' {focus["id"]}:0 "{focus["title"]}"')
            if focus["desc"]:
                localisation_lines.append(f' {focus["id"]}_desc:0 "{focus["desc"]}"')
        localisation_dir = os.path.join(view.mod_root, "localisation", "english")
        os.makedirs(localisation_dir, exist_ok=True)
        localisation_path = os.path.join(localisation_dir, f"{tree_id}_additions_l_english.yml")
        with open(localisation_path, "w", encoding="utf-8-sig") as handle:
            handle.write("\n".join(localisation_lines) + "\n")

        # The new blocks now live in the actual source tree.  Move their
        # in-memory counterparts to the persisted set so another Export does
        # not try to add duplicate ids, and clear the unsaved indicator.
        view.current_tree.setdefault("focuses", []).extend(exported_focuses)
        view.new_focuses = []
        view._render_tree()
        view.status.config(
            text=f"Exported {len(exported_focuses)} new focuses to {os.path.basename(source_path)}"
        )

    def add_focus(self, focus):
        """Add a dialog-confirmed focus and place it in the next free grid cell."""
        view = self.view
        if not view.current_tree:
            messagebox.showerror("No tree loaded", "Load a focus tree first.")
            return
        existing_ids = {item["id"] for item in view._all_focuses()}
        if focus["id"] in existing_ids:
            messagebox.showerror("Duplicate id", "That focus id already exists in this tree.")
            return

        self.auto_place_focus(focus)
        before = self._model_snapshot()
        view.new_focuses.append(focus)
        view.selected_id = focus["id"]
        self._record_model_change(f"adding {focus['id']}", before)
        view._render_tree()
        view._show_details(focus["id"])
        view.status.config(
            text=f"Added {focus['id']} at x={focus['x']} y={focus['y']}. "
                 "Switch Layout to \"mod coordinates\" to drag it into place."
        )

    def auto_place_focus(self, focus):
        """Place a new focus below its first prerequisite without overlapping."""
        view = self.view
        grid = view._mod_grid(view._all_focuses())
        taken = set(grid.values())
        preferred = (0, 0)
        for prerequisite in focus["prerequisite"]:
            if prerequisite in grid:
                grid_x, grid_y = grid[prerequisite]
                preferred = (grid_x, grid_y + 1)
                break
        else:
            if taken:
                preferred = (min(cell[0] for cell in taken), max(cell[1] for cell in taken) + 1)
        focus["x"], focus["y"] = auto_layout_mod.next_free_cell(taken, preferred)

    # ---- play-mode simulation ----

    def on_simulation_toggled(self):
        """Reset completion state when leaving play mode, then redraw once."""
        view = self.view
        if not view.sim_mode.get():
            view.completed = set()
        view._render_tree()

    def toggle_simulation(self):
        view = self.view
        view.sim_mode.set(not view.sim_mode.get())
        self.on_simulation_toggled()

    def reset_simulation(self):
        view = self.view
        view.completed = set()
        view._render_tree()

    def complete_selected(self, focus_id=None):
        view = self.view
        focus_id = focus_id or view.selected_id
        if not focus_id or focus_id not in getattr(view, "_available_now", set()):
            return
        view.completed.add(focus_id)
        view._render_tree()
        view._show_details(focus_id)

    # ---- find ----

    def find_matches(self):
        view = self.view
        needle = view.find_var.get().strip().lower()
        if not needle or not view.current_tree:
            return []
        matches = []
        for focus in view._all_focuses():
            title = view.loc.get(focus["id"], focus.get("title", ""))
            description = view.loc.get(focus["id"] + "_desc", "")
            if needle in focus["id"].lower() or needle in title.lower() or needle in description.lower():
                matches.append(focus["id"])
        return matches

    def update_matches(self):
        view = self.view
        view._matches = self.find_matches()
        view._match_index = -1
        if not view.find_var.get().strip():
            view.find_label.config(text="")
        else:
            view.find_label.config(text=f"{len(view._matches)} match(es)")
        view._render_tree()

    def clear_find(self):
        self.view.find_var.set("")
        self.update_matches()

    def find_next(self):
        view = self.view
        matches = getattr(view, "_matches", None)
        if matches is None:
            self.update_matches()
            matches = view._matches
        if not matches:
            view.find_label.config(text="no matches")
            return

        visible = [focus_id for focus_id in matches if focus_id in view.node_pos]
        if not visible:
            view.find_label.config(text=f"{len(matches)} match(es), all hidden in play mode")
            return
        view._match_index = (getattr(view, "_match_index", -1) + 1) % len(visible)
        focus_id = visible[view._match_index]
        view.selected_id = focus_id
        view._render_tree()
        view._show_details(focus_id)
        view._scroll_to(focus_id)
        view.find_label.config(text=f"{view._match_index + 1} / {len(visible)}")

    # ---- validation ----

    def run_tree_validation(self):
        """Validate the active focus tree and retain the existing dialog feedback."""
        view = self.view
        if not view.current_tree:
            return
        issues = focus_check.check(view._all_focuses())
        self.update_warning_label(issues)
        if issues:
            messagebox.showinfo("Validation", focus_check.format_issues(issues))
        else:
            messagebox.showinfo("Validation", "No issues found in this tree.")

    def update_warning_label(self, issues):
        """Reflect tree-validation state in the action bar without rebuilding it."""
        view = self.view
        if not view.current_tree:
            view.warning_label.configure(text="")
        elif issues:
            view.warning_label.configure(text=f"{len(issues)} warning(s)", foreground=theme.AMBER)
        else:
            view.warning_label.configure(text="No warnings", foreground=theme.GREEN)

    def precheck_before_export(self):
        """Run the existing full-mod validation before external export actions."""
        view = self.view
        view.status.config(text="Checking the mod before export...")
        view.update_idletasks()
        issues = validator.validate(state.mod_root, state.mod_loc, state.gfx_index)
        counts = validator.summarise(issues)
        errors = counts.get("error", 0)
        if not errors:
            return True
        sample = "\n".join(
            f"  {issue['file']}: {issue['message']}"
            for issue in issues if issue["severity"] == "error"
        )[:800]
        return messagebox.askyesno(
            "Fix these before exporting?",
            f"The Validate tab found {errors} error(s) that will likely break the mod in-game:\n\n{sample}\n\n"
            f"({counts.get('warning', 0)} warning(s) too - not shown here)\n\n"
            "Export anyway?",
        )

    @staticmethod
    def branch_ids(root_id, focuses):
        branch = {root_id}
        changed = True
        while changed:
            changed = False
            for focus in focuses:
                if focus["id"] in branch:
                    continue
                if any(prerequisite in branch for prerequisite in focus.get("prerequisite", [])):
                    branch.add(focus["id"])
                    changed = True
        return branch
