"""Data and loading service for the Focus Tree editor.

This module owns no Tk widgets. It preserves the dictionary shape consumed
by ``ModBrowserTab`` while moving filesystem work and stale-request handling
out of that screen class.
"""

import os
import re
import threading

from app import mod_loader as ml


class FocusTreeData:
    """Load Focus Tree data synchronously or through latest-only requests."""

    def __init__(self, base_game):
        self.base_game = base_game
        self._lock = threading.Lock()
        self._next_request_id = 0
        self._active_request_id = 0
        self._results = {}

    @staticmethod
    def list_workshop_mods(workshop_root):
        return ml.list_workshop_mods(workshop_root)

    @staticmethod
    def parse_descriptor(mod_path):
        """Return the existing UI's ``(mod_name, tags)`` descriptor shape."""
        mod_name = os.path.basename(mod_path)
        tags = []
        descriptor = os.path.join(mod_path, "descriptor.mod")
        if not os.path.isfile(descriptor):
            return mod_name, tags

        with open(descriptor, "r", encoding="utf-8-sig", errors="ignore") as handle:
            text = handle.read()
        match = re.search(r'\bname\s*=\s*"([^"]+)"', text)
        if match:
            mod_name = match.group(1)
        tag_block = re.search(r"\btags\s*=\s*\{(.*?)\}", text, flags=re.DOTALL)
        if tag_block:
            tags = re.findall(r'"([^"]+)"', tag_block.group(1))
        return mod_name, tags

    def load_mod(self, mod_path):
        """Build the result dictionary currently consumed by ModBrowserTab."""
        base_tree_files = ml.find_focus_tree_files(self.base_game)
        mod_tree_files = ml.find_focus_tree_files(mod_path)
        mod_by_relative_path = {
            os.path.normcase(os.path.relpath(path, mod_path)): path
            for path in mod_tree_files
        }
        tree_files = []
        for base_path in base_tree_files:
            relative_path = os.path.normcase(os.path.relpath(base_path, self.base_game))
            tree_files.append(mod_by_relative_path.pop(relative_path, base_path))
        tree_files.extend(mod_by_relative_path.values())
        gfx_index = ml.build_gfx_index([self.base_game, mod_path])
        loc = ml.load_localisation(self.base_game)
        loc.update(ml.load_localisation(mod_path))
        characters = ml.load_country_characters(mod_path)

        items = []
        for path in tree_files:
            for tree in ml.parse_focus_trees(path):
                tree["is_vanilla"] = os.path.normcase(path).startswith(
                    os.path.normcase(os.path.abspath(self.base_game)) + os.sep
                )
                countries = "/".join(tree["country_tags"]) or "generic"
                # "vanilla" spelt out rather than left to be inferred from the
                # filename: a mod with entirely custom countries has no way to
                # tell its own trees from the base game's at a glance
                origin = "vanilla" if tree["is_vanilla"] else "MOD"
                items.append((
                    f"[{origin}] {countries} | "
                    f"{tree['id']} - {os.path.basename(path)} "
                    f"({len(tree['focuses'])} focuses)",
                    path,
                    tree,
                ))

        # the mod's own trees first. They used to be appended after all ~50
        # base-game ones, so anybody working on a custom-country mod had to
        # hunt for their own tree at the bottom of the list every time.
        items.sort(key=lambda item: item[2]["is_vanilla"])

        mod_name, tags = self.parse_descriptor(mod_path)
        return {
            "path": mod_path,
            "tree_files": tree_files,
            "gfx_index": gfx_index,
            "loc": loc,
            "characters": characters,
            "items": items,
            "mod_name": mod_name,
            "tags": tags,
        }

    def load_mod_async(self, mod_path):
        """Start a load and return its request id.

        A newer request invalidates every older result. The caller polls the
        result on its own UI thread, so worker threads never touch Tk.
        """
        with self._lock:
            self._next_request_id += 1
            request_id = self._next_request_id
            self._active_request_id = request_id
            self._results.clear()

        def work():
            try:
                result = self.load_mod(mod_path)
            except Exception as exc:
                result = {"path": mod_path, "error": str(exc)}
            with self._lock:
                if request_id == self._active_request_id:
                    self._results[request_id] = result

        threading.Thread(target=work, daemon=True).start()
        return request_id

    def take_load_result(self, request_id):
        """Return a completed current result once, otherwise ``None``."""
        with self._lock:
            if request_id != self._active_request_id:
                return None
            return self._results.pop(request_id, None)

    def cancel_load(self):
        """Invalidate a pending load without attempting to interrupt I/O."""
        with self._lock:
            self._next_request_id += 1
            self._active_request_id = self._next_request_id
            self._results.clear()
