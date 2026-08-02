"""Ctrl+K: one box that searches every focus, event, decision, idea, tech
and script file in the mod at once, instead of remembering which of the
eight tabs a thing lives in before you can even start typing its name.

The index is intentionally shallow - id/title/file name, not full body text
- because it has to rebuild fast enough to feel instant right after a mod
loads. Picking a result jumps to that tab and drops the term into its own
search box, reusing the filtering each tab already does rather than
duplicating it here.
"""

import os
import tkinter as tk
from tkinter import ttk

from app import mod_loader as ml
from app import mod_files
from app import tech_tab
from app import theme


def build_index(mod_root):
    """[{kind, tab, label, term, sub}] - `term` is what gets dropped into the
    destination tab's own search box, `sub` is a short right-aligned hint."""
    items = []

    for path in ml.find_focus_tree_files(mod_root):
        for tree in ml.parse_focus_trees(path):
            for focus in tree["focuses"]:
                items.append({"kind": "Focus", "tab": "focus", "label": focus["id"],
                             "term": focus["id"], "sub": tree.get("id", "")})

    for path in ml.find_event_files(mod_root):
        _, events = ml.parse_events(path)
        for event in events:
            full_id = f"{event['namespace']}.{event['number']}"
            items.append({"kind": "Event", "tab": "events", "label": full_id,
                         "term": full_id, "sub": event.get("type", "")})

    for path in ml.find_decision_files(mod_root):
        for category in ml.parse_decisions(path):
            for decision in category["decisions"]:
                items.append({"kind": "Decision", "tab": "decisions", "label": decision["id"],
                             "term": decision["id"], "sub": category.get("id", "")})

    for path in ml.find_idea_files(mod_root):
        for category in ml.parse_ideas(path):
            for idea in category["ideas"]:
                items.append({"kind": "Idea", "tab": "ideas", "label": idea["id"],
                             "term": idea["id"], "sub": category.get("id", "")})

    for path in tech_tab.find_tech_files(mod_root):
        _, techs = tech_tab.parse_techs(path)
        for tech_id, _, _ in techs:
            items.append({"kind": "Tech", "tab": "tech", "label": tech_id,
                         "term": tech_id, "sub": os.path.basename(path)})

    for tag, chars in ml.load_country_characters(mod_root).items():
        for char in chars:
            items.append({"kind": "Character", "tab": "characters", "label": char["id"],
                         "term": tag, "sub": ", ".join(char["roles"]) or tag})

    for path in mod_files.iter_script_files(mod_root):
        rel = os.path.relpath(path, mod_root)
        items.append({"kind": "File", "tab": "code", "label": os.path.basename(path),
                     "term": path, "sub": os.path.dirname(rel)})

    return items


def _fuzzy_score(text, needle):
    """None if `needle`'s letters don't all appear in order in `text`;
    otherwise a score where lower is better - a tighter, earlier match beats
    a scattered one. Lets "grmfp" find "GER_four_year_plan" without typing
    it out, the way editor command palettes do."""
    pos = 0
    span_start = None
    for ch in needle:
        idx = text.find(ch, pos)
        if idx == -1:
            return None
        if span_start is None:
            span_start = idx
        pos = idx + 1
    span = pos - span_start
    return span * 10 + span_start


def _matches(item, needle):
    """Kept for compatibility with any direct caller; the palette itself
    uses _fuzzy_score for ranking."""
    return needle in item["label"].lower() or needle in item["sub"].lower()


class SearchPalette(tk.Toplevel):
    """A floating filter box - Escape or losing focus closes it, Enter or a
    click jumps to the result."""

    def __init__(self, master, index, on_pick):
        super().__init__(master)
        self.overrideredirect(True)
        self.configure(background=theme.GOLD_DIM, padx=1, pady=1)
        self.index = index
        self.on_pick = on_pick
        self._visible = []
        self._build()
        self._place(master)
        self.bind("<FocusOut>", lambda e: self.after(120, self._maybe_close))
        self.entry.focus_set()

    def _place(self, master):
        w, h = 560, 360
        x = master.winfo_rootx() + (master.winfo_width() - w) // 2
        y = master.winfo_rooty() + 90
        self.geometry(f"{w}x{h}+{max(x, 0)}+{max(y, 0)}")

    def _build(self):
        frame = ttk.Frame(self, style="Card.TFrame", padding=10)
        frame.pack(fill="both", expand=True)

        self.var = tk.StringVar()
        self.entry = ttk.Entry(frame, textvariable=self.var, font=(theme.FACE_UI, 13))
        self.entry.pack(fill="x")
        self.entry.bind("<KeyRelease>", self._on_key)
        self.entry.bind("<Return>", lambda e: self._pick(self._selected_index()))
        self.entry.bind("<Down>", lambda e: self._move(1))
        self.entry.bind("<Up>", lambda e: self._move(-1))
        self.entry.bind("<Escape>", lambda e: self.destroy())

        ttk.Label(frame, text=f"{len(self.index)} things indexed — focuses, events, "
                              "decisions, ideas, techs, files", style="Muted.TLabel",
                 background=theme.SURFACE).pack(anchor="w", pady=(4, 6))

        self.listbox = tk.Listbox(frame, activestyle="none", font=(theme.FACE_UI, 10),
                                  highlightthickness=0, borderwidth=0)
        self.listbox.pack(fill="both", expand=True)
        self.listbox.bind("<Double-Button-1>", lambda e: self._pick(self._clicked_index(e)))
        self.listbox.bind("<Return>", lambda e: self._pick(self._selected_index()))

        self._refresh("")

    def _refresh(self, needle):
        if needle:
            scored = []
            for item in self.index:
                label_score = _fuzzy_score(item["label"].lower(), needle)
                sub_score = _fuzzy_score(item["sub"].lower(), needle)
                best = None
                if label_score is not None:
                    best = label_score
                if sub_score is not None and (best is None or sub_score + 1000 < best):
                    best = sub_score + 1000   # a label hit always outranks a sub-only hit
                if best is not None:
                    scored.append((best, item))
            scored.sort(key=lambda pair: pair[0])
            self._visible = [item for _, item in scored[:200]]
        else:
            self._visible = self.index[:200]
        self.listbox.delete(0, "end")
        for item in self._visible:
            self.listbox.insert("end", f"  {item['kind']:<9} {item['label']}"
                                       + (f"   ({item['sub']})" if item["sub"] else ""))
        if self._visible:
            self.listbox.selection_set(0)

    def _on_key(self, event):
        if event.keysym in ("Down", "Up", "Return", "Escape"):
            return
        self._refresh(self.var.get().strip().lower())

    def _move(self, delta):
        if not self._visible:
            return
        sel = self.listbox.curselection()
        idx = (sel[0] if sel else -1) + delta
        idx = max(0, min(len(self._visible) - 1, idx))
        self.listbox.selection_clear(0, "end")
        self.listbox.selection_set(idx)
        self.listbox.see(idx)

    def _selected_index(self):
        sel = self.listbox.curselection()
        return sel[0] if sel else None

    def _clicked_index(self, event):
        return self.listbox.nearest(event.y)

    def _pick(self, idx):
        if idx is None or not (0 <= idx < len(self._visible)):
            return
        self.on_pick(self._visible[idx])
        self.destroy()

    def _maybe_close(self):
        try:
            if self.focus_get() not in (self.entry, self.listbox):
                self.destroy()
        except (KeyError, tk.TclError):
            self.destroy()
