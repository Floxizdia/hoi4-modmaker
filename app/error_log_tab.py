"""Error Log tab: reads the game's own logs/error.log after you've actually
launched and played the mod - what HOI4 itself said went wrong, not just
what the Validator can catch by reading files in isolation. If a mod
crashes or an event/effect silently fails in game, this is where to look."""

import tkinter as tk
from tkinter import ttk

from app.state import state
from app import error_log
from app import theme, ui_kit


class ErrorLogTab(ttk.Frame):
    def __init__(self, master):
        super().__init__(master, padding=ui_kit.PAD_PAGE)
        self._errors = []
        self._build()
        state.subscribe(self.on_mod_changed)

    def _build(self):
        self.header = ui_kit.PageHeader(
            self, "Error Log",
            "Reads the game's own logs/error.log from your last play session - crashes, failed "
            "events, and script errors HOI4 itself reported, cross-checked against this mod's files.",
            help_key="error_log")

        top = ttk.Frame(self)
        top.pack(fill="x", pady=(0, 8))
        ttk.Button(top, text="Read Log Now", style="Accent.TButton", command=self._scan).pack(side="left")
        self.only_mod_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(top, text="Only show errors touching this mod's files",
                        variable=self.only_mod_var, command=self._refresh_tree).pack(side="left", padx=12)
        self.summary = ttk.Label(top, text="", style="Muted.TLabel")
        self.summary.pack(side="left", padx=12)

        body = ttk.Frame(self)
        body.pack(fill="both", expand=True)

        self.tree = ttk.Treeview(body, columns=("time", "mod_file", "message"), show="headings", height=20)
        self.tree.heading("time", text="time")
        self.tree.heading("mod_file", text="mod file")
        self.tree.heading("message", text="message")
        self.tree.column("time", width=70)
        self.tree.column("mod_file", width=220)
        self.tree.column("message", width=700)
        self.tree.pack(fill="both", expand=True)
        self.tree.tag_configure("mod", foreground=theme.GREEN)
        self.tree.bind("<<TreeviewSelect>>", lambda e: self._show_hint())

        self.hint_label = ttk.Label(self, text="", style="Muted.TLabel", foreground=theme.TEXT,
                                     wraplength=1000, justify="left")
        self.hint_label.pack(anchor="w", pady=(8, 0))

    def on_mod_changed(self):
        if state.is_loaded:
            self.header.set_status(True, state.mod_name)
        else:
            self.header.set_status(False, "no mod open")

    def on_show(self):
        self.on_mod_changed()

    def _scan(self):
        path = error_log.log_path()
        if not path:
            self.summary.config(text="Couldn't find logs/error.log — is HOI4 installed and has it "
                                      "been run at least once?", foreground=theme.RED)
            self._errors = []
            self._refresh_tree()
            return
        mod_root = state.mod_root if state.is_loaded else None
        self._errors = error_log.parse_errors(path, mod_root=mod_root)
        mod_hits = sum(1 for e in self._errors if e[3])
        self.summary.config(
            text=f"{len(self._errors)} error(s) in the log ({mod_hits} touching this mod). "
                 f"Read from: {path}", foreground=theme.MUTED)
        self._refresh_tree()

    def _refresh_tree(self):
        self.tree.delete(*self.tree.get_children())
        only_mod = self.only_mod_var.get()
        for ts, source, message, mod_relevant, mod_file in self._errors:
            if only_mod and not mod_relevant:
                continue
            self.tree.insert("", "end", values=(ts, mod_file or "", message),
                              tags=("mod",) if mod_relevant else ())

    def _show_hint(self):
        sel = self.tree.selection()
        if not sel:
            self.hint_label.config(text="")
            return
        message = self.tree.item(sel[0], "values")[2]
        hint = error_log.hint_for(message)
        self.hint_label.config(text=hint or "")
