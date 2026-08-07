"""Translation tab: English on the left, your translation on the right.

Loc Coverage answers "which keys is this language missing"; this is where
they actually get translated. Edits are held until Save so a half-typed
line never reaches the file.
"""

import tkinter as tk
from tkinter import messagebox, ttk

from app.state import state
from app import mod_export, translation
from app import theme, ui_kit


class TranslationTab(ttk.Frame):
    def __init__(self, master):
        super().__init__(master, padding=12)
        self.pairs = []          # [(key, english, current)]
        self.edits = {}          # key -> new text, unsaved
        self._rows = []          # row index -> key, matching the tree
        self._build()
        state.subscribe(self.on_mod_changed)

    # ---- layout ----

    def _build(self):
        self.header = ui_kit.PageHeader(
            self, "Translation",
            "Every localisation key with its English text beside the target language, so a mod "
            "can be translated in one place instead of hand-editing .yml files.",
            help_key="translation")

        top = ttk.Frame(self)
        top.pack(fill="x", pady=(0, 6))
        ttk.Label(top, text="Language:").pack(side="left")
        self.lang_var = tk.StringVar(value="french")
        combo = ttk.Combobox(top, textvariable=self.lang_var, state="readonly",
                             width=14, values=translation.languages())
        combo.pack(side="left", padx=4)
        combo.bind("<<ComboboxSelected>>", lambda e: self._load())
        ttk.Button(top, text="Load", style="Accent.TButton", command=self._load).pack(side="left")

        self.only_todo = tk.BooleanVar(value=True)
        ttk.Checkbutton(top, text="Only untranslated", variable=self.only_todo,
                        command=self._refresh_tree).pack(side="left", padx=12)
        ttk.Label(top, text="Find:").pack(side="left")
        self.filter_var = tk.StringVar()
        entry = ttk.Entry(top, textvariable=self.filter_var, width=18)
        entry.pack(side="left", padx=4)
        entry.bind("<KeyRelease>", lambda e: self._refresh_tree())
        self.progress_label = ttk.Label(top, text="", style="Muted.TLabel")
        self.progress_label.pack(side="left", padx=10)

        self.tree = ttk.Treeview(self, columns=("key", "english", "translated"),
                                 show="headings", height=18)
        self.tree.heading("key", text="key")
        self.tree.heading("english", text="english")
        self.tree.heading("translated", text="translation")
        self.tree.column("key", width=230)
        self.tree.column("english", width=430)
        self.tree.column("translated", width=430)
        self.tree.pack(fill="both", expand=True)
        self.tree.tag_configure("todo", foreground=theme.MUTED)
        self.tree.tag_configure("done", foreground=theme.GREEN)
        self.tree.bind("<<TreeviewSelect>>", lambda e: self._pick())

        editor = ui_kit.Section(self, "Selected key")
        editor.pack(fill="x", pady=(8, 0))
        self.key_label = ttk.Label(editor.body, text="—", style="Gold.TLabel")
        self.key_label.pack(anchor="w")
        self.english_label = ttk.Label(editor.body, text="", style="Muted.TLabel",
                                       wraplength=1000, justify="left")
        self.english_label.pack(anchor="w", pady=(2, 6))
        self.entry_var = tk.StringVar()
        self.entry = ttk.Entry(editor.body, textvariable=self.entry_var)
        self.entry.pack(fill="x")
        self.entry.bind("<Return>", lambda e: self._apply_and_next())

        buttons = ttk.Frame(editor.body)
        buttons.pack(fill="x", pady=(6, 0))
        ttk.Button(buttons, text="Apply & next  (Enter)",
                   command=self._apply_and_next).pack(side="left")
        ttk.Button(buttons, text="Copy English", command=self._copy_english).pack(side="left", padx=6)
        ttk.Button(buttons, text="Save to mod", style="Accent.TButton",
                   command=self._save).pack(side="left", padx=12)

        self.status = ttk.Label(self, text="", style="Status.TLabel",
                                wraplength=1000, justify="left")
        self.status.pack(fill="x", pady=(6, 0))

        self.on_mod_changed()

    # ---- lifecycle ----

    def on_mod_changed(self):
        if state.is_loaded:
            self.header.set_status(True, state.mod_name)
        else:
            self.header.set_status(False, "no mod open")
        self.pairs = []
        self.edits = {}
        if hasattr(self, "tree"):
            self.tree.delete(*self.tree.get_children())
            self.progress_label.config(text="")

    def on_show(self):
        self.on_mod_changed()

    @property
    def is_dirty(self):
        return bool(self.edits)

    # ---- loading ----

    def _load(self):
        if not state.is_loaded:
            messagebox.showerror("No mod", "Open a mod first.")
            return
        if self.edits and not messagebox.askyesno(
                "Discard edits?",
                f"{len(self.edits)} translation(s) haven't been saved. Discard them?"):
            return
        self.edits = {}
        self.pairs = translation.load_pairs(state.mod_root, self.lang_var.get())
        self._refresh_tree()
        if not self.pairs:
            self.status.config(text="No English keys found — this mod has no "
                                    "localisation/english files yet.")

    def _current(self, key, english, current):
        return self.edits.get(key, current)

    def _refresh_tree(self):
        self.tree.delete(*self.tree.get_children())
        self._rows = []
        needle = self.filter_var.get().strip().lower()
        for key, english, current in self.pairs:
            text = self._current(key, english, current)
            todo = translation.is_untranslated(english, text)
            if self.only_todo.get() and not todo:
                continue
            if needle and needle not in key.lower() and needle not in english.lower():
                continue
            self.tree.insert("", "end", values=(key, english, text),
                             tags=("todo" if todo else "done",))
            self._rows.append(key)

        merged = [(k, e, self._current(k, e, c)) for k, e, c in self.pairs]
        done, total = translation.progress(merged)
        unsaved = f" · {len(self.edits)} unsaved" if self.edits else ""
        self.progress_label.config(
            text=f"{done}/{total} translated{unsaved}" if total else "")

    # ---- editing ----

    def _pick(self):
        selection = self.tree.selection()
        if not selection:
            return
        key, english, text = self.tree.item(selection[0], "values")
        self.key_label.config(text=key)
        self.english_label.config(text=english)
        self.entry_var.set(text)
        self.entry.focus_set()

    def _copy_english(self):
        self.entry_var.set(self.english_label.cget("text"))

    def _apply_and_next(self):
        selection = self.tree.selection()
        if not selection:
            return
        item = selection[0]
        key = self.tree.item(item, "values")[0]
        self.edits[key] = self.entry_var.get()

        # keep the row where it is rather than rebuilding the whole tree:
        # with "only untranslated" ticked a rebuild would pull the row out
        # from under the cursor mid-edit
        english = self.tree.item(item, "values")[1]
        todo = translation.is_untranslated(english, self.edits[key])
        self.tree.item(item, values=(key, english, self.edits[key]),
                       tags=("todo" if todo else "done",))

        following = self.tree.next(item)
        if following:
            self.tree.selection_set(following)
            self.tree.see(following)
            self._pick()
        merged = [(k, e, self._current(k, e, c)) for k, e, c in self.pairs]
        done, total = translation.progress(merged)
        self.progress_label.config(text=f"{done}/{total} translated · {len(self.edits)} unsaved")

    # ---- saving ----

    def _save(self):
        if not state.is_loaded:
            messagebox.showerror("No mod", "Open a mod first.")
            return
        if not self.edits:
            self.status.config(text="Nothing to save — no translations have been typed yet.")
            return
        lang = self.lang_var.get()
        try:
            path = translation.save(state.mod_root, state.mod_name, lang, self.edits)
        except OSError as exc:
            messagebox.showerror("Save failed", str(exc))
            return
        mod_export.record_created(state.mod_root, [path])
        saved = len(self.edits)
        self.edits = {}
        # before reloading, not after: content_changed notifies every screen,
        # and this one's own handler clears the list it is about to rebuild
        state.content_changed()
        self.pairs = translation.load_pairs(state.mod_root, lang)
        self._refresh_tree()
        self.status.config(text=f"{saved} translation(s) written to {path}.")
