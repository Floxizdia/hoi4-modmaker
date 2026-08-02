"""Events generator tab: build country/news events with options and export
to events/<namespace>.txt."""

import os
import tkinter as tk
from tkinter import ttk, messagebox

from app.state import state
from app import pds
from app import theme, ui_kit
from app import mod_loader as ml
from app import safe_io
from app.event_preview import EventPreview
from app import event_owner
from app.effect_wizard import EffectWizard
from app import dirty
from app import templates
from app.template_picker import TemplatePicker
from app import event_picture_composer
from app.map_data import BASE_GAME


def from_parsed(e):
    """Convert an event parsed out of a mod file into this tab's shape."""
    options = []
    for o in e["options"]:
        options.append({
            "name": state.text_for(o["name_key"], o["name_key"]),
            "ai_factor": o.get("ai_factor", ""),
            "effect": o.get("effect", ""),
        })
    return {
        "number": e["number"],
        "type": e["type"],
        "title": state.text_for(e["title_key"], e["title_key"]),
        "desc": state.text_for(e["desc_key"], ""),
        "picture": e.get("picture", "") or "GFX_report_event_generic_meeting",
        "is_triggered_only": e.get("is_triggered_only", True),
        "trigger": e.get("trigger", ""),
        "immediate": e.get("immediate", ""),
        "options": options,
    }


class OptionDialog(tk.Toplevel):
    def __init__(self, master, option=None):
        super().__init__(master)
        self.title("Event Option")
        self.result = None
        self.resizable(False, False)
        o = option or {}

        ttk.Label(self, text="Option name (localisation text)").grid(row=0, column=0, sticky="w", padx=8, pady=4)
        self.name_var = tk.StringVar(value=o.get("name", ""))
        ttk.Entry(self, textvariable=self.name_var, width=42).grid(row=0, column=1, padx=8, pady=4)

        ttk.Label(self, text="ai_chance factor (optional)").grid(row=1, column=0, sticky="w", padx=8, pady=4)
        self.ai_var = tk.StringVar(value=str(o.get("ai_factor", "")))
        ttk.Entry(self, textvariable=self.ai_var, width=42).grid(row=1, column=1, padx=8, pady=4)

        ttk.Label(self, text="Effect (raw)").grid(row=2, column=0, sticky="nw", padx=8, pady=4)
        self.effect_txt = tk.Text(self, width=42, height=5)
        self.effect_txt.insert("1.0", o.get("effect", ""))
        self.effect_txt.grid(row=2, column=1, padx=8, pady=4)
        ttk.Button(self, text="Wizard...", command=lambda: EffectWizard(self, self.effect_txt, "effect")).grid(row=2, column=2, sticky="n", pady=4)

        btns = ttk.Frame(self)
        btns.grid(row=3, column=0, columnspan=2, pady=10)
        ttk.Button(btns, text="Save", command=self._save).pack(side="left", padx=4)
        ttk.Button(btns, text="Cancel", command=self.destroy).pack(side="left", padx=4)
        self.grab_set()

    def _save(self):
        name = self.name_var.get().strip()
        if not name:
            messagebox.showerror("Missing name", "Option name is required.")
            return
        self.result = {
            "name": name,
            "ai_factor": self.ai_var.get().strip(),
            "effect": self.effect_txt.get("1.0", "end").strip(),
        }
        self.destroy()


