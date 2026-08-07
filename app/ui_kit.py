"""Shared chrome every tab should build its page out of, instead of each
one hand-rolling its own banner label + ttk.Frame soup. Grown out of 40+
tabs added over time that each improvised their own header/spacing/card
conventions - the visible seams (seven different ways to say "no mod
open", four different paddings for "the form area") are what makes the
app read as assembled rather than designed. This is the fix: a handful of
primitives that carry one visual language everywhere.
"""

import tkinter as tk
from tkinter import ttk

from app import theme


def repaint_on_becoming_visible(widget, render):
    """Bind `render` to every event that means "you are on screen now".

    Hand-painted canvases used to redraw only on <Configure>, which made
    their whole contents depend on that one event arriving. It does on
    Windows. Under Wayland it can arrive once before the surface is
    drawable and never again, leaving a widget that is laid out and
    clickable but blank - which is exactly how the navigation rail was
    reported from Linux.

    <Map> and <Expose> are what a compositor sends when a surface actually
    becomes visible, and the idle call covers a widget that is already
    mapped by the time it is built.
    """
    for sequence in ("<Configure>", "<Map>", "<Expose>"):
        widget.bind(sequence, lambda e: render(), add="+")
    widget.after_idle(render)

PAD_PAGE = 20     # outer page margin
PAD_SECTION = 16  # gap between stacked sections
PAD_FIELD = 8      # gap between a section's fields


class PageHeader(ttk.Frame):
    """Title + one-line description + a status pill that reads the mod
    state, replacing the old free-floating banner label every tab used to
    build by hand. `on_mod_changed()` keeps the pill in sync.

    `help_key`, if given, adds a "?" button that opens a HelpDialog built
    from `help_content.HELP[help_key]` - the tab explains itself instead of
    the user guessing from field labels alone."""

    def __init__(self, master, title, description="", help_key=None):
        super().__init__(master)
        self.columnconfigure(0, weight=1)

        top = ttk.Frame(self)
        top.grid(row=0, column=0, sticky="ew")
        top.columnconfigure(0, weight=1)

        title_row = ttk.Frame(top)
        title_row.grid(row=0, column=0, sticky="w")
        ttk.Label(title_row, text=title.upper(), style="PageTitle.TLabel").pack(side="left")
        if help_key:
            # a bare "?" two characters wide was being missed entirely by the
            # people it exists for. A labelled button reads as an offer of
            # help rather than as punctuation.
            button = ttk.Button(title_row, text="?  Guide", style="Help.TButton",
                                command=lambda: open_help(self, help_key))
            button.pack(side="left", padx=(10, 0))
            attach_tooltip(button, "What this screen is for, how it works, and a worked "
                                   "example. Every screen has one.")

        self._dot = tk.Canvas(top, width=9, height=9, highlightthickness=0, bg=theme.BG)
        self._dot.grid(row=0, column=1, sticky="e", padx=(0, 6))
        self._pill = ttk.Label(top, text="", style="Muted.TLabel")
        self._pill.grid(row=0, column=2, sticky="e")

        if description:
            ttk.Label(self, text=description, style="Muted.TLabel",
                      wraplength=920, justify="left").grid(row=1, column=0, sticky="w", pady=(3, 0))

        ttk.Separator(self).grid(row=2, column=0, sticky="ew", pady=(PAD_FIELD, 0))
        self.pack(fill="x", pady=(0, PAD_SECTION))

    def set_status(self, connected, text):
        color = theme.GREEN if connected else theme.MUTED
        self._dot.delete("all")
        self._dot.create_oval(1, 1, 8, 8, fill=color, outline="")
        self._pill.config(text=text, foreground=color)


class Section(ttk.Frame):
    """One visually-consistent card: an optional heading, then whatever
    the caller packs into `.body`. Every form area in the app should live
    inside one of these rather than a bare ttk.Frame."""

    def __init__(self, master, heading=""):
        super().__init__(master, style="Card.TFrame")
        inner = ttk.Frame(self, style="CardInner.TFrame", padding=(16, 12))
        inner.pack(fill="both", expand=True)
        if heading:
            ttk.Label(inner, text=heading, style="SectionHead.TLabel").pack(anchor="w", pady=(0, 10))
        self.body = ttk.Frame(inner, style="CardInner.TFrame")
        self.body.pack(fill="both", expand=True)


