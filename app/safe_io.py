"""Writing into somebody else's mod folder needs a seatbelt: never clobber
a file the user (or the mod's author) wrote without asking first, and always
leave a backup behind when they say yes."""

import os
import shutil
from tkinter import messagebox

from app import undo


def write_text(path, content, parent=None, encoding="utf-8", describe=None):
    """Write `content` to `path`.

    If the file already exists, ask before replacing it and keep a .bak copy.
    Returns True when the file was written, False when the user declined.
    """
    exists = os.path.isfile(path)
    if exists:
        label = describe or os.path.basename(path)
        confirm = messagebox.askyesno(
            "Overwrite existing file?",
            f"This will overwrite {label}:\n\n{path}\n\n"
            "A backup will be kept next to it as .bak.\n\nContinue?",
            parent=parent,
        )
        if not confirm:
            return False
        backup = path + ".bak"
        if not os.path.exists(backup):
            try:
                shutil.copy2(path, backup)
            except OSError:
                pass

    os.makedirs(os.path.dirname(path), exist_ok=True)
    undo.record(path, describe or os.path.basename(path))
    with open(path, "w", encoding=encoding) as f:
        f.write(content)
    return True
