"""Ideas / National Spirits tab.

HOI4 stores both under the same common/ideas format: a slot category holds
a list of idea blocks with a picture, optional removal_cost, and a modifier
block. The "country" category is where national spirits and generic
country-wide ideas both live (a spirit is really just an idea with
removal_cost = -1, so it can't be manually removed); the other categories
(political_advisor, army_spirit, industrial_concern, ...) are the classic
advisor/specialist slots.
"""

import os
import glob
import re
import tkinter as tk
from tkinter import ttk, messagebox

from app.state import state
from app import pds
from app import ui_kit
from app import mod_loader as ml
from app import safe_io
from app import icon_library
from app import piece_composer
from app.idea_preview import IdeaPreview
from app.effect_wizard import EffectWizard
from app import dirty
from app import searchable_combo
from app import templates
from app.template_picker import TemplatePicker
from app.map_data import BASE_GAME
from app import pds_scan as scan
from app import tech_graph

CATEGORY_PRESETS = [
    "country", "political_advisor", "high_command", "theorist",
    "army_spirit", "navy_spirit", "air_force_spirit",
    "industrial_concern", "tank_manufacturer", "materiel_manufacturer",
    "naval_manufacturer", "aircraft_manufacturer",
]


def from_parsed(d):
    """Convert an idea parsed out of a mod file into this tab's shape."""
    return {
        "id": d["id"],
        "category": d.get("category", "country"),
        "title": state.text_for(d["id"], d["id"]),
        "desc": state.text_for(d["id"] + "_desc", ""),
        "picture": d.get("picture", ""),
        "removal_cost": d.get("removal_cost", ""),
        "cost": d.get("cost", ""),
        "allowed": d.get("allowed", "") or "always = yes",
        "allowed_civil_war": d.get("allowed_civil_war", ""),
        "available": d.get("available", ""),
        "modifier": d.get("modifier", ""),
        "research_modifier": d.get("research_modifier", ""),
        "equipment_bonus": d.get("equipment_bonus", ""),
        "targeted_modifier": d.get("targeted_modifier", ""),
        "ai_will_do": d.get("ai_will_do", ""),
    }


