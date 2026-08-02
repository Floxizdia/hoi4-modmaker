"""TemplatePicker: choose a starting pattern, give it a prefix/tag, get back
a pre-filled dict shaped for the caller's own Dialog class - the caller
still opens that Dialog for review before anything is added to the list, so
a template is a head start, not a silent insert.
"""

import tkinter as tk
from tkinter import ttk

from app import theme


class TemplatePicker(tk.Toplevel):
    """`self.result` is the built dict, or None if cancelled."""

    def __init__(self, master, templates, prefix_hint="my", tag_hint=""):
        super().__init__(master)
        self.title("Choose a template")
        self.resizable(False, False)
        self.templates = templates
        self.result = None
        self._build(prefix_hint, tag_hint)
        self.grab_set()

    def _build(self, prefix_hint, tag_hint):
        pad = {"padx": 10, "pady": 6}

        body = ttk.Frame(self, padding=10)
        body.pack(fill="both", expand=True)

        left = ttk.Frame(body)
        left.pack(side="left", fill="y", padx=(0, 12))
        self.listbox = tk.Listbox(left, width=32, height=10, exportselection=False)
        for t in self.templates:
            self.listbox.insert("end", t["name"])
        self.listbox.pack()
        self.listbox.bind("<<ListboxSelect>>", lambda e: self._on_pick())
        self.listbox.selection_set(0)

        right = ttk.Frame(body, width=280)
        right.pack(side="left", fill="both", expand=True)
        self.hint_label = ttk.Label(right, text="", wraplength=260, justify="left", style="Muted.TLabel")
        self.hint_label.pack(anchor="w", fill="x")

        form = ttk.Frame(self, padding=(10, 0, 10, 10))
        form.pack(fill="x")
        ttk.Label(form, text="Prefix").grid(row=0, column=0, sticky="w")
        self.prefix_var = tk.StringVar(value=prefix_hint)
        ttk.Entry(form, textvariable=self.prefix_var, width=14).grid(row=0, column=1, padx=8)
        ttk.Label(form, text="Country tag (optional)").grid(row=0, column=2, sticky="w", padx=(16, 0))
        self.tag_var = tk.StringVar(value=tag_hint)
        ttk.Entry(form, textvariable=self.tag_var, width=6).grid(row=0, column=3, padx=8)

        btns = ttk.Frame(self, padding=(10, 0, 10, 10))
        btns.pack(fill="x")
        ttk.Button(btns, text="Use Template", style="Accent.TButton", command=self._use).pack(side="left")
        ttk.Button(btns, text="Cancel", command=self.destroy).pack(side="left", padx=6)

        self._on_pick()

    def _on_pick(self):
        sel = self.listbox.curselection()
        if sel:
            self.hint_label.config(text=self.templates[sel[0]]["hint"])

    def _use(self):
        sel = self.listbox.curselection()
        if not sel:
            return
        template = self.templates[sel[0]]
        prefix = self.prefix_var.get().strip() or "my"
        tag = self.tag_var.get().strip().upper()
        self.result = template["build"](prefix, tag)
        self.destroy()
