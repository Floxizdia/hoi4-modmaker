"""Loc Coverage tab: which languages are missing which keys, and a one-click
fill so non-English players see readable placeholder text instead of a raw
key like `TUR_focus_x` on screen.
"""

import os
import tkinter as tk
from tkinter import ttk, messagebox

from app.state import state
from app import loc_coverage
from app import mod_export
from app import theme, ui_kit


class LocCoverageTab(ttk.Frame):
    def __init__(self, master):
        super().__init__(master, padding=12)
        self._english = {}
        self._report = {}
        self._build()
        state.subscribe(self.on_mod_changed)

    def _build(self):
        self.header = ui_kit.PageHeader(
            self, "Loc Coverage",
            "Which loc keys your mod's focuses/events/decisions/ideas actually reference have no text yet - the id shows raw in-game until you fill it in.", help_key="loc_coverage")

        top = ttk.Frame(self)
        top.pack(fill="x")
        ttk.Button(top, text="Scan Coverage", style="Accent.TButton",
                   command=self._scan).pack(side="left")
        self.total_label = ttk.Label(top, text="", style="Muted.TLabel")
        self.total_label.pack(side="left", padx=10)
        ttk.Label(
            top, text="English is treated as the source of truth — every generator in this "
                     "tool writes it first, so a key missing elsewhere is almost always an "
                     "oversight, not a choice.",
            style="Muted.TLabel",
        ).pack(side="left", padx=14)

        body = ttk.Frame(self)
        body.pack(fill="both", expand=True, pady=8)

        left = ttk.Frame(body, width=260)
        left.pack(side="left", fill="y", padx=(0, 8))
        left.pack_propagate(False)
        self.lang_tree = ttk.Treeview(left, columns=("missing",), show="headings", height=10)
        self.lang_tree.heading("#0", text="")
        self.lang_tree.heading("missing", text="Missing / Total")
        self.lang_tree.column("missing", width=240)
        self.lang_tree.pack(fill="both", expand=True)
        self.lang_tree.bind("<<TreeviewSelect>>", lambda e: self._show_missing())

        right = ttk.Frame(body)
        right.pack(side="left", fill="both", expand=True)
        cols = ("key", "english")
        self.tree = ttk.Treeview(right, columns=cols, show="headings")
        self.tree.heading("key", text="Missing key")
        self.tree.heading("english", text="English text")
        self.tree.column("key", width=260)
        self.tree.column("english", width=520)
        bar = ttk.Scrollbar(right, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=bar.set)
        self.tree.pack(side="left", fill="both", expand=True)
        bar.pack(side="right", fill="y")

        btns = ttk.Frame(self)
        btns.pack(fill="x")
        self.fill_btn = ttk.Button(btns, text="Fill Missing (copy English text)",
                                   command=self._fill, state="disabled")
        self.fill_btn.pack(side="left")
        ttk.Button(btns, text="Fix Untranslated Keys (english)",
                   style="Accent.TButton", command=self._fill_english).pack(side="left", padx=6)
        self.status = ttk.Label(btns, text="", style="Status.TLabel", wraplength=900, justify="left")
        self.status.pack(side="left", padx=10)

        self.on_mod_changed()

    # ---- lifecycle ----

    def on_mod_changed(self):
        if state.is_loaded:
            self.header.set_status(True, state.mod_name)
        else:
            self.header.set_status(False, "no mod open")
        self._english = {}
        self._report = {}
        self.lang_tree.delete(*self.lang_tree.get_children())
        self.tree.delete(*self.tree.get_children())
        self.fill_btn.configure(state="disabled")

    def on_show(self):
        if state.is_loaded and not self._report:
            self._scan()

    def _fill_english(self):
        """The severe case coverage_report can't see: a key the mod's own
        content references that no language defines at all, so it renders as
        a raw id for everyone, english players included."""
        if not state.is_loaded:
            messagebox.showerror("No mod", "Open a mod first.")
            return
        self.status.config(text="Scanning what the mod references...")
        self.update_idletasks()
        missing = loc_coverage.missing_english_keys(state.mod_root)
        if not missing:
            self.status.config(text="Nothing to fix — every key the mod references already has english text.")
            return

        rows = []
        for k, (_owner, text) in sorted(missing.items())[:8]:
            note = "   (left blank: it's a description)" if not text else ""
            rows.append(f'  {k}  ->  "{text}"{note}')
        sample = "\n".join(rows)
        if len(missing) > 8:
            sample += f"\n  ... and {len(missing) - 8} more"

        if not messagebox.askyesno(
            "Write placeholder english text?",
            f"{len(missing)} key(s) are referenced by this mod but have no english text, "
            "so they show as raw ids in game.\n\n"
            f"{sample}\n\n"
            "Placeholders are written into their own file so your real loc files aren't touched. "
            "Continue?"):
            return

        path = loc_coverage.write_english_fill(state.mod_root, state.mod_name, missing)
        self.status.config(
            text=f"Wrote {len(missing)} placeholder key(s) to {os.path.basename(path)}. "
                 "Edit that file to replace the generated names with real text.")

    # ---- scanning ----

    def _scan(self):
        if not state.is_loaded:
            messagebox.showerror("No mod", "Open a mod first.")
            return
        self._english, self._report = loc_coverage.coverage_report(state.mod_root)
        self.lang_tree.delete(*self.lang_tree.get_children())
        for lang, info in self._report.items():
            missing = len(info["missing"])
            self.lang_tree.insert("", "end", iid=lang, text=lang,
                                  values=(f"{missing} / {info['total']}",),
                                  tags=("gap",) if missing else ())
        self.lang_tree.tag_configure("gap", foreground=theme.AMBER)
        self.total_label.config(text=f"{len(self._english)} English key(s) found")
        self.tree.delete(*self.tree.get_children())
        self.fill_btn.configure(state="disabled")

    def _show_missing(self):
        sel = self.lang_tree.selection()
        self.tree.delete(*self.tree.get_children())
        if not sel:
            self.fill_btn.configure(state="disabled")
            return
        lang = sel[0]
        missing = self._report[lang]["missing"]
        for key, text in sorted(missing.items()):
            self.tree.insert("", "end", iid=key, values=(key, text))
        self.fill_btn.configure(state="normal" if missing else "disabled")

    def _fill(self):
        sel = self.lang_tree.selection()
        if not sel:
            return
        lang = sel[0]
        missing = self._report[lang]["missing"]
        if not missing:
            return
        if not messagebox.askyesno(
            "Fill with English text?",
            f"Write {len(missing)} key(s) into a new localisation/{lang}/*_coverage_fill_l_{lang}.yml "
            "file, using the English text as a placeholder?\n\n"
            "This never touches an existing translation file — it only adds what's missing."):
            return
        path = loc_coverage.write_fill(state.mod_root, state.mod_name, lang, missing)
        mod_export.record_created(state.mod_root, [path])
        self.status.config(text=f"Wrote {len(missing)} key(s) to {os.path.relpath(path, state.mod_root)}")
        self._scan()
        self.lang_tree.selection_set(lang)
        self._show_missing()
