"""Reverse lookup: what fires/references a given id.

Every other search in this app goes forward - "this focus rewards event X".
This goes backward: given event X, what would break if it were deleted? That
question has no answer anywhere in the game's own files, because references
are one-directional, so it has to be rebuilt by scanning everything that
could point at it.

Deliberately text-based over parsed structures: a reference can appear
inside any effect or trigger block at any nesting depth, and the parsers
only expose the blocks they were written to understand. A token scan finds
them all, at the cost of also matching a mention inside a comment - which
strip_comments removes first.
"""

import os
import re

from app import mod_loader as ml
from app import mod_files
from app import pds_scan as scan


def _token_re(ref_id):
    """The id as a standalone token, so `germany.1` doesn't match inside
    `germany.14` and `my_focus` doesn't match inside `my_focus_two`."""
    return re.compile(rf"(?<![A-Za-z0-9_.]){re.escape(ref_id)}(?![A-Za-z0-9_.])")


# Blocks that structure an effect but aren't the thing being defined. If one
# of these is the nearest enclosing block, the useful name is further out -
# "inside complete_effect" says nothing about *whose* complete_effect it is.
_STRUCTURAL = {
    "complete_effect", "remove_effect", "effect", "completion_reward",
    "available", "visible", "allowed", "trigger", "immediate", "option",
    "ai_will_do", "ai_chance", "modifier", "decisions", "focuses",
    "focus_tree", "country_event", "news_event", "state_event", "if", "else",
    "limit", "random_list", "hidden_effect", "every_country", "any_country",
}


def _describe_owner(path, text, position, mod_root):
    """Best-effort name for whatever block the hit sits inside.

    Focuses and events declare themselves with `id = X`; decisions and ideas
    declare themselves as `my_id = {`. Structural wrappers are skipped so the
    answer is the content's own name, not the effect block it happens to be
    nested in."""
    before = text[:position]
    id_match = None
    for m in re.finditer(r"\bid\s*=\s*([A-Za-z0-9_.]+)", before):
        id_match = m
    if id_match:
        return id_match.group(1)
    named = [m.group(1) for m in
             re.finditer(r"^\s*([A-Za-z0-9_.]+)\s*=\s*\{", before, re.MULTILINE)]
    for name in reversed(named):
        if name not in _STRUCTURAL:
            return name
    return os.path.basename(path)


def find_references(mod_root, ref_id, progress=None):
    """[{file, line, owner, snippet}] for every place `ref_id` is mentioned.

    The definition site itself is included - seeing "defined here" alongside
    "used here" is what makes the list readable."""
    if not ref_id:
        return []
    pattern = _token_re(ref_id)
    out = []

    for path in mod_files.iter_script_files(mod_root):
        try:
            with open(path, "r", encoding="utf-8-sig", errors="ignore") as f:
                raw = f.read()
        except OSError:
            continue
        if ref_id not in raw:
            continue   # cheap reject before the real work
        text = scan.strip_comments(raw)
        for match in pattern.finditer(text):
            line_no = text.count("\n", 0, match.start()) + 1
            line_start = text.rfind("\n", 0, match.start()) + 1
            line_end = text.find("\n", match.start())
            snippet = text[line_start:line_end if line_end != -1 else len(text)].strip()
            out.append({
                "file": os.path.relpath(path, mod_root),
                "abs_path": path,
                "line": line_no,
                "owner": _describe_owner(path, text, match.start(), mod_root),
                "snippet": snippet[:160],
            })
        if progress:
            progress(f"{len(out)} reference(s) so far...")

    out.sort(key=lambda r: (r["file"], r["line"]))
    return out


def searchable_ids(mod_root):
    """Every focus/event/decision/idea id in the mod, for the picker."""
    ids = set()
    for path in ml.find_focus_tree_files(mod_root):
        try:
            for tree in ml.parse_focus_trees(path):
                for f in tree["focuses"]:
                    ids.add(f["id"])
        except OSError:
            continue
    for path in ml.find_event_files(mod_root):
        try:
            _, events = ml.parse_events(path)
        except OSError:
            continue
        for e in events:
            ids.add(f"{e['namespace']}.{e['number']}")
    for path in ml.find_decision_files(mod_root):
        try:
            for cat in ml.parse_decisions(path):
                for d in cat["decisions"]:
                    ids.add(d["id"])
        except OSError:
            continue
    for path in ml.find_idea_files(mod_root):
        try:
            for cat in ml.parse_ideas(path):
                for idea in cat["ideas"]:
                    ids.add(idea["id"])
        except OSError:
            continue
    return sorted(ids)


