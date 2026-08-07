"""Error Log tab: reads the game's own logs/error.log after you've actually
launched and played the mod - what HOI4 itself said went wrong, not just
what the Validator can catch by reading files in isolation. If a mod
crashes or an event/effect silently fails in game, this is where to look.

Test Play closes the loop: it starts the game with only this mod enabled
and in -debug mode, waits for it to quit, and then shows exactly the
errors from that session rather than everything the log has ever held."""

import os
import threading
import tkinter as tk
from tkinter import messagebox, ttk

from app.state import state
from app import error_log, test_play
from app import theme, ui_kit


class ErrorLogTab(ttk.Frame):
    def __init__(self, master):
        super().__init__(master, padding=ui_kit.PAD_PAGE)
        self._errors = []
        self._session_offset = None   # byte position in error.log at launch
        self._running = False
        self._build()
        state.subscribe(self.on_mod_changed)

    def _build(self):
        self.header = ui_kit.PageHeader(
            self, "Test Play & Errors",
            "Start the game with this mod in debug mode, then read what HOI4 itself reported - "
            "crashes, failed events and script errors, cross-checked against this mod's files.",
            help_key="error_log")

        top = ttk.Frame(self)
        top.pack(fill="x", pady=(0, 8))
        self.play_button = ttk.Button(top, text="Test Play", style="Accent.TButton",
                                       command=self._test_play)
        self.play_button.pack(side="left")
        ui_kit.attach_tooltip(self.play_button,
                       "Starts HOI4 in debug mode with only this mod enabled, then shows the errors "
                       "from that session. Your own mod selection is put back when the game quits.")
        ttk.Button(top, text="Read Log Now", command=self._scan).pack(side="left", padx=(8, 0))
        self.only_mod_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(top, text="Only show errors touching this mod's files",
                        variable=self.only_mod_var, command=self._refresh_tree).pack(side="left", padx=12)
        self.session_var = tk.BooleanVar(value=False)
        self.session_check = ttk.Checkbutton(top, text="Only the last test run",
                                             variable=self.session_var, command=self._scan,
                                             state="disabled")
        self.session_check.pack(side="left")
        self.summary = ttk.Label(top, text="", style="Muted.TLabel")
        self.summary.pack(side="left", padx=12)

        body = ttk.Frame(self)
        body.pack(fill="both", expand=True)

        self.tree = ttk.Treeview(body, columns=("time", "count", "mod_file", "message"),
                                  show="headings", height=20)
        self.tree.heading("time", text="first seen")
        self.tree.heading("count", text="times")
        self.tree.heading("mod_file", text="mod file")
        self.tree.heading("message", text="message")
        self.tree.column("time", width=75, anchor="center")
        self.tree.column("count", width=55, anchor="e")
        self.tree.column("mod_file", width=220)
        self.tree.column("message", width=660)
        self.tree.pack(fill="both", expand=True)
        self.tree.tag_configure("mod", foreground=theme.GREEN)
        self.tree.bind("<<TreeviewSelect>>", lambda e: self._show_hint())
        self.tree.bind("<Double-Button-1>", lambda e: self._open_in_code())

        self.tip = ttk.Label(
            self, text="Green rows reference this mod's own files - double-click one to open it "
                       "in the Code screen at that line.", style="Muted.TLabel")
        self.tip.pack(anchor="w", pady=(6, 0))

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

    # ---- test play ----

    def _test_play(self):
        if self._running:
            return
        if not state.is_loaded:
            messagebox.showinfo("Test Play", "Open a mod first.", parent=self)
            return
        entry = test_play.entry_for_mod(state.mod_root, state.mod_name)
        if entry is None:
            # the mod has never been exported, so the launcher can't see it.
            # Sending the user away to do that by hand put the slow half of
            # the edit-test loop back on them, so offer to do it here.
            if not messagebox.askokcancel(
                    "Export first?",
                    f"\"{state.mod_name}\" isn't in the launcher's mod folder yet, so the game "
                    "can't load it.\n\nExport your own files as a submod now and then start "
                    "the game?", parent=self):
                return
            self.summary.config(text="Exporting...", foreground=theme.MUTED)
            self.update_idletasks()
            try:
                entry = test_play.export_for_test(state.mod_root, state.mod_name)
            except (RuntimeError, OSError) as exc:
                self.summary.config(text="", foreground=theme.MUTED)
                messagebox.showerror("Test Play", str(exc), parent=self)
                return

        if not messagebox.askokcancel(
                "Test Play",
                f"Start Hearts of Iron IV in debug mode with only \"{state.mod_name}\" enabled?\n\n"
                "Your usual mod selection is restored as soon as the game quits.\n\n"
                "Close the game when you're done testing and the errors from that session will "
                "show up here.", parent=self):
            return

        # taken before launch: the game appends to error.log, so anything past
        # this point belongs to the run we're about to start
        offset = test_play.log_size()
        try:
            process, restore = test_play.launch(state.mod_root, state.mod_name, entry=entry)
        except RuntimeError as exc:
            messagebox.showerror("Test Play", str(exc), parent=self)
            return

        self._running = True
        self._session_offset = offset
        self.play_button.config(state="disabled", text="Game running...")
        self.summary.config(text="Waiting for the game to quit...", foreground=theme.MUTED)

        def wait():
            process.wait()
            restore()
            # back to the Tk thread; the game runs for however long the user
            # plays, so this can't block the UI. The window can be gone by
            # then - the restore above is what actually matters, and it has
            # already happened.
            try:
                self.after(0, self._play_finished)
            except tk.TclError:
                pass

        threading.Thread(target=wait, daemon=True).start()

    def _play_finished(self):
        if not self.winfo_exists():
            return
        self._running = False
        self.play_button.config(state="normal", text="Test Play")
        self.session_check.config(state="normal")
        self.session_var.set(True)
        self._scan()

    def _scan(self):
        path = error_log.log_path()
        if not path:
            self.summary.config(text="Couldn't find logs/error.log — is HOI4 installed and has it "
                                      "been run at least once?", foreground=theme.RED)
            self._errors = []
            self._refresh_tree()
            return
        mod_root = state.mod_root if state.is_loaded else None
        session_only = self.session_var.get() and self._session_offset is not None
        self._errors = error_log.parse_errors(
            path, mod_root=mod_root,
            start_offset=self._session_offset if session_only else 0)
        mod_hits = sum(1 for e in self._errors if e[3])
        occurrences = sum(e[5] for e in self._errors)
        scope = "from your last test run" if session_only else "in the log"
        repeats = f" from {occurrences} lines" if occurrences != len(self._errors) else ""
        self.summary.config(
            text=f"{len(self._errors)} distinct error(s) {scope}{repeats} "
                 f"({mod_hits} touching this mod). Read from: {path}",
            foreground=theme.MUTED)
        self._refresh_tree()

    def _refresh_tree(self):
        self.tree.delete(*self.tree.get_children())
        only_mod = self.only_mod_var.get()
        for ts, _source, message, mod_relevant, mod_file, count in self._errors:
            if only_mod and not mod_relevant:
                continue
            self.tree.insert("", "end", values=(ts, count, mod_file or "", message),
                              tags=("mod",) if mod_relevant else ())

    def _open_in_code(self):
        """Green rows already name the file and line the game complained
        about - double-clicking takes you straight there instead of making
        you find it by hand in the Code screen."""
        sel = self.tree.selection()
        if not sel or not state.is_loaded:
            return
        mod_file = self.tree.item(sel[0], "values")[2]
        if not mod_file:
            self.hint_label.config(
                text="That error doesn't name a file in this mod, so there's nowhere to jump to.")
            return

        rel, _, line_text = mod_file.partition(":")
        path = os.path.join(state.mod_root, rel)
        if not os.path.isfile(path):
            self.hint_label.config(text=f"Can't open {rel} - the file isn't there any more.")
            return
        line = int(line_text) if line_text.isdigit() else None
        from app.code_editor import open_in_code
        open_in_code(self, path, line=line)

    def _show_hint(self):
        sel = self.tree.selection()
        if not sel:
            self.hint_label.config(text="")
            return
        message = self.tree.item(sel[0], "values")[3]
        hint = error_log.hint_for(message)
        self.hint_label.config(text=hint or "")
