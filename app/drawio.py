"""Import a focus tree skeleton from a Draw.io diagram.

Plenty of people plan a focus tree in Draw.io (diagrams.net) long before
they open a modding tool - boxes for focuses, arrows for prerequisites.
Redrawing that by hand afterwards is pure retyping, so this reads the
diagram and produces the tree.

The file format, in the two shapes it comes in:

    <mxfile><diagram>…<mxGraphModel><root>
        <mxCell id="2" value="Reform the Army" vertex="1">
            <mxGeometry x="120" y="80" width="120" height="60"/>
        </mxCell>
        <mxCell id="3" edge="1" source="2" target="4"/>
    </root></mxGraphModel></diagram></mxfile>

or, when Draw.io saves compressed (its default for .drawio), the text
inside <diagram> is that same XML deflated, base64'd and URL-escaped.
Both are handled; a file that is neither says so plainly rather than
failing with a parser error nobody can act on.

Positions are the interesting part. Draw.io coordinates are pixels at
whatever spacing the author happened to use, while a focus tree wants grid
cells. Dividing by a constant guesses wrong on anybody's diagram but the
author's own, so columns and rows are worked out by *clustering* the
coordinates instead: boxes that line up visually end up in the same column
whatever the absolute pixel values are.
"""

import base64
import html
import os
import re
import urllib.parse
import zlib
import xml.etree.ElementTree as ET

#: two boxes whose centres are closer together than this fraction of the
#: median box size are treated as sharing a column or row
CLUSTER_FRACTION = 0.6

_TAG_RE = re.compile(r"<[^>]+>")
_ID_CLEAN_RE = re.compile(r"[^a-z0-9]+")


class DrawioError(Exception):
    """Something about the file we can explain to the user."""


# ---- reading the file ----

def _decompress(payload):
    """Draw.io's compressed <diagram> body back into XML, or None."""
    try:
        raw = base64.b64decode(payload)
        # raw deflate, no zlib header - hence the negative window size
        inflated = zlib.decompress(raw, -15).decode("utf-8")
        return urllib.parse.unquote(inflated)
    except (ValueError, zlib.error, UnicodeDecodeError):
        return None


def diagram_sources(text):
    """[(name, mxGraphModel xml)] for every page in the file."""
    try:
        root = ET.fromstring(text)
    except ET.ParseError as exc:
        raise DrawioError(f"This isn't readable XML: {exc}") from exc

    if root.tag == "mxGraphModel":
        return [("Page-1", text)]

    pages = []
    for index, diagram in enumerate(root.iter("diagram"), start=1):
        name = diagram.get("name") or f"Page-{index}"
        inner = list(diagram)
        if inner and inner[0].tag == "mxGraphModel":
            pages.append((name, ET.tostring(inner[0], encoding="unicode")))
            continue
        body = (diagram.text or "").strip()
        if not body:
            continue
        expanded = _decompress(body)
        if expanded is None:
            raise DrawioError(
                f"Page '{name}' is saved in Draw.io's compressed format and couldn't be "
                "unpacked. In Draw.io use File > Save As and untick 'Compressed', or "
                "File > Export as > XML with 'Compressed' off, then import that.")
        pages.append((name, expanded))

    if not pages:
        raise DrawioError("No diagram pages found in this file.")
    return pages


def _clean_label(value):
    """Draw.io labels carry HTML - <br>, <b>, &amp; - none of which belongs
    in a focus name."""
    if not value:
        return ""
    text = value.replace("<br>", " ").replace("<br/>", " ").replace("<br />", " ")
    text = _TAG_RE.sub("", text)
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def parse_diagram(xml_text):
    """(boxes, arrows) from one page.

    boxes: [{id, label, x, y, w, h}] - arrows: [(source_id, target_id)]
    """
    try:
        model = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        raise DrawioError(f"This page isn't readable XML: {exc}") from exc

    boxes, arrows = [], []
    for cell in model.iter("mxCell"):
        cell_id = cell.get("id")
        if not cell_id:
            continue
        if cell.get("edge") == "1":
            source, target = cell.get("source"), cell.get("target")
            if source and target:
                arrows.append((source, target))
            continue
        if cell.get("vertex") != "1":
            continue
        geometry = cell.find("mxGeometry")
        if geometry is None:
            continue
        try:
            x = float(geometry.get("x", 0))
            y = float(geometry.get("y", 0))
            w = float(geometry.get("width", 120))
            h = float(geometry.get("height", 60))
        except ValueError:
            continue
        boxes.append({"id": cell_id, "label": _clean_label(cell.get("value")),
                      "x": x, "y": y, "w": w, "h": h})
    return boxes, arrows


# ---- pixels to grid ----

def _cluster(values, tolerance):
    """Map each value to an index, grouping values within `tolerance`.

    Boxes a designer sees as lined up are rarely at identical pixel
    coordinates, so exact matching would put a column of focuses into five
    columns of one.
    """
    order = sorted(set(values))
    groups, current = [], []
    for value in order:
        if current and value - current[-1] > tolerance:
            groups.append(current)
            current = []
        current.append(value)
    if current:
        groups.append(current)

    lookup = {}
    for index, group in enumerate(groups):
        for value in group:
            lookup[value] = index
    return lookup


def _median(values):
    ordered = sorted(values)
    if not ordered:
        return 1.0
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / 2


