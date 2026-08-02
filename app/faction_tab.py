"""Factions tab: browse the faction templates, goals and rules already in
play, and compose new ones. A faction template is mostly a pick-list of
existing goals and rules, so the form is pickers rather than typed ids."""

import tkinter as tk
from tkinter import ttk, messagebox

from app.state import state
from app import faction_creator as fc
from app import theme, ui_kit

BROWSE_KINDS = [
    ("templates", "Faction templates"),
    ("goals", "Goals & manifests"),
    ("rules", "Rules"),
]


class _PickList(ttk.Frame):
    """A filterable multi-select list that keeps its selection as a set of
    ids, so filtering never silently drops what the user already picked."""

    def __init__(self, master, title, height=8):
        super().__init__(master)
        self.selected = set()
        self._all = []          # [(id, note)]

        head = ttk.Frame(self)
        head.pack(fill="x")
        ttk.Label(head, text=title).pack(side="left")
        self.count_label = ttk.Label(head, text="none picked", style="Muted.TLabel")
        self.count_label.pack(side="right")

        self.filter_var = tk.StringVar()
        ttk.Entry(self, textvariable=self.filter_var).pack(fill="x", pady=(2, 2))
        self.filter_var.trace_add("write", lambda *_: self._refresh())

        self.listbox = tk.Listbox(self, height=height, exportselection=False,
                                   background=theme.SURFACE, foreground="#ddd",
                                   selectbackground=theme.BRONZE, highlightthickness=0)
        self.listbox.pack(fill="both", expand=True)
        self.listbox.bind("<Button-1>", self._on_click)

    def set_items(self, items):
        self._all = list(items)
        self._refresh()

    def _visible(self):
        needle = self.filter_var.get().strip().lower()
        return [(i, note) for i, note in self._all if not needle or needle in i.lower()]

    def _refresh(self):
        self.listbox.delete(0, "end")
        self._shown = self._visible()
        for item_id, note in self._shown:
            mark = "✓ " if item_id in self.selected else "   "
            suffix = f"   ({note})" if note else ""
            self.listbox.insert("end", f"{mark}{item_id}{suffix}")
        n = len(self.selected)
        self.count_label.configure(text="none picked" if not n else f"{n} picked")

    def _on_click(self, event):
        index = self.listbox.nearest(event.y)
        if index < 0 or index >= len(getattr(self, "_shown", [])):
            return "break"
        item_id = self._shown[index][0]
        if item_id in self.selected:
            self.selected.discard(item_id)
        else:
            self.selected.add(item_id)
        self._refresh()
        return "break"

    def clear(self):
        self.selected = set()
        self._refresh()