class EventDialog(tk.Toplevel):
    def __init__(self, master, event=None):
        super().__init__(master)
        self.title("Event")
        self.result = None
        self.options = list((event or {}).get("options", []))
        self.resizable(False, False)
        self._build(event or {})
        self.grab_set()

    def _build(self, e):
        ttk.Label(self, text="Event number (within namespace)").grid(row=0, column=0, sticky="w", padx=8, pady=4)
        self.num_var = tk.StringVar(value=str(e.get("number", "")))
        ttk.Entry(self, textvariable=self.num_var, width=10).grid(row=0, column=1, sticky="w", padx=8, pady=4)

        ttk.Label(self, text="Type").grid(row=1, column=0, sticky="w", padx=8, pady=4)
        self.type_var = tk.StringVar(value=e.get("type", "country_event"))
        ttk.Combobox(
            self, textvariable=self.type_var, values=["country_event", "news_event", "state_event"], width=18
        ).grid(row=1, column=1, sticky="w", padx=8, pady=4)

        ttk.Label(self, text="Title (localisation text)").grid(row=2, column=0, sticky="w", padx=8, pady=4)
        self.title_var = tk.StringVar(value=e.get("title", ""))
        ttk.Entry(self, textvariable=self.title_var, width=42).grid(row=2, column=1, padx=8, pady=4)

        ttk.Label(self, text="Description (localisation text)").grid(row=3, column=0, sticky="w", padx=8, pady=4)
        self.desc_var = tk.StringVar(value=e.get("desc", ""))
        ttk.Entry(self, textvariable=self.desc_var, width=42).grid(row=3, column=1, padx=8, pady=4)

        ttk.Label(self, text="Picture (GFX name)").grid(row=4, column=0, sticky="w", padx=8, pady=4)
        self.picture_var = tk.StringVar(value=e.get("picture", "GFX_report_event_generic_meeting"))
        pic_row = ttk.Frame(self)
        pic_row.grid(row=4, column=1, columnspan=2, sticky="w", padx=8, pady=4)
        ttk.Entry(pic_row, textvariable=self.picture_var, width=32).pack(side="left")
        ttk.Button(pic_row, text="Compose...", command=self._compose_picture).pack(side="left", padx=(4, 0))

        self.triggered_var = tk.BooleanVar(value=e.get("is_triggered_only", True))
        ttk.Checkbutton(self, text="is_triggered_only", variable=self.triggered_var).grid(
            row=5, column=0, columnspan=2, sticky="w", padx=8, pady=4
        )

        ttk.Label(self, text="trigger (raw, optional)").grid(row=6, column=0, sticky="nw", padx=8, pady=4)
        self.trigger_txt = tk.Text(self, width=42, height=3)
        self.trigger_txt.insert("1.0", e.get("trigger", ""))
        self.trigger_txt.grid(row=6, column=1, padx=8, pady=4)
        ttk.Button(self, text="Wizard...", command=lambda: EffectWizard(self, self.trigger_txt, "trigger")).grid(row=6, column=2, sticky="n", pady=4)

        ttk.Label(self, text="immediate (raw effect, optional)").grid(row=7, column=0, sticky="nw", padx=8, pady=4)
        self.immediate_txt = tk.Text(self, width=42, height=3)
        self.immediate_txt.insert("1.0", e.get("immediate", ""))
        self.immediate_txt.grid(row=7, column=1, padx=8, pady=4)
        ttk.Button(self, text="Wizard...", command=lambda: EffectWizard(self, self.immediate_txt, "effect")).grid(row=7, column=2, sticky="n", pady=4)
        from app import ref_picker
        ttk.Button(self, text="Link...",
                   command=lambda: ref_picker.open_picker(self, state.mod_root, self.immediate_txt)
                   ).grid(row=7, column=3, sticky="n", pady=4)

        ttk.Label(self, text="Options").grid(row=8, column=0, sticky="nw", padx=8, pady=4)
        self.opt_list = tk.Listbox(self, height=5, width=42)
        for o in self.options:
            self.opt_list.insert("end", o["name"])
        self.opt_list.grid(row=8, column=1, padx=8, pady=4, sticky="w")

        opt_btns = ttk.Frame(self)
        opt_btns.grid(row=9, column=1, sticky="w", padx=8)
        ttk.Button(opt_btns, text="Add Option", command=self._add_option).pack(side="left", padx=2)
        ttk.Button(opt_btns, text="Edit Option", command=self._edit_option).pack(side="left", padx=2)
        ttk.Button(opt_btns, text="Delete Option", command=self._delete_option).pack(side="left", padx=2)

        btns = ttk.Frame(self)
        btns.grid(row=10, column=0, columnspan=2, pady=10)
        ttk.Button(btns, text="Save", command=self._save).pack(side="left", padx=4)
        ttk.Button(btns, text="Cancel", command=self.destroy).pack(side="left", padx=4)

    def _add_option(self):
        dlg = OptionDialog(self)
        self.wait_window(dlg)
        if dlg.result:
            self.options.append(dlg.result)
            self.opt_list.insert("end", dlg.result["name"])

    def _edit_option(self):
        sel = self.opt_list.curselection()
        if not sel:
            return
        idx = sel[0]
        dlg = OptionDialog(self, self.options[idx])
        self.wait_window(dlg)
        if dlg.result:
            self.options[idx] = dlg.result
            self.opt_list.delete(idx)
            self.opt_list.insert(idx, dlg.result["name"])

    def _delete_option(self):
        sel = self.opt_list.curselection()
        if not sel:
            return
        idx = sel[0]
        del self.options[idx]
        self.opt_list.delete(idx)

    def _compose_picture(self):
        if not event_picture_composer.pack_available():
            messagebox.showerror("Pack missing", "The icon/picture template pack was not found.")
            return
        composer = event_picture_composer.EventPictureComposer(self, state.mod_root)
        self.wait_window(composer)
        if composer.result:
            self.picture_var.set(composer.result["sprite"])

    def _save(self):
        num = self.num_var.get().strip()
        if not num.isdigit():
            messagebox.showerror("Bad number", "Event number must be a positive integer.")
            return
        if not self.options:
            messagebox.showerror("No options", "Add at least one option.")
            return
        self.result = {
            "number": int(num),
            "type": self.type_var.get(),
            "title": self.title_var.get().strip(),
            "desc": self.desc_var.get().strip(),
            "picture": self.picture_var.get().strip(),
            "is_triggered_only": self.triggered_var.get(),
            "trigger": self.trigger_txt.get("1.0", "end").strip(),
            "immediate": self.immediate_txt.get("1.0", "end").strip(),
            "options": self.options,
        }
        self.destroy()


