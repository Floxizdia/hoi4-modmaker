"""Diplomatic Actions tab: define a custom diplomacy-menu action beyond the
game's built-ins (guarantee, alliance, ...) - written to
common/scripted_diplomatic_actions/."""

import tkinter as tk
from tkinter import ttk, messagebox

from app.state import state
from app import diplo_action_creator as dc
from app.effect_wizard import EffectWizard
from app import theme, ui_kit


class DiploActionTab(ttk.Frame):
    def __init__(self, master):
        super().__init__(master, padding=12)
        self._build()
        state.subscribe(self.on_mod_changed)

    def _build(self):
        self.header = ui_kit.PageHeader(
            self, "Diplomatic Actions",
            "Define a new diplomatic action button (like a custom 'Request Alliance') - its cost, requirements, and what accepting/declining does.", help_key="diplo_action")

        row = ttk.Frame(self)
        row.pack(fill="x")
        ttk.Label(row, text="Action id (lowercase, unique)").pack(side="left")
        self.id_var = tk.StringVar()
        ttk.Entry(row, textvariable=self.id_var, width=24).pack(side="left", padx=(4, 16))
        ttk.Label(row, text="Action name").pack(side="left")
        self.name_var = tk.StringVar()
        ttk.Entry(row, textvariable=self.name_var, width=28).pack(side="left", padx=4)
        self.id_hint = ttk.Label(self, text="", style="Muted.TLabel")
        self.id_hint.pack(anchor="w")
        self.id_var.trace_add("write", lambda *_: self._check_id())

        row2 = ttk.Frame(self)
        row2.pack(fill="x", pady=(8, 0))
        ttk.Label(row2, text="PP cost").pack(side="left")
        self.cost_var = tk.StringVar(value="10")
        ttk.Entry(row2, textvariable=self.cost_var, width=6).pack(side="left", padx=(4, 16))
        ttk.Label(row2, text="Command power cost").pack(side="left")
        self.cp_var = tk.StringVar(value="0")
        ttk.Entry(row2, textvariable=self.cp_var, width=6).pack(side="left", padx=(4, 16))
        ttk.Label(row2, text="Icon frame #").pack(side="left")
        self.icon_var = tk.StringVar(value="1")
        ttk.Entry(row2, textvariable=self.icon_var, width=5).pack(side="left", padx=4)
        self.requires_acceptance_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(row2, text="Target must accept", variable=self.requires_acceptance_var).pack(
            side="left", padx=(16, 0))

        trig_row = ttk.Frame(self)
        trig_row.pack(fill="x", pady=(10, 0))
        self.allowed_txt = self._trigger_col(trig_row, "allowed (who can use this)", "always = yes")
        self.visible_txt = self._trigger_col(trig_row, "visible", "always = yes")
        self.selectable_txt = self._trigger_col(trig_row, "selectable", "always = yes")

        eff_row = ttk.Frame(self)
        eff_row.pack(fill="x", pady=(10, 0))
        self.sent_txt = self._effect_col(eff_row, "on_sent_effect")
        self.complete_txt = self._effect_col(eff_row, "complete_effect (target accepted)")
        self.reject_txt = self._effect_col(eff_row, "reject_effect (target refused)")

        loc_row = ttk.Frame(self)
        loc_row.pack(fill="x", pady=(10, 0))
        for label, attr, default in (
            ("Send confirmation text", "send_desc_var", ""),
            ("Accepted feedback text", "accept_desc_var", ""),
            ("Rejected feedback text", "reject_desc_var", ""),
        ):
            c = ttk.Frame(loc_row)
            c.pack(side="left", fill="x", expand=True, padx=(0, 8))
            ttk.Label(c, text=label).pack(anchor="w")
            var = tk.StringVar(value=default)
            ttk.Entry(c, textvariable=var).pack(fill="x")
            setattr(self, attr, var)

        ai_row = ttk.Frame(self)
        ai_row.pack(fill="x", pady=(10, 0))
        c1 = ttk.Frame(ai_row)
        c1.pack(side="left", fill="x", expand=True, padx=(0, 8))
        ttk.Label(c1, text="ai_acceptance (how likely AI accepts)").pack(anchor="w")
        self.ai_accept_txt = tk.Text(c1, height=3, width=32)
        self.ai_accept_txt.insert("1.0", "base = 100")
        self.ai_accept_txt.pack(fill="x")
        c2 = ttk.Frame(ai_row)
        c2.pack(side="left", fill="x", expand=True)
        ttk.Label(c2, text="ai_desire (how likely AI sends this)").pack(anchor="w")
        self.ai_desire_txt = tk.Text(c2, height=3, width=32)
        self.ai_desire_txt.insert("1.0", "base = 0")
        self.ai_desire_txt.pack(fill="x")

        ttk.Button(self, text="Create Diplomatic Action", style="Accent.TButton",
                   command=self._create).pack(anchor="w", pady=12)
        self.status = ttk.Label(self, text="", style="Status.TLabel", wraplength=900, justify="left")
        self.status.pack(anchor="w")

        self.on_mod_changed()

    def _trigger_col(self, parent, label, default):
        c = ttk.Frame(parent)
        c.pack(side="left", fill="x", expand=True, padx=(0, 8))
        ttk.Label(c, text=label).pack(anchor="w")
        row = ttk.Frame(c)
        row.pack(fill="x")
        txt = tk.Text(row, height=4, width=26)
        txt.insert("1.0", default)
        txt.pack(side="left", fill="x", expand=True)
        ttk.Button(row, text="Wizard...", command=lambda: EffectWizard(self, txt, "trigger")).pack(side="left")
        return txt

    def _effect_col(self, parent, label):
        c = ttk.Frame(parent)
        c.pack(side="left", fill="x", expand=True, padx=(0, 8))
        ttk.Label(c, text=label).pack(anchor="w")
        row = ttk.Frame(c)
        row.pack(fill="x")
        txt = tk.Text(row, height=4, width=26)
        txt.pack(side="left", fill="x", expand=True)
        ttk.Button(row, text="Wizard...", command=lambda: EffectWizard(self, txt, "effect")).pack(side="left")
        return txt

    def on_mod_changed(self):
        if state.is_loaded:
            self.header.set_status(True, state.mod_name)
        else:
            self.header.set_status(False, "no mod open")

    def on_show(self):
        self.on_mod_changed()

    def _check_id(self):
        aid = self.id_var.get().strip().lower()
        if not aid or not aid.replace("_", "").isalnum():
            self.id_hint.config(text="lowercase letters/digits/underscore", foreground=theme.MUTED)
        else:
            self.id_hint.config(text="looks good — id uniqueness isn't checked across the whole "
                                     "mod's script, keep it namespaced (e.g. gkl_...)", foreground=theme.MUTED)

    def _create(self):
        if not state.is_loaded:
            messagebox.showerror("No mod", "Open or create a mod first.")
            return
        aid = self.id_var.get().strip().lower()
        name = self.name_var.get().strip()
        if not aid or not aid.replace("_", "").isalnum() or not name:
            messagebox.showerror("Missing info", "A valid action id and a name are required.")
            return
        try:
            cost = int(self.cost_var.get() or 0)
            cp = int(self.cp_var.get() or 0)
            icon = int(self.icon_var.get() or 1)
        except ValueError:
            messagebox.showerror("Bad number", "Cost, command power and icon frame must be numbers.")
            return

        try:
            created = dc.create_action(
                state.mod_root, action_id=aid, display_name=name,
                cost=cost, command_power=cp, requires_acceptance=self.requires_acceptance_var.get(),
                icon=icon,
                allowed_raw=self.allowed_txt.get("1.0", "end"),
                visible_raw=self.visible_txt.get("1.0", "end"),
                selectable_raw=self.selectable_txt.get("1.0", "end"),
                on_sent_effect_raw=self.sent_txt.get("1.0", "end"),
                complete_effect_raw=self.complete_txt.get("1.0", "end"),
                reject_effect_raw=self.reject_txt.get("1.0", "end"),
                send_description=self.send_desc_var.get().strip(),
                accept_feedback=self.accept_desc_var.get().strip(),
                reject_feedback=self.reject_desc_var.get().strip(),
                ai_acceptance_raw=self.ai_accept_txt.get("1.0", "end"),
                ai_desire_raw=self.ai_desire_txt.get("1.0", "end"),
            )
        except Exception as exc:
            messagebox.showerror("Failed", f"Diplomatic action creation failed:\n{exc}")
            return

        state.add_loc(aid, name)
        self.status.config(text=f"Created diplomatic action '{name}' ({aid}) — {len(created)} files written.")
