"""Data layer for the Home screen: everything that touches the filesystem,
the installed game, or does CPU-heavy parsing (validator, mod stats) lives
here, cached by mod path so a repeat lookup from the UI is a dict read
instead of a rescan.

Nothing here imports a widget class. Every asynchronous method takes a
`schedule` callable (a widget's `.after`, injected once into `HomeData`) so
the *caller* decides which Tk thread a result lands back on - this module
only ever touches live widgets through that one indirection, which is what
lets the same "background thread + cached result" shape get reused by
whatever screen is built after this one.
"""

import json
import os
import re
import threading

from PIL import Image, ImageTk

from app import local_mods
from app import mod_health
from app import mod_loader as ml
from app import mod_stats
from app.mod_browser import DEFAULT_STEAM_WORKSHOP
from app.new_mod_wizard import BASE_GAME, detect_game_version

THUMB_SIZE = (40, 24)
THUMB_SIZE_BIG = (52, 32)
THUMB_NAMES = ("thumbnail.png", "thumbnail.jpg", "thumb.png")

# Every cache below is keyed by mod path rather than something that ever
# needs a full-app cache-clear: a mod's own files don't change out from
# under Mod Maker while this screen is showing it (the "Validate" action
# explicitly invalidates the one path it touches), so a plain module dict
# that lives for the process is enough - no eviction policy needed.
_STATS_CACHE = {}        # mod path -> mod_stats.collect() result
_HEALTH_CACHE = {}       # mod path -> mod_health.quick_check() result
_SIZE_BYTES_CACHE = {}   # mod path -> folder size in bytes
_FILE_COUNT_CACHE = {}   # mod path -> quick file count
_FOCUS_CHECK_CACHE = {}  # mod path -> bool "has at least one focus"


