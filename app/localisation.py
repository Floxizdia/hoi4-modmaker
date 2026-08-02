"""Localisation tab: shows every loc key collected while building focuses,
events and decisions, lets you add manual entries, and exports a
localisation/english/<mod>_l_english.yml file."""

import os
import re
import glob
import tkinter as tk
from tkinter import ttk, messagebox

from app.state import state
from app import ui_kit

SAFE_FILENAME = re.compile(r"[^a-z0-9_]+")

# every language folder the base game ships; text is copied from english as
# a placeholder so nothing shows up as a raw key for non-english players
HOI4_LANGUAGES = ["english", "braz_por", "french", "german", "japanese",
                  "korean", "polish", "russian", "simp_chinese", "spanish"]


class LocalisationTab(ttk.Frame):
    def __init__(self, master):
        super().__init__(master, padding=12)
        self._build()

    def _build(self):
        self.header = ui_kit.PageHeader(
            self, "Localisation",
            "Every loc key used anywhere in the mod, in one searchable table you can edit directly - writes real localisation/<language>/*.yml.", help_key="loc")

        top = ttk.Frame(self)
        top.pack(fill="x")
        ttk.Label(top, text="Key").pack(side="left")
        self.key_var = tk.StringVar()
        ttk.Entry(top, textvariable=self.key_var, width=30).pack(side="left", padx=6)
        ttk.Label(top, text="Text").pack(side="left")
        self.text_var = tk.StringVar()
        ttk.Entry(top, textvariable=self.text_var, width=40).pack(side="left", padx=6)
        ttk.Button(top, text="Add / Update", command=self._add).pack(side="left", padx=6)

        cols = ("key", "text")
        self.tree = ttk.Treeview(self, columns=cols, show="headings", height=16)
        self.tree.heading("key", text="key")
        self.tree.heading("text", text="text")
        self.tree.column("key", width=200)
        self.tree.column("text", width=400)
        self.tree.pack(fill="both", expand=True, pady=10)
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

        btns = ttk.Frame(self)
        btns.pack(fill="x")
        ttk.Button(btns, text="Refresh", command=self.refresh).pack(side="left", padx=4)
        ttk.Button(btns, text="Delete Selected", command=self._delete).pack(side="left", padx=4)
        self.show_mod_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            btns, text="Also show the mod's existing keys (read-only)",
            variable=self.show_mod_var, command=self.refresh,
        ).pack(side="left", padx=12)
        ttk.Button(btns, text="Export l_english.yml", command=self._export).pack(side="right", padx=4)
        ttk.Button(btns, text="Generate All Languages", command=self._export_all_langs).pack(side="right", padx=4)
        ttk.Button(btns, text="Mirror Existing to All Languages",
                   command=self._mirror_existing_langs).pack(side="right", padx=4)

        self.status = ttk.Label(self, text="", foreground="#2a7a2a")
        self.status.pack(fill="x", pady=(6, 0))

        self.refresh()

    def refresh(self):
        if state.is_loaded:
            self.header.set_status(True, state.mod_name)
        else:
            self.header.set_status(False, "no mod open")

        self.tree.delete(*self.tree.get_children())
        for key, text in sorted(state.loc_entries.items()):
            self.tree.insert("", "end", iid=key, values=(key, text))

        if self.show_mod_var.get():
            for key, text in sorted(state.mod_loc.items()):
                if key in state.loc_entries:
                    continue
                self.tree.insert("", "end", iid="mod::" + key, values=(key, text), tags=("modkey",))
            self.tree.tag_configure("modkey", foreground="#888")

    def _on_select(self, _event=None):
        sel = self.tree.selection()
        if not sel:
            return
        iid = sel[0]
        # rows sourced from the mod are prefixed so their keys can collide
        # with session edits without clashing in the tree widget
        key = iid[5:] if iid.startswith("mod::") else iid
        self.key_var.set(key)
        self.text_var.set(state.text_for(key, ""))

    def _add(self):
        key = self.key_var.get().strip()
        text = self.text_var.get()
        if not key:
            messagebox.showerror("Missing key", "A loc key is required.")
            return
        state.add_loc(key, text)
        self.refresh()

    def _delete(self):
        sel = self.tree.selection()
        if not sel:
            return
        for iid in sel:
            if iid.startswith("mod::"):
                continue  # belongs to the mod's own files, not ours to drop
            state.loc_entries.pop(iid, None)
        self.refresh()

    def _export(self):
        if not state.is_loaded:
            messagebox.showerror("No mod folder", "Open a mod, or create one in the Settings tab first.")
            return
        if not state.loc_entries:
            messagebox.showerror("Nothing to export", "No localisation entries yet.")
            return

        name = SAFE_FILENAME.sub("_", state.mod_name.lower()).strip("_") or "my_mod"
        lines = ["l_english:"]
        for key, text in sorted(state.loc_entries.items()):
            safe_text = text.replace('"', '\\"')
            lines.append(f' {key}:0 "{safe_text}"')

        out_dir = state.ensure_dir("localisation", "english")
        out_path = os.path.join(out_dir, f"{name}_l_english.yml")
        with open(out_path, "w", encoding="utf-8-sig") as fh:
            fh.write("\n".join(lines) + "\n")

        self.status.config(text=f"Exported {len(state.loc_entries)} keys to {out_path}")

    def _mirror_existing_langs(self):
        """Mirror the mod's whole existing localisation/english/ folder into
        every other language, file for file, copying the english text as a
        placeholder. Different from 'Export all languages', which only
        writes the keys created in this session - this covers a mod that
        already has hundreds of english keys written by earlier sessions or
        by hand, which is the case that actually leaves players on other
        languages staring at raw ids."""
        if not state.is_loaded:
            messagebox.showerror("No mod folder", "Open a mod first.")
            return
        eng_dir = os.path.join(state.mod_root, "localisation", "english")
        if not os.path.isdir(eng_dir):
            messagebox.showerror("No english localisation",
                                 "This mod has no localisation/english folder to mirror.")
            return
        sources = [p for p in glob.glob(os.path.join(eng_dir, "**", "*.yml"), recursive=True)]
        if not sources:
            messagebox.showerror("No english localisation", "No .yml files found under localisation/english.")
            return

        targets = [lang for lang in HOI4_LANGUAGES if lang != "english"]
        if not messagebox.askyesno(
            "Generate translation skeletons?",
            f"Mirror {len(sources)} english file(s) into {len(targets)} other language(s)?\n\n"
            "English text is copied as a placeholder so nothing shows as a raw id in game; "
            "translate the copies later. Existing files in those folders are NOT overwritten."):
            return

        written = skipped = 0
        for src in sources:
            rel = os.path.relpath(src, eng_dir)
            try:
                with open(src, "r", encoding="utf-8-sig", errors="ignore") as fh:
                    text = fh.read()
            except OSError:
                continue
            for lang in targets:
                out_rel = rel.replace("l_english", f"l_{lang}")
                out_path = os.path.join(state.mod_root, "localisation", lang, out_rel)
                if os.path.exists(out_path):
                    skipped += 1
                    continue
                os.makedirs(os.path.dirname(out_path), exist_ok=True)
                # only the header line names the language; the keys and text
                # stay byte-identical so nothing else can drift
                converted = text.replace("l_english:", f"l_{lang}:", 1)
                with open(out_path, "w", encoding="utf-8-sig") as fh:
                    fh.write(converted)
                written += 1

        self.status.config(
            text=f"Wrote {written} skeleton file(s) across {len(targets)} languages"
                 + (f", skipped {skipped} that already existed." if skipped else ".")
        )

    def _export_all_langs(self):
        """Write the session's entries to every language folder, copying the
        english text as a placeholder - players on other languages then see
        readable text instead of raw keys, and translators have a file to
        start from."""
        if not state.is_loaded:
            messagebox.showerror("No mod folder", "Open a mod, or create one in the Settings tab first.")
            return
        if not state.loc_entries:
            messagebox.showerror("Nothing to export", "No localisation entries yet.")
            return

        name = SAFE_FILENAME.sub("_", state.mod_name.lower()).strip("_") or "my_mod"
        written = 0
        for lang in HOI4_LANGUAGES:
            lines = [f"l_{lang}:"]
            for key, text in sorted(state.loc_entries.items()):
                safe_text = text.replace('"', '\\"')
                lines.append(f' {key}:0 "{safe_text}"')
            out_dir = state.ensure_dir("localisation", lang)
            out_path = os.path.join(out_dir, f"{name}_l_{lang}.yml")
            with open(out_path, "w", encoding="utf-8-sig") as fh:
                fh.write("\n".join(lines) + "\n")
            written += 1

        self.status.config(
            text=f"Wrote {len(state.loc_entries)} keys to {written} languages "
                 f"(english text copied as placeholder — translate the files under localisation/<lang>/ later)"
        )