class FactionTab(ttk.Frame):
    def __init__(self, master):
        super().__init__(master, padding=12)
        self._cache = {}
        self._build()
        state.subscribe(self.on_mod_changed)

    def _build(self):
        self.header = ui_kit.PageHeader(
            self, "Factions",
            "Faction templates (e.g. Allies/Axis-style alliances), their join/leave rules, and the icons shown for each.", help_key="factions")

        body = ttk.Frame(self)
        body.pack(fill="both", expand=True)

        # ---- left: browse ----
        browse = ui_kit.Section(body, "Browse what already exists")
        browse.pack(side="left", fill="y", padx=(0, ui_kit.PAD_SECTION))
        browse.configure(width=340)
        browse.pack_propagate(False)
        left = browse.body
        row = ttk.Frame(left)
        row.pack(fill="x")
        ttk.Label(row, text="Show").pack(side="left")
        self.browse_kind = tk.StringVar(value=BROWSE_KINDS[0][1])
        ttk.Combobox(row, textvariable=self.browse_kind, state="readonly", width=20,
                     values=[label for _, label in BROWSE_KINDS]).pack(side="left", padx=6)
        self.browse_kind.trace_add("write", lambda *_: self._refresh_browse())

        self.browse_search = tk.StringVar()
        ttk.Entry(left, textvariable=self.browse_search).pack(fill="x", pady=(6, 0))
        self.browse_search.trace_add("write", lambda *_: self._refresh_browse())

        self.browse_tree = ttk.Treeview(left, columns=("id", "note", "src"), show="headings", height=22)
        for col, text, width in (("id", "id", 190), ("note", "kind", 90), ("src", "from", 55)):
            self.browse_tree.heading(col, text=text)
            self.browse_tree.column(col, width=width)
        self.browse_tree.pack(fill="both", expand=True, pady=(8, 0))
        self.browse_tree.tag_configure("mod", foreground=theme.GREEN)

        # ---- right: create ----
        create = ui_kit.Section(body, "Create")
        create.pack(side="left", fill="both", expand=True)
        right = create.body
        self.notebook = ttk.Notebook(right)
        self.notebook.pack(fill="both", expand=True)
        self._build_template_page()
        self._build_goal_page()

        self.status = ttk.Label(self, text="", style="Status.TLabel", wraplength=900, justify="left")
        self.status.pack(anchor="w", pady=(8, 0))

        self.on_mod_changed()

    # ---- create: faction template ----

    def _build_template_page(self):
        page = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(page, text="New faction")

        ttk.Label(page, text="Faction id (lowercase, no spaces)").pack(anchor="w")
        self.t_id = tk.StringVar(value="faction_template_")
        ttk.Entry(page, textvariable=self.t_id, width=36).pack(anchor="w")
        self.t_id_hint = ttk.Label(page, text="", style="Muted.TLabel")
        self.t_id_hint.pack(anchor="w")
        self.t_id.trace_add("write", lambda *_: self._check_template_id())

        ttk.Label(page, text="Faction name (shown in game)").pack(anchor="w", pady=(8, 0))
        self.t_name = tk.StringVar()
        ttk.Entry(page, textvariable=self.t_name, width=36).pack(anchor="w")

        row = ttk.Frame(page)
        row.pack(fill="x", pady=(8, 0))
        icon_col = ttk.Frame(row)
        icon_col.pack(side="left")
        ttk.Label(icon_col, text="Icon").pack(anchor="w")
        self.t_icon = tk.StringVar()
        self.icon_combo = ttk.Combobox(icon_col, textvariable=self.t_icon, state="readonly", width=30)
        self.icon_combo.pack()
        man_col = ttk.Frame(row)
        man_col.pack(side="left", padx=(16, 0))
        ttk.Label(man_col, text="Manifest (main goal)").pack(anchor="w")
        self.t_manifest = tk.StringVar()
        self.manifest_combo = ttk.Combobox(man_col, textvariable=self.t_manifest, state="readonly", width=36)
        self.manifest_combo.pack()

        self.t_leader_join = tk.BooleanVar(value=True)
        ttk.Checkbutton(page, text="Faction leader may join another faction",
                        variable=self.t_leader_join).pack(anchor="w", pady=(8, 0))

        picks = ttk.Frame(page)
        picks.pack(fill="both", expand=True, pady=(8, 0))
        self.goal_picker = _PickList(picks, "Starting goals (click to toggle)", height=9)
        self.goal_picker.pack(side="left", fill="both", expand=True)
        self.rule_picker = _PickList(picks, "Default rules (click to toggle)", height=9)
        self.rule_picker.pack(side="left", fill="both", expand=True, padx=(10, 0))

        trig = ttk.Frame(page)
        trig.pack(fill="x", pady=(8, 0))
        vcol = ttk.Frame(trig)
        vcol.pack(side="left", fill="x", expand=True)
        ttk.Label(vcol, text="visible (who sees this faction option)").pack(anchor="w")
        self.t_visible = tk.Text(vcol, height=3, width=30)
        self.t_visible.insert("1.0", "always = yes")
        self.t_visible.pack(fill="x")
        acol = ttk.Frame(trig)
        acol.pack(side="left", fill="x", expand=True, padx=(10, 0))
        ttk.Label(acol, text="available (who may pick it) — optional").pack(anchor="w")
        self.t_available = tk.Text(acol, height=3, width=30)
        self.t_available.pack(fill="x")

        ttk.Button(page, text="Create Faction", style="Accent.TButton",
                   command=self._create_template).pack(anchor="w", pady=(10, 0))

    # ---- create: goal ----

    def _build_goal_page(self):
        page = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(page, text="New goal")

        ttk.Label(page, text="Goal id").pack(anchor="w")
        self.g_id = tk.StringVar(value="faction_goal_")
        ttk.Entry(page, textvariable=self.g_id, width=36).pack(anchor="w")
        self.g_id_hint = ttk.Label(page, text="", style="Muted.TLabel")
        self.g_id_hint.pack(anchor="w")
        self.g_id.trace_add("write", lambda *_: self._check_goal_id())

        ttk.Label(page, text="Goal name").pack(anchor="w", pady=(8, 0))
        self.g_name = tk.StringVar()
        ttk.Entry(page, textvariable=self.g_name, width=36).pack(anchor="w")

        ttk.Label(page, text="Description").pack(anchor="w", pady=(8, 0))
        self.g_desc = tk.Text(page, height=3, width=44)
        self.g_desc.pack(anchor="w", fill="x")

        row = ttk.Frame(page)
        row.pack(fill="x", pady=(8, 0))
        ttk.Label(row, text="Category").pack(side="left")
        self.g_category = tk.StringVar(value="short_term")
        ttk.Combobox(row, textvariable=self.g_category, state="readonly", width=14,
                     values=list(fc.GOAL_CATEGORIES)).pack(side="left", padx=6)
        ttk.Label(row, text="AI priority").pack(side="left", padx=(16, 4))
        self.g_ai = tk.StringVar(value="100")
        ttk.Entry(row, textvariable=self.g_ai, width=8).pack(side="left")

        ttk.Label(page, text="completed = { ... }  — when is this goal done?").pack(anchor="w", pady=(8, 0))
        self.g_completed = tk.Text(page, height=5, width=44)
        self.g_completed.pack(fill="x")
        ttk.Label(page, text="Leave blank and the goal can never complete — that is the game's own behaviour.",
                  style="Muted.TLabel", wraplength=440, justify="left").pack(anchor="w")

        ttk.Label(page, text="complete_effect = { ... } — optional reward").pack(anchor="w", pady=(8, 0))
        self.g_effect = tk.Text(page, height=4, width=44)
        self.g_effect.insert("1.0", "add_faction_initiative = 1")
        self.g_effect.pack(fill="x")

        ttk.Button(page, text="Create Goal", style="Accent.TButton",
                   command=self._create_goal).pack(anchor="w", pady=(10, 0))

    # ---- data ----

    def on_mod_changed(self):
        if state.is_loaded:
            self.header.set_status(True, state.mod_name)
        else:
            self.header.set_status(False, "no mod open")
        self._cache = {}
        self._reload()

    def on_show(self):
        self.on_mod_changed()

    def _data(self):
        if not self._cache and state.is_loaded:
            self._cache = {
                "templates": fc.list_templates(state.mod_root),
                "goals": fc.list_goals(state.mod_root),
                "rules": fc.list_rules(state.mod_root),
                "icons": fc.list_icons(state.mod_root),
            }
        return self._cache

    def _reload(self):
        data = self._data()
        goals = data.get("goals", {})
        rules = data.get("rules", {})
        icons = data.get("icons", [])

        manifests = sorted(g for g, (_, cat) in goals.items() if cat == "manifest")
        self.manifest_combo["values"] = [""] + manifests
        self.icon_combo["values"] = [""] + icons

        pickable = sorted((g, cat) for g, (_, cat) in goals.items()
                          if cat in fc.GOAL_CATEGORIES)
        self.goal_picker.set_items(pickable)
        self.rule_picker.set_items(sorted((r, kind) for r, (_, kind) in rules.items()))
        self._refresh_browse()

    def _refresh_browse(self):
        self.browse_tree.delete(*self.browse_tree.get_children())
        if not state.is_loaded:
            return
        label = self.browse_kind.get()
        kind = next((k for k, lab in BROWSE_KINDS if lab == label), "templates")
        data = self._data()
        needle = self.browse_search.get().strip().lower()

        if kind == "templates":
            rows = [(i, "", src) for i, src in sorted(data.get("templates", {}).items())]
        elif kind == "goals":
            rows = [(i, cat, src) for i, (src, cat) in sorted(data.get("goals", {}).items())]
        else:
            rows = [(i, typ, src) for i, (src, typ) in sorted(data.get("rules", {}).items())]

        for item_id, note, src in rows:
            if needle and needle not in item_id.lower():
                continue
            self.browse_tree.insert("", "end", values=(item_id, note, src),
                                     tags=("mod",) if src == "mod" else ())

    # ---- validation ----

    def _check_template_id(self):
        tid = self.t_id.get().strip().lower()
        existing = self._data().get("templates", {})
        if not tid or not tid.replace("_", "").isalnum():
            self.t_id_hint.config(text="lowercase letters/digits/underscore", foreground=theme.MUTED)
        elif tid in existing:
            self.t_id_hint.config(text=f"'{tid}' already exists ({existing[tid]})!", foreground=theme.RED)
        else:
            self.t_id_hint.config(text=f"'{tid}' is free ✓", foreground=theme.GREEN)

    def _check_goal_id(self):
        gid = self.g_id.get().strip().lower()
        existing = self._data().get("goals", {})
        if not gid or not gid.replace("_", "").isalnum():
            self.g_id_hint.config(text="lowercase letters/digits/underscore", foreground=theme.MUTED)
        elif gid in existing:
            self.g_id_hint.config(text=f"'{gid}' already exists ({existing[gid][0]})!", foreground=theme.RED)
        else:
            self.g_id_hint.config(text=f"'{gid}' is free ✓", foreground=theme.GREEN)

    # ---- actions ----

    def _create_template(self):
        if not state.is_loaded:
            messagebox.showerror("No mod", "Open or create a mod first.")
            return
        tid = self.t_id.get().strip().lower()
        name = self.t_name.get().strip()
        if not tid or not tid.replace("_", "").isalnum() or not name:
            messagebox.showerror("Missing info", "A valid faction id and a faction name are required.")
            return
        existing = self._data().get("templates", {})
        if tid in existing:
            messagebox.showerror("Id taken", f"'{tid}' already exists ({existing[tid]}).")
            return

        try:
            created = fc.create_template(
                state.mod_root, template_id=tid, display_name=name,
                icon=self.t_icon.get().strip(), manifest=self.t_manifest.get().strip(),
                goals=sorted(self.goal_picker.selected),
                default_rules=sorted(self.rule_picker.selected),
                can_leader_join_other_factions=self.t_leader_join.get(),
                available_raw=self.t_available.get("1.0", "end"),
                visible_raw=self.t_visible.get("1.0", "end"),
            )
        except Exception as exc:
            messagebox.showerror("Failed", f"Faction creation failed:\n{exc}")
            return

        existing[tid] = "mod"
        state.add_loc(f"{tid}_name", name)
        self._refresh_browse()
        self.status.config(
            text=f"Created faction '{name}' ({tid}) with {len(self.goal_picker.selected)} goals "
                 f"and {len(self.rule_picker.selected)} rules — {len(created)} files written."
        )

    def _create_goal(self):
        if not state.is_loaded:
            messagebox.showerror("No mod", "Open or create a mod first.")
            return
        gid = self.g_id.get().strip().lower()
        name = self.g_name.get().strip()
        if not gid or not gid.replace("_", "").isalnum() or not name:
            messagebox.showerror("Missing info", "A valid goal id and a goal name are required.")
            return
        existing = self._data().get("goals", {})
        if gid in existing:
            messagebox.showerror("Id taken", f"'{gid}' already exists ({existing[gid][0]}).")
            return
        try:
            ai_factor = float(self.g_ai.get() or 100)
            ai_factor = int(ai_factor) if ai_factor == int(ai_factor) else ai_factor
        except ValueError:
            messagebox.showerror("Bad number", "AI priority must be a number.")
            return

        try:
            created = fc.create_goal(
                state.mod_root, goal_id=gid, display_name=name,
                description=self.g_desc.get("1.0", "end").strip(),
                category=self.g_category.get(),
                completed_raw=self.g_completed.get("1.0", "end"),
                complete_effect_raw=self.g_effect.get("1.0", "end"),
                ai_factor=ai_factor,
            )
        except Exception as exc:
            messagebox.showerror("Failed", f"Goal creation failed:\n{exc}")
            return

        existing[gid] = ("mod", self.g_category.get())
        state.add_loc(f"{gid}_name", name)
        self._reload()
        self.status.config(text=f"Created goal '{name}' ({gid}) — {len(created)} files written. "
                                "It is now pickable in the New faction tab.")
