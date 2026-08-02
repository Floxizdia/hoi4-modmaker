"""Opinion Modifiers tab: define the named opinion swings that decisions,
events, focuses and diplomatic actions grant via add_opinion_modifier.

Design showcase: this tab is the first rebuilt on the shared ui_kit
primitives (PageHeader/Section/FieldRow) instead of hand-rolled banner
labels and ad-hoc ttk.Frame padding - the pattern every other creator tab
should eventually move to.
"""

import tkinter as tk
from tkinter import ttk, messagebox

from app.state import state
from app import opinion_modifier_creator as omc
from app import theme, ui_kit


class OpinionModifierTab(ttk.Frame):
    def __init__(self, master):
        super().__init__(master, padding=ui_kit.PAD_PAGE)
        self._build()
        state.subscribe(self.on_mod_changed)

    def _build(self):
        self.header = ui_kit.PageHeader(
            self, "Opinion Modifiers",
            "Named opinion swings that decisions, events, focuses and diplomatic actions "
            "grant via add_opinion_modifier.", help_key="opinion_modifier")

        body = ttk.Frame(self)
        body.pack(fill="both", expand=True)

        browse = ui_kit.Section(body, "Existing modifiers")
        browse.pack(side="left", fill="y", padx=(0, ui_kit.PAD_SECTION))
        browse.configure(width=320)
        browse.pack_propagate(False)

        self.search_var = tk.StringVar()
        ttk.Entry(browse.body, textvariable=self.search_var).pack(fill="x")
        self.search_var.trace_add("write", lambda *_: self._refresh_list())
        self.tree = ttk.Treeview(browse.body, columns=("id", "src"), show="headings", height=22)
        self.tree.heading("id", text="modifier id")
        self.tree.heading("src", text="from")
        self.tree.column("id", width=210)
        self.tree.column("src", width=60)
        self.tree.pack(fill="both", expand=True, pady=(6, 0))
        self.tree.tag_configure("mod", foreground=theme.GREEN)

        create = ui_kit.Section(body, "Create a new modifier")
        create.pack(side="left", fill="both", expand=True)
        right = create.body

        row = ui_kit.FieldRow(right)
        self.id_var = tk.StringVar()
        row.add("Modifier id", ttk.Entry, textvariable=self.id_var, width=28)
        self.value_var = tk.StringVar(value="10")
        row.add("Value", ttk.Entry, textvariable=self.value_var, width=8)
        self.id_hint = ttk.Label(right, text="", style="Muted.TLabel")
        self.id_hint.pack(anchor="w", pady=(0, ui_kit.PAD_FIELD))
        self.id_var.trace_add("write", lambda *_: self._check_id())

        name_row = ui_kit.FieldRow(right)
        self.name_var = tk.StringVar()
        name_row.add("Display name (optional loc text, shown in the opinion breakdown)",
                      ttk.Entry, textvariable=self.name_var, width=44)

        row2 = ui_kit.FieldRow(right)
        self.duration_amount_var = tk.StringVar()
        row2.add("Duration amount", ttk.Entry, textvariable=self.duration_amount_var, width=6)
        self.duration_unit_var = tk.StringVar(value="permanent")
        row2.add("Duration unit", ttk.Combobox, textvariable=self.duration_unit_var, state="readonly",
                  width=10, values=["permanent", "days", "months", "years"])
        self.decay_var = tk.StringVar()
        row2.add("Decay/year (optional)", ttk.Entry, textvariable=self.decay_var, width=6)

        row3 = ui_kit.FieldRow(right)
        self.min_trust_var = tk.StringVar()
        row3.add("Min trust", ttk.Entry, textvariable=self.min_trust_var, width=6)
        self.max_trust_var = tk.StringVar()
        row3.add("Max trust", ttk.Entry, textvariable=self.max_trust_var, width=6)

        check_row = ttk.Frame(right, style="CardInner.TFrame")
        check_row.pack(fill="x", pady=(0, ui_kit.PAD_FIELD))
        self.trade_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(check_row, text="Trade-related", variable=self.trade_var).pack(side="left")
        self.target_only_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(check_row, text="Only visible to the target (target = yes)",
                        variable=self.target_only_var).pack(side="left", padx=(18, 0))

        ttk.Label(
            right, text="Leave duration as 'permanent' for something like non_aggression_pact - it stays "
                       "until code explicitly removes it. Pick a duration + decay for a fading effect "
                       "like a temporary protest or a pact bonus that wears off.",
            style="Muted.TLabel", wraplength=560, justify="left",
        ).pack(anchor="w", pady=(4, ui_kit.PAD_FIELD))

        ttk.Button(right, text="Create Modifier", style="Accent.TButton",
                   command=self._create).pack(anchor="w")
        self.status = ttk.Label(right, text="", style="Status.TLabel", wraplength=560, justify="left")
        self.status.pack(anchor="w", pady=(8, 0))

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
            self._cache = omc.list_modifiers(state.mod_root)
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
        try:
            value = float(self.value_var.get() or 0)
            value = int(value) if value == int(value) else value
            decay = float(self.decay_var.get()) if self.decay_var.get().strip() else None
            if decay is not None and decay == int(decay):
                decay = int(decay)
            min_trust = float(self.min_trust_var.get()) if self.min_trust_var.get().strip() else None
            max_trust = float(self.max_trust_var.get()) if self.max_trust_var.get().strip() else None
        except ValueError:
            messagebox.showerror("Bad number", "Value/decay/trust fields must be numbers.")
            return

        unit = self.duration_unit_var.get()
        duration_unit = "" if unit == "permanent" else unit
        duration_amount = self.duration_amount_var.get().strip()

        try:
            created = omc.create_modifier(
                state.mod_root, modifier_id=mid, display_name=self.name_var.get().strip(),
                value=value, duration_unit=duration_unit, duration_amount=duration_amount,
                decay=decay, min_trust=min_trust, max_trust=max_trust,
                is_trade=self.trade_var.get(), target_only=self.target_only_var.get(),
            )
        except Exception as exc:
            messagebox.showerror("Failed", f"Modifier creation failed:\n{exc}")
            return

        self._data()[mid] = "mod"
        if self.name_var.get().strip():
            state.add_loc(mid, self.name_var.get().strip())
        self._refresh_list()
        self.status.config(text=f"Created opinion modifier '{mid}' — {len(created)} files written.")