class IdeaDialog(tk.Toplevel):
    def __init__(self, master, mod_root, idea=None):
        super().__init__(master)
        self.title("Idea / National Spirit")
        self.result = None
        self.mod_root = mod_root
        self.original = dict(idea or {})
        self.resizable(False, False)
        self._build(idea or {})
        self.grab_set()

    def _build(self, d):
        row = 0
        ttk.Label(self, text="Id").grid(row=row, column=0, sticky="w", padx=8, pady=4)
        self.id_var = tk.StringVar(value=d.get("id", ""))
        ttk.Entry(self, textvariable=self.id_var, width=42).grid(row=row, column=1, padx=8, pady=4)
        row += 1

        ttk.Label(self, text="Category (slot)").grid(row=row, column=0, sticky="w", padx=8, pady=4)
        self.category_var = tk.StringVar(value=d.get("category", "country"))
        ttk.Combobox(
            self, textvariable=self.category_var, width=39, values=CATEGORY_PRESETS,
        ).grid(row=row, column=1, padx=8, pady=4)
        row += 1

        ttk.Label(self, text="Title").grid(row=row, column=0, sticky="w", padx=8, pady=4)
        self.title_var = tk.StringVar(value=d.get("title", ""))
        ttk.Entry(self, textvariable=self.title_var, width=42).grid(row=row, column=1, padx=8, pady=4)
        row += 1

        ttk.Label(self, text="Description").grid(row=row, column=0, sticky="w", padx=8, pady=4)
        self.desc_var = tk.StringVar(value=d.get("desc", ""))
        ttk.Entry(self, textvariable=self.desc_var, width=42).grid(row=row, column=1, padx=8, pady=4)
        row += 1

        ttk.Label(self, text="Icon (picture name)").grid(row=row, column=0, sticky="w", padx=8, pady=4)
        icon_frame = ttk.Frame(self)
        icon_frame.grid(row=row, column=1, sticky="w", padx=8, pady=4)
        self.icon_var = tk.StringVar(value=d.get("picture", ""))
        ttk.Entry(icon_frame, textvariable=self.icon_var, width=26).pack(side="left")
        ttk.Button(icon_frame, text="Library...", command=self._pick_icon).pack(side="left", padx=3)
        ttk.Button(icon_frame, text="Compose...", command=self._compose_icon).pack(side="left", padx=3)
        row += 1

        self.spirit_var = tk.BooleanVar(value=str(d.get("removal_cost", "")) == "-1")
        ttk.Checkbutton(
            self, text="National spirit (permanent — not manually removable)", variable=self.spirit_var,
        ).grid(row=row, column=0, columnspan=2, sticky="w", padx=8, pady=4)
        row += 1

        ttk.Label(self, text="allowed (raw trigger, when this idea can ever exist)").grid(
            row=row, column=0, sticky="nw", padx=8, pady=4
        )
        self.allowed_txt = tk.Text(self, width=42, height=3)
        self.allowed_txt.insert("1.0", d.get("allowed", "always = yes"))
        self.allowed_txt.grid(row=row, column=1, padx=8, pady=4)
        row += 1

        ttk.Label(self, text="available (raw trigger, optional — when it can be added)").grid(
            row=row, column=0, sticky="nw", padx=8, pady=4
        )
        self.available_txt = tk.Text(self, width=42, height=3)
        self.available_txt.insert("1.0", d.get("available", ""))
        self.available_txt.grid(row=row, column=1, padx=8, pady=4)
        row += 1

        ttk.Label(self, text="modifier (raw, the actual effect)").grid(row=row, column=0, sticky="nw", padx=8, pady=4)
        self.modifier_txt = tk.Text(self, width=42, height=6)
        self.modifier_txt.insert("1.0", d.get("modifier", "political_power_factor = 0.1"))
        self.modifier_txt.grid(row=row, column=1, padx=8, pady=4)
        ttk.Button(self, text="Wizard...", command=lambda: EffectWizard(self, self.modifier_txt, "modifier")).grid(row=row, column=2, sticky="n", pady=4)
        row += 1

        btns = ttk.Frame(self)
        btns.grid(row=row, column=0, columnspan=2, pady=10)
        ttk.Button(btns, text="Save", command=self._save).pack(side="left", padx=4)
        ttk.Button(btns, text="Cancel", command=self.destroy).pack(side="left", padx=4)

    def _pick_icon(self):
        # scanning every mod's .gfx takes a couple of seconds - do it once
        # per mod and keep the result on the shared state
        library = state.idea_icon_library
        if library is None:
            library = icon_library.build_idea_library(
                r"C:\Program Files (x86)\Steam\steamapps\common\Hearts of Iron IV",
                r"C:\Program Files (x86)\Steam\steamapps\workshop\content\394360",
                extra_roots=[self.mod_root] if self.mod_root else (),
            )
            state.idea_icon_library = library
        if not library:
            messagebox.showerror("No icons", "No idea icons were indexed.")
            return
        picker = icon_library.IconPicker(self, library)
        self.wait_window(picker)
        if picker.result:
            # store without the GFX_idea_ prefix, matching the file convention
            sprite = picker.result
            self.icon_var.set(sprite[len("GFX_idea_"):] if sprite.upper().startswith("GFX_IDEA_") else sprite)

    def _compose_icon(self):
        if not piece_composer.pack_available():
            messagebox.showerror(
                "Pack missing",
                "The Ultimate-HOI4-GFX asset pack was not found in the app's assets folder.",
            )
            return
        composer = piece_composer.PieceComposer(self, self.mod_root, kind="spirit",
                                                suggested_name="my_custom_spirit")
        self.wait_window(composer)
        if composer.result:
            sprite = composer.result["sprite"]
            self.icon_var.set(sprite[len("GFX_idea_"):] if sprite.upper().startswith("GFX_IDEA_") else sprite)

    def _save(self):
        iid = self.id_var.get().strip()
        if not iid:
            messagebox.showerror("Missing id", "Idea id is required.")
            return

        result = dict(self.original)
        result.update({
            "id": iid,
            "category": self.category_var.get().strip() or "country",
            "title": self.title_var.get().strip() or iid,
            "desc": self.desc_var.get().strip(),
            "picture": self.icon_var.get().strip(),
            "removal_cost": "-1" if self.spirit_var.get() else "",
            "allowed": self.allowed_txt.get("1.0", "end").strip() or "always = yes",
            "available": self.available_txt.get("1.0", "end").strip(),
            "modifier": self.modifier_txt.get("1.0", "end").strip(),
        })
        self.result = result
        self.destroy()


