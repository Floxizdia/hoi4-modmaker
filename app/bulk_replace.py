"""Search and replace across every script file in the mod at once.

The dangerous part of a tool like this isn't the replace, it's doing it
blind — so Find always runs first and shows exactly which files and how
many hits, and Replace re-confirms that same count before touching a single
byte. Every touched file gets the same one-time .bak the rest of the app
uses, so a bad replace is exactly as recoverable as a bad manual edit.
"""

import os
import re
import shutil
import tkinter as tk
from tkinter import ttk, messagebox

from app.state import state
from app import mod_files
from app import tag_rename
from app import theme, ui_kit


def find_matches(mod_root, needle, *, regex=False, case_sensitive=False):
    """{path: count} for every file with at least one hit. Raises re.error
    if `regex` is set and the pattern doesn't compile."""
    if not needle:
        return {}
    flags = 0 if case_sensitive else re.IGNORECASE
    pattern = re.compile(needle if regex else re.escape(needle), flags)
    out = {}
    for path in mod_files.iter_script_files(mod_root):
        try:
            text = mod_files.read_text(path)
        except OSError:
            continue
        n = len(pattern.findall(text))
        if n:
            out[path] = n
    return out


def replace_in_files(paths, needle, replacement, *, regex=False, case_sensitive=False):
    """Applies the replacement to every path, backing each up once first.
    Returns (files_changed, total_replacements)."""
    flags = 0 if case_sensitive else re.IGNORECASE
    pattern = re.compile(needle if regex else re.escape(needle), flags)
    # re.sub always interprets backslash escapes in the replacement (\1, \g<0>,
    # ...) even for a literal search - in plain-text mode that surprises
    # anyone replacing with a Windows path or similar, so it's escaped away
    repl = replacement if regex else replacement.replace("\\", "\\\\")
    changed = 0
    total = 0
    for path in paths:
        try:
            text = mod_files.read_text(path)
        except OSError:
            continue
        new_text, n = pattern.subn(repl, text)
        if n == 0:
            continue
        backup = path + ".bak"
        if not os.path.exists(backup):
            shutil.copy2(path, backup)
        with open(path, "w", encoding="utf-8") as f:
            f.write(new_text)
        changed += 1
        total += n
    return changed, total


