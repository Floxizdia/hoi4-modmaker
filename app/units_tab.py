"""Units tab: browse and edit division sub-units (common/units) and their
equipment (common/units/equipment) - the two files that decide what a
template screen or a production line actually offers.

Same reasoning as the Tech tab: these blocks are dense with engine-specific
keys (game rules, sprite hooks, ai desire modifiers), so instead of a form
that would inevitably fall short, this is a searchable list over the raw
block of one sub-unit or one equipment at a time, byte-preserving the rest
of the file exactly like `tech_tab.py` and `focus_surgery.py` already do.
"""

import glob
import os
import re
import shutil
import tkinter as tk
from tkinter import ttk, messagebox

from app.state import state
from app import pds_scan as scan
from app import theme, ui_kit

NEW_SUB_UNIT_TEMPLATE = """my_new_battalion = {
	need = {
		infantry_equipment = 1
	}
	priority = 5
	group = infantry

	active = yes

	man_hours = 5000

	max_organization = 30
	max_speed = 4
	defense = 5
	soft_attack = 5
	hard_attack = 1
}"""

NEW_EQUIPMENT_TEMPLATE = """my_new_equipment = {
	year = 1936
	is_archetype = yes
	group_by = infantry_weapons

	priority = 5

	build_cost_ic = 1
	manpower = 1

	visual_level = 0

	picture = infantry_group

	soft_attack = 2
	hard_attack = 0
}"""


def _find_files(folder):
    if not os.path.isdir(folder):
        return []
    return sorted(glob.glob(os.path.join(folder, "*.txt")))


def find_unit_files(mod_root):
    return _find_files(os.path.join(mod_root, "common", "units"))


def find_equipment_files(mod_root):
    return _find_files(os.path.join(mod_root, "common", "units", "equipment"))


def parse_named_blocks(path, outer_key):
    """Same shape as tech_tab.parse_techs: (text, [(id, start, end)]) with
    spans over the ORIGINAL text so they can be cut and replaced untouched."""
    with open(path, "r", encoding="utf-8-sig", errors="ignore") as f:
        text = f.read()

    m = re.search(r"\b" + outer_key + r"\s*=\s*\{", text)
    if not m:
        return text, []
    outer_open = m.end() - 1
    outer_close = scan.find_matching_brace(text, outer_open)
    if outer_close == -1:
        return text, []

    items = []
    i = outer_open + 1
    pattern = re.compile(r"([A-Za-z_][\w]*)\s*=\s*\{")
    while i < outer_close:
        found = pattern.search(text, i, outer_close)
        if not found:
            break
        open_idx = found.end() - 1
        close_idx = scan.find_matching_brace(text, open_idx)
        if close_idx == -1 or close_idx > outer_close:
            break
        items.append((found.group(1), found.start(), close_idx + 1))
        i = close_idx + 1
    return text, items