class IdeasTab(ttk.Frame):
    def __init__(self, master):
        super().__init__(master, padding=12)
        self.ideas = []
        self._cat_items = []
        self.source_file = None
        self._build()
        state.subscribe(self.on_mod_changed)
        dirty.track(self, mutators=("_add", "_edit", "_delete", "_from_template"))

    def _build(self):
        self.header = ui_kit.PageHeader(
            self, "Ideas / Spirits",
            "Create/edit ideas - national spirits, country/political advisors, high command and other 'idea' slot categories - each with a modifier block.", help_key="ideas")

        loader = ttk.Frame(self)
        loader.pack(fill="x")
        ttk.Label(loader, text="Load from mod:").pack(side="left")
        self.cat_combo = ttk.Combobox(loader, width=52)
        self.cat_combo.pack(side="left", padx=6)
        searchable_combo.enable_filter(self.cat_combo, lambda: [i[0] for i in self._cat_items])
        ttk.Button(loader, text="Load", command=self._load_from_mod).pack(side="left")
        ttk.Button(loader, text="New empty category", command=self._new_category).pack(side="left", padx=6)

        country_row = ttk.Frame(self)
        country_row.pack(fill="x", pady=(8, 0))
        ttk.Label(country_row, text="Country context:").pack(side="left")
        self.country_var = tk.StringVar()
        self.country_combo = ttk.Combobox(country_row, textvariable=self.country_var, state="readonly", width=9)
        self.country_combo.pack(side="left", padx=6)
        self.country_combo.bind("<<ComboboxSelected>>", lambda _event: self._refresh_country_context())
        self.country_ideas_label = ttk.Label(country_row, text="Select a country to see starting ideas.", style="Muted.TLabel")
        self.country_ideas_label.pack(side="left", padx=8)
        ttk.Button(country_row, text="Assign selected to country", command=self._assign_selected_to_country).pack(side="right")

        top = ttk.Frame(self)
        top.pack(fill="x", pady=(8, 0))
        ttk.Label(top, text="Category (slot) id").pack(side="left")
        self.category_var = tk.StringVar(value="country")
        ttk.Combobox(top, textvariable=self.category_var, width=27, values=CATEGORY_PRESETS).pack(side="left", padx=6)

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

        cols = ("id", "title", "spirit", "modifier")
        self.tree = ttk.Treeview(self, columns=cols, show="headings", height=14)
        headings = {"id": "id", "title": "title", "spirit": "spirit?", "modifier": "modifier (raw, head)"}
        widths = {"id": 220, "title": 200, "spirit": 60, "modifier": 320}
        for c in cols:
            self.tree.heading(c, text=headings[c])
            self.tree.column(c, width=widths[c])
        self.tree.pack(fill="both", expand=True, pady=10)
        self.tree.bind("<Double-Button-1>", lambda e: self._edit())

        btns = ttk.Frame(self)
        btns.pack(fill="x")
        ttk.Button(btns, text="Add Idea", command=self._add).pack(side="left", padx=4)
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
        if state.is_loaded and not self.country_combo["values"]:
            tags = tech_graph.country_tags(state.mod_root)
            self.country_combo["values"] = tags
            if tags:
                self.country_var.set("GER" if "GER" in tags else tags[0])
                self._refresh_country_context()

    def _reload_from_mod_guard(self):
        pass

    def _reload_from_mod(self):
        if not state.is_loaded:
            self.header.set_status(False, "no mod open")
            self.cat_combo["values"] = []
            return
        self.header.set_status(True, state.mod_name)

        items = []
        for path in ml.find_idea_files(BASE_GAME) + ml.find_idea_files(state.mod_root):
            for cat in ml.parse_ideas(path):
                cat["is_vanilla"] = os.path.normcase(path).startswith(os.path.normcase(BASE_GAME) + os.sep)
                items.append((
                    f"{cat['category']}  —  {os.path.basename(path)}  ({len(cat['ideas'])} ideas)",
                    path, cat,
                ))
        self._cat_items = items
        self.cat_combo["values"] = [i[0] for i in items]
        if items:
            self.cat_combo.current(0)

    def _load_from_mod(self):
        item = searchable_combo.resolve(self.cat_combo, self._cat_items)
        if item is None:
            messagebox.showerror("Nothing to load", "Pick an idea category from the list first.")
            return
        _, path, cat = item
        self.ideas = [from_parsed(d) for d in cat["ideas"]]
        self.category_var.set(cat["category"])
        self._refresh()
        self._refresh_country_context()

        # This tab writes exactly one category per file. Saving back over a
        # file that holds several categories would drop the rest, so only
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
                    f"{cat['category']}_ideas.txt instead of overwriting it.")

        self.status.config(text=f"Loaded {len(self.ideas)} ideas from {os.path.basename(path)}.{note}")

    def _new_category(self):
        self.ideas = []
        self.source_file = None
        self.category_var.set("country")
        self._refresh()
        self.status.config(text="Started an empty idea category.")

    def _country_starting_ideas(self, tag):
        """Best-effort list of ideas granted by the selected country's history."""
        found = set()
        for root in (BASE_GAME, state.mod_root):
            folder = os.path.join(root, "history", "countries")
            paths = glob.glob(os.path.join(folder, f"{tag}*.txt")) if os.path.isdir(folder) else []
            for path in paths:
                try:
                    with open(path, "r", encoding="utf-8-sig", errors="ignore") as handle:
                        text = scan.strip_comments(handle.read())
                except OSError:
                    continue
                found.update(re.findall(r"\badd_ideas\s*=\s*(?!\{)([A-Za-z_][\w]*)", text))
                for _, _, block in scan.iter_blocks(text, "add_ideas"):
                    found.update(re.findall(r"(?m)^\s*([A-Za-z_][\w]*)\s*$", block))
        return sorted(found)

    def _refresh_country_context(self):
        tag = self.country_var.get()
        ideas = self._country_starting_ideas(tag) if tag else []
        shown = ", ".join(ideas[:5]) or "(none detected)"
        more = f" +{len(ideas) - 5}" if len(ideas) > 5 else ""
        assignable = len(self.ideas)
        self.country_ideas_label.config(
            text=f"Starts with: {shown}{more}  |  Current category: {assignable} assignable idea(s)"
        )

    def _assign_selected_to_country(self):
        selection = self.tree.selection()
        tag = self.country_var.get()
        if not tag or not selection:
            messagebox.showerror("Missing selection", "Select a country and an idea/spirit first.")
            return
        idea_id = selection[0]
        folder = state.ensure_dir("history", "countries")
        path = os.path.join(folder, f"{tag} - ModMaker Ideas.txt")
        try:
            existing = open(path, "r", encoding="utf-8-sig", errors="ignore").read() if os.path.isfile(path) else ""
            if re.search(r"\b" + re.escape(idea_id) + r"\b", existing):
                self.status.config(text=f"{idea_id} is already assigned to {tag} in this mod.")
                return
            with open(path, "a", encoding="utf-8") as handle:
                if existing and not existing.endswith("\n"):
                    handle.write("\n")
                handle.write(f"add_ideas = {{ {idea_id} }}\n")
        except OSError as exc:
            messagebox.showerror("Couldn't assign idea", str(exc))
            return
        self._refresh_country_context()
        self.status.config(text=f"Assigned {idea_id} to {tag} at campaign start (mod-local history file).")

    # ---- list editing ----

    def _matches(self, d):
        needle = self.search_var.get().strip().lower()
        if not needle:
            return True
        haystack = " ".join([d["id"], d.get("title", ""), d.get("desc", ""), d.get("modifier", "")]).lower()
        return needle in haystack

    def _refresh(self):
        self.tree.delete(*self.tree.get_children())
        shown = 0
        for d in self.ideas:
            if not self._matches(d):
                continue
            mod_head = " ".join(d.get("modifier", "").split())[:60]
            self.tree.insert(
                "", "end", iid=d["id"],
                values=(d["id"], d["title"], "yes" if d.get("removal_cost") == "-1" else "", mod_head),
            )
            shown += 1
        self.count_label.config(
            text=f"{shown} of {len(self.ideas)}" if shown != len(self.ideas) else f"{shown} ideas"
        )

    def _add(self):
        dlg = IdeaDialog(self, state.mod_root, {"category": self.category_var.get()})
        self.wait_window(dlg)
        if dlg.result:
            if any(d["id"] == dlg.result["id"] for d in self.ideas):
                messagebox.showerror("Duplicate id", "An idea with that id already exists.")
                return
            self.ideas.append(dlg.result)
            self._register_loc(dlg.result)
            self._refresh()

    def _from_template(self):
        picker = TemplatePicker(self, templates.IDEA_TEMPLATES, prefix_hint="my")
        self.wait_window(picker)
        if not picker.result:
            return
        picker.result["category"] = self.category_var.get()
        dlg = IdeaDialog(self, state.mod_root, picker.result)
        self.wait_window(dlg)
        if dlg.result:
            if any(d["id"] == dlg.result["id"] for d in self.ideas):
                messagebox.showerror("Duplicate id", "An idea with that id already exists.")
                return
            self.ideas.append(dlg.result)
            self._register_loc(dlg.result)
            self._refresh()

    def _edit(self):
        sel = self.tree.selection()
        if not sel:
            return
        iid = sel[0]
        idx = next(i for i, d in enumerate(self.ideas) if d["id"] == iid)
        dlg = IdeaDialog(self, state.mod_root, self.ideas[idx])
        self.wait_window(dlg)
        if dlg.result:
            self.ideas[idx] = dlg.result
            self._register_loc(dlg.result)
            self._refresh()

    def _delete(self):
        sel = self.tree.selection()
        if not sel:
            return
        self.ideas = [d for d in self.ideas if d["id"] not in sel]
        self._refresh()

    def _register_loc(self, d):
        state.add_loc(d["id"], d["title"])
        if d["desc"]:
            state.add_loc(d["id"] + "_desc", d["desc"])

    def _show_references(self):
        """What would break if this were deleted - references only point one
        way in the game's files, so the answer has to be rebuilt by scanning."""
        sel = self.tree.selection()
        if not sel:
            messagebox.showerror("Nothing selected", "Pick a idea first.")
            return
        if not state.is_loaded:
            messagebox.showerror("No mod", "Open a mod first.")
            return
        from app import references
        references.open_dialog(self, state.mod_root, sel[0])

    def _preview(self):
        shown = [d for d in self.ideas if self._matches(d)]
        if not shown:
            messagebox.showerror("Nothing to preview", "There are no ideas to show.")
            return
        IdeaPreview(self, self.category_var.get().strip() or "country", shown)

    # ---- saving ----

    def _export(self):
        if not state.is_loaded:
            messagebox.showerror("No mod folder", "Open a mod, or create one in the Settings tab first.")
            return
        if not self.ideas:
            messagebox.showerror("Nothing to save", "Add at least one idea first.")
            return

        category = self.category_var.get().strip() or "country"
        idea_blocks = []
        for d in self.ideas:
            body = []
            if d.get("picture"):
                body.append(pds.kv("picture", d["picture"]))
            body.append(pds.block("allowed", d["allowed"] or "always = yes"))
            if d.get("allowed_civil_war"):
                body.append(pds.block("allowed_civil_war", d["allowed_civil_war"]))
            if d.get("available"):
                body.append(pds.block("available", d["available"]))
            if d.get("removal_cost"):
                body.append(pds.kv("removal_cost", d["removal_cost"]))
            if d.get("cost"):
                body.append(pds.kv("cost", d["cost"]))
            if d.get("modifier"):
                body.append(pds.block("modifier", d["modifier"]))
            if d.get("research_modifier"):
                body.append(pds.block("research_modifier", d["research_modifier"]))
            if d.get("equipment_bonus"):
                body.append(pds.block("equipment_bonus", d["equipment_bonus"]))
            if d.get("targeted_modifier"):
                body.append(pds.block("targeted_modifier", d["targeted_modifier"]))
            if d.get("ai_will_do"):
                body.append(pds.block("ai_will_do", d["ai_will_do"]))
            idea_blocks.append(pds.block(d["id"], "\n".join(body)))

        content = pds.block("ideas", pds.block(category, "\n\n".join(idea_blocks)))
        out_dir = state.ensure_dir("common", "ideas")
        out_path = self.source_file or os.path.join(out_dir, f"{category}_ideas.txt")

        if safe_io.write_text(out_path, content + "\n", parent=self, describe="this ideas file"):
            self.status.config(text=f"Saved {len(self.ideas)} ideas to {out_path}")
        else:
            self.status.config(text="Save cancelled.")
