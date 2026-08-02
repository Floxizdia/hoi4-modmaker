"""War Goals tab: define a new casus belli type - what a war justifies
(taking states, puppeting, liberating, toppling, annexing) and what it
costs - common/wargoals/."""

import tkinter as tk
from tkinter import ttk, messagebox

from app.state import state
from app import war_goal_creator as wgc
from app.effect_wizard import EffectWizard
from app import theme, ui_kit


class WarGoalTab(ttk.Frame):
    def __init__(self, master):
        super().__init__(master, padding=12)
        self._build()
        state.subscribe(self.on_mod_changed)

    def _build(self):
        self.header = ui_kit.PageHeader(
            self, "War Goals",
            "Define a new casus belli type - what a war is fought to achieve (take states, puppet, liberate, topple a government, annex) and its cost/threat.", help_key="war_goal")

        body = ttk.Frame(self)
        body.pack(fill="both", expand=True)

        browse = ui_kit.Section(body, "Existing war goals")
        browse.pack(side="left", fill="y", padx=(0, ui_kit.PAD_SECTION))
        browse.configure(width=300)
        browse.pack_propagate(False)
        self.search_var = tk.StringVar()
        ttk.Entry(browse.body, textvariable=self.search_var).pack(fill="x", pady=(4, 0))
        self.search_var.trace_add("write", lambda *_: self._refresh_list())
        self.tree = ttk.Treeview(browse.body, columns=("id", "src"), show="headings", height=24)
        self.tree.heading("id", text="wargoal id")
        self.tree.heading("src", text="from")
        self.tree.column("id", width=210)
        self.tree.column("src", width=60)
        self.tree.pack(fill="both", expand=True, pady=(6, 0))
        self.tree.tag_configure("mod", foreground=theme.GREEN)

        create = ui_kit.Section(body, "Create a new war goal")
        create.pack(side="left", fill="both", expand=True)
        right = create.body

        row = ttk.Frame(right)
        row.pack(fill="x", pady=(8, 0))
        ttk.Label(row, text="War goal id").pack(side="left")
        self.id_var = tk.StringVar()
        ttk.Entry(row, textvariable=self.id_var, width=26).pack(side="left", padx=(4, 16))
        ttk.Label(row, text="Kind").pack(side="left")
        self.kind_var = tk.StringVar(value="take_states")
        ttk.Combobox(row, textvariable=self.kind_var, state="readonly", width=18,
                     values=wgc.GOAL_KINDS).pack(side="left", padx=4)
        self.id_hint = ttk.Label(right, text="", style="Muted.TLabel")
        self.id_hint.pack(anchor="w")
        self.id_var.trace_add("write", lambda *_: self._check_id())

        row2 = ttk.Frame(right)
        row2.pack(fill="x", pady=(8, 0))
        ttk.Label(row2, text="War name loc key").pack(side="left")
        self.warkey_var = tk.StringVar()
        ttk.Entry(row2, textvariable=self.warkey_var, width=24).pack(side="left", padx=(4, 16))
        ttk.Label(row2, text="Display text").pack(side="left")
        self.wartext_var = tk.StringVar()
        ttk.Entry(row2, textvariable=self.wartext_var, width=26).pack(side="left", padx=4)

        row3 = ttk.Frame(right)
        row3.pack(fill="x", pady=(8, 0))
        ttk.Label(row3, text="Base cost").pack(side="left")
        self.base_var = tk.StringVar(value="100")
        ttk.Entry(row3, textvariable=self.base_var, width=8).pack(side="left", padx=(4, 16))
        ttk.Label(row3, text="Per-state cost").pack(side="left")
        self.perstate_var = tk.StringVar(value="20")
        ttk.Entry(row3, textvariable=self.perstate_var, width=8).pack(side="left", padx=(4, 16))
        ttk.Label(row3, text="Threat").pack(side="left")
        self.threat_var = tk.StringVar(value="1")
        ttk.Entry(row3, textvariable=self.threat_var, width=8).pack(side="left", padx=(4, 16))
        ttk.Label(row3, text="Expires (days, blank=never)").pack(side="left")
        self.expire_var = tk.StringVar()
        ttk.Entry(row3, textvariable=self.expire_var, width=8).pack(side="left", padx=4)

        ttk.Label(right, text="allowed (who can generate this war goal — ROOT is the goal's "
                              "owner, PREV the original target)").pack(anchor="w", pady=(8, 0))
        eff_row = ttk.Frame(right)
        eff_row.pack(fill="x")
        self.allowed_txt = tk.Text(eff_row, height=6, width=50)
        self.allowed_txt.pack(side="left", fill="both", expand=True)
        ttk.Button(eff_row, text="Wizard...", command=lambda: EffectWizard(self, self.allowed_txt, "trigger")).pack(
            side="left", padx=(6, 0), anchor="n")

        ttk.Button(right, text="Create War Goal", style="Accent.TButton",
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
            self._cache = wgc.list_wargoals(state.mod_root)
        return self._cache

    def _refresh_list(self):
        self.tree.delete(*self.tree.get_children())
        if not state.is_loaded:
            return
        needle = self.search_var.get().strip().lower()
        for goal_id, source in sorted(self._data().items()):
            if needle and needle not in goal_id.lower():
                continue
            self.tree.insert("", "end", values=(goal_id, source), tags=("mod",) if source == "mod" else ())

    def _check_id(self):
        gid = self.id_var.get().strip()
        if not gid:
            self.id_hint.config(text="", foreground=theme.MUTED)
            return
        existing = self._data()
        if gid in existing:
            self.id_hint.config(text=f"'{gid}' already exists ({existing[gid]})!", foreground=theme.RED)
        else:
            self.id_hint.config(text="free ✓", foreground=theme.GREEN)

    def _create(self):
        if not state.is_loaded:
            messagebox.showerror("No mod", "Open or create a mod first.")
            return
        gid = self.id_var.get().strip()
        if not gid:
            messagebox.showerror("Missing info", "A war goal id is required.")
            return
        if gid in self._data():
            messagebox.showerror("Id taken", f"'{gid}' already exists ({self._data()[gid]}).")
            return
        try:
            base = float(self.base_var.get())
            per_state = float(self.perstate_var.get())
            threat = float(self.threat_var.get())
            expire = int(self.expire_var.get()) if self.expire_var.get().strip() else None
        except ValueError:
            messagebox.showerror("Bad number", "Base cost, per-state cost, threat and expire must be numbers.")
            return

        try:
            path = wgc.create_wargoal(
                state.mod_root, wargoal_id=gid, goal_kind=self.kind_var.get(),
                war_name_key=self.warkey_var.get().strip(), allowed_raw=self.allowed_txt.get("1.0", "end"),
                base_cost=base, per_state_cost=per_state, threat=threat, expire_days=expire,
                war_name_text=self.wartext_var.get().strip(),
            )
        except Exception as exc:
            messagebox.showerror("Failed", f"War goal creation failed:\n{exc}")
            return

        self._data()[gid] = "mod"
        self._refresh_list()
        self.status.config(text=f"Created war goal '{gid}' in {path}.")
