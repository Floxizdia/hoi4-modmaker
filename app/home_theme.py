"""Design tokens for the redesigned Home screen only.

The "Command Table" (1A) direction from the design-system handoff, as a
self-contained palette + ttk style set. Deliberately not merged into
theme.py: the rest of the app hasn't been redesigned yet, and reusing
theme.py's own style names (TButton, Card.TFrame, Treeview, ...) here would
retheme every other screen the moment Home builds its styles. Every style
this module installs is prefixed "Home." so it can only ever apply to
widgets that ask for it by name.

Hex values are the exact palA token list from the design-system doc's 1A
"Command Table" palette - not eyeballed off the mockup.
"""

import tkinter.font as tkfont
from tkinter import ttk

# ---- palette (design doc: P(canvas,surface,panel,raised,hover,active,
# line,lineStrong,textHi,textMid,textLow,textOff,accent,accentHi,accentDim,
# selection,ok,warn,err)) ----
CANVAS = "#0B0F12"
SURFACE = "#11171B"
PANEL = "#161D22"
RAISED = "#1C252B"
HOVER = "#222D34"
ACTIVE = "#2A373F"
LINE = "#202A30"
LINE_STRONG = "#2E3B43"
TEXT_HI = "#DCE5EA"
TEXT_MID = "#96A6B0"
TEXT_LOW = "#63757F"
TEXT_OFF = "#46545C"
ACCENT = "#56C2CE"
ACCENT_HI = "#86DCE6"
ACCENT_DIM = "#1B3B41"
SELECTION = "#143138"
OK = "#6FBF7B"
WARN = "#D9A64A"
ERR = "#D96A5E"
ACCENT_ON = "#07171A"   # text colour sitting on a filled accent surface

# ---- type: real Tkinter fonts, not the web fonts the mockup renders with.
# The design doc's own "Tkinter reality" section is explicit that the built
# app uses Segoe UI / Consolas - IBM Plex is only there so the HTML preview
# has something to render with. ----
FACE_UI = "Segoe UI"
FACE_MONO = "Consolas"


def _pick(root, *candidates):
    families = set(tkfont.families(root))
    return next((c for c in candidates if c in families), candidates[-1])