def assign_grid(boxes):
    """Give every box an integer column and row, starting at 0."""
    if not boxes:
        return {}
    centres_x = {b["id"]: b["x"] + b["w"] / 2 for b in boxes}
    centres_y = {b["id"]: b["y"] + b["h"] / 2 for b in boxes}
    tol_x = _median([b["w"] for b in boxes]) * CLUSTER_FRACTION
    tol_y = _median([b["h"] for b in boxes]) * CLUSTER_FRACTION

    columns = _cluster(centres_x.values(), tol_x)
    rows = _cluster(centres_y.values(), tol_y)
    return {b["id"]: (columns[centres_x[b["id"]]], rows[centres_y[b["id"]]])
            for b in boxes}


# ---- diagram to focuses ----

def make_focus_id(label, prefix="", taken=()):
    """A script-safe id from a drawn label, unique against `taken`."""
    base = _ID_CLEAN_RE.sub("_", label.lower()).strip("_")
    if not base:
        base = "focus"
    if prefix:
        base = f"{prefix.rstrip('_')}_{base}"
    candidate, suffix = base, 2
    while candidate in taken:
        candidate = f"{base}_{suffix}"
        suffix += 1
    return candidate


def build_focuses(boxes, arrows, *, prefix="", flip_arrows=False):
    """[{id, label, x, y, prerequisites}] ready to be written as a tree.

    An arrow is read as pointing from the prerequisite to the focus it
    unlocks, which is how these diagrams are normally drawn. `flip_arrows`
    is there because the opposite convention exists and the file itself
    gives no way to tell them apart.
    """
    grid = assign_grid(boxes)
    ids, taken = {}, set()
    for box in boxes:
        focus_id = make_focus_id(box["label"] or box["id"], prefix, taken)
        taken.add(focus_id)
        ids[box["id"]] = focus_id

    prerequisites = {focus_id: [] for focus_id in ids.values()}
    for source, target in arrows:
        if source not in ids or target not in ids:
            continue        # an arrow to a label or a container, not a box
        if flip_arrows:
            source, target = target, source
        prerequisites[ids[target]].append(ids[source])

    focuses = []
    for box in boxes:
        focus_id = ids[box["id"]]
        column, row = grid[box["id"]]
        focuses.append({
            "id": focus_id,
            "label": box["label"] or focus_id,
            "x": column,
            "y": row,
            "prerequisites": prerequisites[focus_id],
        })
    focuses.sort(key=lambda f: (f["y"], f["x"]))
    return focuses


def load(path, *, prefix="", flip_arrows=False, page=0):
    """Read a .drawio/.xml file into focuses. Returns (focuses, page_names)."""
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as handle:
            text = handle.read()
    except OSError as exc:
        raise DrawioError(str(exc)) from exc

    pages = diagram_sources(text)
    names = [name for name, _xml in pages]
    index = min(max(page, 0), len(pages) - 1)
    boxes, arrows = parse_diagram(pages[index][1])
    if not boxes:
        raise DrawioError(
            f"Page '{names[index]}' has no boxes in it - is the tree on another page?")
    return build_focuses(boxes, arrows, prefix=prefix, flip_arrows=flip_arrows), names


# ---- writing the tree ----

def format_tree(tree_id, country_tag, focuses, *, default_cost=10):
    """A complete `focus_tree = { ... }` block.

    Deliberately a skeleton: every focus gets a placeholder icon and cost
    and no reward at all. The point is to land the shape and the wiring, so
    the rest can be filled in on the Focus Tree screen where it belongs.
    """
    lines = ["focus_tree = {", f"\tid = {tree_id}", "",
             "\tcountry = {", "\t\tfactor = 0", "\t\tmodifier = {",
             "\t\t\tadd = 10", f"\t\t\ttag = {country_tag}", "\t\t}", "\t}", ""]
    if focuses:
        lines.append(f"\tdefault = no")
        lines.append("")

    for focus in focuses:
        lines.append("\tfocus = {")
        lines.append(f"\t\tid = {focus['id']}")
        lines.append("\t\ticon = GFX_goal_unknown")
        lines.append(f"\t\tcost = {default_cost}")
        for prerequisite in focus["prerequisites"]:
            lines.append(f"\t\tprerequisite = {{ focus = {prerequisite} }}")
        lines.append(f"\t\tx = {focus['x']}")
        lines.append(f"\t\ty = {focus['y']}")
        lines.append("\t\tcompletion_reward = {")
        lines.append("\t\t}")
        lines.append("\t}")
        lines.append("")
    lines.append("}")
    return "\n".join(lines) + "\n"


def format_localisation(focuses):
    """The English keys for the imported focuses, so the tree reads as the
    names that were drawn instead of as raw ids."""
    lines = ["l_english:"]
    for focus in focuses:
        text = focus["label"].replace('"', '\\"')
        lines.append(f' {focus["id"]}:0 "{text}"')
        lines.append(f' {focus["id"]}_desc:0 ""')
    return "\n".join(lines) + "\n"


def suggested_filename(tree_id):
    return f"{_ID_CLEAN_RE.sub('_', tree_id.lower()).strip('_') or 'imported'}.txt"


def tree_path(mod_root, tree_id):
    return os.path.join(mod_root, "common", "national_focus", suggested_filename(tree_id))