class FieldRow(ttk.Frame):
    """A strip of label+widget pairs with the app's standard gap, so forms
    stop hand-tuning padx per field. `.add(label, widget_cls, **kwargs)`
    constructs the widget (parented to its own cell) and returns it."""

    def __init__(self, master):
        super().__init__(master, style="CardInner.TFrame")
        self.pack(fill="x", pady=(0, PAD_FIELD))
        self._col = 0

    def add(self, label_text, widget_cls, **kwargs):
        cell = ttk.Frame(self, style="CardInner.TFrame")
        cell.pack(side="left", padx=(0 if self._col == 0 else 18, 0))
        ttk.Label(cell, text=label_text, style="FieldLabel.TLabel").pack(anchor="w")
        widget = widget_cls(cell, **kwargs)
        widget.pack(anchor="w", pady=(2, 0))
        self._col += 1
        return widget


class HelpDialog(tk.Toplevel):
    """What this tab does, how it works, and a worked example - the content
    for each tab lives in help_content.HELP, keyed by the SECTIONS key."""

    def __init__(self, master, entry):
        super().__init__(master)
        self.title(entry.get("title", "Help"))

        # The longest guides run past 850px tall. That fits a 1080p desktop
        # and is cut off on a 768px laptop, with no way to reach the Close
        # button - so the body scrolls and the window is capped to what the
        # screen can actually show.
        self._canvas = tk.Canvas(self, highlightthickness=0, background=theme.BG, bd=0)
        bar = ttk.Scrollbar(self, orient="vertical", command=self._canvas.yview)
        self._canvas.configure(yscrollcommand=bar.set)
        self._canvas.pack(side="left", fill="both", expand=True)
        bar.pack(side="right", fill="y")

        outer = ttk.Frame(self._canvas, padding=18)
        self._canvas.create_window((0, 0), window=outer, anchor="nw")
        outer.bind("<Configure>",
                   lambda e: self._canvas.configure(scrollregion=self._canvas.bbox("all")))
        self._canvas.bind_all("<MouseWheel>", self._on_wheel)
        self.bind("<Destroy>", lambda e: self._canvas.unbind_all("<MouseWheel>"))

        ttk.Label(outer, text=entry.get("title", "").upper(), style="PageTitle.TLabel",
                  wraplength=520, justify="left").pack(anchor="w")
        ttk.Separator(outer).pack(fill="x", pady=(8, 12))

        if entry.get("what"):
            ttk.Label(outer, text="WHAT IT DOES", style="SectionHead.TLabel",
                      background=theme.BG).pack(anchor="w")
            ttk.Label(outer, text=entry["what"], style="Muted.TLabel", foreground=theme.TEXT,
                      wraplength=520, justify="left").pack(anchor="w", pady=(2, 12))

        if entry.get("how"):
            ttk.Label(outer, text="HOW IT WORKS", style="SectionHead.TLabel",
                      background=theme.BG).pack(anchor="w")
            for i, step in enumerate(entry["how"], 1):
                ttk.Label(outer, text=f"{i}. {step}", style="Muted.TLabel", foreground=theme.TEXT,
                          wraplength=500, justify="left").pack(anchor="w", pady=(2, 0))
            ttk.Frame(outer, height=10).pack()

        if entry.get("example"):
            ttk.Label(outer, text="EXAMPLE", style="SectionHead.TLabel",
                      background=theme.BG).pack(anchor="w")
            ex = tk.Text(outer, height=len(entry["example"].splitlines()) + 1, width=64,
                         font=(theme.FACE_MONO, 9), relief="flat", borderwidth=0)
            ex.insert("1.0", entry["example"])
            ex.configure(state="disabled")
            ex.pack(anchor="w", pady=(2, 12), fill="x")

        ttk.Button(outer, text="Close", command=self.destroy).pack(anchor="e")

        self.transient(master.winfo_toplevel())
        self.grab_set()
        # sized once the layout has settled: a frame held by create_window
        # has no usable size until the canvas has laid it out, and measuring
        # in __init__ gave every dialog the same third-of-a-window height
        self.after_idle(self._fit)

    def _fit(self):
        if not self.winfo_exists():
            return
        self.update_idletasks()
        box = self._canvas.bbox("all")
        if not box:
            return
        self._canvas.configure(scrollregion=box)
        wanted_w, wanted_h = box[2], box[3]
        height = min(wanted_h, self.winfo_screenheight() - 120)
        self._canvas.configure(width=wanted_w, height=height)
        self.geometry(f"{wanted_w + 20}x{height}")

    def _on_wheel(self, event):
        self._canvas.yview_scroll(-1 * (event.delta // 120), "units")


class _Tooltip:
    """A small delayed label near the cursor - explains what a button does
    or why it's greyed out, since a short button label can't say both."""

    _DELAY_MS = 500

    def __init__(self, widget, text_fn):
        self.widget = widget
        self.text_fn = text_fn
        self._after_id = None
        self._win = None
        widget.bind("<Enter>", self._schedule, add="+")
        widget.bind("<Leave>", self._hide, add="+")
        widget.bind("<ButtonPress>", self._hide, add="+")

    def _schedule(self, _event=None):
        self._cancel()
        self._after_id = self.widget.after(self._DELAY_MS, self._show)

    def _cancel(self):
        if self._after_id is not None:
            try:
                self.widget.after_cancel(self._after_id)
            except tk.TclError:
                pass
            self._after_id = None

    def _show(self):
        text = self.text_fn() if callable(self.text_fn) else self.text_fn
        if not text or self._win is not None or not self.widget.winfo_exists():
            return
        x = self.widget.winfo_rootx() + 12
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 6
        win = tk.Toplevel(self.widget)
        win.overrideredirect(True)
        win.attributes("-topmost", True)
        win.configure(background=theme.GOLD_DIM, padx=1, pady=1)
        ttk.Label(win, text=text, style="Tooltip.TLabel", wraplength=280,
                  justify="left").pack()
        win.geometry(f"+{x}+{y}")
        self._win = win

    def _hide(self, _event=None):
        self._cancel()
        if self._win is not None:
            self._win.destroy()
            self._win = None


def guard_required(entries, button, on_valid_change=None):
    """Wire a set of required ttk.Entry/Combobox widgets + one action button
    together: the button is disabled and any empty entry gets a red outline
    the moment a field is blank, instead of the button doing nothing (or
    worse, half-writing a file) when clicked with a gap left in the form.

    `entries` is {widget: StringVar}. Call `check()` once after building the
    form so the initial (usually-empty) state is already reflected."""

    def check(_=None):
        all_filled = True
        for widget, var in entries.items():
            filled = bool(var.get().strip())
            widget.configure(style="Invalid.TEntry" if not filled else "TEntry")
            all_filled = all_filled and filled
        button.configure(state=("normal" if all_filled else "disabled"))
        if on_valid_change:
            on_valid_change(all_filled)
        return all_filled

    for widget, var in entries.items():
        var.trace_add("write", lambda *_: check())
    check()
    return check


def attach_tooltip(widget, text):
    """Show `text` (a str, or a zero-arg callable for dynamic text - e.g.
    explaining *why* a button is currently disabled) near `widget` on hover."""
    return _Tooltip(widget, text)


def open_help(widget, help_key):
    from app import help_content
    entry = help_content.HELP.get(help_key)
    if not entry:
        entry = {"title": help_key.replace("_", " ").title(),
                 "what": "No help written for this tab yet."}
    HelpDialog(widget, entry)


def install_styles(style):
    """Extra ttk styles ui_kit needs, layered on top of theme.apply()."""
    style.configure("PageTitle.TLabel", font=(theme.FACE_DISPLAY, 17, "bold"),
                     foreground=theme.TEXT)
    style.configure("SectionHead.TLabel", background=theme.SURFACE, foreground=theme.GOLD_DIM,
                     font=(theme.FACE_DISPLAY, 10, "bold"))
    style.configure("FieldLabel.TLabel", background=theme.SURFACE, foreground=theme.MUTED,
                     font=(theme.FACE_MONO, 8))
    # a status line that reads like a log entry - a coloured left rule
    # instead of a floating icon, echoing the game's own message banners
    style.configure("StatusOk.TLabel", background=theme.SURFACE, foreground=theme.GREEN,
                     font=(theme.FACE_UI, 9))
    style.configure("StatusErr.TLabel", background=theme.SURFACE, foreground=theme.RED,
                     font=(theme.FACE_UI, 9))
    style.configure("Tooltip.TLabel", background=theme.RAISED, foreground=theme.TEXT,
                     font=(theme.FACE_UI, 9), padding=(8, 5))
    # required-field-left-empty: a red outline reads as "fix this" without
    # needing a separate error label next to every field
    style.configure("Invalid.TEntry", fieldbackground=theme.SURFACE,
                     bordercolor=theme.RED, lightcolor=theme.RED, darkcolor=theme.RED)
    style.map("Invalid.TEntry", bordercolor=[("!disabled", theme.RED)])
    style.configure("Help.TButton", font=(theme.FACE_MONO, 9, "bold"), padding=(10, 3),
                    background=theme.RAISED, foreground=theme.GOLD,
                    bordercolor=theme.GOLD_DIM, lightcolor=theme.RAISED,
                    darkcolor=theme.RAISED, relief="solid")
    style.map("Help.TButton",
              background=[("active", theme.SELECTED)],
              foreground=[("active", theme.GOLD)],
              bordercolor=[("active", theme.GOLD)])
