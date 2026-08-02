"""Character Editor tab: pick a country, pick one of its characters, and
edit whichever leader roles it holds - skill numbers and traits for the
three military commander roles with a consistent schema, a raw block editor
for the two roles (advisor, scientist's nested skill tree) that don't.

Built on `character_surgery.py`'s byte-preserving role edits, the same
approach `focus_surgery.py`/`tech_tab.py` already use elsewhere: only the
touched role's fields change, everything else in a country's (possibly
huge) characters file stays untouched.
"""

import os
import shutil
import tkinter as tk
from tkinter import ttk, messagebox

from app.state import state
from app import mod_loader as ml
from app import character_surgery as surgery
from app import character_traits
from app import image_cache
from app import theme, ui_kit
from app import country_creator, ideology_creator
from app.map_data import BASE_GAME

MILITARY_ROLES = {
    "corps_commander": ("skill", "attack_skill", "defense_skill", "planning_skill", "logistics_skill"),
    "field_marshal": ("skill", "attack_skill", "defense_skill", "planning_skill", "logistics_skill"),
    "navy_leader": ("skill", "attack_skill", "defense_skill", "maneuvering_skill", "coordination_skill"),
}
RAW_ROLES = ("advisor", "scientist")
ALL_ROLES = ("country_leader",) + tuple(MILITARY_ROLES) + RAW_ROLES

PORTRAIT_SIZE = (110, 140)


