"""Line-art icons for the navigation rail, drawn straight onto a canvas.

Emoji were the fastest way to get an icon next to each nav item and the
worst-looking: they arrive in someone else's colour palette, render as
full-colour blobs among a gold-on-olive UI, and change shape per Windows
version. These are a dozen strokes each in whatever colour the rail asks
for, so they inherit the theme instead of fighting it, and stay crisp
because nothing is being scaled.

Each function draws inside the box (x, y) .. (x+size, y+size) and returns
the ids it created so the rail can recolour them on hover.
"""

import math


def _line(canvas, colour, width, *points, **kw):
    return canvas.create_line(*points, fill=colour, width=width,
                              capstyle="round", joinstyle="round", **kw)


def _oval(canvas, colour, width, x0, y0, x1, y1, fill=""):
    return canvas.create_oval(x0, y0, x1, y1, outline=colour, width=width, fill=fill)


def _rect(canvas, colour, width, x0, y0, x1, y1, fill=""):
    return canvas.create_rectangle(x0, y0, x1, y1, outline=colour, width=width, fill=fill)


def map_glyph(canvas, x, y, s, colour, w=1.6):
    """A folded paper map."""
    ids = [
        canvas.create_polygon(
            x, y + s * 0.22, x + s * 0.33, y + s * 0.05, x + s * 0.66, y + s * 0.28,
            x + s, y + s * 0.08, x + s, y + s * 0.8, x + s * 0.66, y + s,
            x + s * 0.33, y + s * 0.77, x, y + s * 0.95,
            outline=colour, width=w, fill=""),
        _line(canvas, colour, w, x + s * 0.33, y + s * 0.05, x + s * 0.33, y + s * 0.77),
        _line(canvas, colour, w, x + s * 0.66, y + s * 0.28, x + s * 0.66, y + s),
    ]
    return ids


def globe_glyph(canvas, x, y, s, colour, w=1.6):
    ids = [_oval(canvas, colour, w, x, y, x + s, y + s),
           _oval(canvas, colour, w, x + s * 0.3, y, x + s * 0.7, y + s),
           _line(canvas, colour, w, x, y + s * 0.5, x + s, y + s * 0.5)]
    return ids


def gear_glyph(canvas, x, y, s, colour, w=1.6):
    cx, cy, r = x + s / 2, y + s / 2, s * 0.30
    ids = [_oval(canvas, colour, w, cx - r, cy - r, cx + r, cy + r)]
    for i in range(6):
        a = math.radians(i * 60)
        ids.append(_line(canvas, colour, w,
                         cx + math.cos(a) * r, cy + math.sin(a) * r,
                         cx + math.cos(a) * s * 0.5, cy + math.sin(a) * s * 0.5))
    return ids


def target_glyph(canvas, x, y, s, colour, w=1.6):
    """Concentric rings - the focus tree's goal."""
    cx, cy = x + s / 2, y + s / 2
    ids = []
    for r in (s * 0.48, s * 0.30):
        ids.append(_oval(canvas, colour, w, cx - r, cy - r, cx + r, cy + r))
    ids.append(_oval(canvas, colour, w, cx - s * 0.09, cy - s * 0.09,
                     cx + s * 0.09, cy + s * 0.09, fill=colour))
    return ids


def scroll_glyph(canvas, x, y, s, colour, w=1.6):
    """A rolled document - events."""
    ids = [_rect(canvas, colour, w, x + s * 0.16, y + s * 0.08, x + s * 0.84, y + s * 0.92)]
    for i in range(3):
        ty = y + s * (0.32 + i * 0.20)
        ids.append(_line(canvas, colour, w, x + s * 0.31, ty, x + s * 0.69, ty))
    return ids


