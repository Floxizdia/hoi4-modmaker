"""The left rail: Continue / Start something new / Getting started, plus
the pinned backup tip at the bottom.

Rebuilt as a whole (`rebuild()`) rather than patched piecemeal, because
which cards even appear depends on whether there's a recent mod at all -
same as the original screen. Async lookups (file count, health, "has a
focus tree yet") go through the injected `HomeData` and re-trigger a
rebuild only the one time an answer resolves from unknown, not on a timer.
"""

import tkinter as tk
from tkinter import ttk
import os

from app import home_data
from app import home_theme as ht
from app import recent
from app import ui_kit


class HomeSidebar(ttk.Frame):
    def __init__(self, parent, data, *, on_resume, on_new_mod, on_open_folder):
        super().__init__(parent, style="Home.Surface.TFrame", padding=12, width=300)
        self.grid_propagate(False)
        self.data = data
        self._on_resume = on_resume
        self._on_new_mod = on_new_mod
        self._on_open_folder = on_open_folder
        self._thumbs = {}
        self.rebuild()

    # ---- shared card chrome ----

    def _card(self, parent, title, right_text=None):
        card = ttk.Frame(parent, style="Home.Card.TFrame")
        head = ttk.Frame(card, style="Home.CardHead.TFrame", padding=(12, 6))
        head.pack(fill="x")
        ttk.Label(head, text=title.upper(), style="Home.Eyebrow.TLabel").pack(side="left")
        if right_text:
            ttk.Label(head, text=right_text, style="Home.Eyebrow.TLabel").pack(side="right")
        tk.Frame(card, height=1, background=ht.LINE).pack(fill="x")
        body = ttk.Frame(card, style="Home.Surface.TFrame", padding=12)
        body.pack(fill="both", expand=True)
        return card, body

    # ---- whole-rail rebuild ----

    def rebuild(self):
        for child in self.winfo_children():
            child.destroy()

        entry = recent.last()
        cards = []
        if entry:
            cards.append(self._build_continue_card)
        cards.append(self._build_new_mod_card)
        cards.append(self._build_checklist_card)
        if not entry:
            cards = cards[::-1][:1] + cards[:-1]   # checklist promoted to top with no history

        for i, builder in enumerate(cards):
            card = builder(self)
            card.pack(fill="x", pady=(0, 12) if i < len(cards) - 1 else 0)

        spacer = ttk.Frame(self, style="Home.Surface.TFrame")
        spacer.pack(fill="both", expand=True)

        tip = ttk.Frame(self, style="Home.Panel.TFrame", padding=(11, 9))
        tip.pack(fill="x", pady=(12, 0))
        row = ttk.Frame(tip, style="Home.Panel.TFrame")
        row.pack(fill="x")
        ttk.Label(row, text="▲", style="Home.Warn.TLabel", background=ht.PANEL).pack(
            side="left", anchor="n", padx=(0, 8))
        text_col = ttk.Frame(row, style="Home.Panel.TFrame")
        text_col.pack(side="left", fill="x", expand=True)
        ttk.Label(text_col, text="Back up before you export", style="Home.Panel.TLabel").pack(
            anchor="w")
        ttk.Label(text_col, text="Mod Maker keeps the last 5 exports in /backups.",
                  style="Home.PanelMuted.TLabel", wraplength=250,
                  justify="left").pack(anchor="w", pady=(1, 0))

    # ---- Continue ----

    def _build_continue_card(self, parent):
        entry = recent.last()
        card, body = self._card(parent, "Continue")
        row = ttk.Frame(body, style="Home.Surface.TFrame")
        row.pack(fill="x", pady=(0, 10))
        photo = home_data.load_thumb(entry["path"])
        thumb = tk.Canvas(row, width=home_data.THUMB_SIZE[0], height=home_data.THUMB_SIZE[1],
                          highlightthickness=1, highlightbackground=ht.LINE_STRONG,
                          background=ht.RAISED, bd=0)
        thumb.pack(side="left", padx=(0, 10))
        if photo is not None:
            self._thumbs["continue"] = photo
            thumb.create_image(0, 0, image=photo, anchor="nw")
        text_col = ttk.Frame(row, style="Home.Surface.TFrame")
        text_col.pack(side="left", fill="x", expand=True)
        ttk.Label(text_col, text=entry["name"], style="Home.CardTitle.TLabel").pack(anchor="w")
        opened_text = recent.ago(entry.get("opened", 0))
        file_count_label = ttk.Label(text_col, text=f"last opened {opened_text}",
                                     style="Home.SurfaceMuted.TLabel")
        file_count_label.pack(anchor="w", pady=(2, 0))
        self.data.show_file_count_async(
            entry["path"],
            lambda n: self._apply_file_count(file_count_label, opened_text, n))

        health_row = ttk.Frame(body, style="Home.Panel.TFrame", padding=(8, 5))
        health_row.pack(fill="x", pady=(0, 10))
        dot = tk.Canvas(health_row, width=5, height=5, highlightthickness=0, background=ht.PANEL)
        dot.pack(side="left", padx=(0, 7))
        dot.create_oval(0, 0, 5, 5, fill=ht.ACCENT, outline="")
        health_label = ttk.Label(health_row, text="Checking mod health…", style="Home.PanelMuted.TLabel")
        health_label.pack(side="left")
        self.data.check_health_async(
            entry["path"], lambda stats: self._apply_health_label(health_label, stats))

        actions = ttk.Frame(body, style="Home.Surface.TFrame")
        actions.pack(fill="x")
        resume_btn = ttk.Button(actions, text="Resume", style="Home.Primary.TButton",
                                command=lambda: self._on_resume(entry["path"]))
        resume_btn.pack(side="left", fill="x", expand=True, padx=(0, 6))
        ui_kit.attach_tooltip(resume_btn, "Open this mod again (Ctrl+Shift+R).")
        folder_btn = ttk.Button(actions, text="⌸", width=3, style="Home.Secondary.TButton",
                                command=lambda: self._on_open_folder(entry["path"]))
        folder_btn.pack(side="left", padx=(0, 6))
        ui_kit.attach_tooltip(folder_btn, "Open this mod's folder in Explorer.")
        return card

    def _apply_file_count(self, label, opened_text, n):
        if not label.winfo_exists():
            return
        label.config(text=f"last opened {opened_text}" + (f" · {n} files" if n is not None else ""))

    def _apply_health_label(self, label, stats):
        if not label.winfo_exists():
            return
        if stats is None:
            label.config(text="")
        elif stats["errors"]:
            label.config(text=f"⚠ {stats['errors']} structural error(s)", foreground=ht.ERR)
        else:
            label.config(text="No structural errors found", foreground=ht.OK)

    # ---- Start something new ----

    def _build_new_mod_card(self, parent):
        card, body = self._card(parent, "Start something new")
        ttk.Label(body, text="Create a new mod", style="Home.CardTitle.TLabel").pack(anchor="w")
        ttk.Label(body, text="Start from scratch. Sets up descriptor.mod and the folder "
                             "structure, then opens the generator tabs.",
                  style="Home.SurfaceMuted.TLabel", wraplength=250,
                  justify="left").pack(anchor="w", pady=(4, 10))
        row = ttk.Frame(body, style="Home.Surface.TFrame")
        row.pack(fill="x")
        new_btn = ttk.Button(row, text="+ New mod", style="Home.Secondary.TButton",
                             command=self._on_new_mod)
        new_btn.pack(side="left", fill="x", expand=True)
        ui_kit.attach_tooltip(new_btn, "Set up a brand new mod folder (Ctrl+N).")
        return card

    # ---- Getting started ----

    def _build_checklist_card(self, parent):
        entry = recent.last()
        mod_path = entry["path"] if entry else None

        def exists(*parts):
            return mod_path is not None and os.path.exists(os.path.join(mod_path, *parts))

        focus_done = False
        if mod_path is not None:
            cached = self.data.focus_check_result(mod_path)
            if cached is None:
                self.data.check_focus_tree_async(mod_path, self.rebuild)
            else:
                focus_done = cached

        steps = [
            ("Create or open a mod", None, mod_path is not None),
            ("Add starter content", "characters, history, guide", exists("STARTER_GUIDE.txt")),
            ("Build a focus tree", None, focus_done),
            ("Run Validate to catch mistakes", None, False),
            ("Export the mod and try it in-game", None, False),
        ]
        done_count = sum(1 for *_, d in steps if d)

        card, body = self._card(parent, "Getting started", f"{done_count} / {len(steps)}")
        track = tk.Canvas(card, height=2, highlightthickness=0, background=ht.CANVAS, bd=0)
        track.pack(fill="x")
        card.update_idletasks()

        def draw_track(_=None):
            track.delete("all")
            w = max(track.winfo_width(), 1)
            frac = done_count / len(steps)
            track.create_rectangle(0, 0, w * frac, 2, fill=ht.ACCENT, outline="")
        ui_kit.repaint_on_becoming_visible(track, draw_track)

        ttk.Label(body, text="First time making a mod? Work through these in order.",
                  style="Home.SurfaceMuted.TLabel", wraplength=250,
                  justify="left").pack(anchor="w", pady=(0, 10))

        next_marked = False
        for i, (text, sub, done) in enumerate(steps, 1):
            is_next = (not done) and not next_marked
            if is_next:
                next_marked = True
            row = ttk.Frame(body, style="Home.Selection.TFrame" if is_next else "Home.Surface.TFrame")
            row.pack(fill="x", pady=1)
            mark = tk.Canvas(row, width=15, height=15, highlightthickness=1,
                             highlightbackground=(ht.ACCENT_DIM if is_next else
                                                  (ht.OK if done else ht.LINE_STRONG)),
                             background=(ht.SELECTION if is_next else
                                         ("#16302B" if done else ht.CANVAS)), bd=0)
            mark.pack(side="left", padx=(2, 9), pady=4)
            mark.create_text(7, 7, text=("✓" if done else str(i)),
                             fill=(ht.OK if done else (ht.ACCENT_HI if is_next else ht.TEXT_LOW)),
                             font=(ht.FACE_MONO, 8, "bold" if is_next else "normal"))
            text_col = ttk.Frame(row, style=row["style"])
            text_col.pack(side="left", fill="x", expand=True, pady=3)
            lbl = tk.Label(text_col, text=text, background=(ht.SELECTION if is_next else ht.SURFACE),
                          foreground=(ht.TEXT_LOW if done else (ht.TEXT_HI if is_next else ht.TEXT_MID)),
                          font=(ht.FACE_UI, 9, "overstrike" if done else "normal"), anchor="w")
            lbl.pack(anchor="w")
            if sub and is_next:
                ttk.Label(text_col, text=sub, style="Home.SurfaceMuted.TLabel",
                          font=(ht.FACE_UI, 8)).pack(anchor="w")

        tk.Frame(card, height=1, background=ht.LINE).pack(fill="x", pady=(8, 0))
        footer = ttk.Frame(card, style="Home.Surface.TFrame", padding=(12, 7))
        footer.pack(fill="x")
        ttk.Label(footer, text="Open the modding guide", style="Home.SurfaceMuted.TLabel").pack(side="left")
        ttk.Label(footer, text="F1", style="Home.MonoMuted.TLabel").pack(side="right")
        return card
