"""Game Setup tab: build a new bookmark (scenario) with featured countries -
the date-select screen's cards. Existing bookmark files are only ever read
for reference, never edited in place (see bookmark_creator's doc string)."""

import tkinter as tk
from tkinter import ttk, messagebox

from app.state import state
from app import bookmark_creator as bkc
from app import icon_library
from app import theme, ui_kit
from app.oob_tab import _RowList

IDEOLOGIES = ["neutrality", "democratic", "fascism", "communism"]


class BookmarkTab(ttk.Frame):
    def __init__(self, master):
        super().__init__(master, padding=12)
        self.picture_var = tk.StringVar()
        self._build()
        state.subscribe(self.on_mod_changed)

    def _build(self):
        self.header = ui_kit.PageHeader(
            self, "Game Setup",
            "Bookmarks/scenarios - the games the player can pick from the main menu (start date, featured countries, description).", help_key="game_setup")

        body = ttk.Frame(self)
        body.pack(fill="both", expand=True)

        # ---- left: existing scenarios ----
        left = ttk.Frame(body, width=300)
        left.pack(side="left", fill="y", padx=(0, 16))
        left.pack_propagate(False)
        ttk.Label(left, text="Existing scenarios", font=("Segoe UI", 10, "bold")).pack(anchor="w")
        self.tree = ttk.Treeview(left, columns=("name", "date", "src"), show="headings", height=22)
        for col, text, width in (("name", "loc key", 150), ("date", "start date", 90), ("src", "from", 55)):
            self.tree.heading(col, text=text)
            self.tree.column(col, width=width)
        self.tree.pack(fill="both", expand=True, pady=(6, 0))
        self.tree.tag_configure("mod", foreground=theme.GREEN)

        # ---- right: new scenario ----
        right = ttk.Frame(body)
        right.pack(side="left", fill="both", expand=True)
        ttk.Label(right, text="Create a new scenario", font=("Segoe UI", 10, "bold")).pack(anchor="w")

        row = ttk.Frame(right)
        row.pack(fill="x", pady=(8, 0))
        ttk.Label(row, text="Loc key (unique, no spaces)").pack(side="left")
        self.name_key_var = tk.StringVar(value="MY_SCENARIO_NAME")
        ttk.Entry(row, textvariable=self.name_key_var, width=24).pack(side="left", padx=6)
        self.key_hint = ttk.Label(row, text="", style="Muted.TLabel")
        self.key_hint.pack(side="left")
        self.name_key_var.trace_add("write", lambda *_: self._check_key())

        ttk.Label(right, text="Scenario name (shown on the card)").pack(anchor="w", pady=(8, 0))
        self.display_name_var = tk.StringVar()
        ttk.Entry(right, textvariable=self.display_name_var, width=36).pack(anchor="w")

        ttk.Label(right, text="Description").pack(anchor="w", pady=(8, 0))
        self.desc_txt = tk.Text(right, height=3, width=44)
        self.desc_txt.pack(fill="x")

        row2 = ttk.Frame(right)
        row2.pack(fill="x", pady=(8, 0))
        ttk.Label(row2, text="Start date (YYYY.M.D.H)").pack(side="left")
        self.date_var = tk.StringVar(value="1936.1.1.12")
        ttk.Entry(row2, textvariable=self.date_var, width=16).pack(side="left", padx=(4, 16))
        ttk.Label(row2, text="Default country tag").pack(side="left")
        self.default_country_var = tk.StringVar()
        ttk.Entry(row2, textvariable=self.default_country_var, width=6).pack(side="left", padx=4)

        row3 = ttk.Frame(right)
        row3.pack(fill="x", pady=(8, 0))
        ttk.Label(row3, text="Picture").pack(side="left")
        ttk.Entry(row3, textvariable=self.picture_var, width=26).pack(side="left", padx=4)
        ttk.Button(row3, text="...", width=3, command=self._pick_picture).pack(side="left")
        self.is_default_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(row3, text="This is the default scenario",
                        variable=self.is_default_var).pack(side="left", padx=(16, 0))

        ttk.Label(right, text="Featured countries", font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(12, 0))
        ttk.Label(
            right, text="Ideas / focuses are comma-separated ids that already exist in the mod "
                       "(or vanilla) - not created here.",
            style="Muted.TLabel", wraplength=560, justify="left",
        ).pack(anchor="w")
        self.country_rows = _RowList(right, [
            ("tag", "entry", 5, None),
            ("ideology", "combo", 10, IDEOLOGIES),
            ("blurb", "entry", 24, None),
            ("ideas", "entry", 18, None),
            ("focuses", "entry", 18, None),
        ], add_label="+ Add featured country")
        self.country_rows.pack(fill="x", pady=(4, 0))
        self.country_rows.add_row({"tag": "", "ideology": "neutrality", "blurb": "",
                                    "ideas": "", "focuses": ""})

        ttk.Button(right, text="Create Scenario", style="Accent.TButton",
                   command=self._create).pack(anchor="w", pady=12)

        self.status = ttk.Label(right, text="", style="Status.TLabel", wraplength=560, justify="left")
        self.status.pack(anchor="w")

        self.on_mod_changed()

    def on_mod_changed(self):
        if state.is_loaded:
            self.header.set_status(True, state.mod_name)
        else:
            self.header.set_status(False, "no mod open")
        self._refresh_list()

    def on_show(self):
        self.on_mod_changed()

    def _refresh_list(self):
        self.tree.delete(*self.tree.get_children())
        if not state.is_loaded:
            return
        for name_key, date, source in bkc.list_bookmarks(state.mod_root):
            self.tree.insert("", "end", values=(name_key, date, source),
                             tags=("mod",) if source == "mod" else ())

    def _existing_keys(self):
        return {n for n, _, _ in bkc.list_bookmarks(state.mod_root)} if state.is_loaded else set()

    def _check_key(self):
        key = self.name_key_var.get().strip()
        if not key:
            self.key_hint.config(text="required", foreground=theme.MUTED)
        elif key in self._existing_keys():
            self.key_hint.config(text="already used!", foreground=theme.RED)
        else:
            self.key_hint.config(text="free ✓", foreground=theme.GREEN)

    def _pick_picture(self):
        library = getattr(state, "gfx_index", None)
        if not library:
            messagebox.showerror("No icons", "Load a mod with indexed GFX first.")
            return
        picker = icon_library.IconPicker(self, library)
        self.wait_window(picker)
        if picker.result:
            self.picture_var.set(picker.result)

    def _create(self):
        if not state.is_loaded:
            messagebox.showerror("No mod", "Open or create a mod first.")
            return
        key = self.name_key_var.get().strip()
        name = self.display_name_var.get().strip()
        date = self.date_var.get().strip()
        if not key or not name or not date:
            messagebox.showerror("Missing info", "Loc key, scenario name and start date are required.")
            return
        if key in self._existing_keys():
            messagebox.showerror("Key taken", f"'{key}' already exists.")
            return

        countries = []
        for r in self.country_rows.values():
            tag = r["tag"].strip().upper()
            if not tag:
                continue
            ideas = [i.strip() for i in r["ideas"].split(",") if i.strip()]
            focuses = [i.strip() for i in r["focuses"].split(",") if i.strip()]
            countries.append({
                "tag": tag, "ideology": r["ideology"].strip(),
                "history_key": f"{tag}_{key}_DESC" if r["blurb"].strip() else "",
                "history_text": r["blurb"].strip(),
                "ideas": ideas, "focuses": focuses,
            })

        try:
            created = bkc.create_bookmark(
                state.mod_root, name_key=key, display_name=name,
                desc_key=f"{key}_DESC", description=self.desc_txt.get("1.0", "end").strip(),
                date=date, picture=self.picture_var.get().strip(),
                default_country=self.default_country_var.get().strip().upper(),
                is_default=self.is_default_var.get(), countries=countries,
            )
        except Exception as exc:
            messagebox.showerror("Failed", f"Scenario creation failed:\n{exc}")
            return

        self._refresh_list()
        self.status.config(
            text=f"Created scenario '{name}' with {len(countries)} featured countries — "
                 f"{len(created)} files written."
        )
