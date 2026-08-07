"""The Draw.io import dialog: pick a diagram, check what it found, write it.

The preview matters more than it looks. A diagram gives no way to tell
which end of an arrow is the prerequisite, and a page can hold notes and
legends as well as focuses, so the user has to see what was understood
before any of it reaches the mod.
"""

import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from app import drawio, mod_export, safe_io
from app import theme, ui_kit


class DrawioImportDialog(tk.Toplevel):
    def __init__(self, master, mod_root, on_imported=None):
        super().__init__(master)
        self.title("Import a focus tree from Draw.io")
        self.mod_root = mod_root
        self.on_imported = on_imported
        self.path = ""
        self.pages = []
        self.focuses = []
        self._build()
        self.transient(master.winfo_toplevel())
        self.grab_set()

    # ---- layout ----

    def _build(self):
        outer = ttk.Frame(self, padding=14)
        outer.pack(fill="both", expand=True)

        ttk.Label(outer, style="Muted.TLabel", wraplength=680, justify="left",
                  text="Boxes become focuses and arrows become prerequisites. Positions are "
                       "read as a grid, so boxes that line up in the drawing line up in the "
                       "tree. Everything else - icons, costs, rewards - is left blank for you "
                       "to fill in on the Focus Tree screen.").pack(anchor="w", pady=(0, 10))

        row = ttk.Frame(outer)
        row.pack(fill="x")
        ttk.Button(row, text="Choose .drawio / .xml...",
                   command=self._choose).pack(side="left")
        self.file_label = ttk.Label(row, text="no file chosen", style="Muted.TLabel")
        self.file_label.pack(side="left", padx=8)

        form = ttk.Frame(outer)
        form.pack(fill="x", pady=(10, 0))

        ttk.Label(form, text="Page").grid(row=0, column=0, sticky="w")
        self.page_var = tk.StringVar()
        self.page_combo = ttk.Combobox(form, textvariable=self.page_var, state="readonly", width=24)
        self.page_combo.grid(row=0, column=1, sticky="w", padx=6, pady=2)
        self.page_combo.bind("<<ComboboxSelected>>", lambda e: self._reload())

        ttk.Label(form, text="Country tag").grid(row=0, column=2, sticky="w", padx=(14, 0))
        self.tag_var = tk.StringVar(value="TAG")
        ttk.Entry(form, textvariable=self.tag_var, width=6).grid(row=0, column=3, sticky="w", padx=6)

        ttk.Label(form, text="Tree id").grid(row=1, column=0, sticky="w")
        self.tree_var = tk.StringVar(value="imported_focus_tree")
        ttk.Entry(form, textvariable=self.tree_var, width=26).grid(row=1, column=1, sticky="w",
                                                                   padx=6, pady=2)
        ttk.Label(form, text="Id prefix").grid(row=1, column=2, sticky="w", padx=(14, 0))
        self.prefix_var = tk.StringVar()
        prefix = ttk.Entry(form, textvariable=self.prefix_var, width=8)
        prefix.grid(row=1, column=3, sticky="w", padx=6)
        prefix.bind("<KeyRelease>", lambda e: self._reload())
        ui_kit.attach_tooltip(prefix, "Put in front of every generated focus id, so an imported "
                                      "tree can't collide with another country's focuses.")

        self.flip_var = tk.BooleanVar(value=False)
        flip = ttk.Checkbutton(outer, variable=self.flip_var, command=self._reload,
                               text="Arrows point from the unlocked focus back to its "
                                    "prerequisite (flip them)")
        flip.pack(anchor="w", pady=(8, 0))
        ui_kit.attach_tooltip(flip, "A diagram can't say which end of an arrow is the "
                                    "prerequisite. Check the preview and flip if it reads "
                                    "backwards.")

        self.tree = ttk.Treeview(outer, columns=("id", "x", "y", "prereq", "name"),
                                 show="headings", height=12)
        for column, heading, width in (("id", "focus id", 210), ("x", "x", 40), ("y", "y", 40),
                                       ("prereq", "prerequisites", 240), ("name", "name", 200)):
            self.tree.heading(column, text=heading)
            self.tree.column(column, width=width)
        self.tree.pack(fill="both", expand=True, pady=(10, 0))

        self.status = ttk.Label(outer, text="", style="Status.TLabel",
                                wraplength=680, justify="left")
        self.status.pack(fill="x", pady=(8, 0))

        buttons = ttk.Frame(outer)
        buttons.pack(fill="x", pady=(8, 0))
        self.import_btn = ttk.Button(buttons, text="Write the tree", style="Accent.TButton",
                                     command=self._write, state="disabled")
        self.import_btn.pack(side="left")
        ttk.Button(buttons, text="Cancel", command=self.destroy).pack(side="left", padx=6)

    # ---- loading ----

    def _choose(self):
        path = filedialog.askopenfilename(
            parent=self, title="Pick a Draw.io diagram",
            filetypes=[("Draw.io diagram", "*.drawio *.xml"), ("All files", "*.*")])
        if not path:
            return
        self.path = path
        self.file_label.config(text=os.path.basename(path))
        if self.tree_var.get() == "imported_focus_tree":
            stem = os.path.splitext(os.path.basename(path))[0]
            self.tree_var.set(drawio.suggested_filename(stem)[:-4] or "imported_focus_tree")
        self._reload(reset_page=True)

    def _reload(self, reset_page=False):
        if not self.path:
            return
        page_index = 0
        if not reset_page and self.pages and self.page_var.get() in self.pages:
            page_index = self.pages.index(self.page_var.get())
        try:
            self.focuses, self.pages = drawio.load(
                self.path, prefix=self.prefix_var.get().strip(),
                flip_arrows=self.flip_var.get(), page=page_index)
        except drawio.DrawioError as exc:
            self.focuses = []
            self._refresh_tree()
            self.status.config(text=str(exc), foreground=theme.RED)
            self.import_btn.config(state="disabled")
            return

        self.page_combo.configure(values=self.pages)
        if reset_page or self.page_var.get() not in self.pages:
            self.page_var.set(self.pages[0])
        self._refresh_tree()

        roots = [f for f in self.focuses if not f["prerequisites"]]
        arrows = sum(len(f["prerequisites"]) for f in self.focuses)
        note = (f"{len(self.focuses)} focus(es), {arrows} prerequisite link(s), "
                f"{len(roots)} with no prerequisite.")
        if not arrows:
            note += ("  No arrows were understood - if the drawing has them, they may connect "
                     "to the edge of the page rather than to the boxes themselves.")
        self.status.config(text=note, foreground=theme.MUTED)
        self.import_btn.config(state="normal")

    def _refresh_tree(self):
        self.tree.delete(*self.tree.get_children())
        for focus in self.focuses:
            self.tree.insert("", "end", values=(
                focus["id"], focus["x"], focus["y"],
                ", ".join(focus["prerequisites"]), focus["label"]))

    # ---- writing ----

    def _write(self):
        if not self.focuses:
            return
        tag = self.tag_var.get().strip().upper()
        tree_id = self.tree_var.get().strip()
        if len(tag) != 3:
            self.status.config(text="A country tag is exactly 3 letters.", foreground=theme.RED)
            return
        if not tree_id:
            self.status.config(text="Give the tree an id.", foreground=theme.RED)
            return

        path = drawio.tree_path(self.mod_root, tree_id)
        text = drawio.format_tree(tree_id, tag, self.focuses)
        if not safe_io.write_text(path, text, parent=self,
                                  describe=os.path.basename(path)):
            self.status.config(text="Left the existing file alone.")
            return

        loc_dir = os.path.join(self.mod_root, "localisation", "english")
        os.makedirs(loc_dir, exist_ok=True)
        loc_path = os.path.join(loc_dir, f"{tree_id}_l_english.yml")
        with open(loc_path, "w", encoding="utf-8-sig") as handle:
            handle.write(drawio.format_localisation(self.focuses))

        mod_export.record_created(self.mod_root, [path, loc_path])
        if self.on_imported:
            self.on_imported(path, len(self.focuses))
        messagebox.showinfo(
            "Imported",
            f"{len(self.focuses)} focus(es) written to:\n{path}\n\nNames written to:\n{loc_path}\n\n"
            "Load the tree on the Focus Tree screen to give them icons, costs and rewards.",
            parent=self)
        self.destroy()