class BulkReplaceTab(ttk.Frame):
    def __init__(self, master):
        super().__init__(master, padding=12)
        self._matches = {}
        self._build()
        state.subscribe(self.on_mod_changed)

    def _build(self):
        self.header = ui_kit.PageHeader(
            self, "Find & Replace",
            "Search-and-replace across every file in the mod at once, with a preview before anything is written.", help_key="replace")

        form = ttk.Frame(self)
        form.pack(fill="x")
        ttk.Label(form, text="Find").grid(row=0, column=0, sticky="w", padx=(0, 6), pady=3)
        self.find_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.find_var, width=44).grid(row=0, column=1, sticky="w", pady=3)
        ttk.Label(form, text="Replace with").grid(row=1, column=0, sticky="w", padx=(0, 6), pady=3)
        self.replace_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.replace_var, width=44).grid(row=1, column=1, sticky="w", pady=3)

        opts = ttk.Frame(form)
        opts.grid(row=0, column=2, rowspan=2, padx=16, sticky="w")
        self.regex_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(opts, text="Regex", variable=self.regex_var).pack(anchor="w")
        self.case_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(opts, text="Case sensitive", variable=self.case_var).pack(anchor="w")

        ttk.Button(form, text="Find in Mod", style="Accent.TButton",
                   command=self._find).grid(row=0, column=3, rowspan=2, padx=(16, 0))
        ttk.Button(form, text="Rename a country tag...",
                   command=self._rename_tag).grid(row=0, column=4, rowspan=2, padx=(8, 0))

        ttk.Label(
            self,
            text="Handy for a tag rename (TUR → OTT) or fixing a misspelled focus id everywhere it's "
                 "referenced. Find always runs first so you see exactly what will change before anything "
                 "is written; matched files each get a one-time .bak, same as every other edit in this tool.",
            style="Muted.TLabel", wraplength=980, justify="left",
        ).pack(fill="x", pady=(8, 4))

        body = ttk.Frame(self)
        body.pack(fill="both", expand=True, pady=6)
        self.tree = ttk.Treeview(body, columns=("hits",), show="tree headings")
        self.tree.heading("#0", text="File")
        self.tree.heading("hits", text="Matches")
        self.tree.column("#0", width=760)
        self.tree.column("hits", width=90, anchor="center")
        bar = ttk.Scrollbar(body, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=bar.set)
        self.tree.pack(side="left", fill="both", expand=True)
        bar.pack(side="right", fill="y")

        btns = ttk.Frame(self)
        btns.pack(fill="x")
        self.replace_btn = ttk.Button(btns, text="Replace All", command=self._replace, state="disabled")
        self.replace_btn.pack(side="left")
        self.status = ttk.Label(btns, text="", style="Status.TLabel", wraplength=900, justify="left")
        self.status.pack(side="left", padx=10)

        self.on_mod_changed()

    def on_mod_changed(self):
        if state.is_loaded:
            self.header.set_status(True, state.mod_name)
        else:
            self.header.set_status(False, "no mod open")
        self._matches = {}
        self.tree.delete(*self.tree.get_children())
        self.replace_btn.configure(state="disabled")

    def _rename_tag(self):
        """A tag rename is not a text replace: it also has to move
        `TAG - Name.txt` and `gfx/flags/TAG.tga`, and it must not fire on the
        same three letters appearing inside another word or identifier. That
        lives in tag_rename.py; this just drives it."""
        if not state.is_loaded:
            messagebox.showerror("No mod", "Open a mod first.")
            return
        TagRenameDialog(self, on_done=lambda msg: self.status.config(text=msg))

    def _find(self):
        if not state.is_loaded:
            messagebox.showerror("No mod", "Open a mod first.")
            return
        needle = self.find_var.get()
        if not needle:
            messagebox.showerror("Nothing to find", "Type something to search for.")
            return
        try:
            self._matches = find_matches(state.mod_root, needle,
                                         regex=self.regex_var.get(),
                                         case_sensitive=self.case_var.get())
        except re.error as exc:
            messagebox.showerror("Bad pattern", f"That regex doesn't compile: {exc}")
            return
        self.tree.delete(*self.tree.get_children())
        for path, count in sorted(self._matches.items(), key=lambda kv: -kv[1]):
            self.tree.insert("", "end", text=" " + os.path.relpath(path, state.mod_root),
                             values=(count,))
        total = sum(self._matches.values())
        self.replace_btn.configure(state="normal" if self._matches else "disabled")
        self.status.config(
            text=f"{total} match(es) across {len(self._matches)} file(s)." if self._matches
            else "No matches.")

    def _replace(self):
        if not self._matches:
            return
        total = sum(self._matches.values())
        if not messagebox.askyesno(
            "Replace everywhere?",
            f"Replace {total} match(es) across {len(self._matches)} file(s)?\n\n"
            "Each changed file gets a one-time .bak backup first."):
            return
        try:
            changed, count = replace_in_files(
                list(self._matches), self.find_var.get(), self.replace_var.get(),
                regex=self.regex_var.get(), case_sensitive=self.case_var.get())
        except re.error as exc:
            # Find already validated the search pattern; this is the
            # replacement side - e.g. a regex backreference like \1 that
            # doesn't correspond to a capture group in the pattern.
            self.status.config(text=f"Replacement text isn't valid for this pattern: {exc}")
            return
        self.status.config(text=f"Replaced {count} match(es) in {changed} file(s).")
        self._find()   # refresh counts (should now be zero unless the pattern self-matches)


