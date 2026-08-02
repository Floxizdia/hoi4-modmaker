"""One place for the app's look: the colour palette, the typefaces, the ttk
styles, and the defaults for classic tk widgets (Text, Listbox, Canvas) that
the ttk theme doesn't reach - without this they stay white-on-white and look
broken next to the themed widgets.

Direction: a tactical command-table / blueprint. Deep navy surfaces, sharp
un-rounded edges, a cyan wash for the active state, monospace for anything
that reads as data (ids, values, coordinates) and a condensed display face
for headings and navigation - the same split a war-room map table uses
between its printed labels and its grease-pencil annotations.
"""

import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk

# ---- surfaces ----
# aligned to the "HOI4 Mod Maker UI redesign" design-system doc: bg.app /
# bg.surface / bg.raised / rule / border are five distinct roles there,
# where this file used to double up rule and border under one EDGE.
BG = "#0a1119"           # bg.app
SURFACE = "#101a24"      # bg.surface
CANVAS_BG = "#0a1119"
RAISED = "#16222e"       # bg.raised
RULE = "#1e2d3a"         # hairline divider inside a card (header/body split)
EDGE = "#2c4050"         # border - card/panel/input outlines
HOVER = "#152230"
SELECTED = "#1c3742"     # cyan-washed active nav row / selected table row

# ---- text ----
TEXT = "#d7e2ea"
MUTED = "#5f7280"         # meta labels: KEY / STATUS, dim mono captions
MUTED_BRIGHT = "#7c8f9e"  # text.dim - readable muted, for nav labels sitting on dark

# ---- accents ----
GOLD = "#7fd4d1"          # kept as the name every tab imports; now cyan
GOLD_DIM = "#4bb3af"
BRONZE = "#1d3644"        # accent-button fill (was bronze, now deep teal)
GREEN = "#6fbf73"         # ok
AMBER = "#d9a544"         # warn
RED = "#d4635f"           # error
BLUE = "#7fd4d1"

# alpha-composited over the game's own (warm, olive) panel textures in
# chrome.py, so the header/rail backdrops read as the same navy-blueprint
# surface as everything else instead of clashing with it
CHROME_TINT = (8, 20, 32, 165)

# ---- typefaces ----
# design-system doc calls for Oswald (headings/nav), IBM Plex Mono (data),
# Barlow Semi Condensed (body) - none ship with Windows, so _pick_faces
# below tries each and falls back one step at a time to what does.
FACE_DISPLAY = "Bahnschrift SemiCondensed"   # headings, nav, wordmark
FACE_UI = "Segoe UI"                         # dense body text and forms
FACE_MONO = "Consolas"                       # ids, values, anything data-shaped

FONT_UI = (FACE_UI, 10)
FONT_BOLD = (FACE_UI, 10, "bold")
FONT_TITLE = (FACE_DISPLAY, 30, "bold")
FONT_HEAD = (FACE_DISPLAY, 13, "bold")


def _pick_faces(root):
    """Fall back gracefully on a machine without the ideal face installed."""
    global FACE_DISPLAY, FACE_UI, FACE_MONO, FONT_UI, FONT_BOLD, FONT_TITLE, FONT_HEAD
    families = set(tkfont.families(root))

    def pick(*candidates):
        return next((c for c in candidates if c in families), candidates[-1])

    FACE_DISPLAY = pick("Oswald", "Bahnschrift SemiCondensed", "Bahnschrift",
                        "Franklin Gothic Medium", "Segoe UI Semibold", "Segoe UI")
    FACE_UI = pick("Barlow Semi Condensed", "Segoe UI")
    FACE_MONO = pick("IBM Plex Mono", "Consolas", "Cascadia Mono")

    FONT_UI = (FACE_UI, 10)
    FONT_BOLD = (FACE_UI, 10, "bold")
    FONT_TITLE = (FACE_DISPLAY, 30, "bold")
    FONT_HEAD = (FACE_DISPLAY, 13, "bold")


def _theme_toplevels():
    """Every dialog in the app is a bare tk.Toplevel with ttk children -
    the ttk widgets already pick up the shared style, but the Toplevel's
    own background (visible in every gap the grid/pack layout leaves) never
    got set, so it fell back to the OS default white. Patching the
    constructor once here means every dialog is themed with no per-file
    edits and no risk of a new one being added un-themed later."""
    if getattr(tk.Toplevel, "_hoi4_themed", False):
        return
    original_init = tk.Toplevel.__init__

    def themed_init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        try:
            self.configure(background=BG)
        except tk.TclError:
            pass

    tk.Toplevel.__init__ = themed_init
    tk.Toplevel._hoi4_themed = True


