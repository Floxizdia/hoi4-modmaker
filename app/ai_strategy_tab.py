"""AI Strategy tab: compose a new common/ai_strategy/<TAG>.txt block - who
this country's AI should ally/fight/build, gated by triggers, the same
shape the base game's own per-country strategy files use."""

import tkinter as tk
from tkinter import ttk, messagebox

from app.state import state
from app import ai_strategy_creator as ac
from app import theme, ui_kit
from app.oob_tab import _RowList


class AiStrategyTab(ttk.Frame):
    def __init__(self, master):
        super().__init__(master, padding=12)
        self._existing_ids = set()
        self._build()
        state.subscribe(self.on_mod_changed)

    def _build(self):
        self.header = ui_kit.PageHeader(
            self, "AI Strategy",
            "Tunes how the AI for a specific country tag behaves - who it wants to ally, invade, or build up against, and by how much.", help_key="ai_strategy")

        body = ttk.Frame(self)
        body.pack(fill="both", expand=True)

        # ---- left: existing files ----
        browse = ui_kit.Section(body, "Existing strategy files")
        browse.pack(side="left", fill="y", padx=(0, ui_kit.PAD_SECTION))
        browse.configure(width=260)
        browse.pack_propagate(False)
        self.file_tree = ttk.Treeview(browse.body, columns=("tag", "src"), show="headings", height=24)
        self.file_tree.heading("tag", text="country tag")
        self.file_tree.heading("src", text="from")
        self.file_tree.column("tag", width=140)
        self.file_tree.column("src", width=70)
        self.file_tree.pack(fill="both", expand=True, pady=(6, 0))
        self.file_tree.tag_configure("mod", foreground=theme.GREEN)

        # ---- right: create ----
        create = ui_kit.Section(body, "New strategy block")
        create.pack(side="left", fill="both", expand=True)
        right = create.body

        row = ttk.Frame(right)
        row.pack(fill="x", pady=(8, 0))
        ttk.Label(row, text="Country tag").pack(side="left")
        self.tag_var = tk.StringVar()
        ttk.Entry(row, textvariable=self.tag_var, width=6).pack(side="left", padx=(4, 16))
        self.tag_var.trace_add("write", lambda *_: self._check_id())
        ttk.Label(row, text="Block id (unique)").pack(side="left")
        self.id_var = tk.StringVar()
        ttk.Entry(row, textvariable=self.id_var, width=28).pack(side="left", padx=4)
        self.id_hint = ttk.Label(right, text="", style="Muted.TLabel")
        self.id_hint.pack(anchor="w")
        self.id_var.trace_add("write", lambda *_: self._check_id())

        trig = ttk.Frame(right)
        trig.pack(fill="x", pady=(8, 0))
        for col, (label, height) in enumerate((
            ("allowed (default: original_tag = TAG)", 3),
            ("enable (default: always = yes)", 3),
            ("abort (optional)", 3),
        )):
            c = ttk.Frame(trig)
            c.pack(side="left", fill="x", expand=True, padx=(0 if col == 0 else 8, 0))
            ttk.Label(c, text=label).pack(anchor="w")
            txt = tk.Text(c, height=height, width=22)
            txt.pack(fill="x")
            setattr(self, f"_trig_{col}", txt)
        self.allowed_txt, self.enable_txt, self.abort_txt = self._trig_0, self._trig_1, self._trig_2

        ttk.Label(right, text="Strategy entries", font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(10, 0))
        ttk.Label(
            right, text="'id' and 'value' meanings depend on the token - e.g. role_ratio's id is a "
                       "unit role (infantry, armor...), alliance's id is a country tag.",
            style="Muted.TLabel", wraplength=560, justify="left",
        ).pack(anchor="w")
        self.entry_rows = _RowList(right, [
            ("type", "combo", 26, ac.STRATEGY_TOKENS),
            ("id", "entry", 12, None),
            ("value", "entry", 8, None),
        ])
        self.entry_rows.pack(fill="x", pady=(4, 0))
        self.entry_rows.add_row({"type": "alliance", "id": "", "value": "100"})

        ttk.Button(right, text="Create Strategy Block", style="Accent.TButton",
                   command=self._create).pack(anchor="w", pady=12)
        self.status = ttk.Label(right, text="", style="Status.TLabel", wraplength=560, justify="left")
        self.status.pack(anchor="w")

        self.on_mod_changed()

    def on_mod_changed(self):
        if state.is_loaded:
            self.header.set_status(True, state.mod_name)
        else:
            self.header.set_status(False, "no mod open")
        self._refresh_files()
        self._existing_ids = set()

    def on_show(self):
        self.on_mod_changed()

    def _refresh_files(self):
        self.file_tree.delete(*self.file_tree.get_children())
        if not state.is_loaded:
            return
        for tag, source in sorted(ac.list_strategy_files(state.mod_root).items()):
            self.file_tree.insert("", "end", values=(tag, source), tags=("mod",) if source == "mod" else ())

    def _check_id(self):
        tag = self.tag_var.get().strip().upper()
        bid = self.id_var.get().strip()
        if not tag or not bid:
            self.id_hint.config(text="", foreground=theme.MUTED)
            return
        if not state.is_loaded:
            return
        ids = ac.list_block_ids(state.mod_root, tag)
        if bid in ids:
            self.id_hint.config(text=f"'{bid}' already exists in {tag}.txt!", foreground=theme.RED)
        else:
            self.id_hint.config(text="id is free ✓", foreground=theme.GREEN)

    def _create(self):
        if not state.is_loaded:
            messagebox.showerror("No mod", "Open or create a mod first.")
            return
        tag = self.tag_var.get().strip().upper()
        bid = self.id_var.get().strip()
        if not tag or not bid:
            messagebox.showerror("Missing info", "Country tag and block id are required.")
            return
        if bid in ac.list_block_ids(state.mod_root, tag):
            messagebox.showerror("Id taken", f"'{bid}' already exists in {tag}.txt.")
            return
        entries = []
        for r in self.entry_rows.values():
            if r["type"]:
                entries.append((r["type"], r["id"], r["value"]))
        if not entries:
            messagebox.showerror("No entries", "Add at least one strategy entry.")
            return

        try:
            path = ac.create_strategy(
                state.mod_root, tag=tag, block_id=bid,
                allowed_raw=self.allowed_txt.get("1.0", "end"),
                enable_raw=self.enable_txt.get("1.0", "end"),
                abort_raw=self.abort_txt.get("1.0", "end"),
                entries=entries,
            )
        except Exception as exc:
            messagebox.showerror("Failed", f"Strategy creation failed:\n{exc}")
            return

        self._refresh_files()
        self.status.config(text=f"Added '{bid}' with {len(entries)} strategy entries to {path}.")
