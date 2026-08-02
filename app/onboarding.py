"""First-run tour: a guided walk through what the app actually has, shown
once automatically (tracked by a marker file in the user's home folder,
independent of any particular mod) and re-openable any time from Settings.

Rewritten to match how big the app has actually grown: 40+ tabs across
three sidebar groups, a per-tab "?" help system, real crash-log reading,
and a proper undo/redo/snapshot safety net - the old 5-step version still
described a much smaller app.
"""

import os
import tkinter as tk
from tkinter import ttk

from app import theme, glyphs

MARKER = os.path.join(os.path.expanduser("~"), ".hoi4modmaker_tour_seen")

STEPS = [
    {
        "glyph": "target",
        "title": "Welcome to HOI4 Mod Maker",
        "body": "This builds real Paradox script - focus trees, events, decisions, whole systems "
                "- without hand-typing it. Every tab writes actual common/, history/ and events/ "
                "files straight into your mod.\n\n"
                "The sidebar on the left is grouped into VISUAL, CONTENT and TOOLS. This tour "
                "covers all three in 8 short steps - Skip any time.",
    },
    {
        "glyph": "map",
        "title": "VISUAL — open a mod, see the map",
        "body": "Open Mod loads an existing mod (yours or anything installed from the Steam "
                "Workshop) or starts a fresh one. Everything else in the app reads from and "
                "writes to whatever's open here.\n\n"
                "Map shows the mod's provinces and state ownership on a real, clickable map - "
                "useful for reassigning states or just seeing what a country actually owns.",
    },
    {
        "glyph": "target",
        "title": "CONTENT — the building blocks",
        "body": "Focus Tree, Events, Decisions and Ideas / Spirits are where most of a mod's "
                "actual gameplay lives. Each pairs a visual editor with the raw script, kept in "
                "sync both ways, plus a live in-game-style preview so you're not guessing what "
                "a focus or event will look like.\n\n"
                "Country, Flags, Ideologies and Factions build entirely new tags and political "
                "structures from scratch.",
    },
    {
        "glyph": "tech",
        "title": "CONTENT — the deeper systems",
        "body": "Past the basics, CONTENT also covers the systems most tools skip: Opinion "
                "Modifiers, On Actions, Peace Conference costs, War Goals, Decision Categories, "
                "Equipment tiers, Agency Upgrades, AI Strategy, Diplomatic Actions, Tech, Units "
                "and Starting Forces (land, air and naval).\n\n"
                "If you're not sure what one of these does, click the small ? next to its title "
                "- every tab has a plain-language explanation and a real example.",
    },
    {
        "glyph": "validate",
        "title": "TOOLS — catch problems before the game does",
        "body": "Validate scans the whole mod for broken references, unbalanced braces, and "
                "focus-tree prerequisite cycles that could never actually unlock. Icon Coverage "
                "checks every icon reference against real sprite files, so you find blank/red-X "
                "icons before a player does.\n\n"
                "Error Log is the newest one: after you actually launch and play the mod, it "
                "reads the game's own error.log and highlights which lines are about your mod's "
                "files, not vanilla noise.",
    },
    {
        "glyph": "diff",
        "title": "You can't break anything permanently",
        "body": "Ctrl+Z undoes the last change, Ctrl+Y redoes it - across any tab, in the order "
                "things actually happened. Editing a base-game file always copies it into your "
                "mod first; the original install is never touched.\n\n"
                "Settings also has Snapshots - a full save point you can create any time and "
                "roll back to later, independent of undo history.",
    },
    {
        "glyph": "replace",
        "title": "Shortcuts",
        "body": "Ctrl+K — search everything in the mod\n"
                "Ctrl+Z / Ctrl+Y — undo / redo\n"
                "Ctrl+S — export the current tab\n"
                "Ctrl+1..9 — jump straight to a tab",
    },
    {
        "glyph": "loc",
        "title": "Where to get help",
        "body": "Every tab's title has a ? button — click it any time for what that tab does, "
                "how it works, and a worked example.\n\n"
                "You can reopen this tour any time from the Settings tab. That's the whole tour "
                "- go build something.",
    },
]


def has_been_seen():
    return os.path.exists(MARKER)


def mark_seen():
    try:
        with open(MARKER, "w", encoding="utf-8") as f:
            f.write("1")
    except OSError:
        pass


class TourDialog(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("Quick Tour")
        self.geometry("560x400")
        self.resizable(False, False)
        self.transient(master)
        self.configure(background=theme.BG)
        self.step = 0

        head_row = ttk.Frame(self)
        head_row.pack(fill="x", padx=24, pady=(24, 4))
        self.icon_canvas = tk.Canvas(head_row, width=32, height=32, highlightthickness=0, bg=theme.BG)
        self.icon_canvas.pack(side="left", padx=(0, 12))
        self.title_lbl = ttk.Label(head_row, text="", font=(theme.FACE_DISPLAY, 15, "bold"))
        self.title_lbl.pack(side="left", anchor="w")

        ttk.Separator(self).pack(fill="x", padx=24, pady=(4, 12))

        self.body_lbl = ttk.Label(self, text="", wraplength=510, justify="left")
        self.body_lbl.pack(anchor="w", padx=24, fill="both", expand=True)

        self.step_label = ttk.Label(self, text="", style="Muted.TLabel")
        self.step_label.pack(pady=(0, 2))
        self.dots = ttk.Label(self, text="", foreground=theme.GOLD)
        self.dots.pack(pady=(0, 8))

        row = ttk.Frame(self)
        row.pack(fill="x", padx=24, pady=(0, 20))
        ttk.Button(row, text="Skip", command=self._finish).pack(side="left")
        self.next_btn = ttk.Button(row, text="Next", style="Accent.TButton", command=self._next)
        self.next_btn.pack(side="right")
        self.back_btn = ttk.Button(row, text="Back", command=self._back)
        self.back_btn.pack(side="right", padx=6)

        self._render()
        self.grab_set()

    def _render(self):
        step = STEPS[self.step]
        self.icon_canvas.delete("all")
        glyphs.draw(self.icon_canvas, step["glyph"], 2, 2, 28, theme.GOLD)
        self.title_lbl.config(text=step["title"])
        self.body_lbl.config(text=step["body"])
        self.step_label.config(text=f"Step {self.step + 1} of {len(STEPS)}")
        self.dots.config(text=" ".join("●" if i == self.step else "○" for i in range(len(STEPS))))
        self.back_btn.state(["disabled"] if self.step == 0 else ["!disabled"])
        self.next_btn.config(text="Let's go" if self.step == len(STEPS) - 1 else "Next")

    def _next(self):
        if self.step == len(STEPS) - 1:
            self._finish()
            return
        self.step += 1
        self._render()

    def _back(self):
        self.step = max(0, self.step - 1)
        self._render()

    def _finish(self):
        mark_seen()
        self.destroy()


def maybe_show(master):
    """Show the tour once, automatically, if it hasn't been seen before."""
    if has_been_seen():
        return
    TourDialog(master)


def show_now(master):
    """Force-open the tour regardless of whether it's been seen (Settings button)."""
    TourDialog(master)