class TagRenameDialog(tk.Toplevel):
    def __init__(self, master, on_done=None):
        super().__init__(master)
        self.title("Rename a country tag")
        self.resizable(False, False)
        self.on_done = on_done
        self._plan = None
        pad = {"padx": 10, "pady": 4}

        ttk.Label(self, text="RENAME A COUNTRY TAG", style="PageTitle.TLabel").grid(
            row=0, column=0, columnspan=3, sticky="w", **pad)
        ttk.Label(
            self,
            text="Renames the tag everywhere it's used as a tag - including ids that start with "
                 "it (TUR_1936) - and renames the country/flag files that carry it in their "
                 "filename. Leaves words that merely contain the letters alone.",
            style="Muted.TLabel", wraplength=520, justify="left",
        ).grid(row=1, column=0, columnspan=3, sticky="w", **pad)

        ttk.Label(self, text="Old tag", style="FieldLabel.TLabel").grid(row=2, column=0, sticky="w", **pad)
        self.old_var = tk.StringVar()
        ttk.Entry(self, textvariable=self.old_var, width=6, font=(theme.FACE_MONO, 10)).grid(
            row=2, column=1, sticky="w", **pad)
        ttk.Label(self, text="New tag", style="FieldLabel.TLabel").grid(row=3, column=0, sticky="w", **pad)
        self.new_var = tk.StringVar()
        ttk.Entry(self, textvariable=self.new_var, width=6, font=(theme.FACE_MONO, 10)).grid(
            row=3, column=1, sticky="w", **pad)
        ttk.Button(self, text="Preview", command=self._preview).grid(row=3, column=2, sticky="w", **pad)

        self.report = tk.Text(self, height=14, width=76, wrap="word", relief="flat", borderwidth=0,
                              background=theme.CANVAS_BG, foreground=theme.TEXT,
                              font=(theme.FACE_MONO, 9))
        self.report.grid(row=4, column=0, columnspan=3, sticky="we", padx=10, pady=(6, 4))
        self.report.insert("1.0", "Type both tags and click Preview - nothing is written until you confirm.")
        self.report.configure(state="disabled")

        btns = ttk.Frame(self)
        btns.grid(row=5, column=0, columnspan=3, pady=10)
        self.apply_btn = ttk.Button(btns, text="Apply rename", style="Accent.TButton",
                                    command=self._apply, state="disabled")
        self.apply_btn.pack(side="left", padx=4)
        ttk.Button(btns, text="Close", command=self.destroy).pack(side="left", padx=4)
        self.grab_set()

    def _tags(self):
        old = self.old_var.get().strip().upper()
        new = self.new_var.get().strip().upper()
        if len(old) != 3 or len(new) != 3 or not old.isalnum() or not new.isalnum():
            messagebox.showerror("Bad tag", "Both tags must be exactly 3 letters/digits.", parent=self)
            return None
        if old == new:
            messagebox.showerror("Same tag", "The old and new tags are identical.", parent=self)
            return None
        return old, new

    def _set_report(self, text):
        self.report.configure(state="normal")
        self.report.delete("1.0", "end")
        self.report.insert("1.0", text)
        self.report.configure(state="disabled")

    def _preview(self):
        tags = self._tags()
        if not tags:
            return
        old, new = tags
        self._set_report("Scanning...")
        self.update_idletasks()
        self._plan = tag_rename.plan(state.mod_root, old, new)

        edits, renames, conflicts = self._plan["edits"], self._plan["renames"], self._plan["conflicts"]
        total_hits = sum(n for _, n in edits)
        lines = [f"{old} -> {new}", ""]
        lines.append(f"{total_hits} reference(s) in {len(edits)} file(s) would be rewritten:")
        for path, n in sorted(edits, key=lambda t: -t[1])[:12]:
            lines.append(f"  {n:>4}  {os.path.relpath(path, state.mod_root)}")
        if len(edits) > 12:
            lines.append(f"        ... and {len(edits) - 12} more file(s)")
        lines.append("")
        lines.append(f"{len(renames)} file(s) would be renamed:")
        for old_path, new_path in renames[:10]:
            lines.append(f"  {os.path.basename(old_path)}  ->  {os.path.basename(new_path)}")
        if len(renames) > 10:
            lines.append(f"  ... and {len(renames) - 10} more")
        if conflicts:
            lines.append("")
            lines.append(f"BLOCKED - {len(conflicts)} rename(s) would overwrite an existing file:")
            for c in conflicts[:10]:
                lines.append(f"  {c}")
            lines.append("  Resolve these by hand first; they will be skipped.")
        if not edits and not renames:
            lines.append("")
            lines.append(f"Nothing found - is {old} actually used in this mod?")

        self._set_report(chr(10).join(lines))
        self.apply_btn.configure(state="normal" if (edits or renames) else "disabled")

    def _apply(self):
        tags = self._tags()
        if not tags or not self._plan:
            return
        old, new = tags
        total_hits = sum(n for _, n in self._plan["edits"])
        if not messagebox.askyesno(
            "Rename the tag?",
            f"Rewrite {total_hits} reference(s) across {len(self._plan['edits'])} file(s) and rename "
            f"{len(self._plan['renames'])} file(s), {old} -> {new}?" + chr(10) * 2 +
            "Every edited file keeps a one-time .bak. Taking a snapshot first is still recommended.",
            parent=self):
            return
        edited, total, renamed = tag_rename.apply(state.mod_root, old, new, self._plan)
        msg = (f"Renamed {old} -> {new}: {total} reference(s) in {edited} file(s), "
               f"{renamed} file(s) renamed.")
        self._set_report(msg + chr(10) * 2 +
                         "Reload the mod (Open Mod -> Load) so every tab picks up the change.")
        self.apply_btn.configure(state="disabled")
        if self.on_done:
            self.on_done(msg)