def load_thumb(mod_path, size=THUMB_SIZE, bg="#1C252B"):
    for name in THUMB_NAMES:
        path = os.path.join(mod_path, name)
        if not os.path.isfile(path):
            continue
        try:
            im = Image.open(path).convert("RGB")
        except (OSError, ValueError):
            continue
        im.thumbnail(size, Image.LANCZOS)
        tile = Image.new("RGB", size, bg)
        tile.paste(im, ((size[0] - im.width) // 2, (size[1] - im.height) // 2))
        return ImageTk.PhotoImage(tile)
    return None


def detected_full_version():
    """'1.19.2' straight from launcher-settings.json, or None if the game
    isn't where Mod Maker expects it."""
    path = os.path.join(BASE_GAME, "launcher-settings.json")
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            raw = json.load(f).get("rawVersion", "")
        return raw or None
    except (OSError, ValueError):
        return None


def detected_major_minor():
    detected = detect_game_version()
    return detected.rstrip("*").rstrip(".").split(".")[:2] if detected else None


def describe_local_folder(path):
    """Same descriptor.mod scrape list_workshop_mods does, for one folder
    that isn't inside the Workshop content tree."""
    name = os.path.basename(path.rstrip("\\/"))
    supported = ""
    descriptor = os.path.join(path, "descriptor.mod")
    if os.path.isfile(descriptor):
        try:
            with open(descriptor, "r", encoding="utf-8-sig", errors="ignore") as f:
                text = f.read()
            m = re.search(r'\bname\s*=\s*"([^"]+)"', text)
            if m:
                name = m.group(1)
            m = re.search(r'\bsupported_version\s*=\s*"([^"]+)"', text)
            if m:
                supported = m.group(1)
        except OSError:
            pass
    return {"workshop_id": None, "name": name, "path": path, "supported_version": supported}


def folder_size(path):
    total = 0
    for dirpath, _dirs, files in os.walk(path):
        for f in files:
            try:
                total += os.path.getsize(os.path.join(dirpath, f))
            except OSError:
                pass
    return total


def fmt_size(num_bytes):
    if num_bytes >= 1024 ** 3:
        return f"{num_bytes / 1024 ** 3:.1f} GB"
    if num_bytes >= 1024 ** 2:
        return f"{num_bytes / 1024 ** 2:.0f} MB"
    if num_bytes >= 1024:
        return f"{num_bytes / 1024:.0f} KB"
    return f"{num_bytes} B"


def size_text_for(path):
    nbytes = _SIZE_BYTES_CACHE.get(path)
    return fmt_size(nbytes) if nbytes is not None else "…"


def bytes_for(path):
    """Cache-or-compute: used by the multi-select inspector, which needs a
    total right away rather than waiting on the background size scan."""
    if path not in _SIZE_BYTES_CACHE:
        try:
            _SIZE_BYTES_CACHE[path] = folder_size(path)
        except OSError:
            _SIZE_BYTES_CACHE[path] = 0
    return _SIZE_BYTES_CACHE[path]


def compat_class(entry, detected_mm):
    """'compatible' / 'needs_update' / 'local' - drives both the filter
    chips and the colour of the version string in the table."""
    if entry.get("workshop_id") is None:
        return "local"
    supported = (entry.get("supported_version") or "").strip()
    if not supported:
        return "needs_update"
    prefix = supported.split(".")[:2]
    if detected_mm and prefix == detected_mm:
        return "compatible"
    return "needs_update"


def count_files_quick(mod_path):
    try:
        n = 0
        for _root, _dirs, files in os.walk(mod_path):
            n += len(files)
            if n > 5000:
                return "5000+"
        return n
    except OSError:
        return None


def has_focuses(mod_path):
    try:
        for path in ml.find_focus_tree_files(mod_path):
            for tree in ml.parse_focus_trees(path):
                if tree["focuses"]:
                    return True
    except Exception:
        pass
    return False


def _run_later(schedule, delay_ms, target):
    """Start `target` (a zero-arg callable meant for a worker thread) after
    `delay_ms` on whatever timer `schedule` provides, instead of the instant
    a card is built - so a burst of cards doesn't compete with the very
    first frames the window needs to paint."""
    schedule(delay_ms, lambda: threading.Thread(target=target, daemon=True).start())


class HomeData:
    """Everything the Home screen loads from disk or the installed game,
    with the caching and thread-scheduling policy in one place instead of
    copy-pasted per widget. `schedule` is a widget's `.after`, used only to
    marshal worker-thread results back onto the Tk thread."""

    def __init__(self, schedule):
        self._schedule = schedule
        self.detected_full = detected_full_version()
        self.detected_mm = detected_major_minor()

    # ---- the mod list itself ----

    def list_mods_async(self, on_done):
        """Scanning the Workshop folder means opening a descriptor.mod per
        mod - cheap for one mod, but real disk I/O with dozens installed,
        so it runs on a worker thread rather than blocking the caller."""
        def work():
            mods = ml.list_workshop_mods(DEFAULT_STEAM_WORKSHOP)
            seen_paths = {os.path.normcase(m["path"]) for m in mods}
            for path in local_mods.load():
                if os.path.normcase(path) in seen_paths:
                    continue
                mods.append(describe_local_folder(path))
            self._schedule(0, lambda: on_done(mods))

        threading.Thread(target=work, daemon=True).start()

    def scan_sizes_async(self, mods, on_each):
        """One background thread walks every mod folder once, in order,
        instead of one thread per mod - a Workshop folder with dozens of
        mods used to mean dozens of concurrent os.walk threads fighting the
        UI thread for the GIL, which is what showed up as resize/minimize
        jank right after the window opened. Sizes are cached by path for
        the rest of the run, so a rescan only walks what's missing."""
        mods_snapshot = list(mods)

        def work():
            for m in mods_snapshot:
                path = m["path"]
                if path in _SIZE_BYTES_CACHE:
                    continue
                try:
                    nbytes = folder_size(path)
                except OSError:
                    nbytes = None
                if nbytes is not None:
                    _SIZE_BYTES_CACHE[path] = nbytes
                self._schedule(0, lambda p=path: on_each(p))

        threading.Thread(target=work, daemon=True).start()

    # ---- per-mod checks, each cached and deferred ----

    def show_file_count_async(self, mod_path, on_done):
        """`on_done(n_or_None)` - cached instantly on a repeat visit,
        otherwise counted on a worker thread that doesn't start until the
        window has had a chance to paint."""
        cached = _FILE_COUNT_CACHE.get(mod_path)
        if cached is not None:
            on_done(cached)
            return

        def work():
            n = count_files_quick(mod_path)
            if n is not None:
                _FILE_COUNT_CACHE[mod_path] = n
            self._schedule(0, lambda: on_done(n))

        _run_later(self._schedule, 300, work)

    def invalidate_health(self, mod_path):
        """Drops the cached health result so the next check_health_async
        call for this path genuinely re-checks instead of replaying the old
        answer - used by the "Validate" button."""
        _HEALTH_CACHE.pop(mod_path, None)

    def check_health_async(self, mod_path, on_done):
        """`on_done(stats_or_None)` where stats is {'errors':, 'warnings':}."""
        cached = _HEALTH_CACHE.get(mod_path)
        if cached is not None:
            on_done(cached)
            return

        def work():
            try:
                stats = mod_health.quick_check(mod_path)
            except Exception:
                stats = None
            if stats is not None:
                _HEALTH_CACHE[mod_path] = stats
            self._schedule(0, lambda: on_done(stats))

        # validator.validate() is pure-Python CPU work; starting it the
        # instant a thread is created would contend for the GIL against
        # the very first frames the window needs to draw.
        _run_later(self._schedule, 300, work)

    def load_stats_async(self, mod_path, on_done):
        cached = _STATS_CACHE.get(mod_path)
        if cached is not None:
            on_done(cached)
            return

        def work():
            try:
                stats = mod_stats.collect(mod_path)
            except Exception:
                stats = None
            if stats is not None:
                _STATS_CACHE[mod_path] = stats
            self._schedule(0, lambda: on_done(stats))

        threading.Thread(target=work, daemon=True).start()

    def check_focus_tree_async(self, mod_path, on_changed):
        """Resolves the checklist's "Build a focus tree" step off the UI
        thread, once per path. `on_changed()` fires only the one time the
        answer moves from unknown to known - callers re-read the value via
        `focus_check_result()` rather than receiving it as an argument, so
        a card can just ask "do I need to rebuild?"."""
        if mod_path in _FOCUS_CHECK_CACHE:
            return
        _FOCUS_CHECK_CACHE[mod_path] = False   # claimed now so a second
        # call before the thread finishes can't queue a duplicate check

        def work():
            try:
                val = has_focuses(mod_path)
            except Exception:
                val = False
            _FOCUS_CHECK_CACHE[mod_path] = val
            self._schedule(0, on_changed)

        _run_later(self._schedule, 300, work)

    def focus_check_result(self, mod_path):
        """None if still unknown, else the cached bool."""
        return _FOCUS_CHECK_CACHE.get(mod_path)