class _BlockEditor(ttk.Frame):
    """One half of the tab: a file picker, a searchable list, and a raw-block
    editor. `outer_key` is 'sub_unit' or 'equipment'."""

    def __init__(self, master, outer_key, find_files, template, kind_label):
        super().__init__(master, padding=6)
        self.outer_key = outer_key
        self.find_files = find_files
        self.template = template
        self.kind_label = kind_label
        self._files = []
        self._text = ""
        self._items = []
        self._current = None
        self._path = None
        self._backed_up = set()
        self._build()

    def _build(self):
        top = ttk.Frame(self)
        top.pack(fill="x")
        ttk.Label(top, text="File:").pack(side="left")
        self.file_combo = ttk.Combobox(top, state="readonly", width=32)
        self.file_combo.pack(side="left", padx=6)
        ttk.Button(top, text="Load", command=self._load_file).pack(side="left")
        ttk.Label(top, text="  Search:").pack(side="left")
        self.search_var = tk.StringVar()
        entry = ttk.Entry(top, textvariable=self.search_var, width=20)
        self.search_entry = entry
        entry.pack(side="left", padx=4)
        entry.bind("<KeyRelease>", lambda e: self._refresh_list())
        self.count_label = ttk.Label(top, text="", style="Muted.TLabel")
        self.count_label.pack(side="left", padx=6)

        body = ttk.Frame(self)
        body.pack(fill="both", expand=True, pady=6)
        left = ttk.Frame(body, width=220)
        left.pack(side="left", fill="y", padx=(0, 6))
        left.pack_propagate(False)
        self.listbox = tk.Listbox(left, exportselection=False)
        bar = ttk.Scrollbar(left, orient="vertical", command=self.listbox.yview)
        self.listbox.configure(yscrollcommand=bar.set)
        self.listbox.pack(side="left", fill="both", expand=True)
        bar.pack(side="right", fill="y")
        self.listbox.bind("<<ListboxSelect>>", lambda e: self._pick())

        right = ttk.Frame(body)
        right.pack(side="left", fill="both", expand=True)
        self.editor = tk.Text(right, wrap="none", undo=True, font=("Consolas", 10))
        ebar = ttk.Scrollbar(right, orient="vertical", command=self.editor.yview)
        self.editor.configure(yscrollcommand=ebar.set)
        self.editor.pack(side="left", fill="both", expand=True)
        ebar.pack(side="right", fill="y")

        btns = ttk.Frame(self)
        btns.pack(fill="x")
        ttk.Button(btns, text=f"Save This {self.kind_label}", style="Accent.TButton",
                   command=self._save).pack(side="left")
        ttk.Button(btns, text=f"Add New {self.kind_label}", command=self._add).pack(side="left", padx=6)
        self.status = ttk.Label(btns, text="", style="Status.TLabel", wraplength=600, justify="left")
        self.status.pack(side="left", padx=10)

    # ---- lifecycle ----

    def on_mod_changed(self):
        self._files = self.find_files(state.mod_root) if state.is_loaded else []
        self.file_combo["values"] = [os.path.basename(p) for p in self._files]
        if self._files:
            self.file_combo.current(0)
        self._items = []
        self._current = None
        self._path = None
        self.listbox.delete(0, "end")
        self.editor.delete("1.0", "end")
        self.count_label.config(text="")

    def _load_file(self):
        idx = self.file_combo.current()
        if idx < 0 or not self._files:
            messagebox.showerror("Nothing to load", f"This mod has no {self.kind_label.lower()} files.")
            return
        self._path = self._files[idx]
        self._text, self._items = parse_named_blocks(self._path, self.outer_key)
        self._current = None
        self.editor.delete("1.0", "end")
        self._refresh_list()
        self.status.config(text=f"{len(self._items)} {self.kind_label.lower()}s in {os.path.basename(self._path)}")

    def _refresh_list(self):
        needle = self.search_var.get().strip().lower()
        self.listbox.delete(0, "end")
        self._visible = [t for t in self._items if not needle or needle in t[0].lower()]
        for name, _, _ in self._visible:
            self.listbox.insert("end", " " + name)
        self.count_label.config(text=f"{len(self._visible)} of {len(self._items)}")

    def _pick(self):
        sel = self.listbox.curselection()
        if not sel:
            return
        self._current = self._visible[sel[0]]
        _, start, end = self._current
        self.editor.delete("1.0", "end")
        self.editor.insert("1.0", self._text[start:end])
        self.editor.edit_reset()

    # ---- saving ----

    def _backup_once(self):
        if self._path in self._backed_up:
            return
        backup = self._path + ".bak"
        if not os.path.exists(backup):
            try:
                shutil.copy2(self._path, backup)
            except OSError:
                pass
        self._backed_up.add(self._path)

    def _write_text(self, new_text):
        self._backup_once()
        with open(self._path, "w", encoding="utf-8") as f:
            f.write(new_text)
        self._text, self._items = parse_named_blocks(self._path, self.outer_key)
        self._refresh_list()

    def _save(self):
        if not self._current:
            messagebox.showerror("Nothing selected", f"Pick a {self.kind_label.lower()} from the list first.")
            return
        block = self.editor.get("1.0", "end-1c").strip()
        if not block:
            messagebox.showerror("Empty", "The block is empty.")
            return
        if block.count("{") != block.count("}"):
            messagebox.showerror("Unbalanced braces",
                                 f"{block.count('{')} '{{' vs {block.count('}')} '}}' — fix before saving.")
            return
        name, start, end = self._current
        new_text = self._text[:start] + block + self._text[end:]
        self._write_text(new_text)
        self._current = None
        self.status.config(text=f"Saved '{name}' (backup kept as .bak).")

    def _add(self):
        if not self._path:
            messagebox.showerror("No file", "Load a file first.")
            return
        m = re.search(r"\b" + self.outer_key + r"\s*=\s*\{", self._text)
        if not m:
            messagebox.showerror("Bad file", f"No {self.outer_key} block found in this file.")
            return
        outer_close = scan.find_matching_brace(self._text, m.end() - 1)
        if outer_close == -1:
            messagebox.showerror("Bad file", f"The {self.outer_key} block never closes.")
            return
        insertion = "\n\t" + self.template.replace("\n", "\n\t") + "\n"
        new_text = self._text[:outer_close] + insertion + self._text[outer_close:]
        self._write_text(new_text)
        self.search_var.set("my_new")
        self._refresh_list()
        if self._visible:
            self.listbox.selection_set(0)
            self._pick()
        self.status.config(text=f"Template added — rename it and fill it in, then Save.")


