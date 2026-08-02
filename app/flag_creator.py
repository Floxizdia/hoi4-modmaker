"""Generate a country flag (large/medium/small .tga triplet) from a
procedural pattern plus an optional emblem image the user supplies. HOI4
ships no reusable "flag parts" library to compose from (unlike the focus/
portrait pieces in the bundled Ultimate-HOI4-GFX pack) - what this does
instead is draw the classic flag layouts (tricolors, bicolors, cross,
canton, solid) directly with Pillow, at the exact sizes the game expects,
then optionally layers a user-picked emblem PNG centered on top.

Real sizes, confirmed from the base game's own gfx/flags/: large 82x52 (no
subfolder), medium 41x26 (flags/medium/), small 10x7 (flags/small/).
"""

import os

from PIL import Image, ImageDraw

LARGE_SIZE = (82, 52)
MEDIUM_SIZE = (41, 26)
SMALL_SIZE = (10, 7)

PATTERNS = [
    "solid", "horizontal_bicolor", "horizontal_tricolor",
    "vertical_bicolor", "vertical_tricolor", "diagonal", "nordic_cross", "canton",
]

IDEOLOGY_SUFFIXES = ["", "neutrality", "democratic", "fascism", "communism"]


def _draw_pattern(pattern, size, colors):
    w, h = size
    im = Image.new("RGB", size, colors[0])
    draw = ImageDraw.Draw(im)

    if pattern == "solid":
        pass
    elif pattern == "horizontal_bicolor":
        draw.rectangle([0, h // 2, w, h], fill=colors[1 % len(colors)])
    elif pattern == "horizontal_tricolor":
        third = h / 3
        draw.rectangle([0, third, w, 2 * third], fill=colors[1 % len(colors)])
        draw.rectangle([0, 2 * third, w, h], fill=colors[2 % len(colors)])
    elif pattern == "vertical_bicolor":
        draw.rectangle([w // 2, 0, w, h], fill=colors[1 % len(colors)])
    elif pattern == "vertical_tricolor":
        third = w / 3
        draw.rectangle([third, 0, 2 * third, h], fill=colors[1 % len(colors)])
        draw.rectangle([2 * third, 0, w, h], fill=colors[2 % len(colors)])
    elif pattern == "diagonal":
        draw.polygon([(0, 0), (w, 0), (0, h)], fill=colors[0])
        draw.polygon([(w, 0), (w, h), (0, h)], fill=colors[1 % len(colors)])
    elif pattern == "nordic_cross":
        bar = max(1, h // 5)
        vbar_x = int(w * 0.32)
        draw.rectangle([0, 0, w, h], fill=colors[0])
        draw.rectangle([0, h // 2 - bar // 2, w, h // 2 + bar // 2], fill=colors[1 % len(colors)])
        draw.rectangle([vbar_x - bar // 2, 0, vbar_x + bar // 2, h], fill=colors[1 % len(colors)])
    elif pattern == "canton":
        draw.rectangle([0, 0, w // 2, h // 2], fill=colors[1 % len(colors)])
    return im


def create_flag(mod_root, *, tag, ideology, pattern, colors, emblem_path=None):
    """Writes large/medium/small .tga files under mod_root/gfx/flags/.
    `colors` is a list of 1-3 (r,g,b) tuples used by the pattern. Returns
    the three paths written."""
    tag = tag.upper().strip()
    suffix = f"_{ideology}" if ideology else ""
    filename = f"{tag}{suffix}.tga"

    large = _draw_pattern(pattern, LARGE_SIZE, colors).convert("RGBA")

    if emblem_path and os.path.isfile(emblem_path):
        emblem = Image.open(emblem_path).convert("RGBA")
        target_h = int(LARGE_SIZE[1] * 0.7)
        ratio = target_h / emblem.height
        target_w = max(1, int(emblem.width * ratio))
        emblem = emblem.resize((target_w, target_h), Image.LANCZOS)
        pos = ((LARGE_SIZE[0] - target_w) // 2, (LARGE_SIZE[1] - target_h) // 2)
        large.alpha_composite(emblem, pos)

    paths = []
    folder = os.path.join(mod_root, "gfx", "flags")
    os.makedirs(folder, exist_ok=True)
    large_path = os.path.join(folder, filename)
    large.save(large_path, format="TGA")
    paths.append(large_path)

    for size, sub in ((MEDIUM_SIZE, "medium"), (SMALL_SIZE, "small")):
        sub_folder = os.path.join(folder, sub)
        os.makedirs(sub_folder, exist_ok=True)
        resized = large.resize(size, Image.LANCZOS)
        p = os.path.join(sub_folder, filename)
        resized.save(p, format="TGA")
        paths.append(p)

    return paths


def list_existing_flags(mod_root):
    """{filename: source} across base game + mod's gfx/flags/ (large size only, informational)."""
    from app.map_data import BASE_GAME
    out = {}
    for root, source in ((BASE_GAME, "vanilla"), (mod_root, "mod")):
        folder = os.path.join(root, "gfx", "flags")
        if not os.path.isdir(folder):
            continue
        for name in os.listdir(folder):
            if name.lower().endswith(".tga"):
                out[name] = source
    return out