def scales_glyph(canvas, x, y, s, colour, w=1.6):
    """Balance scales - decisions."""
    cx = x + s / 2
    ids = [_line(canvas, colour, w, cx, y + s * 0.10, cx, y + s * 0.86),
           _line(canvas, colour, w, x + s * 0.06, y + s * 0.26, x + s * 0.94, y + s * 0.26),
           _line(canvas, colour, w, x + s * 0.28, y + s * 0.90, x + s * 0.72, y + s * 0.90)]
    for side in (0.06, 0.94):
        ids.append(canvas.create_arc(x + s * side - s * 0.20, y + s * 0.26 - s * 0.16,
                                     x + s * side + s * 0.20, y + s * 0.26 + s * 0.30,
                                     start=180, extent=180, style="arc",
                                     outline=colour, width=w))
    return ids


def bulb_glyph(canvas, x, y, s, colour, w=1.6):
    """A lightbulb - ideas and national spirits."""
    ids = [_oval(canvas, colour, w, x + s * 0.22, y + s * 0.06, x + s * 0.78, y + s * 0.62),
           _line(canvas, colour, w, x + s * 0.36, y + s * 0.70, x + s * 0.64, y + s * 0.70),
           _line(canvas, colour, w, x + s * 0.40, y + s * 0.86, x + s * 0.60, y + s * 0.86)]
    return ids


def flag_glyph(canvas, x, y, s, colour, w=1.6):
    ids = [_line(canvas, colour, w, x + s * 0.20, y + s * 0.04, x + s * 0.20, y + s * 0.96),
           canvas.create_polygon(
               x + s * 0.20, y + s * 0.12, x + s * 0.92, y + s * 0.12,
               x + s * 0.74, y + s * 0.36, x + s * 0.92, y + s * 0.60,
               x + s * 0.20, y + s * 0.60,
               outline=colour, width=w, fill="")]
    return ids


def flask_glyph(canvas, x, y, s, colour, w=1.6):
    """Research flask - the tech tree."""
    ids = [_line(canvas, colour, w, x + s * 0.34, y + s * 0.06, x + s * 0.66, y + s * 0.06),
           canvas.create_polygon(
               x + s * 0.42, y + s * 0.06, x + s * 0.42, y + s * 0.40,
               x + s * 0.14, y + s * 0.92, x + s * 0.86, y + s * 0.92,
               x + s * 0.58, y + s * 0.40, x + s * 0.58, y + s * 0.06,
               outline=colour, width=w, fill=""),
           _line(canvas, colour, w, x + s * 0.27, y + s * 0.66, x + s * 0.73, y + s * 0.66)]
    return ids


def note_glyph(canvas, x, y, s, colour, w=1.6):
    """A musical note."""
    ids = [_line(canvas, colour, w, x + s * 0.40, y + s * 0.80, x + s * 0.40, y + s * 0.10),
           _line(canvas, colour, w, x + s * 0.40, y + s * 0.10, x + s * 0.86, y + s * 0.22),
           _line(canvas, colour, w, x + s * 0.86, y + s * 0.22, x + s * 0.86, y + s * 0.50),
           _oval(canvas, colour, w, x + s * 0.10, y + s * 0.66, x + s * 0.42, y + s * 0.92, fill=colour),
           _oval(canvas, colour, w, x + s * 0.56, y + s * 0.40, x + s * 0.88, y + s * 0.64, fill=colour)]
    return ids


def code_glyph(canvas, x, y, s, colour, w=1.8):
    ids = [_line(canvas, colour, w, x + s * 0.36, y + s * 0.16, x + s * 0.08, y + s * 0.50,
                 x + s * 0.36, y + s * 0.84),
           _line(canvas, colour, w, x + s * 0.64, y + s * 0.16, x + s * 0.92, y + s * 0.50,
                 x + s * 0.64, y + s * 0.84)]
    return ids


def language_glyph(canvas, x, y, s, colour, w=1.6):
    """Overlapping speech shapes - localisation."""
    ids = [_rect(canvas, colour, w, x + s * 0.04, y + s * 0.12, x + s * 0.62, y + s * 0.62),
           _rect(canvas, colour, w, x + s * 0.38, y + s * 0.38, x + s * 0.96, y + s * 0.88),
           _line(canvas, colour, w, x + s * 0.16, y + s * 0.36, x + s * 0.50, y + s * 0.36)]
    return ids


