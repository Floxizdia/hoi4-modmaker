"""Country tab: form for creating a brand-new tag in the open mod."""

import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, colorchooser

from PIL import Image, ImageTk

from app.state import state
from app import country_creator
from app import ideology_creator
from app import mod_export
from app import portrait_creator
from app import flag_creator
from app.map_picker import MapPickerDialog
from app import theme, ui_kit


class CountryFlagDialog(tk.Toplevel):
    """Compact procedural flag picker used by the Country creation flow."""
    def __init__(self, master, base_color):
        super().__init__(master)
        self.title("Generate country flag")
        self.resizable(False, False)
        self.result = None
        self.colors = [base_color, (255, 255, 255), (30, 30, 30)]
        self.pattern_var = tk.StringVar(value="horizontal_tricolor")
        self.emblem_path = ""
        self.preview_ref = None
        self._build()
        self.grab_set()

    def _build(self):
        body = ttk.Frame(self, padding=12)
        body.pack(fill="both", expand=True)
        row = ttk.Frame(body)
        row.pack(fill="x")
        ttk.Label(row, text="Pattern").pack(side="left")
        combo = ttk.Combobox(row, textvariable=self.pattern_var, values=flag_creator.PATTERNS,
                             state="readonly", width=22)
        combo.pack(side="left", padx=8)
        combo.bind("<<ComboboxSelected>>", lambda _event: self._preview())

        colors = ttk.Frame(body)
        colors.pack(fill="x", pady=10)
        ttk.Label(colors, text="Colours").pack(side="left")
        self.swatches = []
        for index in range(3):
            button = tk.Button(colors, width=5, height=1, command=lambda i=index: self._pick_color(i))
            button.pack(side="left", padx=4)
            self.swatches.append(button)

        emblem = ttk.Frame(body)
        emblem.pack(fill="x")
        ttk.Button(emblem, text="Emblem...", command=self._pick_emblem).pack(side="left")
        self.emblem_label = ttk.Label(emblem, text="No emblem", style="Muted.TLabel")
        self.emblem_label.pack(side="left", padx=8)

        self.canvas = tk.Canvas(body, width=328, height=208, highlightthickness=1,
                                highlightbackground=theme.EDGE, background=theme.CANVAS_BG)
        self.canvas.pack(pady=12)
        buttons = ttk.Frame(body)
        buttons.pack(fill="x")
        ttk.Button(buttons, text="Use this flag", style="Accent.TButton", command=self._accept).pack(side="left")
        ttk.Button(buttons, text="Cancel", command=self.destroy).pack(side="left", padx=6)
        self._refresh_swatches()
        self._preview()

    def _refresh_swatches(self):
        for button, rgb in zip(self.swatches, self.colors):
            color = "#%02x%02x%02x" % rgb
            button.configure(bg=color, activebackground=color)

    def _pick_color(self, index):
        rgb, _ = colorchooser.askcolor(color="#%02x%02x%02x" % self.colors[index], parent=self)
        if rgb:
            self.colors[index] = tuple(int(value) for value in rgb)
            self._refresh_swatches()
            self._preview()

    def _pick_emblem(self):
        path = filedialog.askopenfilename(
            parent=self, title="Pick emblem", filetypes=[("PNG image", "*.png"), ("All", "*.*")]
        )
        if path:
            self.emblem_path = path
            self.emblem_label.configure(text=os.path.basename(path))
            self._preview()

    def _flag_image(self):
        image = flag_creator._draw_pattern(self.pattern_var.get(), flag_creator.LARGE_SIZE, self.colors).convert("RGBA")
        if self.emblem_path and os.path.isfile(self.emblem_path):
            try:
                emblem = Image.open(self.emblem_path).convert("RGBA")
                height = int(flag_creator.LARGE_SIZE[1] * 0.7)
                width = max(1, int(emblem.width * height / emblem.height))
                emblem = emblem.resize((width, height), Image.LANCZOS)
                image.alpha_composite(emblem, ((flag_creator.LARGE_SIZE[0] - width) // 2,
                                               (flag_creator.LARGE_SIZE[1] - height) // 2))
            except OSError:
                pass
        return image

    def _preview(self):
        image = self._flag_image().resize((328, 208), Image.NEAREST)
        self.preview_ref = ImageTk.PhotoImage(image)
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, image=self.preview_ref, anchor="nw")

    def _accept(self):
        self.result = {
            "pattern": self.pattern_var.get(), "colors": list(self.colors), "emblem_path": self.emblem_path,
        }
        self.destroy()


class CountryTab(ttk.Frame):
    def __init__(self, master):
        super().__init__(master, padding=12)
        self.flag_path = None
        self.generated_flag = None
        self.portrait_path = None
        self.color = (120, 30, 30)
        self._flag_preview_ref = None
        self._build()
        state.subscribe(self.on_mod_changed)

    def _build(self):
        self.header = ui_kit.PageHeader(
            self, "Country",
            "Create a brand new playable country tag - colours, ideology, starting political party support, and the history/countries file the game reads on start.", help_key="country")

        body = ttk.Frame(self)
        body.pack(fill="both", expand=True)
        body.columnconfigure(0, weight=12)
        body.columnconfigure(1, weight=10)
        body.rowconfigure(0, weight=1)

        left = ttk.Frame(body)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        right = ttk.Frame(body)
        right.grid(row=0, column=1, sticky="nsew")

        # ---- Identity ----
        identity = ui_kit.Section(left, "Identity")
        identity.pack(fill="x", pady=(0, 12))
        f = identity.body

        row = 0
        ttk.Label(f, text="Country tag (3 letters)", style="FieldLabel.TLabel", background=theme.SURFACE).grid(row=row, column=0, sticky="w", pady=4)
        self.tag_var = tk.StringVar()
        self.tag_entry = ttk.Entry(f, textvariable=self.tag_var, width=8)
        self.tag_entry.grid(row=row, column=1, sticky="w", padx=8)
        self.tag_hint = ttk.Label(f, text="", style="Muted.TLabel", background=theme.SURFACE)
        self.tag_hint.grid(row=row, column=2, columnspan=2, sticky="w")
        self.tag_var.trace_add("write", lambda *_: (self._check_tag(), self._update_preview()))
        row += 1

        ttk.Label(f, text="Country name", style="FieldLabel.TLabel", background=theme.SURFACE).grid(row=row, column=0, sticky="w", pady=4)
        self.name_var = tk.StringVar()
        self.name_entry = ttk.Entry(f, textvariable=self.name_var, width=32)
        self.name_entry.grid(row=row, column=1, columnspan=2, sticky="w", padx=8)
        self.name_var.trace_add("write", lambda *_: self._update_preview())
        row += 1

        ttk.Label(f, text="Map colour", style="FieldLabel.TLabel", background=theme.SURFACE).grid(row=row, column=0, sticky="w", pady=4)
        self.color_btn = tk.Button(f, width=8, command=self._pick_color,
                                   bg="#78201e", activebackground="#78201e", relief="flat")
        self.color_btn.grid(row=row, column=1, sticky="w", padx=8)
        row += 1

        ttk.Label(f, text="Capital state id", style="FieldLabel.TLabel", background=theme.SURFACE).grid(row=row, column=0, sticky="w", pady=4)
        self.capital_var = tk.StringVar(value="49")
        ttk.Entry(f, textvariable=self.capital_var, width=8).grid(row=row, column=1, sticky="w", padx=8)
        ttk.Button(f, text="Pick on map...", command=self._pick_capital).grid(row=row, column=2, sticky="w")
        self.capital_var.trace_add("write", lambda *_: self._update_preview())
        row += 1

        ttk.Label(f, text="Flag image", style="FieldLabel.TLabel", background=theme.SURFACE).grid(row=row, column=0, sticky="w", pady=4)
        fframe = ttk.Frame(f, style="CardInner.TFrame")
        fframe.grid(row=row, column=1, columnspan=3, sticky="w", padx=8)
        ttk.Button(fframe, text="Browse...", command=self._pick_flag).pack(side="left")
        ttk.Button(fframe, text="Generate...", command=self._generate_flag).pack(side="left", padx=4)
        self.flag_preview = ttk.Label(fframe, background=theme.SURFACE)
        self.flag_preview.pack(side="left", padx=8)
        ttk.Label(fframe, text="82x52 / 41x26 / 10x7 TGAs", style="Muted.TLabel",
                  background=theme.SURFACE).pack(side="left")

        # ---- Starting politics ----
        politics = ui_kit.Section(left, "Starting politics")
        politics.pack(fill="x")
        f = politics.body

        row = 0
        ttk.Label(f, text="Ruling ideology", style="FieldLabel.TLabel", background=theme.SURFACE).grid(row=row, column=0, sticky="w", pady=4)
        self.ideology_var = tk.StringVar(value="neutrality")
        self.ideology_combo = ttk.Combobox(f, textvariable=self.ideology_var,
                                            values=country_creator.IDEOLOGIES, state="readonly", width=16)
        self.ideology_combo.grid(row=row, column=1, sticky="w", padx=8)
        ttk.Label(f, text="Popularity %", style="FieldLabel.TLabel", background=theme.SURFACE).grid(row=row, column=2, sticky="e")
        self.pop_var = tk.StringVar(value="60")
        ttk.Entry(f, textvariable=self.pop_var, width=6).grid(row=row, column=3, sticky="w", padx=6)
        self.ideology_var.trace_add("write", lambda *_: self._update_preview())
        self.pop_var.trace_add("write", lambda *_: self._update_preview())
        row += 1

        ttk.Label(f, text="Leader name", style="FieldLabel.TLabel", background=theme.SURFACE).grid(row=row, column=0, sticky="w", pady=4)
        self.leader_var = tk.StringVar()
        ttk.Entry(f, textvariable=self.leader_var, width=32).grid(row=row, column=1, columnspan=2, sticky="w", padx=8)
        self.leader_var.trace_add("write", lambda *_: self._update_preview())
        row += 1

        ttk.Label(f, text="Leader portrait", style="FieldLabel.TLabel", background=theme.SURFACE).grid(row=row, column=0, sticky="w", pady=4)
        pframe = ttk.Frame(f, style="CardInner.TFrame")
        pframe.grid(row=row, column=1, columnspan=3, sticky="w", padx=8)
        ttk.Button(pframe, text="Browse...", command=self._pick_portrait).pack(side="left")
        ttk.Button(pframe, text="Create...", command=self._create_portrait).pack(side="left", padx=4)
        self.portrait_label = ttk.Label(pframe, text="(optional)", style="Muted.TLabel", background=theme.SURFACE)
        self.portrait_label.pack(side="left", padx=6)
        row += 1

        ttk.Separator(f).grid(row=row, column=0, columnspan=4, sticky="we", pady=8)
        row += 1
        ttk.Label(f, text="Ideology-specific names (optional)", style="SectionHead.TLabel").grid(
            row=row, column=0, columnspan=4, sticky="w")
        row += 1
        ttk.Label(
            f, text="Blank = falls back to the country name above.",
            style="Muted.TLabel", background=theme.SURFACE, wraplength=420, justify="left",
        ).grid(row=row, column=0, columnspan=4, sticky="w", pady=(0, 4))
        row += 1
        # This inner frame is rebuilt when custom ideology groups are created.
        # The Country form itself does not need to be recreated for one extra
        # optional localisation field.
        self.ideology_name_vars = {}
        self.ideology_names_frame = ttk.Frame(f, style="CardInner.TFrame")
        self.ideology_names_frame.grid(row=row, column=0, columnspan=4, sticky="we")
        self._rebuild_ideology_name_fields(country_creator.IDEOLOGIES)

        # ---- right column: live preview + create ----
        preview = ui_kit.Section(right, "Generated script")
        preview.pack(fill="both", expand=True, pady=(0, 12))
        self.preview_text = tk.Text(preview.body, height=16, width=40, relief="flat", borderwidth=0,
                                    background=theme.CANVAS_BG, foreground=theme.MUTED_BRIGHT,
                                    font=(theme.FACE_MONO, 9), wrap="none")
        self.preview_text.pack(fill="both", expand=True)
        self.preview_text.tag_configure("key", foreground=theme.MUTED)
        self.preview_text.tag_configure("val", foreground=theme.GOLD)
        self.preview_text.configure(state="disabled")

        actions = ui_kit.Section(right, "Create")
        actions.pack(fill="x")
        self.create_btn = ttk.Button(actions.body, text="Create Country", style="Accent.TButton",
                                     command=self._create)
        self.create_btn.pack(anchor="w")
        ui_kit.attach_tooltip(
            self.create_btn,
            lambda: "Fill in a country tag and name first." if self.create_btn["state"] == "disabled"
            else "Writes the country into the open mod.")
        self.status = ttk.Label(actions.body, text="", style="Status.TLabel", background=theme.SURFACE,
                                wraplength=380, justify="left")
        self.status.pack(anchor="w", pady=(10, 0))
        self._check_required = ui_kit.guard_required(
            {self.tag_entry: self.tag_var, self.name_entry: self.name_var}, self.create_btn)
        ttk.Label(
            actions.body,
            text="Writes the tag, country file, map colour, flag TGAs, starting leader, history file "
                 "and localisation into the open mod. Give it land afterwards via a state's history file "
                 "or a focus/decision.",
            style="Muted.TLabel", background=theme.SURFACE, wraplength=380, justify="left",
        ).pack(anchor="w", pady=(10, 0))

        self.on_mod_changed()
        self._update_preview()

    def _update_preview(self):
        tag = (self.tag_var.get().strip() or "XXX").upper()
        name = self.name_var.get().strip() or "(unnamed)"
        capital = self.capital_var.get().strip() or "0"
        ideology = self.ideology_var.get() or "neutrality"
        pop = self.pop_var.get().strip() or "0"
        leader = self.leader_var.get().strip() or "(none)"

        lines = [
            ("capital", capital),
            ("oob", f'"{tag}_1936"'),
            ("set_research_slots", "4"),
        ]
        self.preview_text.configure(state="normal")
        self.preview_text.delete("1.0", "end")
        for key, val in lines:
            self.preview_text.insert("end", f"{key}", "key")
            self.preview_text.insert("end", f" = {val}\n", "val")
        self.preview_text.insert("end", "set_politics", "key")
        self.preview_text.insert("end", " = {\n", "val")
        self.preview_text.insert("end", f"  ruling_party = {ideology}\n  elections_allowed = yes\n}}\n", "val")
        self.preview_text.insert("end", "add_ideas", "key")
        self.preview_text.insert("end", " = { ideology_" + ideology + " }\n\n", "val")
        self.preview_text.insert("end", f"# {name}  ({tag})\n# leader: {leader}\n# {ideology} popularity: {pop}%\n", "key")
        self.preview_text.configure(state="disabled")

    # ---- helpers ----

    def on_mod_changed(self):
        if state.is_loaded:
            self.header.set_status(True, state.mod_name)
            self._known_tags = None  # recollect lazily per mod
            custom = sorted(ideology_creator.existing_group_ids(state.mod_root))
            ideologies = country_creator.IDEOLOGIES + custom
            self.ideology_combo["values"] = ideologies
            self._rebuild_ideology_name_fields(ideologies)
        else:
            self.header.set_status(False, "no mod open")

    def _rebuild_ideology_name_fields(self, ideologies):
        """Show optional country-name overrides for vanilla and custom groups."""
        previous = {key: value.get() for key, value in self.ideology_name_vars.items()}
        for child in self.ideology_names_frame.winfo_children():
            child.destroy()
        self.ideology_name_vars = {}
        for row, ideology in enumerate(ideologies):
            display = state.text_for(ideology, ideology)
            ttk.Label(
                self.ideology_names_frame, text=f"{display} name",
                style="FieldLabel.TLabel", background=theme.SURFACE,
            ).grid(row=row, column=0, sticky="w", pady=2)
            value = tk.StringVar(value=previous.get(ideology, ""))
            ttk.Entry(self.ideology_names_frame, textvariable=value, width=28).grid(
                row=row, column=1, columnspan=2, sticky="w", padx=8
            )
            self.ideology_name_vars[ideology] = value

    def on_show(self):
        self.on_mod_changed()

    def _check_tag(self):
        tag = self.tag_var.get().strip().upper()
        if len(tag) != 3 or not tag.isalnum() or not tag[0].isalpha():
            self.tag_hint.config(text="3 characters, letters/digits, starts with a letter", foreground=theme.MUTED)
            return
        if not state.is_loaded:
            return
        if getattr(self, "_known_tags", None) is None:
            self._known_tags = country_creator.existing_tags(state.mod_root)
        if tag in self._known_tags:
            self.tag_hint.config(text=f"{tag} is already taken!", foreground=theme.RED)
        else:
            self.tag_hint.config(text=f"{tag} is free ✓", foreground=theme.GREEN)

    def _pick_capital(self):
        if not state.is_loaded:
            messagebox.showerror("No mod", "Open or create a mod first.")
            return
        dlg = MapPickerDialog(self, state.mod_root, purpose="the capital")
        self.wait_window(dlg)
        if dlg.result:
            self.capital_var.set(str(dlg.result["state"]))
            self.status.config(text=f"Capital set to {dlg.result['label']}.")

    def _pick_color(self):
        rgb, _hex = colorchooser.askcolor(color=self.color, title="Map colour")
        if rgb:
            self.color = tuple(int(v) for v in rgb)
            hexcode = "#%02x%02x%02x" % self.color
            self.color_btn.configure(bg=hexcode, activebackground=hexcode)

    def _pick_portrait(self):
        path = filedialog.askopenfilename(
            title="Pick a portrait", filetypes=[("Images", "*.png *.dds *.tga *.jpg *.jpeg"), ("All", "*.*")],
        )
        if path:
            self.portrait_path = path
            self.portrait_label.config(text=os.path.basename(path))

    def _create_portrait(self):
        if not portrait_creator.pack_available():
            messagebox.showerror("Pack missing", "The portrait template pack was not found.")
            return
        creator = portrait_creator.PortraitCreator(self, kind="leader")
        self.wait_window(creator)
        if creator.result:
            self.portrait_path = creator.result
            self.portrait_label.config(text="(composed portrait)")

    def _pick_flag(self):
        path = filedialog.askopenfilename(
            title="Pick a flag image", filetypes=[("Images", "*.png *.jpg *.jpeg *.bmp *.tga *.dds"), ("All", "*.*")],
        )
        if not path:
            return
        self.flag_path = path
        self.generated_flag = None
        try:
            im = Image.open(path).convert("RGBA").resize((82, 52), Image.LANCZOS)
            self._flag_preview_ref = ImageTk.PhotoImage(im)
            self.flag_preview.config(image=self._flag_preview_ref)
        except Exception:
            self.flag_preview.config(image="", text=os.path.basename(path))

    def _generate_flag(self):
        """Create a simple flag while creating the country, without a second workflow."""
        dialog = CountryFlagDialog(self, self.color)
        self.wait_window(dialog)
        if not dialog.result:
            return
        self.generated_flag = dialog.result
        self.flag_path = None
        image = flag_creator._draw_pattern(
            dialog.result["pattern"], flag_creator.LARGE_SIZE, dialog.result["colors"]
        ).convert("RGBA")
        self._flag_preview_ref = ImageTk.PhotoImage(image)
        self.flag_preview.config(image=self._flag_preview_ref, text="")

    # ---- create ----

    def _create(self):
        if not state.is_loaded:
            messagebox.showerror("No mod", "Open or create a mod first.")
            return
        tag = self.tag_var.get().strip().upper()
        name = self.name_var.get().strip()
        leader = self.leader_var.get().strip()
        if len(tag) != 3 or not name or not leader:
            messagebox.showerror("Missing info", "Tag (3 letters), country name and leader name are required.")
            return
        if getattr(self, "_known_tags", None) is None:
            self._known_tags = country_creator.existing_tags(state.mod_root)
        if tag in self._known_tags:
            messagebox.showerror("Tag taken", f"{tag} already exists in the base game or this mod.")
            return
        if not (self.flag_path or self.generated_flag):
            if not messagebox.askyesno("No flag", "No flag image picked — the country will use a missing-texture flag. Continue?"):
                return
        try:
            capital = int(self.capital_var.get())
            popularity = max(1, min(100, int(self.pop_var.get() or 60)))
        except ValueError:
            messagebox.showerror("Bad number", "Capital state id and popularity must be numbers.")
            return

        ideology = self.ideology_var.get()
        leader_sub_ideology = None
        if ideology not in country_creator.IDEOLOGIES:
            leader_sub_ideology = ideology_creator.first_sub_ideology(state.mod_root, ideology)

        try:
            created, char_id, safe_name = country_creator.create_country(
                state.mod_root, tag=tag, name=name, color=self.color,
                capital_state=capital, ideology=ideology,
                leader_name=leader, leader_portrait=self.portrait_path,
                popularity=popularity, leader_sub_ideology=leader_sub_ideology,
            )
            if self.flag_path:
                created.extend(country_creator._write_flags(state.mod_root, tag, self.flag_path))
            elif self.generated_flag:
                created.extend(flag_creator.create_flag(
                    state.mod_root, tag=tag, ideology="",
                    pattern=self.generated_flag["pattern"],
                    colors=self.generated_flag["colors"],
                    emblem_path=self.generated_flag.get("emblem_path") or None,
                ))
            ideology_names = {ideo: var.get() for ideo, var in self.ideology_name_vars.items()}
            loc_path = country_creator.write_localisation(
                state.mod_root, tag, name, leader, char_id, self.ideology_var.get(),
                ideology_names=ideology_names, ideologies=list(self.ideology_combo["values"]),
            )
            created.append(loc_path)
            mod_export.record_created(state.mod_root, [p for p in created if os.path.isfile(str(p))])
        except Exception as exc:
            messagebox.showerror("Failed", f"Country creation failed:\n{exc}")
            return

        self._known_tags.add(tag)
        state.add_loc(tag, name)
        self.status.config(
            text=f"Created {name} ({tag}) — {len(created)} files written.\n"
                 f"In game: the country owns nothing yet; give it state {capital} by editing that state's "
                 "history file, or release it via console (tag switch) to test."
        )
