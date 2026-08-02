"""Peace Conference tab: tune how expensive a peace action is under
conditions you define - common/peace_conference/cost_modifiers/."""

import tkinter as tk
from tkinter import ttk, messagebox

from app.state import state
from app import peace_modifier_creator as pmc
from app.effect_wizard import EffectWizard
from app import theme, ui_kit


class PeaceModifierTab(ttk.Frame):
    def __init__(self, master):
        super().__init__(master, padding=12)
        self._build()
        state.subscribe(self.on_mod_changed)

    def _build(self):
        self.header = ui_kit.PageHeader(
            self, "Peace Conference",
            "Tunes how expensive a peace action (take states, puppet, liberate, force government) is under conditions you set - the 4 action types themselves are engine-fixed and can't be added by script.", help_key="peace_modifier")
        ttk.Label(
            self, text="New peace ACTION types (annex, take states, ...) are fixed by the game engine — "
                       "what mods tune here is how expensive an existing action is under conditions you set.",
            style="Muted.TLabel", wraplength=980, justify="left",
        ).pack(anchor="w", pady=(0, 8))

        body = ttk.Frame(self)
        body.pack(fill="both", expand=True)

        browse = ui_kit.Section(body, "Existing cost modifiers")
        browse.pack(side="left", fill="y", padx=(0, ui_kit.PAD_SECTION))
        browse.configure(width=300)
        browse.pack_propagate(False)
        self.search_var = tk.StringVar()
        ttk.Entry(browse.body, textvariable=self.search_var).pack(fill="x", pady=(4, 0))
        self.search_var.trace_add("write", lambda *_: self._refresh_list())
        self.tree = ttk.Treeview(browse.body, columns=("id", "src"), show="headings", height=24)
        self.tree.heading("id", text="modifier id")
        self.tree.heading("src", text="from")
        self.tree.column("id", width=210)
        self.tree.column("src", width=60)
        self.tree.pack(fill="both", expand=True, pady=(6, 0))
        self.tree.tag_configure("mod", foreground=theme.GREEN)

        create = ui_kit.Section(body, "Create a new cost modifier")
        create.pack(side="left", fill="both", expand=True)
        right = create.body

        row = ttk.Frame(right)
        row.pack(fill="x", pady=(8, 0))
        ttk.Label(row, text="Modifier id").pack(side="left")
        self.id_var = tk.StringVar()
        ttk.Entry(row, textvariable=self.id_var, width=28).pack(side="left", padx=(4, 16))
        ttk.Label(row, text="Category").pack(side="left")
        self.category_var = tk.StringVar(value="other")
        ttk.Combobox(row, textvariable=self.category_var, state="readonly", width=22,
                     values=pmc.CATEGORIES).pack(side="left", padx=4)
        self.id_hint = ttk.Label(right, text="", style="Muted.TLabel")
        self.id_hint.pack(anchor="w")
        self.id_var.trace_add("write", lambda *_: self._check_id())

        ttk.Label(right, text="Applies to peace action type(s)").pack(anchor="w", pady=(8, 0))
        types_row = ttk.Frame(right)
        types_row.pack(fill="x")
        self.type_vars = {}
        for t in pmc.PEACE_ACTION_TYPES:
            var = tk.BooleanVar(value=(t == "take_states"))
            ttk.Checkbutton(types_row, text=t, variable=var).pack(side="left", padx=(0, 12))
            self.type_vars[t] = var

        row2 = ttk.Frame(right)
        row2.pack(fill="x", pady=(8, 0))
        ttk.Label(row2, text="Cost multiplier (1.0 = no change, <1 cheaper, >1 pricier)").pack(side="left")
        self.mult_var = tk.StringVar(value="0.75")
        ttk.Entry(row2, textvariable=self.mult_var, width=8).pack(side="left", padx=6)

        ttk.Label(right, text="enable (when this modifier applies — ROOT is the negotiator, "
                              "FROM the taker, FROM.FROM the giver)").pack(anchor="w", pady=(8, 0))
        eff_row = ttk.Frame(right)
        eff_row.pack(fill="x")
        self.enable_txt = tk.Text(eff_row, height=6, width=50)
        self.enable_txt.insert("1.0", "always = yes")
        self.enable_txt.pack(side="left", fill="both", expand=True)
        ttk.Button(eff_row, text="Wizard...", command=lambda: EffectWizard(self, self.enable_txt, "trigger")).pack(
            side="left", padx=(6, 0), anchor="n")

        ttk.Button(right, text="Create Cost Modifier", style="Accent.TButton",
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
            self._cache = pmc.list_modifiers(state.mod_root)
        return self._cache

    def _refresh_list(self):
        self.tree.delete(*self.tree.get_children())
        if not state.is_loaded:
            return
        needle = self.search_var.get().strip().lower()
        for mod_id, source in sorted(self._data().items()):
            if needle and needle not in mod_id.lower():
                continue
            self.tree.insert("", "end", values=(mod_id, source), tags=("mod",) if source == "mod" else ())

    def _check_id(self):
        mid = self.id_var.get().strip()
        if not mid:
            self.id_hint.config(text="", foreground=theme.MUTED)
            return
        existing = self._data()
        if mid in existing:
            self.id_hint.config(text=f"'{mid}' already exists ({existing[mid]})!", foreground=theme.RED)
        else:
            self.id_hint.config(text="free ✓", foreground=theme.GREEN)

    def _create(self):
        if not state.is_loaded:
            messagebox.showerror("No mod", "Open or create a mod first.")
            return
        mid = self.id_var.get().strip()
        if not mid:
            messagebox.showerror("Missing info", "A modifier id is required.")
            return
        if mid in self._data():
            messagebox.showerror("Id taken", f"'{mid}' already exists ({self._data()[mid]}).")
            return
        types = [t for t, var in self.type_vars.items() if var.get()]
        if not types:
            messagebox.showerror("No action types", "Check at least one peace action type.")
            return
        try:
            mult = float(self.mult_var.get())
            if mult <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Bad number", "Cost multiplier must be a number greater than 0.")
            return

        try:
            path = pmc.create_modifier(
                state.mod_root, modifier_id=mid, category=self.category_var.get(),
                peace_action_types=types, enable_raw=self.enable_txt.get("1.0", "end"),
                cost_multiplier=mult,
            )
        except Exception as exc:
            messagebox.showerror("Failed", f"Cost modifier creation failed:\n{exc}")
            return

        self._data()[mid] = "mod"
        self._refresh_list()
        self.status.config(text=f"Created cost modifier '{mid}' in {path}.")