def shield_glyph(canvas, x, y, s, colour, w=1.6):
    """A unit shield - the units tab."""
    ids = [canvas.create_polygon(
        x + s * 0.5, y + s * 0.04, x + s * 0.92, y + s * 0.20, x + s * 0.92, y + s * 0.52,
        x + s * 0.5, y + s * 0.96, x + s * 0.08, y + s * 0.52, x + s * 0.08, y + s * 0.20,
        outline=colour, width=w, fill="")]
    return ids


def compare_glyph(canvas, x, y, s, colour, w=1.6):
    """Two panes - the diff / 'what changed' view."""
    ids = [_rect(canvas, colour, w, x + s * 0.06, y + s * 0.12, x + s * 0.46, y + s * 0.88),
           _rect(canvas, colour, w, x + s * 0.54, y + s * 0.12, x + s * 0.94, y + s * 0.88),
           _line(canvas, colour, w, x + s * 0.16, y + s * 0.30, x + s * 0.36, y + s * 0.30),
           _line(canvas, colour, w, x + s * 0.64, y + s * 0.48, x + s * 0.84, y + s * 0.48)]
    return ids


def swap_glyph(canvas, x, y, s, colour, w=1.6):
    """Crossed arrows - find & replace."""
    ids = [_line(canvas, colour, w, x + s * 0.08, y + s * 0.32, x + s * 0.80, y + s * 0.32),
           canvas.create_polygon(x + s * 0.72, y + s * 0.20, x + s * 0.92, y + s * 0.32,
                                 x + s * 0.72, y + s * 0.44, fill=colour, outline=""),
           _line(canvas, colour, w, x + s * 0.92, y + s * 0.68, x + s * 0.20, y + s * 0.68),
           canvas.create_polygon(x + s * 0.28, y + s * 0.56, x + s * 0.08, y + s * 0.68,
                                 x + s * 0.28, y + s * 0.80, fill=colour, outline="")]
    return ids


def person_glyph(canvas, x, y, s, colour, w=1.6):
    """A head-and-shoulders silhouette - the character editor."""
    ids = [_oval(canvas, colour, w, x + s * 0.30, y + s * 0.06, x + s * 0.70, y + s * 0.46),
           canvas.create_arc(x + s * 0.10, y + s * 0.46, x + s * 0.90, y + s * 1.10,
                             start=0, extent=180, style="chord", outline=colour, width=w)]
    return ids


def puzzle_glyph(canvas, x, y, s, colour, w=1.6):
    """Interlocking pieces - mod compatibility."""
    ids = [_rect(canvas, colour, w, x + s * 0.08, y + s * 0.20, x + s * 0.50, y + s * 0.90),
           _rect(canvas, colour, w, x + s * 0.50, y + s * 0.10, x + s * 0.92, y + s * 0.80),
           canvas.create_line(x + s * 0.50, y + s * 0.45, x + s * 0.50, y + s * 0.55, fill=colour, width=w)]
    return ids


def link_glyph(canvas, x, y, s, colour, w=1.6):
    """Two connected links - event firing chains."""
    ids = [canvas.create_oval(x + s * 0.06, y + s * 0.30, x + s * 0.55, y + s * 0.70,
                              outline=colour, width=w),
           canvas.create_oval(x + s * 0.45, y + s * 0.30, x + s * 0.94, y + s * 0.70,
                              outline=colour, width=w)]
    return ids


def chart_glyph(canvas, x, y, s, colour, w=1.6):
    """Bar chart - the mod stats panel."""
    ids = [_line(canvas, colour, w, x + s * 0.08, y + s * 0.94, x + s * 0.94, y + s * 0.94)]
    for i, h in enumerate((0.35, 0.65, 0.5)):
        bx = x + s * (0.20 + i * 0.28)
        ids.append(_rect(canvas, colour, w, bx - s * 0.07, y + s * (0.90 - h),
                         bx + s * 0.07, y + s * 0.90))
    return ids