def install(root):
    """Build every Home.* ttk style. Safe to call more than once (e.g. if
    the home screen is rebuilt after returning from a mod)."""
    global FACE_UI, FACE_MONO
    FACE_UI = _pick(root, "Segoe UI", "Tahoma", "TkDefaultFont")
    FACE_MONO = _pick(root, "Consolas", "Courier New", "TkFixedFont")

    style = ttk.Style(root)

    style.configure("Home.TFrame", background=CANVAS)
    style.configure("Home.Surface.TFrame", background=SURFACE)
    style.configure("Home.Panel.TFrame", background=PANEL)
    style.configure("Home.Sash.TFrame", background=LINE_STRONG)

    style.configure("Home.TLabel", background=CANVAS, foreground=TEXT_HI, font=(FACE_UI, 10))
    style.configure("Home.Surface.TLabel", background=SURFACE, foreground=TEXT_HI, font=(FACE_UI, 10))
    style.configure("Home.Panel.TLabel", background=PANEL, foreground=TEXT_HI, font=(FACE_UI, 10))
    style.configure("Home.Muted.TLabel", background=CANVAS, foreground=TEXT_MID, font=(FACE_UI, 9))
    style.configure("Home.SurfaceMuted.TLabel", background=SURFACE, foreground=TEXT_MID, font=(FACE_UI, 9))
    style.configure("Home.PanelMuted.TLabel", background=PANEL, foreground=TEXT_MID, font=(FACE_UI, 9))
    style.configure("Home.Eyebrow.TLabel", background=PANEL, foreground=TEXT_LOW,
                    font=(FACE_MONO, 8))
    style.configure("Home.EyebrowAccent.TLabel", background=CANVAS, foreground=ACCENT,
                    font=(FACE_MONO, 8))
    style.configure("Home.Mono.TLabel", background=SURFACE, foreground=TEXT_HI, font=(FACE_MONO, 9))
    style.configure("Home.MonoMuted.TLabel", background=SURFACE, foreground=TEXT_LOW, font=(FACE_MONO, 9))
    style.configure("Home.Ok.TLabel", background=CANVAS, foreground=OK, font=(FACE_MONO, 9))
    style.configure("Home.Warn.TLabel", background=CANVAS, foreground=WARN, font=(FACE_MONO, 9))
    style.configure("Home.Err.TLabel", background=CANVAS, foreground=ERR, font=(FACE_MONO, 9))
    style.configure("Home.Wordmark.TLabel", background=PANEL, foreground=TEXT_HI,
                    font=(FACE_UI, 19, "bold"))
    style.configure("Home.CardTitle.TLabel", background=SURFACE, foreground=TEXT_HI,
                    font=(FACE_UI, 10, "bold"))
    style.configure("Home.SectionTitle.TLabel", background=CANVAS, foreground=TEXT_HI,
                    font=(FACE_UI, 11, "bold"))

    # buttons: primary (filled accent), secondary (raised + border), ghost
    style.configure("Home.Primary.TButton", background=ACCENT, foreground=ACCENT_ON,
                    bordercolor=ACCENT, lightcolor=ACCENT, darkcolor=ACCENT,
                    relief="flat", font=(FACE_UI, 10, "bold"), padding=(14, 6))
    style.map("Home.Primary.TButton",
              background=[("disabled", RAISED), ("pressed", "#3AA3AF"), ("active", ACCENT_HI)],
              foreground=[("disabled", TEXT_OFF)],
              bordercolor=[("disabled", LINE_STRONG)])

    style.configure("Home.Secondary.TButton", background=RAISED, foreground=TEXT_HI,
                    bordercolor=ACTIVE, lightcolor=RAISED, darkcolor=RAISED,
                    relief="flat", font=(FACE_UI, 9), padding=(13, 5))
    style.map("Home.Secondary.TButton",
              background=[("pressed", SELECTION), ("active", HOVER)],
              bordercolor=[("active", ACCENT_DIM)],
              foreground=[("disabled", TEXT_OFF)])

    style.configure("Home.Ghost.TButton", background=SURFACE, foreground=TEXT_MID,
                    bordercolor=SURFACE, lightcolor=SURFACE, darkcolor=SURFACE,
                    relief="flat", font=(FACE_UI, 9), padding=(11, 5))
    style.map("Home.Ghost.TButton",
              background=[("active", HOVER)], bordercolor=[("active", ACTIVE)],
              foreground=[("active", TEXT_HI)])

    style.configure("Home.Filter.TButton", background=PANEL, foreground=TEXT_MID,
                    bordercolor=PANEL, relief="flat", font=(FACE_UI, 9), padding=(10, 4))
    style.map("Home.Filter.TButton", background=[("active", HOVER)])
    style.configure("Home.FilterActive.TButton", background=ACCENT_DIM, foreground=ACCENT_HI,
                    bordercolor=ACCENT_DIM, relief="flat", font=(FACE_UI, 9, "bold"), padding=(10, 4))

    style.configure("Home.TEntry", fieldbackground=CANVAS, foreground=TEXT_HI,
                    bordercolor=LINE_STRONG, lightcolor=LINE_STRONG, darkcolor=LINE_STRONG,
                    insertcolor=ACCENT, padding=4, font=(FACE_UI, 10))
    style.map("Home.TEntry", bordercolor=[("focus", ACCENT)],
              lightcolor=[("focus", ACCENT)], darkcolor=[("focus", ACCENT)])

    style.configure("Home.Treeview", background=CANVAS, fieldbackground=CANVAS,
                    foreground=TEXT_HI, bordercolor=LINE_STRONG, borderwidth=0,
                    relief="flat", rowheight=34, font=(FACE_UI, 10))
    style.configure("Home.Treeview.Heading", background=RAISED, foreground=TEXT_MID,
                    bordercolor=LINE_STRONG, relief="flat",
                    font=(FACE_UI, 9, "bold"), padding=(9, 5))
    style.map("Home.Treeview.Heading", background=[("active", HOVER)])
    style.map("Home.Treeview", background=[("selected", SELECTION)],
              foreground=[("selected", TEXT_HI)])

    for orient in ("Home.Vertical.TScrollbar", "Home.Horizontal.TScrollbar"):
        style.configure(orient, background=RAISED, troughcolor=CANVAS,
                        bordercolor=CANVAS, lightcolor=RAISED, darkcolor=RAISED,
                        arrowcolor=TEXT_MID, relief="flat", arrowsize=11)
        style.map(orient, background=[("active", ACCENT_DIM)])

    style.configure("Home.TProgressbar", background=ACCENT, troughcolor=CANVAS,
                    bordercolor=LINE, lightcolor=ACCENT, darkcolor=ACCENT, thickness=4)

    style.configure("Home.Selection.TFrame", background=SELECTION)
    style.configure("Home.Card.TFrame", background=SURFACE, relief="solid",
                    borderwidth=1, bordercolor=LINE_STRONG,
                    lightcolor=LINE_STRONG, darkcolor=LINE_STRONG)
    style.configure("Home.CardHead.TFrame", background=PANEL, relief="flat", borderwidth=0)