class CharacterEditorTab(ttk.Frame):
    def __init__(self, master):
        super().__init__(master, padding=12)
        self._characters = {}     # tag -> [char dicts]
        self._current = None      # char dict currently shown
        self._role_widgets = {}   # role_key -> {"skills": {...}, "traits": Listbox/Text, "raw": Text}
        self._icon_ref = None
        self._build()
        state.subscribe(self.on_mod_changed)

    def _build(self):
        self.header = ui_kit.PageHeader(
            self, "Characters",
            "Country leaders, generals/admirals and advisors - portraits, traits, and the history/characters file entries the game reads.", help_key="characters")

        top = ttk.Frame(self)
        top.pack(fill="x")
        ttk.Label(top, text="Country").pack(side="left")
        self.tag_var = tk.StringVar()
        self.tag_combo = ttk.Combobox(top, textvariable=self.tag_var, state="readonly", width=12)
        self.tag_combo.pack(side="left", padx=4)
        self.tag_combo.bind("<<ComboboxSelected>>", self._load_tag)
        self.count_label = ttk.Label(top, text="", style="Muted.TLabel")
        self.count_label.pack(side="left", padx=10)

        body = ttk.Frame(self)
        body.pack(fill="both", expand=True, pady=8)

        left = ttk.Frame(body, width=260)
        left.pack(side="left", fill="y", padx=(0, 10))
        left.pack_propagate(False)
        self.listbox = tk.Listbox(left, exportselection=False)
        bar = ttk.Scrollbar(left, orient="vertical", command=self.listbox.yview)
        self.listbox.configure(yscrollcommand=bar.set)
        self.listbox.pack(side="left", fill="both", expand=True)
        bar.pack(side="right", fill="y")
        self.listbox.bind("<<ListboxSelect>>", lambda e: self._select())

        right = ttk.Frame(body)
        right.pack(side="left", fill="both", expand=True)

        head = ttk.Frame(right)
        head.pack(fill="x")
        self.portrait_label = tk.Label(head, background=theme.SURFACE, width=PORTRAIT_SIZE[0],
                                       height=PORTRAIT_SIZE[1])
        self.portrait_label.pack(side="left", padx=(0, 12))
        info = ttk.Frame(head)
        info.pack(side="left", fill="both", expand=True)
        self.name_label = ttk.Label(info, text="Pick a character", style="Gold.TLabel",
                                    font=(theme.FACE_DISPLAY, 14, "bold"))
        self.name_label.pack(anchor="w")
        self.roles_label = ttk.Label(info, text="", style="Muted.TLabel")
        self.roles_label.pack(anchor="w", pady=(2, 0))

        add_row = ttk.Frame(info)
        add_row.pack(anchor="w", pady=(8, 0))
        ttk.Label(add_row, text="Add role:").pack(side="left")
        self.add_role_var = tk.StringVar()
        self.add_role_combo = ttk.Combobox(add_row, textvariable=self.add_role_var, state="readonly", width=16)
        self.add_role_combo.pack(side="left", padx=4)
        ttk.Button(add_row, text="+", width=3, command=self._add_role).pack(side="left")

        self.nb = ttk.Notebook(right)
        self.nb.pack(fill="both", expand=True, pady=(10, 0))
        for role in ALL_ROLES:
            frame = ttk.Frame(self.nb, padding=10)
            if role in MILITARY_ROLES:
                self._build_military_form(frame, role)
            elif role == "country_leader":
                self._build_leader_form(frame)
            else:
                self._build_raw_form(frame, role)

        self.status = ttk.Label(self, text="", style="Status.TLabel", wraplength=900, justify="left")
        self.status.pack(fill="x")

        self.on_mod_changed()

    # ---- per-role form builders ----

    def _build_military_form(self, frame, role):
        widgets = {}
        for i, key in enumerate(MILITARY_ROLES[role]):
            ttk.Label(frame, text=key.replace("_", " ")).grid(row=i, column=0, sticky="w", pady=3)
            var = tk.StringVar()
            ttk.Spinbox(frame, textvariable=var, from_=0, to=10, width=6).grid(row=i, column=1, padx=8, pady=3, sticky="w")
            widgets[key] = var

        traits_row = len(MILITARY_ROLES[role])
        ttk.Label(frame, text="Traits").grid(row=traits_row, column=0, sticky="nw", pady=(10, 0))
        traits_box = ttk.Frame(frame)
        traits_box.grid(row=traits_row, column=1, columnspan=2, sticky="w", pady=(10, 0))
        listbox = tk.Listbox(traits_box, selectmode="multiple", height=10, width=34, exportselection=False)
        tbar = ttk.Scrollbar(traits_box, orient="vertical", command=listbox.yview)
        listbox.configure(yscrollcommand=tbar.set)
        listbox.pack(side="left")
        tbar.pack(side="left", fill="y")

        ttk.Button(frame, text="Save", style="Accent.TButton",
                   command=lambda r=role: self._save_military(r)).grid(
            row=traits_row + 1, column=0, columnspan=2, sticky="w", pady=(10, 0))

        self._role_widgets[role] = {"skills": widgets, "traits": listbox}
        self.nb.add(frame, text=role.replace("_", " ").title())

    def _build_leader_form(self, frame):
        ttk.Label(frame, text="Ideology (from the leader block)").grid(row=0, column=0, sticky="w")
        var = tk.StringVar()
        combo = ttk.Combobox(frame, textvariable=var, state="readonly", width=28)
        combo.grid(row=0, column=1, padx=8, sticky="w")
        ttk.Label(frame, text="Traits (space-separated - country leader traits are usually mod-specific ideas)").grid(
            row=1, column=0, columnspan=2, sticky="w", pady=(10, 0))
        traits_var = tk.StringVar()
        ttk.Entry(frame, textvariable=traits_var, width=50).grid(row=2, column=0, columnspan=2, sticky="w")
        ttk.Button(frame, text="Save", style="Accent.TButton",
                   command=self._save_leader).grid(row=3, column=0, sticky="w", pady=(10, 0))
        self._role_widgets["country_leader"] = {"ideology": var, "ideology_combo": combo, "traits_text": traits_var}
        self.nb.add(frame, text="Country Leader")

    def _build_raw_form(self, frame, role):
        ttk.Label(
            frame, text=f"{role.replace('_', ' ').title()} has fields ({'idea_token/allowed/visible' if role == 'advisor' else 'nested skills = {...}'}) "
                       "too varied for a form — edit the raw block instead.",
            style="Muted.TLabel", wraplength=560, justify="left",
        ).pack(anchor="w")
        text = tk.Text(frame, width=64, height=16, font=("Consolas", 10))
        text.pack(fill="both", expand=True, pady=(8, 8))
        ttk.Button(frame, text="Save", style="Accent.TButton",
                   command=lambda r=role: self._save_raw(r)).pack(anchor="w")
        self._role_widgets[role] = {"raw": text}
        self.nb.add(frame, text=role.title())

    # ---- lifecycle ----

    def on_mod_changed(self):
        if state.is_loaded:
            self.header.set_status(True, state.mod_name)
        else:
            self.header.set_status(False, "no mod open")
        self._characters = {}
        self._needs_reload = True
        self._current = None
        self.listbox.delete(0, "end")
        self.count_label.config(text="")
        self.name_label.config(text="Pick a character")
        self.roles_label.config(text="")
        self.portrait_label.configure(image="")

    def on_show(self):
        if not state.is_loaded or not getattr(self, "_needs_reload", False):
            return
        self._needs_reload = False
        merged = {}
        for root in (BASE_GAME, state.mod_root):
            for tag, characters in ml.load_country_characters(root).items():
                by_id = {item["id"]: item for item in merged.get(tag, [])}
                by_id.update({item["id"]: item for item in characters})
                merged[tag] = list(by_id.values())
        self._characters = merged
        tags = sorted(merged)
        self.tag_combo["values"] = tags
        self._role_widgets["country_leader"]["ideology_combo"]["values"] = (
            country_creator.IDEOLOGIES + sorted(ideology_creator.existing_group_ids(state.mod_root))
        )
        if tags:
            self.tag_var.set(tags[0])
            self._load_tag()

    def _load_tag(self, _event=None):
        if not state.is_loaded:
            messagebox.showerror("No mod", "Open a mod first.")
            return
        tag = self.tag_var.get().strip().upper()
        chars = self._characters.get(tag, [])
        self.listbox.delete(0, "end")
        for c in chars:
            self.listbox.insert("end", f" {c['id']}  ({', '.join(c['roles']) or 'no roles'})")
        self._visible = chars
        self.count_label.config(text=f"{len(chars)} character(s) for {tag}" if tag else "")

    # ---- selection ----

    def _select(self):
        sel = self.listbox.curselection()
        if not sel:
            return
        self._current = self._visible[sel[0]]
        c = self._current
        self.name_label.config(text=state.text_for(c["name_key"], c["id"]))
        self.roles_label.config(text=", ".join(c["roles"]) or "no structured roles yet")

        missing = [r for r in ALL_ROLES if r not in c["roles"]]
        self.add_role_combo["values"] = missing
        if missing:
            self.add_role_var.set(missing[0])

        icon_path = None
        for p in c.get("portraits", []):
            icon_path = ml.resolve_texture(p, state.mod_root, state.gfx_index)
            if icon_path:
                break
        photo = image_cache.get_scaled(icon_path, PORTRAIT_SIZE) if icon_path else None
        self._icon_ref = photo
        self.portrait_label.configure(image=photo or "")

        for role in c["roles"]:
            self._load_role_into_form(c, role)

    def _char_block_text(self, c):
        with open(c["source_file"], "r", encoding="utf-8-sig", errors="ignore") as f:
            text = f.read()
        span = surgery.find_character_span(text, c["id"])
        return text[span[0]:span[1]] if span else ""

    def _load_role_into_form(self, c, role):
        block = self._char_block_text(c)
        role_span = surgery.find_role_span(block, role)
        role_text = block[role_span[0]:role_span[1]] if role_span else ""

        if role in MILITARY_ROLES:
            from app import pds_scan as scan
            widgets = self._role_widgets[role]
            for key, var in widgets["skills"].items():
                var.set(scan.scalar(role_text, key, "0"))
            traits_inner = scan.first_block(role_text, "traits") or ""
            current_traits = set(traits_inner.split())
            catalog = character_traits.traits_for_role(state.mod_root, role)
            listbox = widgets["traits"]
            listbox.delete(0, "end")
            for extra in sorted(current_traits - set(catalog)):
                listbox.insert("end", extra)      # mod-specific/unknown traits still shown
            for name in catalog:
                listbox.insert("end", name)
            for i in range(listbox.size()):
                if listbox.get(i).strip() in current_traits:
                    listbox.selection_set(i)
        elif role == "country_leader":
            from app import pds_scan as scan
            widgets = self._role_widgets["country_leader"]
            widgets["ideology"].set(scan.scalar(role_text, "ideology", ""))
            traits_inner = scan.first_block(role_text, "traits") or ""
            widgets["traits_text"].set(traits_inner.strip())
        else:
            self._role_widgets[role]["raw"].delete("1.0", "end")
            self._role_widgets[role]["raw"].insert("1.0", role_text.strip())

    # ---- saving ----

    def _confirm_and_apply(self, role, **kwargs):
        c = self._current
        if not c:
            messagebox.showerror("Nothing selected", "Pick a character first.")
            return
        source = c["source_file"]
        if os.path.normcase(source).startswith(os.path.normcase(BASE_GAME) + os.sep):
            relative = os.path.relpath(source, BASE_GAME)
            destination = os.path.join(state.mod_root, relative)
            try:
                os.makedirs(os.path.dirname(destination), exist_ok=True)
                shutil.copy2(source, destination)
            except OSError as exc:
                messagebox.showerror("Couldn't create editable copy", str(exc))
                return
            c["source_file"] = destination
        ok = surgery.apply_role_edits(c["source_file"], c["id"], role, **kwargs)
        if not ok:
            messagebox.showerror("Not found", f"Couldn't locate '{c['id']}' in its source file.")
            return
        if role not in c["roles"]:
            c["roles"].append(role)
            self.roles_label.config(text=", ".join(c["roles"]))
        self.status.config(text=f"Saved {role} for {c['id']} (backup kept as .bak).")

    def _save_military(self, role):
        widgets = self._role_widgets[role]
        scalars = {k: v.get().strip() for k, v in widgets["skills"].items()}
        selected = [widgets["traits"].get(i) for i in widgets["traits"].curselection()]
        self._confirm_and_apply(role, scalars=scalars, traits=selected)

    def _save_leader(self):
        widgets = self._role_widgets["country_leader"]
        ideology = widgets["ideology"].get().strip()
        traits = widgets["traits_text"].get().strip()
        body = (f"ideology = {ideology}\n" if ideology else "") + (f"traits = {{ {traits} }}" if traits else "")
        self._confirm_and_apply("country_leader", raw_body=body)

    def _save_raw(self, role):
        text = self._role_widgets[role]["raw"].get("1.0", "end").strip()
        if text.count("{") != text.count("}"):
            messagebox.showerror("Unbalanced braces", "Fix the braces before saving.")
            return
        self._confirm_and_apply(role, raw_body=text)

    def _add_role(self):
        role = self.add_role_var.get()
        if not role or not self._current:
            return
        for i, name in enumerate(ALL_ROLES):
            if name == role:
                self.nb.select(i)
                break
        self._load_role_into_form(self._current, role) if role in self._current["roles"] else None