class EventsTab(ttk.Frame):
    def __init__(self, master):
        super().__init__(master, padding=12)
        self.events = []
        self._file_items = []
        self.source_file = None
        self._build()
        state.subscribe(self.on_mod_changed)
        dirty.track(self, mutators=("_add", "_edit", "_delete", "_from_template"))

    def _build(self):
        self.header = ui_kit.PageHeader(
            self, "Events",
            "Create/edit events (country_event, news_event...) with options, triggers and effects - the pop-ups the game shows the player.", help_key="events")

        loader = ttk.Frame(self)
        loader.pack(fill="x")
        ttk.Label(loader, text="Load from mod:").pack(side="left")
        self.file_combo = ttk.Combobox(loader, state="readonly", width=52)
        self.file_combo.pack(side="left", padx=6)
        ttk.Button(loader, text="Load", command=self._load_from_mod).pack(side="left")
        ttk.Button(loader, text="New empty file", command=self._new_file).pack(side="left", padx=6)

        top = ttk.Frame(self)
        top.pack(fill="x", pady=(8, 0))
        ttk.Label(top, text="Namespace").pack(side="left")
        self.ns_var = tk.StringVar(value="my_events")
        ttk.Entry(top, textvariable=self.ns_var, width=25).pack(side="left", padx=6)

        search = ttk.Frame(self)
        search.pack(fill="x", pady=(8, 0))
        ttk.Label(search, text="Search:").pack(side="left")
        self.search_var = tk.StringVar()
        entry = ttk.Entry(search, textvariable=self.search_var, width=36)
        self.search_entry = entry
        entry.pack(side="left", padx=6)
        entry.bind("<KeyRelease>", lambda e: self._refresh())
        ttk.Button(search, text="Clear", command=lambda: (self.search_var.set(""), self._refresh())).pack(side="left")

        ttk.Label(search, text="   Country:").pack(side="left")
        self.country_var = tk.StringVar(value="(all)")
        self.country_combo = ttk.Combobox(
            search, textvariable=self.country_var, state="readonly", width=14, values=["(all)"]
        )
        self.country_combo.pack(side="left", padx=4)
        self.country_var.trace_add("write", lambda *_: self._refresh())
        ttk.Button(search, text="Detect countries", command=self._detect_countries).pack(side="left", padx=4)

        self.count_label = ttk.Label(search, text="", foreground="#888")
        self.count_label.pack(side="left", padx=10)

        body = ttk.Frame(self)
        body.pack(fill="both", expand=True, pady=10)
        body.columnconfigure(0, weight=1)
        body.rowconfigure(0, weight=1)

        cols = ("id", "type", "title", "opt", "triggered")
        widths = {"id": 150, "type": 110, "title": 300, "opt": 50, "triggered": 90}
        headings = {"id": "ID", "type": "TYPE", "title": "TITLE", "opt": "OPT", "triggered": "TRIGGERED"}
        self.tree = ttk.Treeview(body, columns=cols, show="headings", height=14)
        for c in cols:
            self.tree.heading(c, text=headings[c])
            self.tree.column(c, width=widths[c], anchor=("center" if c == "opt" else "w"))
        self.tree.grid(row=0, column=0, sticky="nsew")
        self.tree.tag_configure("odd", background=theme.RAISED)
        self.tree.bind("<Double-Button-1>", lambda e: self._preview())
        self.tree.bind("<<TreeviewSelect>>", lambda e: self._refresh_detail())

        detail = ui_kit.Section(body, "Detail")
        detail.grid(row=0, column=1, sticky="ns", padx=(12, 0))
        detail.configure(width=280)
        detail.pack_propagate(False)
        self.detail_title = ttk.Label(detail.body, text="Select an event", background=theme.SURFACE,
                                      foreground=theme.TEXT, font=(theme.FACE_DISPLAY, 11, "bold"),
                                      wraplength=250, justify="left")
        self.detail_title.pack(anchor="w", pady=(0, 8))
        self.detail_fields = ttk.Label(detail.body, text="", background=theme.SURFACE,
                                       foreground=theme.MUTED_BRIGHT, font=(theme.FACE_MONO, 9),
                                       justify="left", wraplength=250)
        self.detail_fields.pack(anchor="w", pady=(0, 8))
        ttk.Label(detail.body, text=f"OPTIONS", style="FieldLabel.TLabel").pack(anchor="w")
        self.detail_options = tk.Listbox(detail.body, height=6, relief="flat", borderwidth=0,
                                         background=theme.CANVAS_BG, foreground=theme.TEXT,
                                         font=(theme.FACE_MONO, 9), highlightthickness=0)
        self.detail_options.pack(fill="x", pady=(2, 8))
        detail_btns = ttk.Frame(detail.body, style="CardInner.TFrame")
        detail_btns.pack(anchor="w")
        ttk.Button(detail_btns, text="Edit event", style="Accent.TButton", command=self._edit).pack(side="left")
        ttk.Button(detail_btns, text="Preview", command=self._preview).pack(side="left", padx=(6, 0))
        ttk.Button(detail_btns, text="Used by...", command=self._show_references).pack(side="left", padx=(6, 0))

        btns = ttk.Frame(self)
        btns.pack(fill="x")
        ttk.Button(btns, text="Add Event", command=self._add).pack(side="left", padx=4)
        ttk.Button(btns, text="From Template...", command=self._from_template).pack(side="left", padx=4)
        ttk.Button(btns, text="Edit Selected", command=self._edit).pack(side="left", padx=4)
        ttk.Button(btns, text="Delete Selected", command=self._delete).pack(side="left", padx=4)
        ttk.Button(btns, text="Preview in game style", command=self._preview).pack(side="left", padx=12)
        ttk.Button(btns, text="Save to mod", command=self._export).pack(side="right", padx=4)

        self.status = ttk.Label(self, text="", foreground="#2a7a2a", wraplength=900, justify="left")
        self.status.pack(fill="x", pady=(6, 0))

        self.on_mod_changed()

    # ---- mod integration ----

    def on_mod_changed(self):
        # keep this cheap - the heavy scan runs when the tab is shown
        self._needs_reload = True
        self.is_dirty = False
        if state.is_loaded:
            self.header.set_status(True, state.mod_name)
        else:
            self.header.set_status(False, "no mod open")

    def on_show(self):
        if getattr(self, "_needs_reload", False) and state.is_loaded:
            self._needs_reload = False
            self._reload_from_mod()

    def _reload_from_mod_guard(self):
        pass

    def _reload_from_mod(self):
        if not state.is_loaded:
            self.header.set_status(False, "no mod open")
            self.file_combo["values"] = []
            return
        self.header.set_status(True, state.mod_name)
        self._file_items = [(path, "vanilla") for path in ml.find_event_files(BASE_GAME)]
        self._file_items += [(path, "mod") for path in ml.find_event_files(state.mod_root)]
        self.file_combo["values"] = [
            f"[{source}] {os.path.relpath(path, BASE_GAME if source == 'vanilla' else state.mod_root)}"
            for path, source in self._file_items
        ]
        if paths:
            self.file_combo.current(0)

    def _load_from_mod(self):
        idx = self.file_combo.current()
        if idx < 0 or not self._file_items:
            messagebox.showerror("Nothing to load", "This mod has no event files, or no mod is open.")
            return
        path, source = self._file_items[idx]
        namespaces, parsed = ml.parse_events(path)
        if not parsed:
            messagebox.showerror("Empty file", "No events could be read from that file.")
            return

        # this tab writes one namespace per file, so edit the dominant one
        counts = {}
        for e in parsed:
            counts[e["namespace"]] = counts.get(e["namespace"], 0) + 1
        main_ns = max(counts, key=counts.get)

        self.events = [from_parsed(e) for e in parsed
                       if e["namespace"] == main_ns and isinstance(e["number"], int)]
        self.ns_var.set(main_ns)
        self._refresh()

        # This tab writes exactly one namespace per file. Saving back over a
        # file that declares several would delete the rest, so only reuse the
        # source path when this namespace is the whole file.
        if len(counts) == 1 and len(self.events) == len(parsed) and source != "vanilla":
            self.source_file = path
            note = ""
        else:
            self.source_file = None
            note = ("  Vanilla source is read-only; saving creates a mod-local event file."
                    if source == "vanilla" else
                    f"  That file holds {len(counts)} namespaces, so saving will create a separate "
                    f"{main_ns}.txt instead of overwriting it.")

        self.status.config(text=f"Loaded {len(self.events)} events from {os.path.basename(path)}.{note}")

    def _new_file(self):
        self.events = []
        self.source_file = None
        self.ns_var.set("my_events")
        self._refresh()
        self.status.config(text="Started an empty event file.")

    def _full_id(self, number):
        return f"{self.ns_var.get().strip()}.{number}"

    def _detect_countries(self):
        """Work out which country each event belongs to. Cached on the shared
        state so the scan runs once per mod, not once per tab visit."""
        if not state.is_loaded:
            messagebox.showerror("No mod", "Open a mod first.")
            return

        owners = getattr(state, "event_owners", None)
        if owners is None:
            self.status.config(text="Tracing which focus, decision or event fires each event...")
            self.update_idletasks()
            owners = event_owner.build_ownership(
                state.mod_root,
                progress=lambda m: (self.status.config(text=m), self.update_idletasks()),
            )
            state.event_owners = owners

        ns = self.ns_var.get().strip()
        tags = set()
        unknown = 0
        for e in self.events:
            found = owners.get(f"{ns}.{e['number']}") or set()
            if found:
                tags |= found
            else:
                unknown += 1

        values = ["(all)"] + sorted(tags)
        if unknown:
            values.append("(unknown)")
        self.country_combo["values"] = values
        self.country_var.set("(all)")

        self.status.config(
            text=f"Detected {len(tags)} countries across these events "
                 f"({unknown} could not be traced and show as \"(unknown)\"). "
                 "Ownership is inferred from what fires each event, so it is a strong hint, not a guarantee."
        )
        self._refresh()

    def _country_ok(self, e):
        choice = self.country_var.get()
        if choice == "(all)":
            return True
        owners = getattr(state, "event_owners", None) or {}
        found = owners.get(f"{self.ns_var.get().strip()}.{e['number']}") or set()
        if choice == "(unknown)":
            return not found
        return choice in found

    def _matches(self, e):
        if not self._country_ok(e):
            return False
        needle = self.search_var.get().strip().lower()
        if not needle:
            return True
        haystack = " ".join([
            str(e["number"]), e["type"], e.get("title", ""), e.get("desc", ""),
            " ".join(o.get("name", "") for o in e["options"]),
        ]).lower()
        return needle in haystack

    def _refresh(self):
        self.tree.delete(*self.tree.get_children())
        shown = 0
        for e in self.events:
            if not self._matches(e):
                continue
            fid = self._full_id(e["number"])
            self.tree.insert(
                "", "end", iid=fid, tags=("odd",) if shown % 2 else (),
                values=(fid, e["type"], e["title"], len(e["options"]),
                        "yes" if e["is_triggered_only"] else "no"),
            )
            shown += 1
        self.count_label.config(
            text=f"{shown} of {len(self.events)}" if len(self.events) != shown else f"{shown} events"
        )
        self._refresh_detail()

    def _selected_event(self):
        sel = self.tree.selection()
        if not sel:
            return None
        number = int(sel[0].split(".")[-1])
        return next((e for e in self.events if e["number"] == number), None)

    def _refresh_detail(self):
        e = self._selected_event()
        self.detail_options.delete(0, "end")
        if not e:
            self.detail_title.config(text="Select an event")
            self.detail_fields.config(text="")
            return
        fid = self._full_id(e["number"])
        self.detail_title.config(text=f"{fid}\n{e['title']}")
        self.detail_fields.config(
            text=f"type      {e['type']}\n"
                 f"picture   {e['picture']}\n"
                 f"triggered {'yes' if e['is_triggered_only'] else 'no'}"
        )
        for i, o in enumerate(e["options"], start=1):
            self.detail_options.insert("end", f"{chr(96 + i)} — {o['name']}")
        if not e["options"]:
            self.detail_options.insert("end", "(no options)")

    def _show_references(self):
        """What would break if this event were deleted - the question the
        game's own files can't answer, because references only point one way."""
        e = self._selected_event()
        if not e:
            messagebox.showerror("Nothing selected", "Pick an event first.")
            return
        if not state.is_loaded:
            messagebox.showerror("No mod", "Open a mod first.")
            return
        from app import references
        references.open_dialog(self, state.mod_root, self._full_id(e["number"]))

    def _preview(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showerror("Nothing selected", "Pick an event first.")
            return
        number = int(sel[0].split(".")[-1])
        event = next((e for e in self.events if e["number"] == number), None)
        if event:
            EventPreview(self, event, self.ns_var.get().strip() or "my_events")

    def _add(self):
        dlg = EventDialog(self)
        self.wait_window(dlg)
        if dlg.result:
            if any(e["number"] == dlg.result["number"] for e in self.events):
                messagebox.showerror("Duplicate number", "An event with that number already exists.")
                return
            self.events.append(dlg.result)
            self._register_loc(dlg.result)
            self._refresh()

    def _from_template(self):
        picker = TemplatePicker(self, templates.EVENT_TEMPLATES,
                                prefix_hint=self.ns_var.get().strip() or "my")
        self.wait_window(picker)
        if not picker.result:
            return
        dlg = EventDialog(self, picker.result)
        self.wait_window(dlg)
        if dlg.result:
            if any(e["number"] == dlg.result["number"] for e in self.events):
                messagebox.showerror("Duplicate number", "An event with that number already exists.")
                return
            self.events.append(dlg.result)
            self._register_loc(dlg.result)
            self._refresh()

    def _edit(self):
        sel = self.tree.selection()
        if not sel:
            return
        number = int(sel[0].split(".")[-1])
        idx = next(i for i, e in enumerate(self.events) if e["number"] == number)
        dlg = EventDialog(self, self.events[idx])
        self.wait_window(dlg)
        if dlg.result:
            self.events[idx] = dlg.result
            self._register_loc(dlg.result)
            self._refresh()

    def _delete(self):
        sel = self.tree.selection()
        if not sel:
            return
        numbers = {int(s.split(".")[-1]) for s in sel}
        self.events = [e for e in self.events if e["number"] not in numbers]
        self._refresh()

    def _register_loc(self, e):
        fid = self._full_id(e["number"])
        state.add_loc(f"{fid}.t", e["title"])
        state.add_loc(f"{fid}.d", e["desc"])
        for i, o in enumerate(e["options"], start=1):
            state.add_loc(f"{fid}.{chr(96 + i)}", o["name"])

    def _export(self):
        if not state.is_loaded:
            messagebox.showerror("No mod folder", "Open a mod, or create one in the Settings tab first.")
            return
        if not self.events:
            messagebox.showerror("Nothing to save", "Add at least one event first.")
            return

        ns = self.ns_var.get().strip() or "my_events"
        blocks = []
        for e in self.events:
            fid = self._full_id(e["number"])
            body = [
                pds.kv("id", fid),
                pds.kv("title", f"{fid}.t"),
                pds.kv("desc", f"{fid}.d"),
                pds.kv("picture", e["picture"]),
            ]
            if e["is_triggered_only"]:
                body.append(pds.kv("is_triggered_only", "yes"))
            if e["trigger"]:
                body.append(pds.block("trigger", e["trigger"]))
            if e["immediate"]:
                body.append(pds.block("immediate", e["immediate"]))
            for i, o in enumerate(e["options"], start=1):
                opt_body = [pds.kv("name", f"{fid}.{chr(96 + i)}")]
                if o["ai_factor"]:
                    opt_body.append(pds.block("ai_chance", pds.kv("factor", o["ai_factor"])))
                if o["effect"]:
                    opt_body.append(o["effect"])
                body.append(pds.block("option", "\n".join(opt_body)))
            blocks.append(pds.block(e["type"], "\n".join(body)))

        content = f"add_namespace = {ns}\n\n" + "\n\n".join(blocks) + "\n"
        out_dir = state.ensure_dir("events")
        out_path = self.source_file or os.path.join(out_dir, f"{ns}.txt")

        if safe_io.write_text(out_path, content, parent=self, describe="this event file"):
            self.status.config(text=f"Saved {len(self.events)} events to {out_path}")
        else:
            self.status.config(text="Save cancelled.")
