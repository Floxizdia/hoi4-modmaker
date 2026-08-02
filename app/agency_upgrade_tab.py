"""Agency Upgrades tab: add a new intelligence agency upgrade (the spy
agency's own tech tree, grouped into branches) - common/intelligence_agency_upgrades/.

See agency_upgrade_creator.py's docstring for why this replaces a literal
"operative type" creator: raw La Resistance operative-archetype files
aren't present in this install to verify a schema against, so this targets
the closest area that's fully real and checkable here."""

import tkinter as tk
from tkinter import ttk, messagebox

from app.state import state
from app import agency_upgrade_creator as auc
from app.effect_wizard import EffectWizard
from app import theme, ui_kit


class AgencyUpgradeTab(ttk.Frame):
    def __init__(self, master):
        super().__init__(master, padding=12)
        self._levels = []
        self._build()
        state.subscribe(self.on_mod_changed)

    def _build(self):
        self.header = ui_kit.PageHeader(
            self, "Agency Upgrades",
            "Adds an entry to a country's intelligence agency upgrade tree (branch_intelligence/defense/operation/operative/crypto), each with its own AI weight and a modifier per level.", help_key="agency_upgrade")
        ttk.Label(
            self, text="Raw La Resistance operative-type files aren't present in this HOI4 install to "
                       "verify syntax against, so this creates entries in the agency upgrade tree instead — "
                       "same spy/intel gameplay area, fully real and checked.",
            style="Muted.TLabel", wraplength=980, justify="left",
        ).pack(anchor="w", pady=(0, 8))

        body = ttk.Frame(self)
        body.pack(fill="both", expand=True)

        browse = ui_kit.Section(body, "Existing upgrades")
        browse.pack(side="left", fill="y", padx=(0, ui_kit.PAD_SECTION))
        browse.configure(width=300)
        browse.pack_propagate(False)
        self.search_var = tk.StringVar()
        ttk.Entry(browse.body, textvariable=self.search_var).pack(fill="x", pady=(4, 0))
        self.search_var.trace_add("write", lambda *_: self._refresh_list())
        self.tree = ttk.Treeview(browse.body, columns=("id", "branch", "lvls", "src"), show="headings", height=24)
        for col, w in (("id", 150), ("branch", 110), ("lvls", 40), ("src", 45)):
            self.tree.heading(col, text=col)
            self.tree.column(col, width=w)
        self.tree.pack(fill="both", expand=True, pady=(6, 0))
        self.tree.tag_configure("mod", foreground=theme.GREEN)

        create = ui_kit.Section(body, "Create a new upgrade")
        create.pack(side="left", fill="both", expand=True)
        right = create.body

        row = ttk.Frame(right)
        row.pack(fill="x", pady=(8, 0))
        ttk.Label(row, text="Upgrade id").pack(side="left")
        self.id_var = tk.StringVar()
        ttk.Entry(row, textvariable=self.id_var, width=26).pack(side="left", padx=(4, 16))
        ttk.Label(row, text="Branch").pack(side="left")
        self.branch_var = tk.StringVar(value="branch_operative")
        ttk.Combobox(row, textvariable=self.branch_var, state="readonly", width=18,
                     values=auc.BRANCHES).pack(side="left", padx=4)
        self.id_hint = ttk.Label(right, text="", style="Muted.TLabel")
        self.id_hint.pack(anchor="w")
        self.id_var.trace_add("write", lambda *_: self._check_id())

        row2 = ttk.Frame(right)
        row2.pack(fill="x", pady=(8, 0))
        ttk.Label(row2, text="Picture (GFX_...)").pack(side="left")
        self.picture_var = tk.StringVar(value="GFX_agency_army_department")
        ttk.Entry(row2, textvariable=self.picture_var, width=30).pack(side="left", padx=(4, 16))
        ttk.Label(row2, text="AI factor").pack(side="left")
        self.ai_var = tk.StringVar(value="1")
        ttk.Entry(row2, textvariable=self.ai_var, width=6).pack(side="left", padx=4)

        ttk.Label(right, text="modifiers_during_progress (optional)").pack(anchor="w", pady=(8, 0))
        self.progress_txt = tk.Text(right, height=3, width=60)
        self.progress_txt.insert("1.0", "civilian_factory_use = 5")
        self.progress_txt.pack(anchor="w")

        ttk.Label(right, text="Levels — one modifier block per completed level",
                  font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(10, 2))
        self.levels_frame = ttk.Frame(right)
        self.levels_frame.pack(fill="x")
        btn_row = ttk.Frame(right)
        btn_row.pack(fill="x", pady=(2, 0))
        ttk.Button(btn_row, text="+ Add level", command=self._add_level).pack(side="left")
        self._add_level()

        ttk.Button(right, text="Create Upgrade", style="Accent.TButton",
                   command=self._create).pack(anchor="w", pady=12)
        self.status = ttk.Label(right, text="", style="Status.TLabel", wraplength=640, justify="left")
        self.status.pack(anchor="w")

        self.on_mod_changed()

    def _add_level(self):
        row = ttk.Frame(self.levels_frame)
        row.pack(fill="x", pady=2)
        n = len(self._levels) + 1
        ttk.Label(row, text=f"Level {n}").pack(side="left")
        txt = tk.Text(row, height=2, width=45)
        txt.pack(side="left", padx=6)
        ttk.Button(row, text="Wizard...", command=lambda t=txt: EffectWizard(self, t, "effect")).pack(side="left")
        remove_btn = ttk.Button(row, text="Remove")
        remove_btn.pack(side="left", padx=4)
        entry = {"row": row, "text": txt}
        remove_btn.config(command=lambda e=entry: self._remove_level(e))
        self._levels.append(entry)

    def _remove_level(self, entry):
        if len(self._levels) <= 1:
            return
        entry["row"].destroy()
        self._levels.remove(entry)

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
            self._cache = auc.list_upgrades(state.mod_root)
        return self._cache

    def _refresh_list(self):
        self.tree.delete(*self.tree.get_children())
        if not state.is_loaded:
            return
        needle = self.search_var.get().strip().lower()
        for up_id, (source, branch, levels) in sorted(self._data().items()):
            if needle and needle not in up_id.lower():
                continue
            self.tree.insert("", "end", values=(up_id, branch, levels, source),
                              tags=("mod",) if source == "mod" else ())

    def _check_id(self):
        uid = self.id_var.get().strip()
        if not uid:
            self.id_hint.config(text="", foreground=theme.MUTED)
            return
        existing = self._data()
        if uid in existing:
            self.id_hint.config(text=f"'{uid}' already exists ({existing[uid][0]})!", foreground=theme.RED)
        else:
            self.id_hint.config(text="free ✓", foreground=theme.GREEN)

    def _create(self):
        if not state.is_loaded:
            messagebox.showerror("No mod", "Open or create a mod first.")
            return
        uid = self.id_var.get().strip()
        if not uid:
            messagebox.showerror("Missing info", "An upgrade id is required.")
            return
        if uid in self._data():
            messagebox.showerror("Id taken", f"'{uid}' already exists ({self._data()[uid][0]}).")
            return
        try:
            ai_factor = float(self.ai_var.get())
        except ValueError:
            messagebox.showerror("Bad number", "AI factor must be a number.")
            return

        level_mods = [e["text"].get("1.0", "end").strip() for e in self._levels]
        level_mods = [m for m in level_mods if m]
        if not level_mods:
            messagebox.showerror("No levels", "At least one level's modifier block is required.")
            return

        try:
            path = auc.create_upgrade(
                state.mod_root, upgrade_id=uid, branch=self.branch_var.get(),
                picture=self.picture_var.get().strip(), ai_factor=ai_factor,
                progress_modifier_raw=self.progress_txt.get("1.0", "end"), level_modifiers=level_mods,
            )
        except Exception as exc:
            messagebox.showerror("Failed", f"Upgrade creation failed:\n{exc}")
            return

        self._data()[uid] = ("mod", self.branch_var.get(), len(level_mods))
        self._refresh_list()
        self.status.config(text=f"Created upgrade '{uid}' with {len(level_mods)} level(s) in {path}.")
