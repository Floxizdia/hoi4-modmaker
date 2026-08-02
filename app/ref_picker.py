"""Insert-a-reference dialog: pick an existing event or decision from the
currently open mod and drop the right script snippet (country_event = {...}
or activate_decision = ...) into a raw-effect text widget at the cursor.
Used from Focus/Events/Decisions to link content together without having
to remember ids or exact effect syntax."""

import tkinter as tk
from tkinter import ttk, messagebox

from app import mod_loader as ml
from app import searchable_combo


def _collect(mod_root):
    """[(label, snippet)] for every event and decision in the mod."""
    items = []
    for path in ml.find_event_files(mod_root):
        try:
            _, events = ml.parse_events(path)
        except Exception:
            continue
        for e in events:
            full_id = f"{e['namespace']}.{e['number']}"
            snippet = f"country_event = {{ id = {full_id} }}"
            items.append((f"[event] {full_id}  ({e['type']})", snippet))
    for path in ml.find_decision_files(mod_root):
        try:
            categories = ml.parse_decisions(path)
        except Exception:
            continue
        for cat in categories:
            for d in cat["decisions"]:
                snippet = f"activate_decision = {d['id']}"
                items.append((f"[decision] {d['id']}", snippet))
    return items


class RefPickerDialog(tk.Toplevel):
    def __init__(self, master, mod_root, on_pick):
        super().__init__(master)
        self.title("Insert Event / Decision Reference")
        self.geometry("460x140")
        self.resizable(False, False)
        self.transient(master)
        self.on_pick = on_pick
        self._items = _collect(mod_root)

        ttk.Label(self, text="Pick the event or decision to insert "
                              "(type to filter):").pack(anchor="w", padx=14, pady=(14, 4))
        self.combo = ttk.Combobox(self, width=52)
        self.combo.pack(padx=14, fill="x")
        searchable_combo.enable_filter(self.combo, lambda: [i[0] for i in self._items])
        self.combo["values"] = [i[0] for i in self._items]

        if not self._items:
            ttk.Label(self, text="No events or decisions found in this mod yet.",
                       foreground="#b06").pack(padx=14, pady=(8, 0), anchor="w")

        row = ttk.Frame(self)
        row.pack(fill="x", padx=14, pady=14)
        ttk.Button(row, text="Cancel", command=self.destroy).pack(side="right")
        ttk.Button(row, text="Insert", style="Accent.TButton", command=self._confirm).pack(side="right", padx=6)
        self.grab_set()

    def _confirm(self):
        found = None
        for label, snippet in self._items:
            if label == self.combo.get():
                found = snippet
                break
        if found is None:
            messagebox.showerror("Nothing selected", "Pick an event or decision from the list.")
            return
        self.on_pick(found)
        self.destroy()


def open_picker(master, mod_root, text_widget):
    """Show the dialog; on pick, insert the snippet at the text widget's
    cursor (or append with a leading newline if nothing is focused)."""
    if not mod_root:
        messagebox.showerror("No mod", "Open a mod first.")
        return

    def _insert(snippet):
        try:
            text_widget.insert(tk.INSERT, snippet + "\n")
        except tk.TclError:
            text_widget.insert("end", snippet + "\n")

    RefPickerDialog(master, mod_root, _insert)