STAT_KEYS = ["combat_width", "manpower", "max_strength", "max_organisation",
            "defense", "soft_attack", "hard_attack", "breakthrough",
            "armor_value", "max_speed"]

# stats where the division total is the SLOWEST/weakest piece rather than a
# sum - HOI4 sets division speed to its slowest sub-unit, not the total of
# everyone's speed, so adding them would be nonsense
MIN_KEYS = {"max_speed"}


def unit_stats(block_text):
    """{key: float} pulled from a sub_unit's top-level scalars. A plain regex
    is enough here: none of STAT_KEYS collide with names used inside the
    nested `type`/`categories`/`need` blocks."""
    out = {}
    for key in STAT_KEYS:
        m = re.search(r"\b" + key + r"\s*=\s*(-?[\d.]+)", block_text)
        if m:
            try:
                out[key] = float(m.group(1))
            except ValueError:
                pass
    return out


def combine_stats(per_unit_stats):
    """[{key: value}] -> {key: total} using sum, except MIN_KEYS which use
    the smallest value present (division speed = slowest sub-unit)."""
    totals = {}
    for key in STAT_KEYS:
        values = [s[key] for s in per_unit_stats if key in s]
        if not values:
            continue
        totals[key] = min(values) if key in MIN_KEYS else sum(values)
    return totals


