"""The centre panel: search + filter chips + the sortable installed-mods
table + the Refresh/Browse/Add-folder bar underneath it.

Owns its own search/filter/sort state and does its own filtering - nothing
above it needs to know how a row got shown or hidden. It reports upward
through the callbacks given to the constructor (`on_selection_changed`,
`on_open`, `on_refresh`, `on_browse`, `on_add_folder`) rather than reaching
back into a parent, so this widget could be dropped into another screen
that needs "a filterable table of things" with a different data source.
"""

import os
import tkinter as tk
from tkinter import ttk

from app import home_data
from app import home_theme as ht
from app import recent
from app import ui_kit


class HomeTable(ttk.Frame):
    def __init__(self, parent, data, *, on_selection_changed, on_open,
                 on_refresh, on_browse, on_add_folder):
        super().__init__(parent, style="Home.TFrame")
        self.data = data
        self._on_selection_changed = on_selection_changed
        self._on_open = on_open
        self._on_refresh = on_refresh
        self._on_browse = on_browse
        self._on_add_folder = on_add_folder

        self._mods = []
        self._row_by_iid = {}
        self._sort_desc = False
        self._active_filter = "all"
        self._search = ""

        self._build()

    # ---- construction ----

    def _build(self):
        toolbar = ttk.Frame(self, style="Home.Panel.TFrame", padding=(12, 5))
        toolbar.pack(fill="x")

        search_box = ttk.Frame(toolbar, style="Home.TFrame")
        search_box.pack(side="left")
        search_wrap = tk.Frame(search_box, background=ht.CANVAS, highlightthickness=1,
                               highlightbackground=ht.LINE_STRONG)
        search_wrap.pack()
        ttk.Label(search_wrap, text="⌕", style="Home.Muted.TLabel", background=ht.CANVAS).pack(
            side="left", padx=(8, 4), pady=3)
        self.search_var = tk.StringVar()
        search_entry = tk.Entry(search_wrap, textvariable=self.search_var, width=24,
                                background=ht.CANVAS, foreground=ht.TEXT_HI,
                                insertbackground=ht.ACCENT, relief="flat",
                                font=(ht.FACE_UI, 10), highlightthickness=0, bd=0)
        search_entry.pack(side="left", fill="y", pady=3)
        ttk.Label(search_wrap, text="Ctrl+F", style="Home.MonoMuted.TLabel",
                  background=ht.CANVAS).pack(side="left", padx=8)
        self.search_var.trace_add("write", lambda *_: self._on_search_change())
        self.search_entry = search_entry

        filters = ttk.Frame(toolbar, style="Home.TFrame")
        filters.pack(side="left", padx=(10, 0))
        self._filter_buttons = {}
        for key, label in (("all", "All"), ("compatible", "Compatible"),
                           ("needs_update", "Needs update"), ("local", "Local")):
            btn = ttk.Button(filters, text=label, style="Home.Filter.TButton",
                             command=lambda k=key: self._set_filter(k))
            btn.pack(side="left")
            self._filter_buttons[key] = btn
        self._filter_buttons["all"].configure(style="Home.FilterActive.TButton")

        right_tools = ttk.Frame(toolbar, style="Home.TFrame")
        right_tools.pack(side="right")
        refresh_btn2 = ttk.Button(right_tools, text="↻", width=3, style="Home.Secondary.TButton",
                                  command=self._on_refresh)
        refresh_btn2.pack(side="right")
        ui_kit.attach_tooltip(refresh_btn2, "Rescan for mods (F5).")

        header = ttk.Frame(self, style="Home.TFrame", padding=(12, 10, 12, 8))
        header.pack(fill="x")
        ttk.Label(header, text="INSTALLED MODS", style="Home.Eyebrow.TLabel",
                  background=ht.CANVAS).pack(anchor="w")
        ttk.Label(header, text="Double-click a mod to open it. Enter opens the selection.",
                  style="Home.Muted.TLabel").pack(anchor="w", pady=(3, 0))

        table_wrap = tk.Frame(self, background=ht.CANVAS, highlightthickness=1,
                              highlightbackground=ht.LINE_STRONG)
        table_wrap.pack(fill="both", expand=True, padx=12)

        cols = ("supports", "size", "last")
        self.tree = ttk.Treeview(table_wrap, columns=cols, show="tree headings",
                                 style="Home.Treeview", selectmode="extended")
        self.tree.heading("#0", text="Mod ↑", command=self._toggle_sort)
        self.tree.heading("supports", text="Supports")
        self.tree.heading("size", text="Size")
        self.tree.heading("last", text="Last opened")
        self.tree.column("#0", width=420, stretch=True)
        self.tree.column("supports", width=92, stretch=False, anchor="w")
        self.tree.column("size", width=78, stretch=False, anchor="e")
        self.tree.column("last", width=100, stretch=False, anchor="w")
        bar = ttk.Scrollbar(table_wrap, orient="vertical", command=self.tree.yview,
                            style="Home.Vertical.TScrollbar")
        self.tree.configure(yscrollcommand=bar.set)
        self.tree.pack(side="left", fill="both", expand=True)
        bar.pack(side="right", fill="y")

        self.tree.tag_configure("compatible", foreground=ht.TEXT_HI)
        self.tree.tag_configure("needs_update", foreground=ht.TEXT_MID)
        self.tree.tag_configure("local", foreground=ht.TEXT_MID)

        self.tree.bind("<Double-Button-1>", lambda e: self._handle_open())
        self.tree.bind("<Return>", lambda e: self._handle_open())
        self.tree.bind("<<TreeviewSelect>>", lambda e: self._on_selection_changed())

        bottom = ttk.Frame(self, style="Home.TFrame", padding=12)
        bottom.pack(fill="x")
        refresh_btn = ttk.Button(bottom, text="Refresh", style="Home.Secondary.TButton",
                                 command=self._on_refresh)
        refresh_btn.pack(side="left")
        browse_btn = ttk.Button(bottom, text="Browse folder…", style="Home.Secondary.TButton",
                                command=self._on_browse)
        browse_btn.pack(side="left", padx=8)
        ui_kit.attach_tooltip(browse_btn, "Open a mod that isn't in the Workshop folder, once.")
        add_btn = ttk.Button(bottom, text="Add mod folder…", style="Home.Ghost.TButton",
                             command=self._on_add_folder)
        add_btn.pack(side="left")
        ui_kit.attach_tooltip(add_btn, "Pin a local folder so it always shows up in this list.")
        self.hint = ttk.Label(bottom, text="", style="Home.Muted.TLabel")
        self.hint.pack(side="right")

    # ---- toolbar events ----

    def _on_search_change(self):
        self._search = self.search_var.get().strip().lower()
        self._render_rows()

    def _set_filter(self, key):
        self._active_filter = key
        for k, btn in self._filter_buttons.items():
            btn.configure(style="Home.FilterActive.TButton" if k == key else "Home.Filter.TButton")
        self._render_rows()

    def _toggle_sort(self):
        self._sort_desc = not self._sort_desc
        self.tree.heading("#0", text=f"Mod {'↓' if self._sort_desc else '↑'}")
        self._render_rows()

    def _handle_open(self):
        mods = self.get_selected_mods()
        if not mods:
            self.hint.config(text="Pick a mod from the list first (or Browse folder).")
            return
        self._on_open(mods[0]["path"])

    # ---- data in/out ----

    def show_scanning(self):
        self.hint.config(text="Scanning for mods…")

    def set_mods(self, mods):
        self._mods = mods
        self._render_rows()

    def update_row_size(self, path):
        text = home_data.size_text_for(path)
        for iid, m in self._row_by_iid.items():
            if m["path"] == path and self.tree.exists(iid):
                vals = list(self.tree.item(iid, "values"))
                if vals[1] != text:
                    vals[1] = text
                    self.tree.item(iid, values=vals)

    def get_selected_mods(self):
        return [self._row_by_iid[i] for i in self.tree.selection() if i in self._row_by_iid]

    def get_selected_paths(self):
        return [m["path"] for m in self.get_selected_mods()]

    def all_mods(self):
        return self._mods

    def _render_rows(self):
        self.tree.delete(*self.tree.get_children())
        self._row_by_iid = {}
        opened = {os.path.normcase(e["path"]): e.get("opened", 0) for e in recent.load()}
        detected_mm = self.data.detected_mm

        rows = []
        for m in self._mods:
            cls = home_data.compat_class(m, detected_mm)
            if self._active_filter != "all" and cls != self._active_filter:
                continue
            if self._search and self._search not in m["name"].lower():
                continue
            rows.append((m, cls))
        rows.sort(key=lambda pair: pair[0]["name"].lower(), reverse=self._sort_desc)

        for i, (m, cls) in enumerate(rows):
            iid = str(i)
            self._row_by_iid[iid] = m
            last_ts = opened.get(os.path.normcase(m["path"]))
            last_text = recent.ago(last_ts) if last_ts else "—"
            supports = m.get("supported_version") or ("local" if cls == "local" else "—")
            size_text = home_data.size_text_for(m["path"])
            self.tree.insert("", "end", iid=iid, text=f"  {m['name']}",
                             values=(supports, size_text, last_text), tags=(cls,))

        counts = {"all": len(self._mods)}
        for key in ("compatible", "needs_update", "local"):
            counts[key] = sum(1 for m in self._mods if home_data.compat_class(m, detected_mm) == key)
        for key, btn in self._filter_buttons.items():
            label = {"all": "All", "compatible": "Compatible",
                     "needs_update": "Needs update", "local": "Local"}[key]
            btn.configure(text=f"{label} {counts.get(key, 0)}")

        if rows:
            first = self.tree.get_children()[0]
            self.tree.selection_set(first)
            self.tree.focus(first)
        self.hint.config(
            text=f"{len(self._mods)} mods in the Steam Workshop folder"
            if self._mods else "No Workshop mods found — use Browse folder")
        self._on_selection_changed()
