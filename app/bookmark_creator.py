"""Game setup: bookmarks (scenarios) and their featured countries - the
date-select screen's cards, each with a handful of countries that get a
custom blurb, starting ideas and starting focuses highlighted.

Only whole new bookmark files are written here, never edits to an existing
one: a vanilla or mod bookmark file is exactly the kind of large,
hand-tuned content this app avoids splicing into blind (see focus_surgery's
doc string, or the OOB tab's same reasoning for history/countries files).
"""

import os

from app import pds_scan as scan
from app import loc_surgery
from app.map_data import BASE_GAME

BOOKMARK_DIR = os.path.join("common", "bookmarks")
FILENAME = "zzz_custom_bookmark.txt"


def list_bookmarks(mod_root):
    """[(name_key, date, source)] across base game + mod, newest-first by
    nothing in particular - just for reference/duplicate-avoidance."""
    out = []
    for root, source in ((BASE_GAME, "vanilla"), (mod_root, "mod")):
        folder = os.path.join(root, BOOKMARK_DIR)
        if not os.path.isdir(folder):
            continue
        for name in sorted(os.listdir(folder)):
            if not name.endswith(".txt"):
                continue
            try:
                with open(os.path.join(folder, name), "r", encoding="utf-8-sig", errors="ignore") as f:
                    text = scan.strip_comments(f.read())
            except OSError:
                continue
            outer = scan.first_block(text, "bookmarks")
            if outer is None:
                continue
            for _, _, inner in scan.iter_blocks(outer, "bookmark"):
                out.append((scan.scalar(inner, "name", ""), scan.scalar(inner, "date", ""), source))
    return out


def create_bookmark(mod_root, *, name_key, display_name, desc_key, description,
                     date, picture, default_country, is_default, countries):
    """`countries` is a list of dicts: tag, history_key, history_text,
    ideology, ideas (list of ids), focuses (list of ids). Returns the files
    written."""
    def country_block(c):
        lines = [f'\t\t"{c["tag"]}" = {{']
        if c.get("history_text"):
            lines.append(f'\t\t\thistory = "{c["history_key"]}"')
        if c.get("ideology"):
            lines.append(f'\t\t\tideology = {c["ideology"]}')
        if c.get("ideas"):
            lines.append("\t\t\tideas = {\n" + "\n".join(f"\t\t\t\t{i}" for i in c["ideas"]) + "\n\t\t\t}")
        if c.get("focuses"):
            lines.append("\t\t\tfocuses = {\n" + "\n".join(f"\t\t\t\t{i}" for i in c["focuses"]) + "\n\t\t\t}")
        lines.append("\t\t}")
        return "\n".join(lines)

    body = [
        "\tbookmark = {",
        f'\t\tname = "{name_key}"',
        f'\t\tdesc = "{desc_key}"',
        f"\t\tdate = {date}",
    ]
    if picture:
        body.append(f'\t\tpicture = "{picture}"')
    if default_country:
        body.append(f'\t\tdefault_country = "{default_country}"')
    if is_default:
        body.append("\t\tdefault = yes")
    body.extend(country_block(c) for c in countries)
    body.append("\t}")
    script = "bookmarks = {\n" + "\n".join(body) + "\n}\n"

    folder = os.path.join(mod_root, BOOKMARK_DIR)
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, FILENAME)
    if os.path.isfile(path):
        with open(path, "r", encoding="utf-8-sig", errors="ignore") as f:
            existing = f.read().rstrip()
        if existing.endswith("}"):
            content = existing[:-1].rstrip("\n") + "\n" + "\n".join(body) + "\n}\n"
        else:
            content = existing + "\n\n" + script
    else:
        content = script

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

    created = [path]
    created.append(loc_surgery.set_key(mod_root, name_key, display_name))
    created.append(loc_surgery.set_key(mod_root, desc_key, description))
    for c in countries:
        if c.get("history_text"):
            created.append(loc_surgery.set_key(mod_root, c["history_key"], c["history_text"]))
    return created
