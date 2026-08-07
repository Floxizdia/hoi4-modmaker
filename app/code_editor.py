"""Code tab: a real text editor over the open mod's files, for the people
who want to write Paradox script by hand instead of (or alongside) the
wizards. File tree on the left, editor with PDS syntax highlighting on the
right, Ctrl+S to save.

Saving is deliberately low-friction here - opening a file in an editor IS
the statement of intent - so instead of a confirmation dialog, the first
save of each session quietly drops a .bak next to the original.
"""

import os
import re
import shutil
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog

from app.state import state
from app import mod_export
from app import theme, ui_kit

EDITABLE_EXT = {".txt", ".yml", ".gfx", ".gui", ".lua", ".mod", ".csv", ".info"}
HIGHLIGHT_LIMIT = 400_000  # bytes; germany.txt-sized files skip full colouring

TOKEN_STYLES = {
    "comment": {"foreground": "#7a8471"},
    "string": {"foreground": theme.GOLD},
    "number": {"foreground": theme.AMBER},
    "key": {"foreground": "#8fb4d8"},
    "brace": {"foreground": theme.MUTED},
}

TOKEN_RES = [
    ("comment", re.compile(r"#[^\n]*")),
    ("string", re.compile(r'"[^"\n]*"')),
    ("key", re.compile(r"^[ \t]*([A-Za-z_][\w.]*)(?=[ \t]*=)", re.MULTILINE)),
    ("number", re.compile(r"(?<![\w.])-?\d+(?:\.\d+)?(?![\w.])")),
    ("brace", re.compile(r"[{}]")),
]


def open_in_code(widget, path, line=None):
    """Send another tab's finding to the Code screen and jump to its line.

    Callers used to guard with `"code" in app.tabs`, but tabs are built
    lazily on first visit - so that check was False for anyone who hadn't
    already opened the Code screen, and the jump silently did nothing.
    `show` is what constructs it, so ask for the screen first and read the
    tab back afterwards. Returns True when the file was actually opened.
    """
    app = widget.winfo_toplevel()
    if not (hasattr(app, "show") and hasattr(app, "tabs")):
        return False
    app.show("code")
    tab = app.tabs.get("code")
    # show() can be refused - an unsaved generator tab asks to confirm
    # first, and leaving the user on that tab while loading a file into a
    # hidden one would be worse than doing nothing
    if tab is None or getattr(app, "current_key", None) != "code":
        return False
    tab.open_file(path, line=line)
    return True


