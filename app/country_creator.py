"""Country creator: everything a brand-new playable tag needs, written in
one go into the open mod.

  common/country_tags/zzz_<TAG>.txt          registers the tag
  common/countries/<Name>.txt                graphical culture + colour
  common/countries/colors.txt                map colour (see note below)
  common/characters/zzz_<TAG>_leader.txt     the starting leader
  history/countries/<TAG> - <Name>.txt       capital, politics, leader
  gfx/flags/<TAG>.tga (+medium/small)        flags at all three sizes
  localisation/english/zzz_<TAG>_...yml      names for country and parties

colors.txt is the one landmine: HOI4 replaces the whole file rather than
merging it, so a mod shipping a colors.txt containing only the new tag
would strip the map colour of every other country. If the mod already has
one we append to it (with a .bak backup); otherwise we copy the base
game's full file first and then append.
"""

import os
import re
import shutil

from PIL import Image

from app import pds_scan as scan

from app.game_paths import find_base_game

#: resolved once at import; empty when HOI4 isn't installed here
BASE_GAME = find_base_game()

FLAG_SIZES = {
    "": (82, 52),
    "medium": (41, 26),
    "small": (10, 7),
}

IDEOLOGIES = ["neutrality", "democratic", "fascism", "communism"]
LEADER_SUBS = {
    "neutrality": "despotism",
    "democratic": "liberalism",
    "fascism": "fascism_ideology",
    "communism": "marxism",
}


def existing_tags(mod_root):
    """Tags already registered by the mod or the base game."""
    tags = set()
    for root in (BASE_GAME, mod_root):
        folder = os.path.join(root, "common", "country_tags")
        if not os.path.isdir(folder):
            continue
        for name in os.listdir(folder):
            path = os.path.join(folder, name)
            try:
                with open(path, "r", encoding="utf-8-sig", errors="ignore") as f:
                    text = scan.strip_comments(f.read())
            except OSError:
                continue
            tags.update(re.findall(r"^\s*([A-Z][A-Z0-9]{2})\s*=", text, flags=re.MULTILINE))
    return tags


def _write_flags(mod_root, tag, flag_image_path):
    src = Image.open(flag_image_path).convert("RGBA")
    paths = []
    for sub, (w, h) in FLAG_SIZES.items():
        out_dir = os.path.join(mod_root, "gfx", "flags", sub) if sub else os.path.join(mod_root, "gfx", "flags")
        os.makedirs(out_dir, exist_ok=True)
        resized = src.resize((w, h), Image.LANCZOS)
        path = os.path.join(out_dir, f"{tag}.tga")
        resized.save(path)
        paths.append(path)
    return paths


def _ensure_colors_file(mod_root):
    """Return the path of the mod's colors.txt, creating it from the base
    game's full copy if the mod doesn't have one yet."""
    dest = os.path.join(mod_root, "common", "countries", "colors.txt")
    if os.path.isfile(dest):
        backup = dest + ".bak"
        if not os.path.exists(backup):
            shutil.copy2(dest, backup)
        return dest
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    vanilla = os.path.join(BASE_GAME, "common", "countries", "colors.txt")
    if os.path.isfile(vanilla):
        shutil.copy2(vanilla, dest)
    else:
        with open(dest, "w", encoding="utf-8") as f:
            f.write("")
    return dest


