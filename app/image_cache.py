"""Thumbnail loader/cache for HOI4 texture files (.dds/.png/.tga/.jpg).
Failures (unsupported DDS compression variant, missing file, etc.) return
None so callers can fall back to a placeholder instead of crashing."""

from PIL import Image, ImageTk

_cache = {}


def clear():
    """Drop cached thumbnails, e.g. after a texture file was replaced."""
    _cache.clear()


def get_scaled(path, size):
    """Exact resize (ignores aspect ratio). Used for UI frames like the
    focus titlebar plaque, which must fill a precise box."""
    if not path:
        return None
    key = ("scaled", path, size)
    if key in _cache:
        return _cache[key]
    try:
        im = Image.open(path)
        im.load()
        if im.mode != "RGBA":
            im = im.convert("RGBA")
        im = im.resize(size, Image.LANCZOS)
        photo = ImageTk.PhotoImage(im)
    except Exception:
        _cache[key] = None
        return None
    _cache[key] = photo
    return photo


def get_thumbnail(path, size=(64, 64)):
    if not path:
        return None
    key = (path, size)
    if key in _cache:
        return _cache[key]

    try:
        im = Image.open(path)
        im.load()
        if im.mode not in ("RGBA", "RGB"):
            im = im.convert("RGBA")
        im.thumbnail(size, Image.LANCZOS)
        photo = ImageTk.PhotoImage(im)
    except Exception:
        _cache[key] = None
        return None

    _cache[key] = photo
    return photo
