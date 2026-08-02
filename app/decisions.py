"""Decisions generator tab: build decisions under a category and export to
common/decisions/<category>.txt."""

import os
import tkinter as tk
from tkinter import ttk, messagebox

from app.state import state
from app import pds
from app import ui_kit
from app import mod_loader as ml
from app import safe_io
from app.decision_preview import DecisionPreview
from app.effect_wizard import EffectWizard
from app.ai_wizard import AIWizard
from app import dirty
from app import templates
from app.template_picker import TemplatePicker
from app.map_data import BASE_GAME
from app import searchable_combo


def from_parsed(d):
    """Convert a decision parsed out of a mod file into this tab's shape."""
    return {
        "id": d["id"],
        "title": state.text_for(d["id"], d["id"]),
        "desc": state.text_for(d["id"] + "_desc", ""),
        "icon": d.get("icon", "") or "GFX_decision_generic",
        "cost": d.get("cost", "") or 100,
        "days_re_enable": d.get("days_re_enable", ""),
        "allowed": d.get("allowed", "") or "always = yes",
        "visible": d.get("visible", ""),
        "available": d.get("available", ""),
        "effect": d.get("effect", ""),
        "ai_factor": d.get("ai_factor", ""),
        "ai_will_do_raw": d.get("ai_will_do_raw", ""),
    }


class DecisionDialog(tk.Toplevel):
    def __init__(self, master, decision=None):
        super().__init__(master)
        self.title("Decision")
        self.result = None
        self.resizable(False, False)
        self._build(decision or {})
        self.grab_set()

    def _build(self, d):
        fields = [
            ("id", "Decision id (e.g. xxx_form_alliance)"),
            ("title", "Title (localisation text)"),
            ("desc", "Description (localisation text)"),
            ("icon", "Icon (e.g. GFX_decision_generic)"),
            ("cost", "Political power cost (default 100)"),
            ("days_re_enable", "Days re-enable (blank = one-time)"),
        ]
        self.vars = {}
        row = 0
        for key, label in fields:
            ttk.Label(self, text=label).grid(row=row, column=0, sticky="w", padx=8, pady=4)
            var = tk.StringVar(value=str(d.get(key, "")))
            ttk.Entry(self, textvariable=var, width=42).grid(row=row, column=1, padx=8, pady=4)
            self.vars[key] = var
            row += 1

        text_fields = [
            ("allowed", "allowed (raw trigger, when the decision category is even considered)", "always = yes"),
            ("visible", "visible (raw trigger, optional)", ""),
            ("available", "available (raw trigger, optional)", ""),
            ("effect", "effect (raw, required)", ""),
        ]
        self.texts = {}
        for key, label, default in text_fields:
            ttk.Label(self, text=label).grid(row=row, column=0, sticky="nw", padx=8, pady=4)
            txt = tk.Text(self, width=42, height=3)
            txt.insert("1.0", d.get(key, default))
            txt.grid(row=row, column=1, padx=8, pady=4)
            kind = "effect" if key == "effect" else "trigger"
            ttk.Button(self, text="Wizard...",
                       command=lambda t=txt, k=kind: EffectWizard(self, t, k)).grid(row=row, column=2, sticky="n", pady=4)
            if key == "effect":
                from app import ref_picker
                ttk.Button(self, text="Link...",
                           command=lambda t=txt: ref_picker.open_picker(self, state.mod_root, t)
                           ).grid(row=row, column=3, sticky="n", pady=4)
            self.texts[key] = txt
            row += 1

        ttk.Label(self, text="ai_will_do (optional)").grid(row=row, column=0, sticky="nw", padx=8, pady=4)
        self.ai_txt = tk.Text(self, width=42, height=3)
        existing_ai = d.get("ai_will_do_raw", "") or (f"factor = {d['ai_factor']}" if d.get("ai_factor") else "")
        self.ai_txt.insert("1.0", existing_ai)
        self.ai_txt.grid(row=row, column=1, padx=8, pady=4)
        ttk.Button(self, text="AI Wizard...", command=lambda: AIWizard(self, self.ai_txt)).grid(row=row, column=2, sticky="n", pady=4)
        row += 1

        btns = ttk.Frame(self)
        btns.grid(row=row, column=0, columnspan=2, pady=10)
        ttk.Button(btns, text="Save", command=self._save).pack(side="left", padx=4)
        ttk.Button(btns, text="Cancel", command=self.destroy).pack(side="left", padx=4)

    def _save(self):
        fid = self.vars["id"].get().strip()
        if not fid:
            messagebox.showerror("Missing id", "Decision id is required.")
            return
        effect = self.texts["effect"].get("1.0", "end").strip()
        if not effect:
            messagebox.showerror("Missing effect", "The effect field is required.")
            return
        try:
            cost = float(self.vars["cost"].get() or 100)
        except ValueError:
            messagebox.showerror("Bad number", "Cost must be a number.")
            return
        days = self.vars["days_re_enable"].get().strip()

        self.result = {
            "id": fid,
            "title": self.vars["title"].get().strip() or fid,
            "desc": self.vars["desc"].get().strip(),
            "icon": self.vars["icon"].get().strip() or "GFX_decision_generic",
            "cost": cost,
            "days_re_enable": days,
            "allowed": self.texts["allowed"].get("1.0", "end").strip() or "always = yes",
            "visible": self.texts["visible"].get("1.0", "end").strip(),
            "available": self.texts["available"].get("1.0", "end").strip(),
            "effect": effect,
            "ai_factor": "",
            "ai_will_do_raw": self.ai_txt.get("1.0", "end").strip(),
        }
        self.destroy()


