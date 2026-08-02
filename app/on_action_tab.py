"""On Actions tab: hook an effect onto a game event (war declared, country
capitulates, peace conference starts...) - common/on_actions/."""

import tkinter as tk
from tkinter import ttk, messagebox

from app.state import state
from app import on_action_creator as oac
from app.effect_wizard import EffectWizard
from app import theme, ui_kit


class OnActionTab(ttk.Frame):
    def __init__(self, master):
        super().__init__(master, padding=12)
        self._build()
        state.subscribe(self.on_mod_changed)

    def _build(self):
        self.header = ui_kit.PageHeader(
            self, "On Actions",
            "Hooks an effect onto a real game event - war declared, a country capitulates, a peace conference starts - one of 74 known trigger points.", help_key="on_action")

        body = ttk.Frame(self)
        body.pack(fill="both", expand=True)

        browse = ui_kit.Section(body, "Hooks already in use")
        browse.pack(side="left", fill="y", padx=(0, ui_kit.PAD_SECTION))
        browse.configure(width=320)
        browse.pack_propagate(False)
        ttk.Label(
            browse.body, text="Informational only — on_actions are additive, so adding your own effect to a "
                       "hook another mod already uses never overwrites theirs.",
            style="Muted.TLabel", wraplength=280, justify="left",
        ).pack(anchor="w", pady=(2, 4))
        self.used_tree = ttk.Treeview(browse.body, columns=("key", "count"), show="headings", height=22)
        self.used_tree.heading("key", text="on_action")
        self.used_tree.heading("count", text="# hooked")
        self.used_tree.column("key", width=210)
        self.used_tree.column("count", width=60)
        self.used_tree.pack(fill="both", expand=True)

        create = ui_kit.Section(body, "Hook a new effect")
        create.pack(side="left", fill="both", expand=True)
        right = create.body

        row = ttk.Frame(right)
        row.pack(fill="x", pady=(8, 0))
        ttk.Label(row, text="on_action").pack(side="left")
        self.key_var = tk.StringVar(value="on_declare_war")
        ttk.Combobox(row, textvariable=self.key_var, values=oac.ON_ACTION_TOKENS, width=36).pack(
            side="left", padx=6)

        chance_row = ttk.Frame(right)
        chance_row.pack(fill="x", pady=(8, 0))
        self.use_chance_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(chance_row, text="Only fire some of the time (%)",
                        variable=self.use_chance_var).pack(side="left")
        self.chance_var = tk.StringVar(value="50")
        ttk.Entry(chance_row, textvariable=self.chance_var, width=6).pack(side="left", padx=6)

        ttk.Label(right, text="Effect (ROOT is whatever the hook's own scope is - see the wiki for that "
                              "hook's exact scope/FROM meaning)").pack(anchor="w", pady=(8, 0))
        eff_row = ttk.Frame(right)
        eff_row.pack(fill="x")
        self.effect_txt = tk.Text(eff_row, height=8, width=50)
        self.effect_txt.pack(side="left", fill="both", expand=True)
        ttk.Button(eff_row, text="Wizard...", command=lambda: EffectWizard(self, self.effect_txt, "effect")).pack(
            side="left", padx=(6, 0), anchor="n")

        ttk.Button(right, text="Create Hook", style="Accent.TButton",
                   command=self._create).pack(anchor="w", pady=12)
        self.status = ttk.Label(right, text="", style="Status.TLabel", wraplength=560, justify="left")
        self.status.pack(anchor="w")

        self.on_mod_changed()

    def on_mod_changed(self):
        if state.is_loaded:
            self.header.set_status(True, state.mod_name)
        else:
            self.header.set_status(False, "no mod open")
        self._refresh_used()

    def on_show(self):
        self.on_mod_changed()

    def _refresh_used(self):
        self.used_tree.delete(*self.used_tree.get_children())
        if not state.is_loaded:
            return
        for key, sources in sorted(oac.list_hooks_used(state.mod_root).items()):
            self.used_tree.insert("", "end", values=(key, len(sources)))

    def _create(self):
        if not state.is_loaded:
            messagebox.showerror("No mod", "Open or create a mod first.")
            return
        key = self.key_var.get().strip()
        effect = self.effect_txt.get("1.0", "end").strip()
        if not key or not effect:
            messagebox.showerror("Missing info", "An on_action key and an effect are required.")
            return
        chance = None
        if self.use_chance_var.get():
            try:
                chance = int(self.chance_var.get())
                if not (0 <= chance <= 100):
                    raise ValueError
            except ValueError:
                messagebox.showerror("Bad number", "Chance must be a whole number 0-100.")
                return

        try:
            path = oac.create_hook(state.mod_root, on_action_key=key, effect_raw=effect, random_chance=chance)
        except Exception as exc:
            messagebox.showerror("Failed", f"Hook creation failed:\n{exc}")
            return

        self._refresh_used()
        self.status.config(text=f"Hooked an effect onto '{key}' in {path}.")