def _orphan_candidates(mod_root):
    """Only the kinds where "nothing references it" actually means dead.

    Decisions and focuses are player-facing: the game finds them structurally
    (a decision is listed in its category, a focus in its tree) and nothing
    ever needs to name them in script. Reporting those would mark almost
    every one as an orphan and bury the real findings.

    Events and ideas are the opposite - an event is only reachable if
    something fires it, and an idea only matters if something adds it - so
    an unreferenced one really is unreachable content.
    """
    out = []
    for path in ml.find_event_files(mod_root):
        try:
            _, events = ml.parse_events(path)
        except OSError:
            continue
        for e in events:
            # an event that isn't triggered-only can fire itself on MTTH, so
            # having nothing call it by id is expected, not suspicious
            if not e.get("is_triggered_only", True):
                continue
            out.append(("event", f"{e['namespace']}.{e['number']}"))

    for path in ml.find_idea_files(mod_root):
        try:
            categories = ml.parse_ideas(path)
        except OSError:
            continue
        for cat in categories:
            # advisor-slot ideas are picked by the player from a menu, the
            # same structural-not-referenced case as decisions
            if cat["category"] != "country":
                continue
            for idea in cat["ideas"]:
                out.append(("idea", idea["id"]))
    return out


def find_orphans(mod_root, progress=None):
    """[{kind, id, file}] for content nothing else mentions.

    Read as "worth a look", not "delete this" - an event can still be fired
    from an on_action in a different mod, or be intended for a chain that
    isn't written yet.
    """
    candidates = _orphan_candidates(mod_root)
    if not candidates:
        return []

    # one pass over every file, counting mentions of everything at once -
    # scanning the whole mod separately per id would be O(ids x files)
    texts = []
    for path in mod_files.iter_script_files(mod_root):
        try:
            with open(path, "r", encoding="utf-8-sig", errors="ignore") as f:
                texts.append((path, scan.strip_comments(f.read())))
        except OSError:
            continue

    orphans = []
    for i, (kind, ref_id) in enumerate(candidates):
        if progress and i % 50 == 0:
            progress(f"Checking {i}/{len(candidates)}...")
        pattern = _token_re(ref_id)
        mentions = 0
        where = None
        for path, text in texts:
            if ref_id not in text:
                continue
            hits = len(pattern.findall(text))
            if hits and where is None:
                where = os.path.relpath(path, mod_root)
            mentions += hits
            if mentions > 1:
                break
        # exactly one mention == only the definition itself
        if mentions <= 1:
            orphans.append({"kind": kind, "id": ref_id, "file": where or "(not found)"})
    return orphans


# ---- UI ----

def open_dialog(master, mod_root, ref_id):
    """Show every place `ref_id` is referenced, with a jump-to-file action."""
    import tkinter as tk
    from tkinter import ttk
    from app import theme

    dlg = tk.Toplevel(master)
    dlg.title(f"References to {ref_id}")
    dlg.geometry("900x460")
    outer = ttk.Frame(dlg, padding=12)
    outer.pack(fill="both", expand=True)

    ttk.Label(outer, text=f"REFERENCES TO {ref_id}", style="PageTitle.TLabel").pack(anchor="w")
    hint = ttk.Label(outer, text="Scanning every script file...", style="Muted.TLabel",
                     wraplength=820, justify="left")
    hint.pack(anchor="w", pady=(2, 8))
    dlg.update_idletasks()

    rows = find_references(mod_root, ref_id)

    cols = ("owner", "file", "line", "snippet")
    tree = ttk.Treeview(outer, columns=cols, show="headings")
    for col, width in (("owner", 200), ("file", 240), ("line", 60), ("snippet", 380)):
        tree.heading(col, text=col.upper())
        tree.column(col, width=width, anchor=("e" if col == "line" else "w"))
    bar = ttk.Scrollbar(outer, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=bar.set)
    tree.pack(side="left", fill="both", expand=True)
    bar.pack(side="right", fill="y")

    for i, r in enumerate(rows):
        tree.insert("", "end", iid=str(i), values=(r["owner"], r["file"], r["line"], r["snippet"]))

    if rows:
        hint.config(
            text=f"{len(rows)} mention(s), including where it's defined. Double-click a row to open "
                 "that file in the Code tab at the exact line. Deleting this id breaks everything "
                 "listed here that isn't the definition itself.")
    else:
        hint.config(text=f"Nothing references {ref_id} anywhere in this mod - it may be dead content.")

    def jump(_event=None):
        sel = tree.selection()
        if not sel:
            return
        r = rows[int(sel[0])]
        app = master.winfo_toplevel()
        if hasattr(app, "show") and hasattr(app, "tabs") and "code" in app.tabs:
            app.show("code")
            app.tabs["code"].open_file(r["abs_path"], line=r["line"])
            dlg.destroy()

    tree.bind("<Double-Button-1>", jump)
    ttk.Button(dlg, text="Close", command=dlg.destroy).pack(pady=(0, 10))
    dlg.grab_set()
    return dlg
