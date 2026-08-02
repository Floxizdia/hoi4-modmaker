"""Type-to-filter for a ttk.Combobox holding a long "id — file.txt (N)"
style list. A `state="readonly"` combobox can only be scrolled through, and
some of these lists run to a hundred+ entries (one row per country file) -
letting the box narrow itself as you type turns "scroll and squint" into
"type the country name".

The combobox stays free-text while filtering, which means .current() can no
longer be trusted as the selection index once the visible list has been
narrowed - callers must look the chosen item up by matching the box's
current text against their own full label list instead (see `resolve`).
"""


def enable_filter(combo, get_all_labels):
    """`get_all_labels()` returns the full, unfiltered label list. Typing
    narrows `combo['values']` to whatever contains the typed text."""
    combo.configure(state="normal")

    def on_key(event):
        if event.keysym in ("Up", "Down", "Return", "Escape", "Tab"):
            return
        needle = combo.get().strip().lower()
        all_labels = get_all_labels()
        combo["values"] = [v for v in all_labels if needle in v.lower()] if needle else all_labels

    combo.bind("<KeyRelease>", on_key)


def resolve(combo, items, label_index=0):
    """The item in `items` whose label (items[i][label_index]) exactly
    matches the combobox's current text, or None. Use this instead of
    `.current()` on a filterable combobox - the visible list may be a
    narrowed subset, so the index no longer lines up with `items`."""
    text = combo.get()
    for item in items:
        if item[label_index] == text:
            return item
    return None