def diff_split_glyph(canvas, x, y, s, colour, w=1.6):
    """A split rectangle - version-to-version comparison."""
    ids = [_rect(canvas, colour, w, x + s * 0.06, y + s * 0.15, x + s * 0.94, y + s * 0.85),
           _line(canvas, colour, w, x + s * 0.5, y + s * 0.15, x + s * 0.5, y + s * 0.85)]
    return ids


def check_glyph(canvas, x, y, s, colour, w=2.0):
    ids = [_oval(canvas, colour, 1.4, x + s * 0.04, y + s * 0.04, x + s * 0.96, y + s * 0.96),
           _line(canvas, colour, w, x + s * 0.28, y + s * 0.52,
                 x + s * 0.45, y + s * 0.70, x + s * 0.74, y + s * 0.32)]
    return ids


def pennant_glyph(canvas, x, y, s, colour, w=1.6):
    """A three-band pennant - ideologies."""
    ids = [_line(canvas, colour, w, x + s * 0.22, y + s * 0.08, x + s * 0.22, y + s * 0.92)]
    ids.append(canvas.create_polygon(
        x + s * 0.22, y + s * 0.10, x + s * 0.90, y + s * 0.30, x + s * 0.22, y + s * 0.50,
        outline=colour, width=w, fill=""))
    return ids


def network_glyph(canvas, x, y, s, colour, w=1.6):
    """Three linked nodes - factions."""
    pts = [(0.20, 0.75), (0.50, 0.20), (0.80, 0.75)]
    ids = [_line(canvas, colour, w, x + s * pts[0][0], y + s * pts[0][1], x + s * pts[1][0], y + s * pts[1][1]),
           _line(canvas, colour, w, x + s * pts[1][0], y + s * pts[1][1], x + s * pts[2][0], y + s * pts[2][1]),
           _line(canvas, colour, w, x + s * pts[0][0], y + s * pts[0][1], x + s * pts[2][0], y + s * pts[2][1])]
    for px, py in pts:
        ids.append(_oval(canvas, colour, w, x + s * (px - 0.1), y + s * (py - 0.1),
                         x + s * (px + 0.1), y + s * (py + 0.1)))
    return ids


def compass_glyph(canvas, x, y, s, colour, w=1.6):
    """A compass needle - AI strategy."""
    ids = [_oval(canvas, colour, w, x + s * 0.08, y + s * 0.08, x + s * 0.92, y + s * 0.92),
           canvas.create_polygon(x + s * 0.5, y + s * 0.22, x + s * 0.62, y + s * 0.5,
                                 x + s * 0.5, y + s * 0.78, x + s * 0.38, y + s * 0.5,
                                 outline=colour, width=w, fill="")]
    return ids


def handshake_glyph(canvas, x, y, s, colour, w=1.6):
    """Two overlapping rings - diplomatic agreements."""
    ids = [_oval(canvas, colour, w, x + s * 0.06, y + s * 0.30, x + s * 0.62, y + s * 0.86),
           _oval(canvas, colour, w, x + s * 0.38, y + s * 0.14, x + s * 0.94, y + s * 0.70)]
    return ids


def heart_glyph(canvas, x, y, s, colour, w=1.6):
    """A heart outline - opinion modifiers."""
    ids = [canvas.create_arc(x + s * 0.06, y + s * 0.10, x + s * 0.52, y + s * 0.56,
                             start=20, extent=200, style="arc", outline=colour, width=w),
           canvas.create_arc(x + s * 0.48, y + s * 0.10, x + s * 0.94, y + s * 0.56,
                             start=-40, extent=200, style="arc", outline=colour, width=w),
           _line(canvas, colour, w, x + s * 0.10, y + s * 0.42, x + s * 0.50, y + s * 0.92,
                 x + s * 0.90, y + s * 0.42)]
    return ids


