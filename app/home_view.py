"""Static shell of the Home screen: banner, the three-zone body (rail / mod
browser / inspector), and the status bar.

Pure layout - it builds the sidebar/table/inspector widgets and wires them
to a `controller` object's public methods, but does not itself decide what
any control does. That split is what let the redesign's perf fixes land in
home_data.py/home_table.py without touching a line of layout code.
"""

import tkinter as tk
from tkinter import ttk

from app import home_theme as ht
from app import version
from app.home_inspector import HomeInspector
from app.home_sidebar import HomeSidebar
from app.home_table import HomeTable
from app.mod_browser import DEFAULT_STEAM_WORKSHOP


class HomeView(ttk.Frame):
    def __init__(self, master, controller):
        super().__init__(master, style="Home.TFrame", padding=0)
        self.controller = controller
        self._build()

    def _build(self):
        self._banner()

        body = ttk.Frame(self, style="Home.TFrame")
        body.pack(fill="both", expand=True)
        body.columnconfigure(2, weight=1)
        body.rowconfigure(0, weight=1)

        c = self.controller
        self.sidebar = HomeSidebar(
            body, c.data, on_resume=c.open_mod, on_new_mod=c.new_mod,
            on_open_folder=c.open_folder)
        self.sidebar.grid(row=0, column=0, sticky="ns")

        ttk.Frame(body, style="Home.Sash.TFrame", width=1).grid(row=0, column=1, sticky="ns")

        center = ttk.Frame(body, style="Home.TFrame")
        center.grid(row=0, column=2, sticky="nsew")
        self.table = HomeTable(
            center, c.data, on_selection_changed=c.on_selection_changed,
            on_open=c.open_mod, on_refresh=c.refresh, on_browse=c.browse,
            on_add_folder=c.add_local_folder)
        self.table.pack(fill="both", expand=True)

        ttk.Frame(body, style="Home.Sash.TFrame", width=1).grid(row=0, column=3, sticky="ns")

        self.inspector = HomeInspector(
            body, c.data, on_open=c.open_mod, on_duplicate=c.duplicate_mod,
            on_validate_one=c.validate_one, on_validate_many=c.validate_many,
            on_open_folder=c.open_folder)
        self.inspector.grid(row=0, column=4, sticky="ns")

        self._status_bar()

    def _banner(self):
        bar = ttk.Frame(self, style="Home.Panel.TFrame", padding=0)
        bar.pack(fill="x")
        bar.pack_propagate(False)
        # Windows text scaling can make the two-line brand block taller than
        # the old fixed 88 px header, clipping its subtitle.  Leave enough
        # vertical room at 100–150% DPI while retaining the dense layout.
        bar.configure(height=108)

        accent = tk.Frame(bar, width=2, background=ht.ACCENT)
        accent.pack(side="left", fill="y", padx=(20, 18), pady=16)

        left = ttk.Frame(bar, style="Home.Panel.TFrame")
        left.pack(side="left", fill="y", pady=18)
        ttk.Label(left, text="HOI4 MOD MAKER", style="Home.Wordmark.TLabel").pack(anchor="w")
        ttk.Label(left, text="Build focus trees, events, decisions, ideas and leaders — "
                             "no Paradox scripting required.",
                  style="Home.PanelMuted.TLabel").pack(anchor="w", pady=(4, 0))

        right = ttk.Frame(bar, style="Home.Panel.TFrame")
        right.pack(side="right", fill="y", padx=20, pady=18)

        detected_full = self.controller.data.detected_full

        game_box = ttk.Frame(right, style="Home.Panel.TFrame")
        game_box.pack(side="left")
        ttk.Label(game_box, text="GAME DETECTED", style="Home.Eyebrow.TLabel",
                  font=(ht.FACE_MONO, 8)).pack(anchor="e")
        game_row = ttk.Frame(game_box, style="Home.Panel.TFrame")
        game_row.pack(anchor="e", pady=(3, 0))
        dot_color = ht.OK if detected_full else ht.TEXT_OFF
        dot = tk.Canvas(game_row, width=7, height=7, highlightthickness=0, background=ht.PANEL)
        dot.pack(side="left", padx=(0, 6))
        dot.create_oval(1, 1, 6, 6, fill=dot_color, outline="")
        text = f"Hearts of Iron IV {detected_full}" if detected_full else "Not found"
        ttk.Label(game_row, text=text, style="Home.Panel.TLabel",
                  font=(ht.FACE_MONO, 10)).pack(side="left")

        tk.Frame(right, width=1, background=ht.LINE).pack(side="left", fill="y", padx=20)

        mm_box = ttk.Frame(right, style="Home.Panel.TFrame")
        mm_box.pack(side="left")
        ttk.Label(mm_box, text="MOD MAKER", style="Home.Eyebrow.TLabel",
                  font=(ht.FACE_MONO, 8)).pack(anchor="e")
        ttk.Label(mm_box, text=f"v{version.VERSION}", style="Home.PanelMuted.TLabel",
                  font=(ht.FACE_MONO, 10)).pack(anchor="e", pady=(3, 0))

        tk.Frame(self, height=1, background=ht.LINE_STRONG).pack(fill="x")

    def _status_bar(self):
        bar = ttk.Frame(self, style="Home.Panel.TFrame", padding=(12, 4))
        bar.pack(fill="x", side="bottom")
        tk.Frame(self, height=1, background=ht.LINE_STRONG).pack(fill="x", side="bottom")

        ready = ttk.Frame(bar, style="Home.Panel.TFrame")
        ready.pack(side="left")
        dot = tk.Canvas(ready, width=6, height=6, highlightthickness=0, background=ht.PANEL)
        dot.pack(side="left", padx=(0, 6))
        dot.create_oval(1, 1, 5, 5, fill=ht.OK, outline="")
        ttk.Label(ready, text="Ready", style="Home.Panel.TLabel",
                  font=(ht.FACE_MONO, 9)).pack(side="left")

        self._sep(bar)
        self.status_mod_label = ttk.Label(bar, text="No mod open", style="Home.PanelMuted.TLabel",
                                          font=(ht.FACE_MONO, 9))
        self.status_mod_label.pack(side="left")
        self._sep(bar)
        ttk.Label(bar, text=DEFAULT_STEAM_WORKSHOP or "(no Workshop folder found)",
                  style="Home.PanelMuted.TLabel", font=(ht.FACE_MONO, 9)).pack(side="left")

        self.status_count_label = ttk.Label(bar, text="", style="Home.PanelMuted.TLabel",
                                            font=(ht.FACE_MONO, 9))
        self.status_count_label.pack(side="right")

    def _sep(self, parent):
        tk.Frame(parent, width=1, height=12, background=ht.LINE_STRONG).pack(
            side="left", padx=12)
