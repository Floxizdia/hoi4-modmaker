"""Focus Tree-specific Command Table tokens and scoped ttk styles.

The palette matches the approved Home screen Direction 1A system.  Style
names are intentionally prefixed ``FocusTree.`` so this redesign cannot
retheme another screen.
"""

from tkinter import ttk

from app import theme


# Direction 1A palette, aligned with ``home_theme.py``.
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
ACCENT_ON = "#07171A"


def install(root):
    """Install Focus Tree-only styles without touching shared ttk names."""
    style = ttk.Style(root)
    ui = theme.FACE_UI
    mono = theme.FACE_MONO
    display = theme.FACE_DISPLAY

    style.configure("FocusTree.TFrame", background=CANVAS)
    style.configure("FocusTree.Toolbar.TFrame", background=PANEL)
    style.configure("FocusTree.ToolbarRow.TFrame", background=PANEL)
    style.configure("FocusTree.Workspace.TFrame", background=CANVAS)
    style.configure("FocusTree.Sidebar.TFrame", background=SURFACE)
    style.configure("FocusTree.Inspector.TFrame", background=SURFACE)
    style.configure("FocusTree.ActionBar.TFrame", background=PANEL)
    style.configure("FocusTree.Status.TFrame", background=SURFACE)
    style.configure("FocusTree.Sash.TFrame", background=LINE_STRONG)
    style.configure("FocusTree.Card.TFrame", background=SURFACE, relief="solid",
                    borderwidth=1, bordercolor=LINE_STRONG,
                    lightcolor=LINE_STRONG, darkcolor=LINE_STRONG)
    style.configure("FocusTree.Panel.TFrame", background=PANEL)

    style.configure("FocusTree.TLabel", background=CANVAS, foreground=TEXT_HI, font=(ui, 10))
    style.configure("FocusTree.Toolbar.TLabel", background=PANEL, foreground=TEXT_HI, font=(ui, 10))
    style.configure("FocusTree.Surface.TLabel", background=SURFACE, foreground=TEXT_HI, font=(ui, 10))
    style.configure("FocusTree.Panel.TLabel", background=PANEL, foreground=TEXT_HI, font=(ui, 10))
    style.configure("FocusTree.Muted.TLabel", background=CANVAS, foreground=TEXT_MID, font=(ui, 9))
    style.configure("FocusTree.ToolbarMuted.TLabel", background=PANEL, foreground=TEXT_MID, font=(mono, 9))
    style.configure("FocusTree.SurfaceMuted.TLabel", background=SURFACE, foreground=TEXT_MID, font=(ui, 9))
    style.configure("FocusTree.Eyebrow.TLabel", background=PANEL, foreground=TEXT_LOW, font=(mono, 8))
    style.configure("FocusTree.SurfaceEyebrow.TLabel", background=SURFACE, foreground=TEXT_LOW,
                    font=(mono, 8))
    style.configure("FocusTree.Section.TLabel", background=PANEL, foreground=TEXT_HI,
                    font=(display, 10, "bold"))
    style.configure("FocusTree.StatusOk.TLabel", background=PANEL, foreground=OK, font=(mono, 9))
    style.configure("FocusTree.StatusWarn.TLabel", background=PANEL, foreground=WARN, font=(mono, 9))

    style.configure("FocusTree.Primary.TButton", background=ACCENT, foreground=ACCENT_ON,
                    bordercolor=ACCENT, lightcolor=ACCENT, darkcolor=ACCENT,
                    relief="flat", font=(ui, 9, "bold"), padding=(12, 5))
    style.map("FocusTree.Primary.TButton",
              background=[("disabled", RAISED), ("pressed", "#3AA3AF"), ("active", ACCENT_HI)],
              foreground=[("disabled", TEXT_OFF)],
              bordercolor=[("disabled", LINE_STRONG)])
    style.configure("FocusTree.Secondary.TButton", background=RAISED, foreground=TEXT_HI,
                    bordercolor=ACTIVE, lightcolor=RAISED, darkcolor=RAISED,
                    relief="flat", font=(ui, 9), padding=(10, 4))
    style.map("FocusTree.Secondary.TButton",
              background=[("pressed", SELECTION), ("active", HOVER)],
              bordercolor=[("active", ACCENT_DIM)], foreground=[("disabled", TEXT_OFF)])
    style.configure("FocusTree.Ghost.TButton", background=PANEL, foreground=TEXT_MID,
                    bordercolor=PANEL, lightcolor=PANEL, darkcolor=PANEL,
                    relief="flat", font=(ui, 9), padding=(9, 4))
    style.map("FocusTree.Ghost.TButton", background=[("active", HOVER)],
              bordercolor=[("active", ACTIVE)], foreground=[("active", TEXT_HI), ("disabled", TEXT_OFF)])
    style.configure("FocusTree.Action.TButton", background=RAISED, foreground=TEXT_HI,
                    bordercolor=LINE_STRONG, lightcolor=RAISED, darkcolor=RAISED,
                    relief="flat", font=(mono, 8), padding=(9, 4))
    style.map("FocusTree.Action.TButton", background=[("pressed", SELECTION), ("active", HOVER)],
              bordercolor=[("active", ACCENT_DIM)], foreground=[("active", ACCENT_HI), ("disabled", TEXT_OFF)])

    style.configure("FocusTree.TEntry", fieldbackground=CANVAS, foreground=TEXT_HI,
                    bordercolor=LINE_STRONG, lightcolor=LINE_STRONG, darkcolor=LINE_STRONG,
                    insertcolor=ACCENT, padding=4, font=(mono, 9))
    style.map("FocusTree.TEntry", bordercolor=[("focus", ACCENT)],
              lightcolor=[("focus", ACCENT)], darkcolor=[("focus", ACCENT)])
    style.configure("FocusTree.TCombobox", fieldbackground=CANVAS, background=RAISED,
                    foreground=TEXT_HI, bordercolor=LINE_STRONG, lightcolor=LINE_STRONG,
                    darkcolor=LINE_STRONG, arrowcolor=ACCENT, padding=4, font=(mono, 9))
    style.map("FocusTree.TCombobox", fieldbackground=[("readonly", CANVAS)],
              foreground=[("readonly", TEXT_HI)], bordercolor=[("focus", ACCENT), ("active", ACCENT_DIM)],
              arrowcolor=[("active", ACCENT_HI)])
    style.configure("FocusTree.TSpinbox", fieldbackground=CANVAS, background=RAISED,
                    foreground=TEXT_HI, bordercolor=LINE_STRONG, arrowcolor=ACCENT, padding=3,
                    font=(mono, 9))
    style.configure("FocusTree.TCheckbutton", background=PANEL, foreground=TEXT_MID,
                    indicatorbackground=CANVAS, indicatorforeground=ACCENT, font=(ui, 9), padding=2)
    style.map("FocusTree.TCheckbutton", foreground=[("active", TEXT_HI), ("selected", ACCENT_HI)],
              indicatorforeground=[("selected", ACCENT)])

    style.configure("FocusTree.Treeview", background=CANVAS, fieldbackground=CANVAS,
                    foreground=TEXT_HI, bordercolor=LINE_STRONG, borderwidth=0,
                    relief="flat", rowheight=26, font=(mono, 9))
    style.map("FocusTree.Treeview", background=[("selected", SELECTION)],
              foreground=[("selected", ACCENT_HI)])
    for orient in ("FocusTree.Vertical.TScrollbar", "FocusTree.Horizontal.TScrollbar"):
        style.configure(orient, background=RAISED, troughcolor=CANVAS,
                        bordercolor=CANVAS, lightcolor=RAISED, darkcolor=RAISED,
                        arrowcolor=TEXT_MID, relief="flat", arrowsize=10)
        style.map(orient, background=[("active", ACCENT_DIM), ("pressed", ACCENT)])

    style.configure("FocusTree.TNotebook", background=SURFACE, bordercolor=LINE_STRONG,
                    tabmargins=(0, 0, 0, 0))
    style.configure("FocusTree.TNotebook.Tab", background=PANEL, foreground=TEXT_MID,
                    bordercolor=LINE_STRONG, lightcolor=PANEL, padding=(12, 6), font=(ui, 9))
    style.map("FocusTree.TNotebook.Tab", background=[("selected", SURFACE), ("active", HOVER)],
              foreground=[("selected", ACCENT_HI), ("active", TEXT_HI)])


ORIGIN = 80
NODE_WIDTH = 190
NODE_HEIGHT = 56
NODE_SPACING_X = 210
NODE_SPACING_Y = 96

PLAQUE_SPRITES = {
    "completed": "focus_completed_bg",
    "available": "focus_can_start_bg",
    "locked": "focus_unavailable_bg",
}

STATE_COLORS = {
    "completed": OK,
    "available": WARN,
    "locked": TEXT_LOW,
    "new": OK,
    "plain": LINE_STRONG,
}

NODE_FILL = "#151E24"
NODE_FILL_LOCKED = "#11171B"
NODE_TEXT = TEXT_HI
NODE_TEXT_DIM = TEXT_LOW
NODE_META = ACCENT_HI
CONNECTOR = "#40515A"
CONNECTOR_COMPLETED = OK
MUTEX = ERR