class CodeEditorTab(ttk.Frame):
    def __init__(self, master):
        super().__init__(master, padding=8)
        self.current_path = None
        self.dirty = False
        self._backed_up = set()
        self._build()
        state.subscribe(self.on_mod_changed)

    # ---- layout ----

    def _build(self):
        self.header = ui_kit.PageHeader(
            self, "Code",
            "A raw file-tree code editor with HOI4 script syntax highlighting, for anything the visual tabs don't cover yet.", help_key="code")

        body = ttk.Frame(self)
        body.pack(fill="both", expand=True)

        # file tree
        left = ttk.Frame(body, width=290)
        left.pack(side="left", fill="y", padx=(0, 8))
        left.pack_propagate(False)
        row = ttk.Frame(left)
        row.pack(fill="x")
        ttk.Button(row, text="Refresh", command=self._fill_tree).pack(side="left")
        ttk.Button(row, text="New File...", command=self._new_file).pack(side="left", padx=4)
        self.tree = ttk.Treeview(left, show="tree")
        tree_bar = ttk.Scrollbar(left, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=tree_bar.set)
        self.tree.pack(side="left", fill="both", expand=True, pady=(6, 0))
        tree_bar.pack(side="right", fill="y", pady=(6, 0))
        self.tree.bind("<<TreeviewOpen>>", self._on_open_dir)
        self.tree.bind("<Double-Button-1>", self._on_pick_file)

        # editor
        right = ttk.Frame(body)
        right.pack(side="left", fill="both", expand=True)

        bar = ttk.Frame(right)
        bar.pack(fill="x")
        self.path_label = ttk.Label(bar, text="No file open", style="Muted.TLabel")
        self.path_label.pack(side="left")
        self.brace_label = ttk.Label(bar, text="", style="Muted.TLabel")
        self.brace_label.pack(side="right", padx=8)
        ttk.Button(bar, text="Save  (Ctrl+S)", style="Accent.TButton", command=self.save).pack(side="right")

        search_row = ttk.Frame(right)
        search_row.pack(fill="x", pady=(4, 2))
        ttk.Label(search_row, text="Find:").pack(side="left")
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(search_row, textvariable=self.search_var, width=28)
        self.search_entry.pack(side="left", padx=4)
        self.search_entry.bind("<Return>", lambda e: self._find_next())
        ttk.Button(search_row, text="Next", command=self._find_next).pack(side="left")
        self.search_info = ttk.Label(search_row, text="", style="Muted.TLabel")
        self.search_info.pack(side="left", padx=8)

        frame = ttk.Frame(right)
        frame.pack(fill="both", expand=True)
        self.linenums = tk.Text(frame, width=5, padx=4, takefocus=0, state="disabled",
                                background=theme.BG, foreground=theme.MUTED, relief="flat")
        self.linenums.pack(side="left", fill="y")
        self.text = tk.Text(frame, wrap="none", undo=True, font=("Consolas", 10))
        vbar = ttk.Scrollbar(frame, orient="vertical", command=self._on_vscroll)
        hbar = ttk.Scrollbar(right, orient="horizontal", command=self.text.xview)
        self.text.configure(yscrollcommand=lambda a, b: (vbar.set(a, b), self._sync_lines()),
                            xscrollcommand=hbar.set)
        self.text.pack(side="left", fill="both", expand=True)
        vbar.pack(side="right", fill="y")
        hbar.pack(fill="x")

        for tag, style in TOKEN_STYLES.items():
            self.text.tag_configure(tag, **style)
        self.text.tag_configure("found", background=theme.BRONZE)

        self.text.bind("<Control-s>", lambda e: (self.save(), "break")[-1])
        self.text.bind("<Control-f>", lambda e: (self.search_entry.focus_set(), "break")[-1])
        self.text.bind("<<Modified>>", self._on_modified)
        self.text.bind("<KeyRelease-Return>", lambda e: self._sync_lines())

        self.status = ttk.Label(self, text="Double-click a file to open it. Ctrl+S saves (first save keeps a .bak). "
                                           "Ctrl+F jumps to search.", style="Muted.TLabel")
        self.status.pack(fill="x", pady=(4, 0))

        self.on_mod_changed()

    # ---- file tree ----

    def on_mod_changed(self):
        if state.is_loaded:
            self.header.set_status(True, state.mod_name)
        else:
            self.header.set_status(False, "no mod open")
        self.current_path = None
        self.dirty = False
        self._backed_up = set()
        self.text.delete("1.0", "end")
        self.path_label.config(text="No file open")
        self._fill_tree()

    def _fill_tree(self):
        self.tree.delete(*self.tree.get_children())
        if not state.is_loaded:
            return
        self._add_dir("", state.mod_root)

    def _add_dir(self, parent, path):
        try:
            entries = sorted(os.listdir(path), key=lambda n: (not os.path.isdir(os.path.join(path, n)), n.lower()))
        except OSError:
            return
        for name in entries:
            full = os.path.join(path, name)
            if os.path.isdir(full):
                if name.startswith("."):
                    continue
                node = self.tree.insert(parent, "end", text=" " + name, values=(full,), open=False)
                # dummy child so the expand arrow shows; real children load on open
                self.tree.insert(node, "end", text="...")
            elif os.path.splitext(name)[1].lower() in EDITABLE_EXT:
                self.tree.insert(parent, "end", text=" " + name, values=(full,))

    def _on_open_dir(self, _event):
        node = self.tree.focus()
        children = self.tree.get_children(node)
        if len(children) == 1 and self.tree.item(children[0], "text") == "...":
            self.tree.delete(children[0])
            values = self.tree.item(node, "values")
            if values:
                self._add_dir(node, values[0])

    def _on_pick_file(self, _event):
        node = self.tree.focus()
        values = self.tree.item(node, "values")
        if not values:
            return
        path = values[0]
        if os.path.isfile(path):
            self.open_file(path)

    # ---- editing ----

    def _confirm_discard(self):
        if not self.dirty:
            return True
        return messagebox.askyesno("Unsaved changes", "This file has unsaved changes. Discard them?")

    def open_file(self, path, line=None):
        """`line` (1-based) scrolls to and highlights that line - used when
        another tab hands off a finding that already knows where it is."""
        if not self._confirm_discard():
            return
        try:
            with open(path, "r", encoding="utf-8-sig", errors="replace") as f:
                content = f.read()
        except OSError as exc:
            messagebox.showerror("Cannot open", str(exc))
            return
        self.current_path = path
        self.text.delete("1.0", "end")
        self.text.insert("1.0", content)
        self.text.edit_reset()
        self.text.edit_modified(False)
        self.dirty = False
        rel = os.path.relpath(path, state.mod_root) if state.is_loaded else path
        self.path_label.config(text=rel)
        self._highlight_all()
        self._sync_lines()
        self._update_braces()
        if line:
            self._goto_line(line)

    def _goto_line(self, line):
        index = f"{max(1, int(line))}.0"
        self.text.see(index)
        self.text.tag_remove("found", "1.0", "end")
        self.text.tag_add("found", index, f"{index} lineend")
        self.text.mark_set("insert", index)
        self.text.focus_set()

    def save(self):
        if not self.current_path:
            return
        if self.current_path not in self._backed_up and os.path.isfile(self.current_path):
            backup = self.current_path + ".bak"
            if not os.path.exists(backup):
                try:
                    shutil.copy2(self.current_path, backup)
                except OSError:
                    pass
            self._backed_up.add(self.current_path)

        content = self.text.get("1.0", "end-1c")
        # keep the BOM for localisation files - HOI4 refuses .yml without it
        encoding = "utf-8-sig" if self.current_path.lower().endswith(".yml") else "utf-8"
        try:
            with open(self.current_path, "w", encoding=encoding) as f:
                f.write(content)
        except OSError as exc:
            messagebox.showerror("Save failed", str(exc))
            return
        self.dirty = False
        self.text.edit_modified(False)
        self._highlight_all()
        self._update_braces()
        self.status.config(text=f"Saved {os.path.basename(self.current_path)}  "
                                f"({len(content.splitlines())} lines). Backup kept as .bak.")

    def _new_file(self):
        if not state.is_loaded:
            messagebox.showerror("No mod", "Open a mod first.")
            return
        rel = simpledialog.askstring(
            "New file", "Path inside the mod (e.g. common/ideas/my_ideas.txt):", parent=self,
        )
        if not rel:
            return
        path = os.path.normpath(os.path.join(state.mod_root, rel.strip().lstrip("/\\")))
        if not path.startswith(os.path.abspath(state.mod_root)):
            messagebox.showerror("Bad path", "The file must live inside the mod folder.")
            return
        if os.path.exists(path):
            messagebox.showerror("Exists", "That file already exists — open it from the tree instead.")
            return
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write("")
        mod_export.record_created(state.mod_root, [path])
        self._fill_tree()
        self.open_file(path)

    # ---- highlighting / gutter / braces ----

    def _on_modified(self, _event):
        if self.text.edit_modified():
            self.dirty = True
            self.text.edit_modified(False)
            self._highlight_line()
            self._update_braces()

    def _highlight_all(self):
        for tag in TOKEN_STYLES:
            self.text.tag_remove(tag, "1.0", "end")
        content = self.text.get("1.0", "end-1c")
        if len(content) > HIGHLIGHT_LIMIT:
            self.status.config(text="File too large for full colouring — editing still works fine.")
            return
        self._apply_tokens(content, "1.0")

    def _highlight_line(self):
        start = self.text.index("insert linestart")
        end = self.text.index("insert lineend")
        for tag in TOKEN_STYLES:
            self.text.tag_remove(tag, start, end)
        self._apply_tokens(self.text.get(start, end), start)

    def _apply_tokens(self, content, base_index):
        taken = []
        for tag, regex in TOKEN_RES:
            for m in regex.finditer(content):
                s, e = m.span(1) if m.groups() else m.span()
                if any(s < te and e > ts for ts, te in taken):
                    continue
                if tag in ("comment", "string"):
                    taken.append((s, e))
                self.text.tag_add(tag, f"{base_index}+{s}c", f"{base_index}+{e}c")

    def _sync_lines(self):
        total = int(self.text.index("end-1c").split(".")[0])
        self.linenums.configure(state="normal")
        self.linenums.delete("1.0", "end")
        self.linenums.insert("1.0", "\n".join(str(i) for i in range(1, total + 1)))
        self.linenums.configure(state="disabled")
        self.linenums.yview_moveto(self.text.yview()[0])

    def _on_vscroll(self, *args):
        self.text.yview(*args)
        self.linenums.yview_moveto(self.text.yview()[0])

    def _update_braces(self):
        content = self.text.get("1.0", "end-1c")
        opens = closes = 0
        in_quotes = False
        i = 0
        while i < len(content):
            ch = content[i]
            if in_quotes:
                if ch == '"':
                    in_quotes = False
            elif ch == '"':
                in_quotes = True
            elif ch == "#":
                nl = content.find("\n", i)
                i = len(content) if nl == -1 else nl
                continue
            elif ch == "{":
                opens += 1
            elif ch == "}":
                closes += 1
            i += 1
        if opens == closes:
            self.brace_label.config(text=f"braces balanced ({opens})", foreground=theme.GREEN)
        else:
            self.brace_label.config(text=f"braces UNBALANCED: {opens} open / {closes} close",
                                    foreground=theme.RED)

    # ---- search ----

    def _find_next(self):
        needle = self.search_var.get()
        if not needle:
            return
        self.text.tag_remove("found", "1.0", "end")
        start = self.text.index("insert")
        pos = self.text.search(needle, f"{start}+1c", nocase=True)
        if not pos:
            pos = self.text.search(needle, "1.0", nocase=True)
            if not pos:
                self.search_info.config(text="not found")
                return
        end = f"{pos}+{len(needle)}c"
        self.text.tag_add("found", pos, end)
        self.text.mark_set("insert", pos)
        self.text.see(pos)
        self.text.focus_set()
        self.search_info.config(text=f"at {pos}")
