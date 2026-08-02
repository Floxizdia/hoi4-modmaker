"""The app's metal: HOI4's own panel textures, stretched to whatever size a
widget happens to be.

The game's UI art is nine-sliced - a panel has a carved bevel border that
must stay at its native pixel size while the middle stretches to fill. Scale
the whole bitmap instead and the bevel smears into mush, which is exactly
what makes a re-skinned Tk app look fake. So this module does the same
nine-slice the game's own renderer does, and caches the result per size
because a resize storm would otherwise decode the same .dds hundreds of
times.

Everything degrades to a flat colour if the game isn't installed - the tool
has to stay usable for someone editing a mod on a machine without HOI4.
"""

import os

from PIL import Image, ImageTk

BASE_GAME = r"C:\Program Files (x86)\Steam\steamapps\common\Hearts of Iron IV"
INTERFACE = os.path.join(BASE_GAME, "gfx", "interface")

# name -> (texture file, nine-slice border l/t/r/b, fallback colour)
SKINS = {
    "panel":   ("generic_popup_win.dds", (24, 24, 24, 24), "#26251f"),
    "header":  ("header_wide_bg.dds", (16, 10, 16, 10), "#32302b"),
    "rail":    ("generic_bg2.dds", (10, 8, 10, 8), "#25241e"),
    "entry":   ("generic_entry_bg_small.dds", (8, 6, 8, 6), "#22231f"),
    "row":     ("generic_text_bg_203.dds", (8, 6, 8, 6), "#1d1f1c"),
    "divider": ("divider.dds", (30, 0, 30, 0), "#3a3833"),
    "button":  ("button_type_1.dds", (10, 8, 10, 8), "#38362c"),
}

_source_cache = {}
_photo_cache = {}


def _source(name):
    """The raw RGBA texture, or None when the game isn't installed."""
    if name in _source_cache:
        return _source_cache[name]
    file, _, _ = SKINS[name]
    path = os.path.join(INTERFACE, file)
    image = None
    try:
        image = Image.open(path).convert("RGBA")
    except (OSError, ValueError, KeyError):
        image = None
    _source_cache[name] = image
    return image


def fallback(name):
    return SKINS[name][2]


def nine_slice(image, width, height, border):
    """Stretch `image` to width x height leaving the bevel border intact."""
    left, top, right, bottom = border
    sw, sh = image.size
    # a target smaller than the borders themselves can't keep them - clamp so
    # the slices never overlap and produce garbage
    left = min(left, sw // 2, max(1, width // 2))
    right = min(right, sw // 2, max(1, width // 2))
    top = min(top, sh // 2, max(1, height // 2))
    bottom = min(bottom, sh // 2, max(1, height // 2))

    out = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    mid_w, mid_h = max(1, width - left - right), max(1, height - top - bottom)
    src_mid_w, src_mid_h = max(1, sw - left - right), max(1, sh - top - bottom)

    columns = ((0, left, 0, left), (left, src_mid_w, left, mid_w),
               (sw - right, right, width - right, right))
    rows = ((0, top, 0, top), (top, src_mid_h, top, mid_h),
            (sh - bottom, bottom, height - bottom, bottom))

    for sx, sw_, dx, dw in columns:
        if sw_ <= 0 or dw <= 0:
            continue
        for sy, sh_, dy, dh in rows:
            if sh_ <= 0 or dh <= 0:
                continue
            piece = image.crop((sx, sy, sx + sw_, sy + sh_))
            if (sw_, sh_) != (dw, dh):
                piece = piece.resize((dw, dh), Image.BILINEAR)
            out.paste(piece, (dx, dy))
    return out


def photo(name, width, height, tint=None):
    """A cached PhotoImage of skin `name` at this size, or None if the
    texture is unavailable and the caller should fall back to a flat fill."""
    width, height = max(1, int(width)), max(1, int(height))
    key = (name, width, height, tint)
    if key in _photo_cache:
        return _photo_cache[key]
    source = _source(name)
    if source is None:
        return None
    image = nine_slice(source, width, height, SKINS[name][1])
    if tint:
        overlay = Image.new("RGBA", image.size, tint)
        image = Image.alpha_composite(image, overlay)
    result = ImageTk.PhotoImage(image)
    _photo_cache[key] = result       # also the only reference keeping it alive
    return result


def paint(canvas, name, width, height, tag="skin", tint=None):
    """Lay skin `name` over a canvas as its background, flat colour if the
    texture is missing. Returns True when the real texture was used."""
    canvas.delete(tag)
    image = photo(name, width, height, tint=tint)
    if image is None:
        canvas.create_rectangle(0, 0, width, height, fill=fallback(name),
                                outline="", tags=tag)
        canvas.tag_lower(tag)
        return False
    canvas.create_image(0, 0, image=image, anchor="nw", tags=tag)
    canvas.tag_lower(tag)
    return True


def available():
    """True when the game's textures can actually be read."""
    return os.path.isdir(INTERFACE)