def bolt_glyph(canvas, x, y, s, colour, w=1.6):
    """A lightning bolt - on_actions hooks."""
    ids = [canvas.create_polygon(
        x + s * 0.58, y + s * 0.05, x + s * 0.20, y + s * 0.58, x + s * 0.46, y + s * 0.58,
        x + s * 0.38, y + s * 0.95, x + s * 0.80, y + s * 0.38, x + s * 0.52, y + s * 0.38,
        outline=colour, width=w, fill="")]
    return ids


def olive_glyph(canvas, x, y, s, colour, w=1.6):
    """An olive branch - peace conference."""
    ids = [_line(canvas, colour, w, x + s * 0.15, y + s * 0.90, x + s * 0.85, y + s * 0.15)]
    for t in (0.30, 0.50, 0.70):
        px, py = x + s * (0.15 + t * 0.70), y + s * (0.90 - t * 0.75)
        ids.append(_oval(canvas, colour, w, px - s * 0.08, py - s * 0.08, px + s * 0.08, py + s * 0.08))
    return ids


def tile_glyph(canvas, x, y, s, colour, w=1.6):
    """A subdivided map tile - states / provinces."""
    ids = [_rect(canvas, colour, w, x + s * 0.08, y + s * 0.08, x + s * 0.92, y + s * 0.92),
           _line(canvas, colour, w, x + s * 0.08, y + s * 0.5, x + s * 0.50, y + s * 0.5),
           _line(canvas, colour, w, x + s * 0.50, y + s * 0.08, x + s * 0.50, y + s * 0.92)]
    return ids


def swords_glyph(canvas, x, y, s, colour, w=1.6):
    """Crossed swords - war goals."""
    ids = [_line(canvas, colour, w, x + s * 0.12, y + s * 0.12, x + s * 0.88, y + s * 0.88),
           _line(canvas, colour, w, x + s * 0.88, y + s * 0.12, x + s * 0.12, y + s * 0.88),
           _line(canvas, colour, w, x + s * 0.12, y + s * 0.12, x + s * 0.28, y + s * 0.12),
           _line(canvas, colour, w, x + s * 0.88, y + s * 0.12, x + s * 0.72, y + s * 0.12)]
    return ids


def tag_glyph(canvas, x, y, s, colour, w=1.6):
    """A price tag - decision categories."""
    ids = [canvas.create_polygon(
        x + s * 0.10, y + s * 0.15, x + s * 0.60, y + s * 0.15, x + s * 0.92, y + s * 0.50,
        x + s * 0.60, y + s * 0.85, x + s * 0.10, y + s * 0.85, outline=colour, width=w, fill=""),
        _oval(canvas, colour, w, x + s * 0.24, y + s * 0.42, x + s * 0.38, y + s * 0.56)]
    return ids


def wrench_glyph(canvas, x, y, s, colour, w=1.6):
    """A wrench - equipment."""
    ids = [_line(canvas, colour, w, x + s * 0.24, y + s * 0.76, x + s * 0.68, y + s * 0.32),
           canvas.create_arc(x + s * 0.06, y + s * 0.58, x + s * 0.42, y + s * 0.94,
                             start=30, extent=250, style="arc", outline=colour, width=w),
           canvas.create_arc(x + s * 0.58, y + s * 0.06, x + s * 0.94, y + s * 0.42,
                             start=210, extent=250, style="arc", outline=colour, width=w)]
    return ids


def eye_glyph(canvas, x, y, s, colour, w=1.6):
    """A watching eye - agency upgrades."""
    ids = [canvas.create_arc(x + s * 0.05, y + s * 0.15, x + s * 0.95, y + s * 0.85,
                             start=20, extent=140, style="arc", outline=colour, width=w),
           canvas.create_arc(x + s * 0.05, y + s * 0.15, x + s * 0.95, y + s * 0.85,
                             start=200, extent=140, style="arc", outline=colour, width=w),
           _oval(canvas, colour, w, x + s * 0.40, y + s * 0.40, x + s * 0.60, y + s * 0.60)]
    return ids


