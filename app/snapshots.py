"""Snapshots: a lightweight version history for the mod's script files.

Every snapshot zips the text-bearing folders (script, localisation,
interface) with a timestamp into .hoi4modmaker_snapshots/ inside the mod.
Restoring extracts a chosen zip back over those folders. Textures and other
heavy binaries are deliberately left out - they are rarely the thing a bad
edit destroys, and including them would turn snapshots of a large mod into
gigabytes.
"""

import os
import glob
import zipfile
from datetime import datetime

SNAP_DIR = ".hoi4modmaker_snapshots"
SNAP_EXT = {".txt", ".yml", ".gfx", ".gui", ".lua", ".mod", ".csv"}
SNAP_FOLDERS = ["common", "events", "history", "localisation", "interface"]


def _snap_dir(mod_root):
    path = os.path.join(mod_root, SNAP_DIR)
    os.makedirs(path, exist_ok=True)
    return path


def create(mod_root, note=""):
    """Zip the script folders. Returns (zip_path, file_count)."""
    stamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    safe_note = "".join(c for c in note if c.isalnum() or c in "-_ ")[:40].strip().replace(" ", "-")
    name = f"snap_{stamp}{'_' + safe_note if safe_note else ''}.zip"
    zip_path = os.path.join(_snap_dir(mod_root), name)

    count = 0
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for folder in SNAP_FOLDERS:
            base = os.path.join(mod_root, folder)
            if not os.path.isdir(base):
                continue
            for dirpath, _, filenames in os.walk(base):
                for filename in filenames:
                    if os.path.splitext(filename)[1].lower() not in SNAP_EXT:
                        continue
                    if filename.endswith(".bak"):
                        continue
                    full = os.path.join(dirpath, filename)
                    zf.write(full, os.path.relpath(full, mod_root))
                    count += 1
        descriptor = os.path.join(mod_root, "descriptor.mod")
        if os.path.isfile(descriptor):
            zf.write(descriptor, "descriptor.mod")
            count += 1
    return zip_path, count


def list_snapshots(mod_root):
    """Newest first: [(path, label, size_mb)]."""
    out = []
    for path in sorted(glob.glob(os.path.join(mod_root, SNAP_DIR, "snap_*.zip")), reverse=True):
        label = os.path.basename(path)[5:-4].replace("_", " ")
        size = os.path.getsize(path) / (1024 * 1024)
        out.append((path, label, size))
    return out


def prune_auto(mod_root, keep=8):
    """Keep only the newest `keep` auto-snapshots (manual ones are untouched)."""
    autos = sorted(
        glob.glob(os.path.join(mod_root, SNAP_DIR, "snap_*_auto.zip")), reverse=True
    )
    for path in autos[keep:]:
        try:
            os.remove(path)
        except OSError:
            pass


def _inside(mod_root, target):
    """True when `target` really is under `mod_root` - a zip-slip guard.

    Comparing raw strings was wrong twice over: `target` is only absolute
    when `mod_root` happens to be, so a relative mod folder failed every
    check and restored nothing at all, and a bare prefix match would let
    "/mods/foo-backup" pass as being inside "/mods/foo".
    """
    root = os.path.abspath(mod_root)
    target = os.path.abspath(target)
    return target == root or target.startswith(root + os.sep)


def restore(mod_root, zip_path, safety_snapshot=True):
    """Extract a snapshot back over the mod.

    Returns (restored_count, safety_path). Restoring is the one destructive
    thing this screen does, and picking the wrong entry from the list used
    to overwrite the current files with no way back - so unless the caller
    opts out, the current state is snapshotted first and its path handed
    back to be shown to the user.
    """
    safety = None
    if safety_snapshot:
        safety, _ = create(mod_root, note="before-restore")

    count = 0
    with zipfile.ZipFile(zip_path, "r") as zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            target = os.path.normpath(os.path.join(mod_root, info.filename))
            if not _inside(mod_root, target):
                continue
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with zf.open(info) as src, open(target, "wb") as dst:
                dst.write(src.read())
            count += 1
    return count, safety


def export_archive(mod_root, out_path, progress=None):
    """Zip the WHOLE mod - textures, audio, everything - for sharing outside
    the Workshop, moving to another machine, or archiving a release. Unlike
    a snapshot (script files only, kept inside the mod) this is a complete,
    self-contained copy written wherever the user points it.

    Returns (file_count, total_bytes)."""
    count = 0
    total = 0
    skip_dirs = {SNAP_DIR, ".git", "__pycache__"}
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for dirpath, dirnames, filenames in os.walk(mod_root):
            dirnames[:] = [d for d in dirnames if d not in skip_dirs]
            for filename in filenames:
                if filename.endswith(".bak"):
                    continue
                full = os.path.join(dirpath, filename)
                rel = os.path.relpath(full, mod_root)
                try:
                    total += os.path.getsize(full)
                    zf.write(full, rel)
                except OSError:
                    continue
                count += 1
                if progress and count % 200 == 0:
                    progress(f"Packing... {count} files")
    return count, total
