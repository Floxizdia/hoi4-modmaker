"""Shared state: which mod is currently open, everything expensive that was
scanned out of it, and the localisation strings collected while editing.

Every tab reads from this one object, so opening a mod anywhere in the app
puts all the other tabs to work on that same mod. Tabs register a callback
with `subscribe` and get told when the open mod changes.
"""

import os


class AppState:
    def __init__(self):
        self.mod_root = ""
        self.mod_name = "My HOI4 Mod"
        self.mod_tags = []

        # scanned from the open mod, shared so each tab doesn't rescan
        self.gfx_index = {}
        self.mod_loc = {}
        self.characters = {}

        # localisation authored in this session, exported on demand
        self.loc_entries = {}

        # per-mod lazy caches (cleared automatically when the mod changes)
        self.event_owners = None
        self.idea_icon_library = None
        self.search_index = None

        self._listeners = []

    # ---- observers ----

    def subscribe(self, callback):
        self._listeners.append(callback)

    def _notify(self):
        for callback in list(self._listeners):
            callback()

    # ---- mod context ----

    def set_mod(self, root, name=None, gfx_index=None, mod_loc=None, characters=None, tags=None):
        switched = root != self.mod_root
        if switched:
            # per-mod caches built lazily elsewhere; stale data from the
            # previous mod must not leak into the new one
            self.event_owners = None
            self.idea_icon_library = None
            self.search_index = None
            from app import map_picker
            map_picker.invalidate_cache()
            # undo history from mod A restoring files into mod B would be
            # actively dangerous, so the stack is dropped on every switch.
            # (This used to be checked after self.mod_root was reassigned,
            # so the comparison was always False and it never actually ran.)
            from app import undo
            undo.clear()
        self.mod_root = root
        if name is not None:
            self.mod_name = name
        if gfx_index is not None:
            self.gfx_index = gfx_index
        if mod_loc is not None:
            self.mod_loc = mod_loc
        if characters is not None:
            self.characters = characters
        if tags is not None:
            self.mod_tags = tags
        if self.is_loaded:
            from app import recent
            recent.remember(self.mod_root, self.mod_name)
        self._notify()

    def set_mod_root(self, path):
        self.mod_root = path
        self._notify()

    def content_changed(self):
        """Notify screens after a creator writes new mod content in-place."""
        self.search_index = None
        self._notify()

    @property
    def is_loaded(self):
        return bool(self.mod_root) and os.path.isdir(self.mod_root)

    # ---- localisation ----

    def add_loc(self, key, text):
        if key:
            self.loc_entries[key] = text

    def text_for(self, key, default=""):
        """Session edits win over what was loaded from the mod."""
        if key in self.loc_entries:
            return self.loc_entries[key]
        return self.mod_loc.get(key, default)

    # ---- paths ----

    def path(self, *parts):
        return os.path.join(self.mod_root, *parts)

    def ensure_dir(self, *parts):
        full = self.path(*parts)
        os.makedirs(full, exist_ok=True)
        return full


state = AppState()