def star_glyph(canvas, x, y, s, colour, w=1.6):
    """A five-point star - traits."""
    pts = []
    for i in range(10):
        r = 0.46 if i % 2 == 0 else 0.20
        ang = -math.pi / 2 + i * math.pi / 5
        pts.append(x + s * (0.5 + r * math.cos(ang)))
        pts.append(y + s * (0.5 + r * math.sin(ang)))
    return [canvas.create_polygon(*pts, outline=colour, width=w, fill="")]


def barracks_glyph(canvas, x, y, s, colour, w=1.6):
    """A building with a roof - starting forces (OOB)."""
    ids = [_rect(canvas, colour, w, x + s * 0.12, y + s * 0.45, x + s * 0.88, y + s * 0.90),
           _line(canvas, colour, w, x + s * 0.06, y + s * 0.45, x + s * 0.5, y + s * 0.10,
                 x + s * 0.94, y + s * 0.45)]
    return ids


def pin_glyph(canvas, x, y, s, colour, w=1.6):
    """A map pin - game setup / bookmarks."""
    ids = [_oval(canvas, colour, w, x + s * 0.26, y + s * 0.06, x + s * 0.74, y + s * 0.54),
           canvas.create_polygon(x + s * 0.30, y + s * 0.46, x + s * 0.70, y + s * 0.46,
                                 x + s * 0.5, y + s * 0.94, outline=colour, width=w, fill="")]
    return ids


def search_glyph(canvas, x, y, s, colour, w=1.6):
    """A magnifying glass - icon coverage."""
    ids = [_oval(canvas, colour, w, x + s * 0.08, y + s * 0.08, x + s * 0.62, y + s * 0.62),
           _line(canvas, colour, w, x + s * 0.56, y + s * 0.56, x + s * 0.92, y + s * 0.92)]
    return ids


def layers_glyph(canvas, x, y, s, colour, w=1.6):
    """Stacked layers - mod load order."""
    ids = []
    for i, ty in enumerate((0.20, 0.45, 0.70)):
        ids.append(canvas.create_polygon(
            x + s * 0.5, y + s * ty, x + s * 0.92, y + s * (ty + 0.12), x + s * 0.5, y + s * (ty + 0.24),
            x + s * 0.08, y + s * (ty + 0.12), outline=colour, width=w, fill=""))
    return ids


def warning_glyph(canvas, x, y, s, colour, w=1.6):
    """A warning triangle with an exclamation mark - error log."""
    ids = [canvas.create_polygon(
        x + s * 0.5, y + s * 0.08, x + s * 0.94, y + s * 0.90, x + s * 0.06, y + s * 0.90,
        outline=colour, width=w, fill="")]
    ids.append(_line(canvas, colour, w, x + s * 0.5, y + s * 0.38, x + s * 0.5, y + s * 0.68))
    ids.append(_oval(canvas, colour, w, x + s * 0.46, y + s * 0.76, x + s * 0.54, y + s * 0.82, fill=colour))
    return ids


def rail_glyph(canvas, x, y, s, colour, w=1.6):
    """Two rails and their sleepers - the railway/supply network."""
    ids = [_line(canvas, colour, w, x + s * 0.28, y + s * 0.08, x + s * 0.28, y + s * 0.92),
           _line(canvas, colour, w, x + s * 0.72, y + s * 0.08, x + s * 0.72, y + s * 0.92)]
    for ty in (0.24, 0.50, 0.76):
        ids.append(_line(canvas, colour, w, x + s * 0.14, y + s * ty, x + s * 0.86, y + s * ty))
    return ids


