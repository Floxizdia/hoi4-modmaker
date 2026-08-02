"""Byte-preserving edits to a single localisation key, wherever in the
mod's localisation/english/*.yml files it happens to live. If the key isn't
defined anywhere yet, it's appended to a dedicated overrides file instead
of guessing which existing file "should" own it."""

import glob
import os
import re
import shutil

from app import undo

_KEY_RE_TEMPLATE = r'(^[ \t]*{key}[ \t]*:[ \t]*\d*[ \t]*")(.*?)("[ \t]*$)'


def set_key(mod_root, key, new_text, fallback_filename="zzz_focus_overrides_l_english.yml"):
    """Find `key` in any localisation/english/*.yml and replace its text,
    or append it to `fallback_filename` if it isn't defined yet. Returns
    the path written."""
    loc_dir = os.path.join(mod_root, "localisation", "english")
    os.makedirs(loc_dir, exist_ok=True)
    escaped = new_text.replace('\\', '\\\\').replace('"', '\\"')
    pattern = re.compile(_KEY_RE_TEMPLATE.format(key=re.escape(key)), re.MULTILINE)

    for path in glob.glob(os.path.join(loc_dir, "**", "*.yml"), recursive=True):
        try:
            with open(path, "r", encoding="utf-8-sig", errors="ignore") as f:
                text = f.read()
        except OSError:
            continue
        if pattern.search(text):
            new_text_full = pattern.sub(lambda m: m.group(1) + escaped + m.group(3), text, count=1)
            backup = path + ".bak"
            if not os.path.exists(backup):
                shutil.copy2(path, backup)
            undo.record(path, f"{key} localisation")
            with open(path, "w", encoding="utf-8-sig") as f:
                f.write(new_text_full)
            return path

    path = os.path.join(loc_dir, fallback_filename)
    if os.path.isfile(path):
        with open(path, "r", encoding="utf-8-sig", errors="ignore") as f:
            existing = f.read().rstrip("\n")
        content = existing + f'\n {key}:0 "{escaped}"\n'
    else:
        content = f'l_english:\n {key}:0 "{escaped}"\n'
    undo.record(path, f"{key} localisation")
    with open(path, "w", encoding="utf-8-sig") as f:
        f.write(content)
    return path