class TemplateCalculator(ttk.Frame):
    """Tick sub-units from the currently loaded file, see the division's
    combined stats update live - a rough approximation (real HOI4 also
    weighs in support-company halving, terrain, doctrines...) good enough
    for comparing two draft templates against each other."""

    def __init__(self, master, editor):
        super().__init__(master, padding=6)
        self.editor = editor      # the _BlockEditor holding sub_units
        self._checks = {}         # name -> BooleanVar
        self._build()

    def _build(self):
        ttk.Label(
            self, style="Muted.TLabel", wraplength=900, justify="left",
            text="Tick the battalions in a template to add up their stats. This sums what the "
                 "file itself declares — it doesn't model support-company halving, terrain or "
                 "doctrines, so treat it as a way to compare two drafts, not an exact in-game number.",
        ).pack(anchor="w", pady=(0, 8))

        top = ttk.Frame(self)
        top.pack(fill="x", pady=(0, 6))
        ttk.Button(top, text="Load from Battalions Tab", command=self.refresh).pack(side="left")
        ttk.Button(top, text="Clear", command=self._clear).pack(side="left", padx=6)

        body = ttk.Frame(self)
        body.pack(fill="both", expand=True)

        left = ttk.Frame(body, width=260)
        left.pack(side="left", fill="y", padx=(0, 10))
        left.pack_propagate(False)
        canvas = tk.Canvas(left, highlightthickness=0, background=theme.SURFACE)
        bar = ttk.Scrollbar(left, orient="vertical", command=canvas.yview)
        self.checklist = ttk.Frame(canvas)
        canvas.create_window((0, 0), window=self.checklist, anchor="nw")
        canvas.configure(yscrollcommand=bar.set)
        self.checklist.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.pack(side="left", fill="both", expand=True)
        bar.pack(side="right", fill="y")

        right = ttk.LabelFrame(body, text="Division totals (approximate)", padding=10)
        right.pack(side="left", fill="both", expand=True)
        self.total_labels = {}
        for i, key in enumerate(STAT_KEYS):
            ttk.Label(right, text=key.replace("_", " ")).grid(row=i, column=0, sticky="w", pady=2)
            value = ttk.Label(right, text="—", style="Gold.TLabel")
            value.grid(row=i, column=1, sticky="e", padx=(20, 0), pady=2)
            self.total_labels[key] = value

    def refresh(self):
        for child in self.checklist.winfo_children():
            child.destroy()
        self._checks = {}
        items = getattr(self.editor, "_items", [])
        if not items:
            ttk.Label(self.checklist, text="Load a units file in the Battalions tab first.",
                      style="Muted.TLabel").pack(anchor="w")
        for name, _, _ in items:
            var = tk.BooleanVar(value=False)
            ttk.Checkbutton(self.checklist, text=name, variable=var,
                            command=self._recompute).pack(anchor="w", pady=1)
            self._checks[name] = var
        self._recompute()

    def _clear(self):
        for var in self._checks.values():
            var.set(False)
        self._recompute()

    def _recompute(self):
        text = getattr(self.editor, "_text", "")
        items = getattr(self.editor, "_items", [])
        chosen = [(name, s, e) for name, s, e in items if self._checks.get(name, tk.BooleanVar()).get()]
        stats = [unit_stats(text[s:e]) for _, s, e in chosen]
        totals = combine_stats(stats)
        for key, label in self.total_labels.items():
            label.configure(text=f"{totals[key]:g}" if key in totals else "—")


class UnitsTab(ttk.Frame):
    def __init__(self, master):
        super().__init__(master, padding=12)
        self.header = ui_kit.PageHeader(
            self, "Units",
            "Browse and edit unit types (the building blocks equipment attaches to) across the base game and this mod.", help_key="units")

        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True)
        self.units = _BlockEditor(nb, "sub_units", find_unit_files, NEW_SUB_UNIT_TEMPLATE, "Battalion")
        self.equipment = _BlockEditor(nb, "equipments", find_equipment_files, NEW_EQUIPMENT_TEMPLATE, "Equipment")
        self.calculator = TemplateCalculator(nb, self.units)
        nb.add(self.units, text="Division Sub-Units")
        nb.add(self.equipment, text="Equipment")
        nb.add(self.calculator, text="Template Calculator")
        nb.bind("<<NotebookTabChanged>>", self._on_tab_changed)
        self._nb = nb

        state.subscribe(self.on_mod_changed)
        self.on_mod_changed()

    def on_mod_changed(self):
        if state.is_loaded:
            self.header.set_status(True, state.mod_name)
        else:
            self.header.set_status(False, "no mod open")
        self.units.on_mod_changed()
        self.equipment.on_mod_changed()
        self.calculator.refresh()

    def _on_tab_changed(self, event):
        if self._nb.index("current") == 2:      # Template Calculator
            self.calculator.refresh()