def braces_glyph(canvas, x, y, s, colour, w=1.8):
    """A pair of braces - a named block of script."""
    ids = []
    for sign, sx in ((1, 0.34), (-1, 0.66)):
        ids.append(canvas.create_line(
            x + s * (sx + sign * 0.12), y + s * 0.10,
            x + s * sx, y + s * 0.30, x + s * sx, y + s * 0.44,
            x + s * (sx - sign * 0.10), y + s * 0.50,
            x + s * sx, y + s * 0.56, x + s * sx, y + s * 0.70,
            x + s * (sx + sign * 0.12), y + s * 0.90,
            fill=colour, width=w, smooth=False))
    return ids


def grid_glyph(canvas, x, y, s, colour, w=1.6):
    """A filled block grid - a division template's regiment layout."""
    ids = []
    for column in range(3):
        for row in range(3):
            left = x + s * (0.10 + column * 0.29)
            top = y + s * (0.10 + row * 0.29)
            ids.append(canvas.create_rectangle(
                left, top, left + s * 0.20, top + s * 0.20,
                outline=colour, width=w,
                fill=colour if row < 2 else ""))
    return ids


def translate_glyph(canvas, x, y, s, colour, w=1.6):
    """An A beside a character block with an arrow - translation."""
    ids = [_line(canvas, colour, w, x + s * 0.06, y + s * 0.62, x + s * 0.24, y + s * 0.14),
           _line(canvas, colour, w, x + s * 0.24, y + s * 0.14, x + s * 0.42, y + s * 0.62),
           _line(canvas, colour, w, x + s * 0.13, y + s * 0.44, x + s * 0.35, y + s * 0.44),
           _line(canvas, colour, w, x + s * 0.20, y + s * 0.82, x + s * 0.80, y + s * 0.82),
           _line(canvas, colour, w, x + s * 0.66, y + s * 0.70, x + s * 0.80, y + s * 0.82),
           _line(canvas, colour, w, x + s * 0.66, y + s * 0.94, x + s * 0.80, y + s * 0.82)]
    ids.append(canvas.create_rectangle(x + s * 0.56, y + s * 0.10, x + s * 0.94, y + s * 0.52,
                                       outline=colour, width=w, fill=""))
    return ids


GLYPHS = {
    "open_mod": map_glyph,
    "map": globe_glyph,
    "settings": gear_glyph,
    "focus": target_glyph,
    "events": scroll_glyph,
    "decisions": scales_glyph,
    "ideas": bulb_glyph,
    "country": flag_glyph,
    "tech": flask_glyph,
    "units": shield_glyph,
    "music": note_glyph,
    "code": code_glyph,
    "loc": language_glyph,
    "validate": check_glyph,
    "diff": compare_glyph,
    "replace": swap_glyph,
    "loc_coverage": language_glyph,
    "idea_gallery": bulb_glyph,
    "characters": person_glyph,
    "compat": puzzle_glyph,
    "event_chain": link_glyph,
    "stats": chart_glyph,
    "tree_diff": diff_split_glyph,
    "flags": flag_glyph,
    "ideology": pennant_glyph,
    "factions": network_glyph,
    "ai_strategy": compass_glyph,
    "diplo_action": handshake_glyph,
    "opinion_modifier": heart_glyph,
    "on_action": bolt_glyph,
    "peace_modifier": olive_glyph,
    "state_edit": tile_glyph,
    "war_goal": swords_glyph,
    "decision_category": tag_glyph,
    "equipment": wrench_glyph,
    "agency_upgrade": eye_glyph,
    "traits": star_glyph,
    "oob": barracks_glyph,
    "game_setup": pin_glyph,
    "icon_coverage": search_glyph,
    "load_order": layers_glyph,
    "error_log": warning_glyph,
    "refactor": swap_glyph,
    "guides": compass_glyph,
    "railways": rail_glyph,
    "scripted": braces_glyph,
    "divisions": grid_glyph,
    "translation": translate_glyph,
    # aliases for callers outside the nav rail
    "target": target_glyph,
    "globe": globe_glyph,
}


def draw(canvas, key, x, y, size, colour):
    fn = GLYPHS.get(key)
    if not fn:
        return []
    return fn(canvas, x, y, size, colour)