def apply(root):
    """Build the whole theme. Call once, before any widget is created.

    Built on ttk's `clam` rather than a packaged dark theme: the pretty ones
    (sv_ttk and friends) draw their widgets from bitmap sprites, so a
    `style.configure(background=...)` on them is silently ignored and every
    accent button stays the theme author's blue. clam draws from colour
    options, which means every pixel here is ours.
    """
    _pick_faces(root)
    _theme_toplevels()
    style = ttk.Style(root)
    style.theme_use("clam")

    # classic tk widgets don't follow the ttk theme - give them dark defaults
    for widget in ("Text", "Listbox"):
        root.option_add(f"*{widget}.background", SURFACE)
        root.option_add(f"*{widget}.foreground", TEXT)
        root.option_add(f"*{widget}.selectBackground", BRONZE)
        root.option_add(f"*{widget}.selectForeground", "#eafdfb")
        root.option_add(f"*{widget}.relief", "flat")
        root.option_add(f"*{widget}.borderWidth", 0)
        root.option_add(f"*{widget}.highlightThickness", 0)
    root.option_add("*Text.insertBackground", GOLD)
    root.option_add("*Listbox.activeStyle", "none")
    root.option_add("*Canvas.highlightThickness", 0)
    root.configure(background=BG)

    style.configure(".", background=BG, foreground=TEXT, fieldbackground=CANVAS_BG,
                    bordercolor=EDGE, darkcolor=BG, lightcolor=BG,
                    troughcolor=CANVAS_BG, focuscolor=GOLD_DIM,
                    selectbackground=BRONZE, selectforeground="#eafdfb",
                    font=FONT_UI, borderwidth=1)

    style.configure("TFrame", background=BG)
    style.configure("TLabel", background=BG, foreground=TEXT, font=FONT_UI)
    style.configure("TSeparator", background=EDGE)

    # the tick itself is drawn in the indicator's *foreground*, so the box
    # stays dark in every state and only the mark lights up cyan - clam's
    # default flips the box to a pale grey instead, which reads as disabled
    for element in ("TCheckbutton", "TRadiobutton"):
        style.configure(element, background=BG, foreground=TEXT, font=FONT_UI,
                        indicatorbackground=CANVAS_BG, indicatorforeground=GOLD,
                        indicatorrelief="flat", indicatormargin=(0, 0, 6, 0),
                        bordercolor=EDGE, upperbordercolor=EDGE, lowerbordercolor=EDGE,
                        focuscolor=BG, padding=3)
        style.map(element,
                  foreground=[("active", GOLD)],
                  background=[("active", BG)],
                  indicatorbackground=[("selected", CANVAS_BG), ("active", HOVER),
                                       ("pressed", HOVER)],
                  indicatorforeground=[("selected", GOLD), ("active", GOLD)],
                  upperbordercolor=[("selected", GOLD_DIM), ("active", GOLD_DIM)],
                  lowerbordercolor=[("selected", GOLD_DIM), ("active", GOLD_DIM)],
                  bordercolor=[("selected", GOLD_DIM), ("active", GOLD_DIM)])

    style.configure("TLabelframe", background=BG, bordercolor=EDGE,
                    relief="solid", borderwidth=1)
    style.configure("TLabelframe.Label", background=BG, foreground=GOLD_DIM,
                    font=(FACE_DISPLAY, 10, "bold"))

    # buttons: flat plates, sharp corners, a cyan edge that lights on hover
    style.configure("TButton", background=RAISED, foreground=TEXT,
                    bordercolor=EDGE, lightcolor=RAISED, darkcolor=RAISED,
                    relief="flat", font=(FACE_MONO, 9), padding=(11, 5), anchor="center")
    style.map("TButton",
              background=[("pressed", SELECTED), ("active", HOVER)],
              lightcolor=[("pressed", SELECTED), ("active", HOVER)],
              darkcolor=[("pressed", SELECTED), ("active", HOVER)],
              foreground=[("pressed", GOLD), ("active", GOLD)],
              bordercolor=[("active", GOLD_DIM), ("pressed", GOLD)])

    style.configure("Accent.TButton", background=BRONZE, foreground="#eafdfb",
                    bordercolor=GOLD_DIM, lightcolor=BRONZE, darkcolor=BRONZE,
                    relief="flat", font=(FACE_MONO, 9, "bold"), padding=(13, 5))
    style.map("Accent.TButton",
              background=[("pressed", "#12262f"), ("active", "#2a4d5a")],
              lightcolor=[("pressed", "#12262f"), ("active", "#2a4d5a")],
              darkcolor=[("pressed", "#12262f"), ("active", "#2a4d5a")],
              foreground=[("active", "#f2fffd")],
              bordercolor=[("active", GOLD)])

    # inputs
    style.configure("TEntry", fieldbackground=CANVAS_BG, foreground=TEXT,
                    bordercolor=EDGE, lightcolor=EDGE, darkcolor=EDGE,
                    insertcolor=GOLD, padding=4, font=(FACE_MONO, 10))
    style.map("TEntry", bordercolor=[("focus", GOLD_DIM)],
              lightcolor=[("focus", GOLD_DIM)], darkcolor=[("focus", GOLD_DIM)])

    style.configure("TCombobox", fieldbackground=CANVAS_BG, background=RAISED,
                    foreground=TEXT, bordercolor=EDGE, lightcolor=EDGE,
                    darkcolor=EDGE, arrowcolor=GOLD_DIM, padding=4, font=(FACE_MONO, 10))
    style.map("TCombobox",
              fieldbackground=[("readonly", CANVAS_BG)],
              foreground=[("readonly", TEXT)],
              bordercolor=[("focus", GOLD_DIM), ("active", GOLD_DIM)],
              arrowcolor=[("active", GOLD)])
    style.configure("TSpinbox", fieldbackground=CANVAS_BG, background=RAISED,
                    foreground=TEXT, bordercolor=EDGE, arrowcolor=GOLD_DIM, padding=3,
                    font=(FACE_MONO, 10))

    root.option_add("*TCombobox*Listbox.background", SURFACE)
    root.option_add("*TCombobox*Listbox.foreground", TEXT)
    root.option_add("*TCombobox*Listbox.selectBackground", BRONZE)
    root.option_add("*TCombobox*Listbox.selectForeground", "#eafdfb")

    # lists: a cyan-lettered header on a raised strip
    style.configure("Treeview", background=SURFACE, fieldbackground=SURFACE,
                    foreground=TEXT, bordercolor=EDGE, borderwidth=1,
                    relief="solid", rowheight=24, font=(FACE_MONO, 10))
    style.configure("Treeview.Heading", background=RAISED, foreground=GOLD_DIM,
                    bordercolor=EDGE, relief="flat",
                    font=(FACE_DISPLAY, 10, "bold"), padding=(6, 5))
    style.map("Treeview.Heading",
              background=[("active", HOVER)], foreground=[("active", GOLD)])
    style.map("Treeview", background=[("selected", BRONZE)],
              foreground=[("selected", "#eafdfb")])

    # slim scrollbars: no arrow buttons, just a cyan thumb in a dark trough
    for orient in ("Vertical.TScrollbar", "Horizontal.TScrollbar"):
        style.configure(orient, background=RAISED, troughcolor=CANVAS_BG,
                        bordercolor=CANVAS_BG, lightcolor=RAISED, darkcolor=RAISED,
                        arrowcolor=MUTED, relief="flat", arrowsize=12)
        style.map(orient, background=[("active", BRONZE), ("pressed", GOLD_DIM)],
                  arrowcolor=[("active", GOLD)])

    style.configure("TNotebook", background=BG, bordercolor=EDGE, tabmargins=(2, 4, 2, 0))
    style.configure("TNotebook.Tab", background=SURFACE, foreground=MUTED_BRIGHT,
                    bordercolor=EDGE, lightcolor=SURFACE, padding=(14, 6),
                    font=(FACE_DISPLAY, 10))
    style.map("TNotebook.Tab",
              background=[("selected", RAISED), ("active", HOVER)],
              foreground=[("selected", GOLD), ("active", TEXT)],
              lightcolor=[("selected", RAISED)])

    style.configure("TProgressbar", background=GOLD_DIM, troughcolor=CANVAS_BG,
                    bordercolor=EDGE, lightcolor=GOLD_DIM, darkcolor=GOLD_DIM)
    style.configure("TPanedwindow", background=BG)

    # roles used across the tabs, so every screen speaks the same language
    style.configure("Banner.TLabel", font=(FACE_DISPLAY, 12, "bold"), foreground=GREEN)
    style.configure("BannerOff.TLabel", font=(FACE_DISPLAY, 12, "bold"), foreground=MUTED)
    style.configure("Status.TLabel", foreground=GREEN)
    style.configure("Muted.TLabel", foreground=MUTED)
    style.configure("Warn.TLabel", foreground=RED)
    style.configure("Gold.TLabel", foreground=GOLD, font=(FACE_DISPLAY, 10, "bold"))
    style.configure("Title.TLabel", font=FONT_TITLE, foreground=TEXT)
    style.configure("Head.TLabel", font=FONT_HEAD, foreground=TEXT)
    style.configure("Card.TFrame", background=SURFACE, relief="solid",
                    borderwidth=1, bordercolor=EDGE,
                    lightcolor=EDGE, darkcolor=EDGE)
    # inner rows of a card: same fill, no second border drawn around them
    style.configure("CardInner.TFrame", background=SURFACE, borderwidth=0, relief="flat")
    style.configure("Card.TLabel", background=SURFACE, foreground=TEXT)

    from app import ui_kit
    ui_kit.install_styles(style)
