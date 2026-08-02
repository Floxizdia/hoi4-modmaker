"""Canvas viewport, node rendering, and minimap for the Focus Tree screen.

The caller owns editor state and callbacks. This component owns the Canvas
items and their presentation, keeping the drawing hot path independent from
the toolbar and inspector.
"""

import tkinter as tk
from tkinter import ttk

from app import focus_tree_theme as ft
from app import image_cache
from app import mod_loader as ml


class FocusTreeCanvas(ttk.Frame):
    """Scrollable focus-tree canvas with a navigable minimap."""

    MINIMAP_WIDTH = 200
    MINIMAP_HEIGHT = 140
    MINIMAP_PADDING = 10

    def __init__(self, parent, *, on_zoom, on_canvas_press, on_canvas_drag):
        super().__init__(parent, style="FocusTree.Workspace.TFrame")
        self._on_zoom = on_zoom
        self._on_canvas_press = on_canvas_press
        self._on_canvas_drag = on_canvas_drag
        self._minimap_scale = None
        self._minimap_origin = (0, 0)
        self._node_positions = {}
        self._focus_by_id = {}
        self._node_states = {}
        self._selected_id = None
        self._playing = False
        self._build()

    def _build(self):
        self.canvas = tk.Canvas(
            self, background=ft.CANVAS, highlightthickness=1,
            highlightbackground=ft.LINE, highlightcolor=ft.ACCENT_DIM,
        )
        self.vbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview,
                                  style="FocusTree.Vertical.TScrollbar")
        self.hbar = ttk.Scrollbar(self, orient="horizontal", command=self.canvas.xview,
                                  style="FocusTree.Horizontal.TScrollbar")
        self.canvas.configure(
            yscrollcommand=lambda *args: self._on_scroll(self.vbar, *args),
            xscrollcommand=lambda *args: self._on_scroll(self.hbar, *args),
        )
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.vbar.grid(row=0, column=1, sticky="ns")
        self.hbar.grid(row=1, column=0, sticky="ew")
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

        self.canvas.bind("<MouseWheel>", self._on_wheel)
        self.canvas.bind("<Control-MouseWheel>", self._on_ctrl_wheel)
        self.canvas.bind("<ButtonPress-3>", lambda event: self.canvas.scan_mark(event.x, event.y))
        self.canvas.bind("<B3-Motion>", self._on_right_drag)
        self.canvas.bind("<ButtonPress-1>", self._on_canvas_press)
        self.canvas.bind("<B1-Motion>", self._on_canvas_drag)

        self.minimap = tk.Canvas(
            self,
            width=self.MINIMAP_WIDTH,
            height=self.MINIMAP_HEIGHT,
            background=ft.PANEL,
            highlightthickness=1,
            highlightbackground=ft.ACCENT_DIM,
        )
        self.minimap.place(relx=1.0, rely=1.0, anchor="se", x=-18, y=-18)
        self.minimap.bind("<Button-1>", self._on_minimap_click)
        self.minimap.bind("<B1-Motion>", self._on_minimap_click)

    def _on_scroll(self, scrollbar, *args):
        scrollbar.set(*args)
        self.render_minimap()

    def _on_wheel(self, event):
        self.canvas.yview_scroll(-1 * (event.delta // 120), "units")
        self.render_minimap()

    def _on_ctrl_wheel(self, event):
        self._on_zoom(1.1 if event.delta > 0 else 1 / 1.1)

    def _on_right_drag(self, event):
        self.canvas.scan_dragto(event.x, event.y, gain=1)
        self.render_minimap()

    def set_minimap_data(self, node_positions, focus_by_id, *, node_states=None,
                         selected_id=None, playing=False):
        self._node_positions = node_positions
        self._focus_by_id = focus_by_id
        self._node_states = node_states or {}
        self._selected_id = selected_id
        self._playing = playing

    def render_minimap(self):
        """Render the full-tree overview and current viewport rectangle."""
        self.minimap.delete("all")
        bbox = self.canvas.bbox("all")
        if not bbox or not self._node_positions:
            self._minimap_scale = None
            return

        x0, y0, x1, y1 = bbox
        span_x, span_y = max(1, x1 - x0), max(1, y1 - y0)
        scale = min(
            (self.MINIMAP_WIDTH - self.MINIMAP_PADDING * 2) / span_x,
            (self.MINIMAP_HEIGHT - self.MINIMAP_PADDING * 2) / span_y,
        )
        self._minimap_scale = scale
        self._minimap_origin = (x0, y0)

        def to_minimap(x, y):
            return (
                self.MINIMAP_PADDING + (x - x0) * scale,
                self.MINIMAP_PADDING + (y - y0) * scale,
            )

        for focus_id, (x, y) in self._node_positions.items():
            mini_x, mini_y = to_minimap(x, y)
            state = self._node_states.get(focus_id)
            is_selected = focus_id == self._selected_id
            is_new = self._focus_by_id.get(focus_id, {}).get("is_new")
            if is_selected:
                fill, radius = ft.ACCENT_HI, 2.5
            elif is_new:
                fill, radius = ft.ACCENT, 1.8
            elif self._playing and state == "completed":
                fill, radius = ft.OK, 1.5
            elif self._playing and state == "locked":
                fill, radius = ft.TEXT_LOW, 1.25
            else:
                fill, radius = ft.TEXT_MID, 1.5
            self.minimap.create_oval(
                mini_x - radius,
                mini_y - radius,
                mini_x + radius,
                mini_y + radius,
                fill=fill,
                outline="",
            )

        view_x0, view_x1 = self.canvas.xview()
        view_y0, view_y1 = self.canvas.yview()
        full_width, full_height = x1 - x0 + 100, y1 - y0 + 100
        rect_x0, rect_y0 = to_minimap(x0 - 50 + view_x0 * full_width, y0 - 50 + view_y0 * full_height)
        rect_x1, rect_y1 = to_minimap(x0 - 50 + view_x1 * full_width, y0 - 50 + view_y1 * full_height)
        self.minimap.create_rectangle(rect_x0, rect_y0, rect_x1, rect_y1, outline=ft.ACCENT, width=1.5)

    def _on_minimap_click(self, event):
        if not self._minimap_scale:
            return
        x0, y0 = self._minimap_origin
        target_x = x0 + (event.x - self.MINIMAP_PADDING) / self._minimap_scale
        target_y = y0 + (event.y - self.MINIMAP_PADDING) / self._minimap_scale
        bbox = self.canvas.bbox("all")
        if not bbox:
            return
        box_x0, box_y0, box_x1, box_y1 = bbox
        full_width, full_height = (box_x1 - box_x0 + 100) or 1, (box_y1 - box_y0 + 100) or 1
        frac_x = ((target_x - (box_x0 - 50)) / full_width) - 0.5 * (self.canvas.xview()[1] - self.canvas.xview()[0])
        frac_y = ((target_y - (box_y0 - 50)) / full_height) - 0.5 * (self.canvas.yview()[1] - self.canvas.yview()[0])
        self.canvas.xview_moveto(max(0.0, min(1.0, frac_x)))
        self.canvas.yview_moveto(max(0.0, min(1.0, frac_y)))
        self.render_minimap()

    def scroll_to_node(self, node_positions, focus_id):
        """Scroll the viewport so a focus node is centered when possible."""
        if focus_id not in node_positions:
            return
        bbox = self.canvas.bbox("all")
        if not bbox:
            return
        x, y = node_positions[focus_id]
        total_width = max(1, bbox[2] - bbox[0])
        total_height = max(1, bbox[3] - bbox[1])
        view_width = self.canvas.winfo_width() or 800
        view_height = self.canvas.winfo_height() or 600
        self.canvas.xview_moveto(max(0.0, (x - bbox[0] - view_width / 2) / total_width))
        self.canvas.yview_moveto(max(0.0, (y - bbox[1] - view_height / 2) / total_height))
        self.render_minimap()

    def center_on_node(self, node_positions, focus_id):
        """Center the viewport using the existing minimap navigation geometry."""
        position = node_positions.get(focus_id)
        bbox = self.canvas.bbox("all")
        if not position or not bbox:
            return
        x, y = position
        box_x0, box_y0, box_x1, box_y1 = bbox
        full_width, full_height = (box_x1 - box_x0) or 1, (box_y1 - box_y0) or 1
        fraction_x = (x - box_x0) / full_width - 0.5 * (self.canvas.xview()[1] - self.canvas.xview()[0])
        fraction_y = (y - box_y0) / full_height - 0.5 * (self.canvas.yview()[1] - self.canvas.yview()[0])
        self.canvas.xview_moveto(max(0.0, min(1.0, fraction_x)))
        self.canvas.yview_moveto(max(0.0, min(1.0, fraction_y)))
        self.render_minimap()

    # ---- scene rendering ----

    def render_scene(self, *, focuses, visible, node_positions, focus_by_id,
                     node_states, playing, completed, selected_id, matches,
                     mod_root, gfx_index, localisation, node_width, node_height, zoom,
                     state_colors, on_node_press, on_node_drag, on_node_release,
                     on_node_double):
        """Redraw the tree scene and return the image references it needs.

        The caller owns selection and editor state; this widget owns every
        Canvas item, connector, node image, and node event binding.
        """
        self.canvas.delete("all")
        image_refs = []

        scaled_height = node_height * zoom
        for focus in visible:
            x2, y2 = node_positions[focus["id"]]
            for prerequisite in focus.get("prerequisite", []):
                if prerequisite not in node_positions:
                    continue
                x1, y1 = node_positions[prerequisite]
                lit = playing and prerequisite in completed
                color = ft.CONNECTOR_COMPLETED if lit else ft.CONNECTOR
                width = 2 if lit else 1
                top = y1 + scaled_height / 2
                bottom = y2 - scaled_height / 2
                if abs(x1 - x2) < 1:
                    self.canvas.create_line(x1, top, x2, bottom, fill=color, width=width)
                else:
                    middle_y = top + (bottom - top) / 2
                    self.canvas.create_line(x1, top, x1, middle_y, fill=color, width=width)
                    self.canvas.create_line(x1, middle_y, x2, middle_y, fill=color, width=width)
                    self.canvas.create_line(x2, middle_y, x2, bottom, fill=color, width=width)

        drawn_mutex = set()
        for focus in visible:
            focus_id = focus["id"]
            for other in focus.get("mutually_exclusive", []):
                pair = tuple(sorted((focus_id, other)))
                if pair in drawn_mutex or other not in node_positions:
                    continue
                drawn_mutex.add(pair)
                other_x, other_y = node_positions[other]
                focus_x, focus_y = node_positions[focus_id]
                self.canvas.create_line(focus_x, focus_y, other_x, other_y,
                                        fill=ft.MUTEX, width=1, dash=(4, 3))
                middle_x, middle_y = (focus_x + other_x) / 2, (focus_y + other_y) / 2
                radius = 4 * zoom
                self.canvas.create_oval(middle_x - radius, middle_y - radius,
                                        middle_x + radius, middle_y + radius,
                                        fill=ft.MUTEX, outline=ft.PANEL)

        for focus in visible:
            focus_id = focus["id"]
            x, y = node_positions[focus_id]
            state = node_states[focus_id]
            dim = playing and state == "locked"
            if focus.get("is_new"):
                outline = state_colors["new"]
            elif playing:
                outline = state_colors[state]
            else:
                outline = state_colors["plain"]
            tag_name = f"focus_{focus_id}"
            icon_path = ml.resolve_texture(focus.get("icon", ""), mod_root, gfx_index)
            self._draw_card_node(
                focus, x, y, tag_name, outline, dim, icon_path, playing,
                selected_id, matches, node_width, node_height, localisation, zoom, image_refs,
            )
            self.canvas.tag_bind(tag_name, "<Button-1>",
                                 lambda event, item=focus_id: on_node_press(event, item))
            self.canvas.tag_bind(tag_name, "<B1-Motion>",
                                 lambda event, item=focus_id: on_node_drag(event, item))
            self.canvas.tag_bind(tag_name, "<ButtonRelease-1>",
                                 lambda event, item=focus_id: on_node_release(event, item))
            self.canvas.tag_bind(tag_name, "<Double-Button-1>",
                                 lambda _event, item=focus_id: on_node_double(item))

        bbox = self.canvas.bbox("all")
        if bbox:
            self.canvas.configure(scrollregion=(bbox[0] - 50, bbox[1] - 50, bbox[2] + 50, bbox[3] + 50))
        self.set_minimap_data(
            node_positions,
            focus_by_id,
            node_states=node_states,
            selected_id=selected_id,
            playing=playing,
        )
        self.render_minimap()
        return image_refs

    def _draw_card_node(self, focus, x, y, tag_name, outline, dim, icon_path,
                        playing, selected_id, matches, node_width, node_height,
                        localisation, zoom, image_refs):
        focus_id = focus["id"]
        width, height = node_width * zoom, node_height * zoom
        left, top = x - width / 2, y - height / 2
        right, bottom = x + width / 2, y + height / 2
        highlighted = focus_id in matches
        selected = focus_id == selected_id
        fill = ft.NODE_FILL_LOCKED if dim else (ft.SELECTION if selected else ft.NODE_FILL)
        border = ft.WARN if highlighted else (ft.ACCENT_HI if selected else outline)
        border_width = 3 if (selected or highlighted) else 1
        self._rounded_rect(left, top, right, bottom, 6 * zoom, fill, border, border_width, tag_name)

        if selected and not highlighted:
            handle_size = 3 * zoom
            for handle_x, handle_y in ((left, top), (right, top), (left, bottom), (right, bottom)):
                self.canvas.create_rectangle(handle_x - handle_size, handle_y - handle_size,
                                             handle_x + handle_size, handle_y + handle_size,
                                             fill=ft.ACCENT, outline="", tags=(tag_name,))

        icon_size = max(16, int(height - 12 * zoom))
        icon_x = left + 10 * zoom + icon_size / 2
        thumbnail = image_cache.get_thumbnail(icon_path, (icon_size, icon_size)) if icon_path else None
        if thumbnail:
            image_refs.append(thumbnail)
            self.canvas.create_image(icon_x, y, image=thumbnail, tags=(tag_name,))
        else:
            self.canvas.create_text(icon_x, y, text="?", fill=ft.TEXT_OFF,
                                    font=(ft.theme.FACE_UI, max(7, int(14 * zoom))), tags=(tag_name,))

        if playing and focus_id in completed:
            self.canvas.create_text(right - 10 * zoom, top + 10 * zoom, text="✓", fill=ft.OK,
                                    font=(ft.theme.FACE_UI, max(8, int(12 * zoom)), "bold"), tags=(tag_name,))

        text_left = icon_x + icon_size / 2 + 8 * zoom
        text_width = right - 8 * zoom - text_left
        if zoom >= 0.45 and text_width > 20:
            title = localisation.get(focus_id, focus.get("title", focus_id))
            if len(title) > 34:
                title = title[:32] + "…"
            self.canvas.create_text(text_left, top + height * 0.32, text=title, anchor="w",
                                    fill=ft.NODE_TEXT_DIM if dim else ft.NODE_TEXT, width=text_width,
                                    font=(ft.theme.FACE_UI, max(6, int(9 * zoom)), "bold"), tags=(tag_name,))
            prereq_count = len(focus.get("prerequisite", []))
            subtitle = f"cost {focus.get('cost', 10)}"
            if prereq_count:
                subtitle += f"  ·  {prereq_count} req"
            self.canvas.create_text(text_left, top + height * 0.68, text=subtitle, anchor="w",
                                    fill=ft.NODE_TEXT_DIM if dim else ft.NODE_META, width=text_width,
                                    font=(ft.theme.FACE_MONO, max(6, int(8 * zoom))), tags=(tag_name,))

    def _rounded_rect(self, x1, y1, x2, y2, radius, fill, outline, width, tag_name):
        # Command Table panels use sharp edges. Canvas rectangles also cost
        # less to render than smoothed polygons on very large focus trees.
        self.canvas.create_rectangle(
            x1, y1, x2, y2, fill=fill, outline=outline, width=width, tags=(tag_name,)
        )