class DecisionsTab(ttk.Frame):
    def __init__(self, master):
        super().__init__(master, padding=12)
        self.decisions = []
        self._cat_items = []
        self.source_file = None
        self._build()
        state.subscribe(self.on_mod_changed)
        dirty.track(self, mutators=("_add", "_edit", "_delete", "_from_template"))

    def _build(self):
        self.header = ui_kit.PageHeader(
            self, "Decisions",
            "Create/edit decisions - the buttons in the Decisions panel a country can click to run an effect, usually gated by a cost and a visible/available trigger.", help_key="decisions")

        loader = ttk.Frame(self)
        loader.pack(fill="x")
        ttk.Label(loader, text="Load from mod:").pack(side="left")
        self.cat_combo = ttk.Combobox(loader, width=52)
        self.cat_combo.pack(side="left", padx=6)
        searchable_combo.enable_filter(self.cat_combo, lambda: [i[0] for i in self._cat_items])
        ttk.Button(loader, text="Load", command=self._load_from_mod).pack(side="left")
        ttk.Button(loader, text="New empty category", command=self._new_category).pack(side="left", padx=6)

        top = ttk.Frame(self)
        top.pack(fill="x", pady=(8, 0))
        ttk.Label(top, text="Decision category id").pack(side="left")
        self.cat_var = tk.StringVar(value="my_category")
        ttk.Entry(top, textvariable=self.cat_var, width=30).pack(side="left", padx=6)

        search = ttk.Frame(self)
        search.pack(fill="x", pady=(8, 0))
        ttk.Label(search, text="Search:").pack(side="left")
        self.search_var = tk.StringVar()
        entry = ttk.Entry(search, textvariable=self.search_var, width=36)
        self.search_entry = entry
        entry.pack(side="left", padx=6)
        entry.bind("<KeyRelease>", lambda e: self._refresh())
        ttk.Button(search, text="Clear", command=lambda: (self.search_var.set(""), self._refresh())).pack(side="left")
        self.count_label = ttk.Label(search, text="", foreground="#888")
        self.count_label.pack(side="left", padx=10)

        cols = ("id", "title", "cost", "days_re_enable")
        self.tree = ttk.Treeview(self, columns=cols, show="headings", height=14)
        for c in cols:
            self.tree.heading(c, text=c)
            self.tree.column(c, width=140)
        self.tree.pack(fill="both", expand=True, pady=10)

        btns = ttk.Frame(self)
        btns.pack(fill="x")
        ttk.Button(btns, text="Add Decision", command=self._add).pack(side="left", padx=4)
        ttk.Button(btns, text="From Template...", command=self._from_template).pack(side="left", padx=4)
        ttk.Button(btns, text="Edit Selected", command=self._edit).pack(side="left", padx=4)
        ttk.Button(btns, text="Delete Selected", command=self._delete).pack(side="left", padx=4)
        ttk.Button(btns, text="Used by...", command=self._show_references).pack(side="left", padx=4)
        ttk.Button(btns, text="Preview in game style", command=self._preview).pack(side="left", padx=12)
        ttk.Button(btns, text="Save to mod", command=self._export).pack(side="right", padx=4)

        self.status = ttk.Label(self, text="", foreground="#2a7a2a", wraplength=900, justify="left")
        self.status.pack(fill="x", pady=(6, 0))

        self.on_mod_changed()

    # ---- mod integration ----

    def on_mod_changed(self):
        # keep this cheap - the heavy scan runs when the tab is shown
        self._needs_reload = True
        self.is_dirty = False
        if state.is_loaded:
            self.header.set_status(True, state.mod_name)
        else:
            self.header.set_status(False, "no mod open")

    def on_show(self):
        if getattr(self, "_needs_reload", False) and state.is_loaded:
            self._needs_reload = False
            self._reload_from_mod()

    def _reload_from_mod_guard(self):
        pass

    def _reload_from_mod(self):
        if not state.is_loaded:
            self.header.set_status(False, "no mod open")
            self.cat_combo["values"] = []
            return
        self.header.set_status(True, state.mod_name)

        items = []
        for path in ml.find_decision_files(BASE_GAME) + ml.find_decision_files(state.mod_root):
            for cat in ml.parse_decisions(path):
                cat["is_vanilla"] = os.path.normcase(path).startswith(os.path.normcase(BASE_GAME) + os.sep)
                items.append((
                    f"{cat['category']}  —  {os.path.basename(path)}  ({len(cat['decisions'])} decisions)",
                    path, cat,
                ))
        self._cat_items = items
        self.cat_combo["values"] = [i[0] for i in items]
        if items:
            self.cat_combo.current(0)

    def _load_from_mod(self):
        item = searchable_combo.resolve(self.cat_combo, self._cat_items)
        if item is None:
            messagebox.showerror("Nothing to load", "Pick a decision category from the list first.")
            return
        _, path, cat = item
        self.decisions = [from_parsed(d) for d in cat["decisions"]]
        self.cat_var.set(cat["category"])
        self._refresh()

        # This tab writes exactly one category per file. Saving back over a
        # file that holds several would silently drop the others, so only
        # reuse the source path when this category is the whole file.
        siblings = sum(1 for _, p, _ in self._cat_items if p == path)
        if siblings == 1 and not cat.get("is_vanilla"):
            self.source_file = path
            note = ""
        else:
            self.source_file = None
            note = ("  Vanilla source is read-only; saving creates a mod-local category file."
                    if cat.get("is_vanilla") else
                    f"  That file holds {siblings} categories, so saving will create a separate "
                    f"{cat['category']}.txt instead of overwriting it.")

        self.status.config(text=f"Loaded {len(self.decisions)} decisions from {os.path.basename(path)}.{note}")

    def _show_references(self):
        """What would break if this were deleted - references only point one
        way in the game's files, so the answer has to be rebuilt by scanning."""
        sel = self.tree.selection()
        if not sel:
            messagebox.showerror("Nothing selected", "Pick a decision first.")
            return
        if not state.is_loaded:
            messagebox.showerror("No mod", "Open a mod first.")
            return
        from app import references
        references.open_dialog(self, state.mod_root, sel[0])

    def _preview(self):
        shown = [d for d in self.decisions if self._matches(d)]
        if not shown:
            messagebox.showerror("Nothing to preview", "There are no decisions to show.")
            return
        DecisionPreview(self, self.cat_var.get().strip() or "my_category", shown)

    def _new_category(self):
        self.decisions = []
        self.source_file = None
        self.cat_var.set("my_category")
        self._refresh()
        self.status.config(text="Started an empty decision category.")

    def _matches(self, d):
        needle = self.search_var.get().strip().lower()
        if not needle:
            return True
        haystack = " ".join([
            d["id"], d.get("title", ""), d.get("desc", ""), d.get("icon", ""), str(d.get("effect", "")),
        ]).lower()
        return needle in haystack

    def _refresh(self):
        self.tree.delete(*self.tree.get_children())
        shown = 0
        for d in self.decisions:
            if not self._matches(d):
                continue
            self.tree.insert(
                "", "end", iid=d["id"],
                values=(d["id"], d["title"], d["cost"], d["days_re_enable"] or "one-time"),
            )
            shown += 1
        self.count_label.config(
            text=f"{shown} of {len(self.decisions)}" if shown != len(self.decisions) else f"{shown} decisions"
        )

    def _add(self):
        dlg = DecisionDialog(self)
        self.wait_window(dlg)
        if dlg.result:
            if any(d["id"] == dlg.result["id"] for d in self.decisions):
                messagebox.showerror("Duplicate id", "A decision with that id already exists.")
                return
            self.decisions.append(dlg.result)
            self._register_loc(dlg.result)
            self._refresh()

    def _from_template(self):
        picker = TemplatePicker(self, templates.DECISION_TEMPLATES,
                                prefix_hint=self.cat_var.get().strip() or "my")
        self.wait_window(picker)
        if not picker.result:
            return
        dlg = DecisionDialog(self, picker.result)
        self.wait_window(dlg)
        if dlg.result:
            if any(d["id"] == dlg.result["id"] for d in self.decisions):
                messagebox.showerror("Duplicate id", "A decision with that id already exists.")
                return
            self.decisions.append(dlg.result)
            self._register_loc(dlg.result)
            self._refresh()

    def _edit(self):
        sel = self.tree.selection()
        if not sel:
            return
        did = sel[0]
        idx = next(i for i, d in enumerate(self.decisions) if d["id"] == did)
        dlg = DecisionDialog(self, self.decisions[idx])
        self.wait_window(dlg)
        if dlg.result:
            self.decisions[idx] = dlg.result
            self._register_loc(dlg.result)
            self._refresh()

    def _delete(self):
        sel = self.tree.selection()
        if not sel:
            return
        self.decisions = [d for d in self.decisions if d["id"] not in sel]
        self._refresh()

    def _register_loc(self, d):
        state.add_loc(d["id"], d["title"])
        if d["desc"]:
            state.add_loc(d["id"] + "_desc", d["desc"])

    def _export(self):
        if not state.is_loaded:
            messagebox.showerror("No mod folder", "Open a mod, or create one in the Settings tab first.")
            return
        if not self.decisions:
            messagebox.showerror("Nothing to save", "Add at least one decision first.")
            return

        category = self.cat_var.get().strip() or "my_category"
        decision_blocks = []
        for d in self.decisions:
            body = [
                pds.kv("icon", d["icon"]),
                pds.kv("cost", d["cost"]),
            ]
            if d["days_re_enable"]:
                body.append(pds.kv("days_re_enable", d["days_re_enable"]))
            body.append(pds.block("allowed", d["allowed"]))
            if d["visible"]:
                body.append(pds.block("visible", d["visible"]))
            if d["available"]:
                body.append(pds.block("available", d["available"]))
            body.append(pds.block("effect", d["effect"]))
            if d.get("ai_factor"):
                body.append(pds.block("ai_will_do", pds.kv("factor", d["ai_factor"])))
            elif d.get("ai_will_do_raw"):
                body.append(pds.block("ai_will_do", d["ai_will_do_raw"]))
            decision_blocks.append(pds.block(d["id"], "\n".join(body)))

        content = pds.block(category, pds.block("decisions", "\n\n".join(decision_blocks)))
        out_dir = state.ensure_dir("common", "decisions")
        out_path = self.source_file or os.path.join(out_dir, f"{category}.txt")

        if safe_io.write_text(out_path, content + "\n", parent=self, describe="this decisions file"):
            self.status.config(text=f"Saved {len(self.decisions)} decisions to {out_path}")
        else:
            self.status.config(text="Save cancelled.")
