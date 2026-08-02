"""Decision Categories tab: define a new tab/folder for the decisions panel
- common/decisions/categories/."""

import tkinter as tk
from tkinter import ttk, messagebox

from app.state import state
from app import decision_category_creator as dcc
from app.effect_wizard import EffectWizard
from app import theme, ui_kit


class DecisionCategoryTab(ttk.Frame):
    def __init__(self, master):
        super().__init__(master, padding=12)
        self._build()
        state.subscribe(self.on_mod_changed)

    def _build(self):
        self.header = ui_kit.PageHeader(
            self, "Decision Categories",
            "Define a new tab/folder for the Decisions panel - icon, priority, visibility - so your decisions don't have to drop into an existing category.", help_key="decision_category")
        ttk.Label(
            self, text="Decisions in the Decisions tab pick one of these categories by name — "
                       "make one here first if you don't want them dropping into an existing tab.",
            style="Muted.TLabel", wraplength=980, justify="left",
        ).pack(anchor="w", pady=(0, 8))

        body = ttk.Frame(self)
        body.pack(fill="both", expand=True)

        browse = ui_kit.Section(body, "Existing categories")
        browse.pack(side="left", fill="y", padx=(0, ui_kit.PAD_SECTION))
        browse.configure(width=300)
        browse.pack_propagate(False)
        self.search_var = tk.StringVar()
        ttk.Entry(browse.body, textvariable=self.search_var).pack(fill="x", pady=(4, 0))
        self.search_var.trace_add("write", lambda *_: self._refresh_list())
        self.tree = ttk.Treeview(browse.body, columns=("id", "src"), show="headings", height=24)
        self.tree.heading("id", text="category id")
        self.tree.heading("src", text="from")
        self.tree.column("id", width=210)
        self.tree.column("src", width=60)
        self.tree.pack(fill="both", expand=True, pady=(6, 0))
        self.tree.tag_configure("mod", foreground=theme.GREEN)

        create = ui_kit.Section(body, "Create a new category")
        create.pack(side="left", fill="both", expand=True)
        right = create.body

        row = ttk.Frame(right)
        row.pack(fill="x", pady=(8, 0))
        ttk.Label(row, text="Category id").pack(side="left")
        self.id_var = tk.StringVar()
        ttk.Entry(row, textvariable=self.id_var, width=26).pack(side="left", padx=(4, 16))
        ttk.Label(row, text="Icon").pack(side="left")
        self.icon_var = tk.StringVar(value="generic_political_actions")
        ttk.Entry(row, textvariable=self.icon_var, width=26).pack(side="left", padx=4)
        self.id_hint = ttk.Label(right, text="", style="Muted.TLabel")
        self.id_hint.pack(anchor="w")
        self.id_var.trace_add("write", lambda *_: self._check_id())

        row2 = ttk.Frame(right)
        row2.pack(fill="x", pady=(8, 0))
        ttk.Label(row2, text="Tab display name").pack(side="left")
        self.name_var = tk.StringVar()
        ttk.Entry(row2, textvariable=self.name_var, width=30).pack(side="left", padx=(4, 16))
        ttk.Label(row2, text="Priority (higher = further left)").pack(side="left")
        self.priority_var = tk.StringVar()
        ttk.Entry(row2, textvariable=self.priority_var, width=6).pack(side="left", padx=4)

        ttk.Label(right, text="visible (when the tab itself shows up at all)").pack(anchor="w", pady=(8, 0))
        vis_row = ttk.Frame(right)
        vis_row.pack(fill="x")
        self.visible_txt = tk.Text(vis_row, height=5, width=50)
        self.visible_txt.pack(side="left", fill="both", expand=True)
        ttk.Button(vis_row, text="Wizard...", command=lambda: EffectWizard(self, self.visible_txt, "trigger")).pack(
            side="left", padx=(6, 0), anchor="n")

        ttk.Label(right, text="allowed (optional — one-time gate, e.g. DLC check)").pack(anchor="w", pady=(8, 0))
        allow_row = ttk.Frame(right)
        allow_row.pack(fill="x")
        self.allowed_txt = tk.Text(allow_row, height=3, width=50)
        self.allowed_txt.pack(side="left", fill="both", expand=True)
        ttk.Button(allow_row, text="Wizard...", command=lambda: EffectWizard(self, self.allowed_txt, "trigger")).pack(
            side="left", padx=(6, 0), anchor="n")

        ttk.Button(right, text="Create Category", style="Accent.TButton",
                   command=self._create).pack(anchor="w", pady=12)
        self.status = ttk.Label(right, text="", style="Status.TLabel", wraplength=560, justify="left")
        self.status.pack(anchor="w")

        self.on_mod_changed()

    def on_mod_changed(self):
        if state.is_loaded:
            self.header.set_status(True, state.mod_name)
        else:
            self.header.set_status(False, "no mod open")
        self._cache = {}
        self._refresh_list()

    def on_show(self):
        self.on_mod_changed()

    def _data(self):
        if not self._cache and state.is_loaded:
            self._cache = dcc.list_categories(state.mod_root)
        return self._cache

    def _refresh_list(self):
        self.tree.delete(*self.tree.get_children())
        if not state.is_loaded:
            return
        needle = self.search_var.get().strip().lower()
        for cat_id, source in sorted(self._data().items()):
            if needle and needle not in cat_id.lower():
                continue
            self.tree.insert("", "end", values=(cat_id, source), tags=("mod",) if source == "mod" else ())

    def _check_id(self):
        cid = self.id_var.get().strip()
        if not cid:
            self.id_hint.config(text="", foreground=theme.MUTED)
            return
        existing = self._data()
        if cid in existing:
            self.id_hint.config(text=f"'{cid}' already exists ({existing[cid]})!", foreground=theme.RED)
        else:
            self.id_hint.config(text="free ✓", foreground=theme.GREEN)

    def _create(self):
        if not state.is_loaded:
            messagebox.showerror("No mod", "Open or create a mod first.")
            return
        cid = self.id_var.get().strip()
        if not cid:
            messagebox.showerror("Missing info", "A category id is required.")
            return
        if cid in self._data():
            messagebox.showerror("Id taken", f"'{cid}' already exists ({self._data()[cid]}).")
            return
        priority = self.priority_var.get().strip()
        if priority:
            try:
                int(priority)
            except ValueError:
                messagebox.showerror("Bad number", "Priority must be a whole number.")
                return

        try:
            path = dcc.create_category(
                state.mod_root, category_id=cid, icon=self.icon_var.get().strip(),
                display_name=self.name_var.get().strip(), priority=priority or None,
                visible_raw=self.visible_txt.get("1.0", "end"), allowed_raw=self.allowed_txt.get("1.0", "end"),
            )
        except Exception as exc:
            messagebox.showerror("Failed", f"Category creation failed:\n{exc}")
            return

        self._data()[cid] = "mod"
        self._refresh_list()
        self.status.config(text=f"Created category '{cid}' in {path}.")
