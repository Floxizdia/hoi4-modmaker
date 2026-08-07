"""Guides screen: pick a job, get the screens it needs in order.

Clicking a step opens that screen, so the guide is a way to navigate rather
than a page of instructions to read and then act on from memory. Ticks are
remembered per mod, because "where was I" is the actual question after
coming back to a mod a week later.
"""

import json
import os
import tkinter as tk
from tkinter import ttk

from app.state import state
from app import guides
from app import recent
from app import theme, ui_kit

PROGRESS_FILE = os.path.join(recent.CONFIG_DIR, "guide_progress.json")


def _load_progress():
    try:
        with open(PROGRESS_FILE, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _save_progress(data):
    try:
        os.makedirs(recent.CONFIG_DIR, exist_ok=True)
        with open(PROGRESS_FILE, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=1)
    except OSError:
        pass


class GuidesTab(ttk.Frame):
    def __init__(self, master):
        super().__init__(master, padding=12)
        self.selected = 0
        self._step_rows = []
        self._build()
        state.subscribe(self.on_mod_changed)

    # ---- layout ----

    def _build(self):
        self.header = ui_kit.PageHeader(
            self, "Guides",
            "What a real job actually takes, in order. Each step opens the screen it needs — "
            "so you don't have to know which of the 46 a thing lives on before you can start.",
            help_key="guides")

        body = ttk.Frame(self)
        body.pack(fill="both", expand=True)

        picker = ui_kit.Section(body, "What do you want to do?")
        picker.pack(side="left", fill="y", padx=(0, ui_kit.PAD_SECTION))
        picker.configure(width=300)
        picker.pack_propagate(False)
        self.listbox = tk.Listbox(picker.body, width=34, height=20, exportselection=False,
                                  activestyle="none")
        self.listbox.pack(fill="both", expand=True)
        for title, _why, _steps in guides.GUIDES:
            self.listbox.insert("end", title)
        self.listbox.bind("<<ListboxSelect>>", lambda e: self._pick())

        self.detail = ui_kit.Section(body, "Steps")
        self.detail.pack(side="left", fill="both", expand=True)

        self.why = ttk.Label(self.detail.body, text="", style="Muted.TLabel",
                             wraplength=700, justify="left")
        self.why.pack(anchor="w", pady=(2, 8))
        self.steps_frame = ttk.Frame(self.detail.body)
        self.steps_frame.pack(fill="both", expand=True)

        self.status = ttk.Label(self, text="", style="Status.TLabel",
                                wraplength=1000, justify="left")
        self.status.pack(fill="x", pady=(6, 0))

        self.listbox.selection_set(0)
        self._pick()

    # ---- lifecycle ----

    def on_mod_changed(self):
        if state.is_loaded:
            self.header.set_status(True, state.mod_name)
        else:
            self.header.set_status(False, "no mod open")
        if hasattr(self, "steps_frame"):
            self._render_steps()

    def on_show(self):
        self.on_mod_changed()

    # ---- progress ----

    def _progress_key(self):
        """Ticks belong to a mod, not to the app - two mods are at different
        points in the same guide."""
        return os.path.normcase(state.mod_root) if state.is_loaded else "__no_mod__"

    def _done_steps(self):
        return set(_load_progress().get(self._progress_key(), []))

    def _toggle_step(self, step_id):
        data = _load_progress()
        key = self._progress_key()
        done = set(data.get(key, []))
        done.symmetric_difference_update({step_id})
        data[key] = sorted(done)
        _save_progress(data)
        self._render_steps()

    # ---- rendering ----

    def _pick(self):
        selection = self.listbox.curselection()
        self.selected = selection[0] if selection else 0
        self._render_steps()

    def _render_steps(self):
        for child in self.steps_frame.winfo_children():
            child.destroy()
        self._step_rows = []

        title, why, steps = guides.GUIDES[self.selected]
        self.why.config(text=why)
        done = self._done_steps()

        for number, (text, key, hint) in enumerate(steps, start=1):
            step_id = f"{title}|{number}"
            is_done = step_id in done

            row = ttk.Frame(self.steps_frame)
            row.pack(fill="x", pady=3)

            tick = tk.BooleanVar(value=is_done)
            ttk.Checkbutton(row, variable=tick,
                            command=lambda sid=step_id: self._toggle_step(sid)).pack(side="left")
            ttk.Label(row, text=f"{number}.", style="Muted.TLabel", width=3).pack(side="left")

            label = ttk.Label(row, text=text, style="Muted.TLabel" if is_done else "TLabel")
            label.pack(side="left")
            ttk.Button(row, text=f"Open {self._screen_label(key)}",
                       command=lambda k=key: self._open(k)).pack(side="right")

            ttk.Label(self.steps_frame, text=f"      {hint}", style="Muted.TLabel",
                      wraplength=700, justify="left").pack(anchor="w", pady=(0, 4))

        finished = sum(1 for i in range(1, len(steps) + 1) if f"{title}|{i}" in done)
        self.status.config(
            text=f"{finished} of {len(steps)} ticked."
                 + ("" if state.is_loaded else "  Open a mod and the ticks are remembered per mod."))

    @staticmethod
    def _screen_label(key):
        import main
        for _section, entries in main.SECTIONS:
            for entry_key, label, _cls in entries:
                if entry_key == key:
                    return label
        return key

    def _open(self, key):
        app = self.winfo_toplevel()
        if hasattr(app, "show"):
            app.show(key)