def create_country(mod_root, *, tag, name, color, capital_state, ideology,
                   leader_name, leader_portrait=None, popularity=60, leader_sub_ideology=None):
    """Write every file. Returns a list of the files created/updated.
    `color` is an (r, g, b) tuple; `leader_portrait` an image path or None."""
    created = []
    tag = tag.upper()
    safe_name = re.sub(r"[^A-Za-z0-9 ]+", "", name).strip() or tag

    # 1. tag registration
    tags_dir = os.path.join(mod_root, "common", "country_tags")
    os.makedirs(tags_dir, exist_ok=True)
    path = os.path.join(tags_dir, f"zzz_{tag}.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write(f'{tag} = "countries/{safe_name}.txt"\n')
    created.append(path)

    # 2. country file
    countries_dir = os.path.join(mod_root, "common", "countries")
    os.makedirs(countries_dir, exist_ok=True)
    path = os.path.join(countries_dir, f"{safe_name}.txt")
    r, g, b = color
    with open(path, "w", encoding="utf-8") as f:
        f.write(
            "graphical_culture = western_european_gfx\n"
            "graphical_culture_2d = western_european_2d\n"
            f"color = rgb {{ {r} {g} {b} }}\n"
        )
    created.append(path)

    # 3. map colour
    colors_path = _ensure_colors_file(mod_root)
    with open(colors_path, "r", encoding="utf-8-sig", errors="ignore") as f:
        colors_text = f.read()
    if not re.search(rf"^\s*{tag}\s*=", colors_text, flags=re.MULTILINE):
        block = f'\n{tag} = {{\n\tcolor = rgb {{ {r} {g} {b} }}\n\tcolor_ui = rgb {{ {r} {g} {b} }}\n}}\n'
        with open(colors_path, "a", encoding="utf-8") as f:
            f.write(block)
    created.append(colors_path)

    # 4. starting leader character
    char_id = f"{tag}_{re.sub(r'[^a-z0-9]+', '_', leader_name.lower()).strip('_') or 'leader'}"
    portrait_line = "\t\t\t\tlarge = GFX_portrait_unknown"
    if leader_portrait and os.path.isfile(leader_portrait):
        dest_dir = os.path.join(mod_root, "gfx", "leaders", tag)
        os.makedirs(dest_dir, exist_ok=True)
        ext = os.path.splitext(leader_portrait)[1] or ".png"
        dest = os.path.join(dest_dir, char_id + ext)
        shutil.copy2(leader_portrait, dest)
        rel = os.path.relpath(dest, mod_root).replace("\\", "/")
        portrait_line = f'\t\t\t\tlarge = "{rel}"'
        created.append(dest)

    chars_dir = os.path.join(mod_root, "common", "characters")
    os.makedirs(chars_dir, exist_ok=True)
    path = os.path.join(chars_dir, f"zzz_{tag}_leader.txt")
    sub_ideology = leader_sub_ideology or LEADER_SUBS.get(ideology, "despotism")
    with open(path, "w", encoding="utf-8") as f:
        f.write(
            "characters = {\n"
            f"\t{char_id} = {{\n"
            f"\t\tname = {char_id}\n"
            "\t\tportraits = {\n"
            "\t\t\tcivilian = {\n"
            f"{portrait_line}\n"
            "\t\t\t}\n"
            "\t\t}\n"
            "\t\tcountry_leader = {\n"
            f"\t\t\tideology = {sub_ideology}\n"
            '\t\t\texpire = "1965.1.1.1"\n'
            "\t\t\tid = -1\n"
            "\t\t}\n"
            "\t}\n"
            "}\n"
        )
    created.append(path)

    # 5. country history
    history_dir = os.path.join(mod_root, "history", "countries")
    os.makedirs(history_dir, exist_ok=True)
    path = os.path.join(history_dir, f"{tag} - {safe_name}.txt")
    # ideology may be a custom group (from the Ideologies tab) that isn't one
    # of the four vanilla ones - keep all vanilla ideologies present at a
    # small share and give the ruling one (vanilla or custom) the rest, so
    # set_popularities always covers whatever ruling_party points at.
    pool = list(IDEOLOGIES) if ideology in IDEOLOGIES else list(IDEOLOGIES) + [ideology]
    others = [i for i in pool if i != ideology]
    pops = {i: round((100 - popularity) / len(others)) for i in others}
    pops[ideology] = popularity
    # fix rounding so it sums to 100
    pops[ideology] += 100 - sum(pops.values())
    with open(path, "w", encoding="utf-8") as f:
        f.write(
            f"capital = {capital_state}\n\n"
            "set_research_slots = 3\n"
            "set_stability = 0.6\n"
            "set_war_support = 0.3\n\n"
            "set_politics = {\n"
            f"\truling_party = {ideology}\n"
            "\tlast_election = \"1932.1.1\"\n"
            "\telection_frequency = 48\n"
            f"\telections_allowed = {'yes' if ideology == 'democratic' else 'no'}\n"
            "}\n\n"
            "set_popularities = {\n"
            + "".join(f"\t{i} = {p}\n" for i, p in pops.items())
            + "}\n\n"
            f"recruit_character = {char_id}\n"
        )
    created.append(path)

    return created, char_id, safe_name


def write_localisation(mod_root, tag, name, leader_name, char_id, ideology, ideology_names=None,
                       ideologies=None):
    """`ideology_names` is an optional {ideology: name} map (e.g. {"fascism":
    "GonaKol Empire"}) - any ideology missing or blank falls back to the
    country's base `name`, exactly like the game does when a mod doesn't
    define TAG_fascism etc."""
    ideology_names = ideology_names or {}
    ideologies = ideologies or IDEOLOGIES
    loc_dir = os.path.join(mod_root, "localisation", "english")
    os.makedirs(loc_dir, exist_ok=True)
    path = os.path.join(loc_dir, f"zzz_{tag}_country_l_english.yml")
    lines = ["l_english:"]
    for suffix in ("", "_DEF", "_ADJ"):
        lines.append(f' {tag}{suffix}:0 "{name}"')
    for ideo in ideologies:
        ideo_name = (ideology_names.get(ideo) or "").strip() or name
        for suffix in ("", "_DEF", "_ADJ"):
            lines.append(f' {tag}_{ideo}{suffix}:0 "{ideo_name}"')
    lines.append(f' {char_id}:0 "{leader_name}"')
    with open(path, "w", encoding="utf-8-sig") as f:
        f.write("\n".join(lines) + "\n")
    return path
