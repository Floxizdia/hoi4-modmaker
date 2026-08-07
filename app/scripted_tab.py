"""Scripted tab: define scripted effects, scripted triggers and dynamic
modifiers - common/scripted_effects, common/scripted_triggers and
common/dynamic_modifiers.

Every other screen can already reference these by name; this is where they
get written. The list on the left exists mainly to answer "does this name
already exist?", because unlike on_actions these are last-one-loaded-wins:
reusing a base-game name replaces it instead of adding to it.
"""

import tkinter as tk
from tkinter import messagebox, ttk

from app.state import state
from app import scripted
from app import theme, ui_kit


class ScriptedTab(ttk.Frame):
    def __init__(self, master):
        super().__init__(master, padding=12)
        self._defined = {}
        self._build()
        state.subscribe(self.on_mod_changed)

    # ---- layout ----

    def _build(self):
        self.header = ui_kit.PageHeader(
            self, "Scripted Effects & Triggers",
            "Reusable named blocks you write once and call by name from focuses, events and "
            "decisions - plus dynamic modifiers, the country/state modifiers a script can hand "
            "out and take back.", help_key="scripted")

        top = ttk.Frame(self)
        top.pack(fill="x", pady=(0, 6))
        ttk.Label(top, text="Kind:").pack(side="left")
        self.kind = tk.StringVar(value="effect")
        for value in ("effect", "trigger", "modifier"):
            ttk.Radiobutton(top, text=scripted.KIND_LABELS[value], value=value,
                            variable=self.kind, command=self._kind_changed).pack(side="left", padx=4)
        ttk.Button(top, text="Refresh list", command=self._refresh).pack(side="left", padx=12)
        self.count_label = ttk.Label(top, text="", style="Muted.TLabel")
        self.count_label.pack(side="left", padx=8)

        body = ttk.Frame(self)
        body.pack(fill="both", expand=True)

        browse = ui_kit.Section(body, "Already defined")
        browse.pack(side="left", fill="y", padx=(0, ui_kit.PAD_SECTION))
        browse.configure(width=330)
        browse.pack_propagate(False)
        ttk.Label(browse.body,
                  text="These are not additive: defining a name that already exists replaces the "
                       "other one entirely. Rows marked 'vanilla' belong to the base game.",
                  style="Muted.TLabel", wraplength=300, justify="left").pack(anchor="w", pady=(2, 4))

        filter_row = ttk.Frame(browse.body)
        filter_row.pack(fill="x", pady=(0, 4))
        ttk.Label(filter_row, text="Find:").pack(side="left")
        self.filter_var = tk.StringVar()
        entry = ttk.Entry(filter_row, textvariable=self.filter_var)
        entry.pack(side="left", fill="x", expand=True, padx=4)
        entry.bind("<KeyRelease>", lambda e: self._refresh_tree())

        self.tree = ttk.Treeview(browse.body, columns=("name", "source"),
                                 show="headings", height=22)
        self.tree.heading("name", text="name")
        self.tree.heading("source", text="from")
        self.tree.column("name", width=220)
        self.tree.column("source", width=80)
        self.tree.pack(fill="both", expand=True)
        self.tree.tag_configure("mod", foreground=theme.GREEN)
        self.tree.bind("<<TreeviewSelect>>", lambda e: self._pick_name())

        create = ui_kit.Section(body, "Define a new one")
        create.pack(side="left", fill="both", expand=True)
        right = create.body

        name_row = ttk.Frame(right)
        name_row.pack(fill="x", pady=(8, 0))
        ttk.Label(name_row, text="name").pack(side="left")
        self.name_var = tk.StringVar()
        name_entry = ttk.Entry(name_row, textvariable=self.name_var, width=36)
        name_entry.pack(side="left", padx=6)
        name_entry.bind("<KeyRelease>", lambda e: self._check_name())
        self.name_note = ttk.Label(name_row, text="", style="Muted.TLabel")
        self.name_note.pack(side="left", padx=6)

        # dynamic modifiers carry fields of their own that the other two
        # kinds have no use for, so the whole group is hidden for them
        self.modifier_box = ttk.Frame(right)
        icon_row = ttk.Frame(self.modifier_box)
        icon_row.pack(fill="x", pady=(8, 0))
        ttk.Label(icon_row, text="icon (optional)").pack(side="left")
        self.icon_var = tk.StringVar(value="GFX_idea_unknown")
        ttk.Entry(icon_row, textvariable=self.icon_var, width=28).pack(side="left", padx=6)
        ttk.Label(self.modifier_box, text="enable = { ... }   when the modifier applies",
                  style="Muted.TLabel").pack(anchor="w", pady=(6, 0))
        self.enable_text = tk.Text(self.modifier_box, height=4, wrap="none")
        self.enable_text.pack(fill="x")
        ttk.Label(self.modifier_box, text="remove_trigger = { ... }   when it goes away",
                  style="Muted.TLabel").pack(anchor="w", pady=(6, 0))
        self.remove_text = tk.Text(self.modifier_box, height=3, wrap="none")
        self.remove_text.pack(fill="x")

        self.body_label = ttk.Label(right, text="", style="Muted.TLabel", justify="left")
        self.body_label.pack(anchor="w", pady=(8, 0))
        self.body_text = tk.Text(right, height=14, wrap="none")
        self.body_text.pack(fill="both", expand=True)

        buttons = ttk.Frame(right)
        buttons.pack(fill="x", pady=(8, 0))
        ttk.Button(buttons, text="Add to mod", style="Accent.TButton",
                   command=self._create).pack(side="left")
        ttk.Button(buttons, text="Insert example", command=self._example).pack(side="left", padx=6)
        self.status = ttk.Label(right, text="", style="Status.TLabel",
                                wraplength=620, justify="left")
        self.status.pack(fill="x", pady=(6, 0))

        self._kind_changed()
        self.on_mod_changed()

    # ---- lifecycle ----

    def on_mod_changed(self):
        if state.is_loaded:
            self.header.set_status(True, state.mod_name)
        else:
            self.header.set_status(False, "no mod open")
        self._defined = {}
        if hasattr(self, "tree"):
            self.tree.delete(*self.tree.get_children())
            self.count_label.config(text="")

    def on_show(self):
        self.on_mod_changed()
        self._refresh()

    # ---- browsing ----

    def _refresh(self):
        if not state.is_loaded:
            self.count_label.config(text="open a mod to list these")
            return
        self._defined = scripted.list_defined(state.mod_root, self.kind.get())
        mine = sum(1 for sources in self._defined.values()
                   if any(s == "mod" for s, _f in sources))
        self.count_label.config(text=f"{len(self._defined)} defined · {mine} in this mod")
        self._refresh_tree()

    def _refresh_tree(self):
        self.tree.delete(*self.tree.get_children())
        needle = self.filter_var.get().strip().lower()
        for name in sorted(self._defined):
            if needle and needle not in name.lower():
                continue
            sources = self._defined[name]
            in_mod = any(s == "mod" for s, _f in sources)
            label = "mod" if in_mod else "vanilla"
            if in_mod and any(s == "vanilla" for s, _f in sources):
                label = "mod (overrides)"
            self.tree.insert("", "end", values=(name, label),
                             tags=("mod",) if in_mod else ())

    def _pick_name(self):
        selection = self.tree.selection()
        if not selection:
            return
        name = self.tree.item(selection[0], "values")[0]
        self.name_var.set(name)
        self._check_name()

    # ---- creating ----

    def _kind_changed(self):
        kind = self.kind.get()
        if kind == "modifier":
            self.modifier_box.pack(fill="x", before=self.body_label)
            self.body_label.config(
                text="modifiers, one per line — e.g.  political_power_gain = 0.2")
        else:
            self.modifier_box.pack_forget()
            self.body_label.config(
                text=("the effects this runs, e.g.  add_political_power = 50"
                      if kind == "effect"
                      else "the conditions this checks, e.g.  has_war = yes"))
        self._refresh()
        self._check_name()

    def _check_name(self):
        name = self.name_var.get().strip()
        if not name:
            self.name_note.config(text="")
            return
        if scripted.overrides_vanilla(self._defined, name):
            self.name_note.config(text="replaces a base-game definition", foreground=theme.RED)
        elif name in self._defined:
            self.name_note.config(text="already defined in this mod", foreground=theme.MUTED)
        else:
            self.name_note.config(text="free", foreground=theme.GREEN)

    EXAMPLES = {
        "effect": "add_political_power = 50\nadd_stability = 0.05",
        "trigger": "has_war = yes\nhas_stability < 0.4",
        "modifier": "political_power_gain = 0.2\nstability_factor = -0.05",
    }

    def _example(self):
        self.body_text.delete("1.0", "end")
        self.body_text.insert("1.0", self.EXAMPLES[self.kind.get()])
        if self.kind.get() == "modifier" and not self.enable_text.get("1.0", "end").strip():
            self.enable_text.insert("1.0", "always = yes")

    def _create(self):
        if not state.is_loaded:
            messagebox.showerror("No mod", "Open a mod first.")
            return
        name = self.name_var.get().strip()
        if not name or " " in name:
            self.status.config(text="Give it a name with no spaces — that name is how you call it "
                                    "from a focus, event or decision.")
            return
        body = self.body_text.get("1.0", "end").strip()
        kind = self.kind.get()
        enable = self.enable_text.get("1.0", "end") if kind == "modifier" else ""
        if not body and not enable.strip():
            self.status.config(text="Nothing to write — fill in the box below first.")
            return

        if scripted.overrides_vanilla(self._defined, name):
            if not messagebox.askyesno(
                    "Replace a base-game definition?",
                    f"'{name}' already exists in the base game.\n\nThese files are not additive: "
                    "yours would replace vanilla's everywhere it's used, including in the base "
                    "game's own focuses and events.\n\nUse this name anyway?"):
                return

        try:
            path = scripted.create(
                state.mod_root, kind, name, body,
                icon=self.icon_var.get().strip() if kind == "modifier" else "",
                enable=enable,
                remove_trigger=(self.remove_text.get("1.0", "end")
                                if kind == "modifier" else ""),
                parent=self)
        except OSError as exc:
            messagebox.showerror("Write failed", str(exc))
            return
        if path is None:
            self.status.config(text="Left the existing file alone.")
            return

        from app import mod_export
        mod_export.record_created(state.mod_root, [path])
        state.content_changed()
        self._refresh()
        self.status.config(
            text=f"{scripted.KIND_LABELS[kind]} '{name}' written to {path}. "
                 f"Call it by name: {name} = yes" if kind != "modifier" else
                 f"Dynamic modifier '{name}' written to {path}. Hand it out with "
                 f"add_dynamic_modifier = {{ modifier = {name} }}")
