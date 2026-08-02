"""Traits tab: browse every political leader / commander / scientist trait
already in play (base game + mod) and create new ones - the trait library
Character editor didn't have its own place for."""

import tkinter as tk
from tkinter import ttk, messagebox

from app.state import state
from app import character_traits
from app import trait_creator
from app import theme, ui_kit

ROLES = [
    ("political", "Political leader"),
    ("land", "Army commander (land)"),
    ("navy", "Navy commander"),
    ("scientist", "Scientist"),
]


class TraitTab(ttk.Frame):
    def __init__(self, master):
        super().__init__(master, padding=12)
        self._catalog = {}
        self._build()
        state.subscribe(self.on_mod_changed)

    def _build(self):
        self.header = ui_kit.PageHeader(
            self, "Traits",
            "A library of leader/general/admiral/advisor traits already in the base game plus your mod, so you can browse what exists and reuse or clone one.", help_key="traits")

        body = ttk.Frame(self)
        body.pack(fill="both", expand=True)

        # ---- left: browse ----
        left = ttk.Frame(body, width=340)
        left.pack(side="left", fill="y", padx=(0, 16))
        left.pack_propagate(False)
        ttk.Label(left, text="Browse existing traits", font=("Segoe UI", 10, "bold")).pack(anchor="w")
        role_row = ttk.Frame(left)
        role_row.pack(fill="x", pady=(6, 0))
        ttk.Label(role_row, text="Category").pack(side="left")
        self.browse_role_display = tk.StringVar(value=ROLES[0][1])
        ttk.Combobox(role_row, textvariable=self.browse_role_display, state="readonly", width=20,
                     values=[label for _, label in ROLES]).pack(side="left", padx=6)
        self.browse_role_display.trace_add("write", lambda *_: self._refresh_browse())

        self.search_var = tk.StringVar()
        ttk.Entry(left, textvariable=self.search_var).pack(fill="x", pady=(6, 0))
        self.search_var.trace_add("write", lambda *_: self._refresh_browse())

        cols = ("id", "source")
        self.tree = ttk.Treeview(left, columns=cols, show="headings", height=20)
        self.tree.heading("id", text="trait id")
        self.tree.heading("source", text="from")
        self.tree.column("id", width=220)
        self.tree.column("source", width=80)
        self.tree.pack(fill="both", expand=True, pady=(8, 0))
        self.tree.tag_configure("mod", foreground=theme.GREEN)

        # ---- right: create ----
        right = ttk.Frame(body)
        right.pack(side="left", fill="both", expand=True)
        ttk.Label(right, text="Create a new trait", font=("Segoe UI", 10, "bold")).pack(anchor="w")

        row = ttk.Frame(right)
        row.pack(fill="x", pady=(8, 0))
        ttk.Label(row, text="Category").pack(side="left")
        self.role_var = tk.StringVar(value=ROLES[0][1])
        role_combo = ttk.Combobox(row, textvariable=self.role_var, state="readonly", width=22,
                                   values=[label for _, label in ROLES])
        role_combo.pack(side="left", padx=6)
        role_combo.bind("<<ComboboxSelected>>", lambda e: self._on_role_change())

        ttk.Label(right, text="Trait id (lowercase, no spaces)").pack(anchor="w", pady=(8, 0))
        self.id_var = tk.StringVar()
        ttk.Entry(right, textvariable=self.id_var, width=32).pack(anchor="w")
        self.id_hint = ttk.Label(right, text="", style="Muted.TLabel")
        self.id_hint.pack(anchor="w")
        self.id_var.trace_add("write", lambda *_: self._check_id())

        ttk.Label(right, text="Display name").pack(anchor="w", pady=(8, 0))
        self.name_var = tk.StringVar()
        ttk.Entry(right, textvariable=self.name_var, width=32).pack(anchor="w")

        self.type_row = ttk.Frame(right)
        ttk.Label(self.type_row, text="Applies to").pack(side="left")
        self.unit_type_var = tk.StringVar(value="all")
        ttk.Combobox(self.type_row, textvariable=self.unit_type_var, state="readonly", width=8,
                     values=["land", "navy", "all"]).pack(side="left", padx=6)

        opts_row = ttk.Frame(right)
        self.opts_row = opts_row
        self.random_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(opts_row, text="Can be randomly assigned", variable=self.random_var).pack(side="left")
        ttk.Label(opts_row, text="AI factor").pack(side="left", padx=(16, 4))
        self.ai_factor_var = tk.StringVar(value="1")
        ttk.Entry(opts_row, textvariable=self.ai_factor_var, width=6).pack(side="left")

        ttk.Label(right, text="Modifiers (one per line, raw script)").pack(anchor="w", pady=(8, 0))
        self.mod_txt = tk.Text(right, height=8, width=44)
        self.mod_txt.pack(fill="x")
        self.mod_hint = ttk.Label(
            right, text="", style="Muted.TLabel", wraplength=440, justify="left",
        )
        self.mod_hint.pack(anchor="w", pady=(2, 0))

        ttk.Button(right, text="Create Trait", style="Accent.TButton",
                   command=self._create).pack(anchor="w", pady=12)

        self.status = ttk.Label(right, text="", style="Status.TLabel", wraplength=440, justify="left")
        self.status.pack(anchor="w")

        self._on_role_change()
        self.on_mod_changed()

    # ---- helpers ----

    def _role_key(self):
        display = self.role_var.get()
        return next(k for k, label in ROLES if label == display)

    def _on_role_change(self):
        role = self._role_key()
        self.type_row.pack_forget()
        self.opts_row.pack_forget()
        if role in ("land", "navy"):
            self.unit_type_var.set(role)
            self.type_row.pack(fill="x", pady=(8, 0))
        if role in ("political", "land", "navy"):
            self.opts_row.pack(fill="x", pady=(8, 0))
        hints = {
            "political": "e.g. political_power_factor = 0.1, stability_factor = 0.05",
            "land": "e.g. attack = 0.1, defense = 0.1, org_loss_when_moving_factor = -0.1",
            "navy": "e.g. naval_speed_factor = 0.1, night_accuracy_factor = 0.15",
            "scientist": "e.g. special_project_speed_factor = 0.1 (only special-project modifiers apply here)",
        }
        self.mod_hint.configure(text=hints[role])
        self._check_id()

    def on_mod_changed(self):
        if state.is_loaded:
            self.header.set_status(True, state.mod_name)
        else:
            self.header.set_status(False, "no mod open")
        self._catalog = {}
        self._refresh_browse()

    def on_show(self):
        self.on_mod_changed()

    def _ensure_catalog(self):
        if not self._catalog and state.is_loaded:
            self._catalog = character_traits.all_traits_by_category(state.mod_root)
        return self._catalog

    def _refresh_browse(self):
        self.tree.delete(*self.tree.get_children())
        if not state.is_loaded:
            return
        display = self.browse_role_display.get()
        role = next((k for k, label in ROLES if label == display), "political")
        catalog = self._ensure_catalog().get(role, {})
        needle = self.search_var.get().strip().lower()
        for trait_id, source in sorted(catalog.items()):
            if needle and needle not in trait_id.lower():
                continue
            tags = ("mod",) if source == "mod" else ()
            self.tree.insert("", "end", values=(trait_id, source), tags=tags)

    def _check_id(self):
        tid = self.id_var.get().strip().lower()
        if not tid or not tid.replace("_", "").isalnum():
            self.id_hint.config(text="lowercase letters/digits/underscore", foreground=theme.MUTED)
            return
        if not state.is_loaded:
            return
        role = self._role_key()
        catalog = self._ensure_catalog().get(role, {})
        if tid in catalog:
            self.id_hint.config(text=f"'{tid}' already exists ({catalog[tid]})!", foreground=theme.RED)
        else:
            self.id_hint.config(text=f"'{tid}' is free ✓", foreground=theme.GREEN)

    # ---- create ----

    def _create(self):
        if not state.is_loaded:
            messagebox.showerror("No mod", "Open or create a mod first.")
            return
        role = self._role_key()
        tid = self.id_var.get().strip().lower()
        name = self.name_var.get().strip()
        if not tid or not tid.replace("_", "").isalnum() or not name:
            messagebox.showerror("Missing info", "A valid trait id and a display name are required.")
            return
        catalog = self._ensure_catalog().get(role, {})
        if tid in catalog:
            messagebox.showerror("Id taken", f"'{tid}' already exists ({catalog[tid]}).")
            return
        try:
            ai_factor = float(self.ai_factor_var.get() or 1)
        except ValueError:
            messagebox.showerror("Bad number", "AI factor must be a number.")
            return

        try:
            created = trait_creator.create_trait(
                state.mod_root, role=role, trait_id=tid, display_name=name,
                random=self.random_var.get(), unit_type=self.unit_type_var.get(),
                ai_factor=ai_factor, modifiers_raw=self.mod_txt.get("1.0", "end"),
            )
        except Exception as exc:
            messagebox.showerror("Failed", f"Trait creation failed:\n{exc}")
            return

        catalog[tid] = "mod"
        state.add_loc(tid, name)
        self._refresh_browse()
        self.status.config(text=f"Created trait '{name}' ({tid}) — {len(created)} files written.")
