"""Which DLC the game install carries, and what that changes.

HOI4 ships expansion content inside the base install and switches it on by
ownership rather than by adding files, so "what the research screen looks
like" is not a property of common/technologies alone:

* `common/technology_tags/00_technology.txt` gates whole folders on DLC -
  `armour_folder` is available only WITHOUT No Step Back and
  `nsb_armour_folder` only WITH it, and the same pairing exists for air
  (By Blood Alone) and naval (Man the Guns). Ignoring those rules shows
  both the legacy and the current folder at once, so an owner of every
  expansion sees the pre-DLC tree sitting in front of the one they
  actually play.

* DLC art lives in `dlc/<dlcNNN_name>/interface/*.gfx` + `gfx/`, outside
  the base game's own interface/ and gfx/ folders. An index built from the
  base root alone therefore resolves none of it, which is why DLC-era tech
  icons come out blank while the pre-DLC ones look fine.

Nothing here reports *ownership* - only what the install has on disk, which
is what the editor can actually read.
"""

import glob
import os
import re

from app import pds_scan as scan

_NAME_RE = re.compile(r'name\s*=\s*"([^"]+)"')
_CATEGORY_RE = re.compile(r'category\s*=\s*"([^"]+)"')
_HAS_DLC_RE = re.compile(r'has_dlc\s*=\s*"([^"]+)"')


def catalogue(base_game):
    """{name} for every DLC the game itself knows about, from
    dlc_metadata/dlc_info. This lists DLC that no longer ships its own
    dlc/<folder> - content folded into the base game, as Man the Guns was -
    which is why "is there a folder for it" alone can't answer whether the
    game applies it."""
    names = set()
    info_dir = os.path.join(base_game, "dlc_metadata", "dlc_info")
    for path in sorted(glob.glob(os.path.join(info_dir, "*.txt"))):
        try:
            with open(path, "r", encoding="utf-8-sig", errors="ignore") as handle:
                text = scan.strip_comments(handle.read())
        except OSError:
            continue
        names.update(_NAME_RE.findall(text))
    return names


def available(base_game):
    """Every DLC the editor can switch on, newest information first:

    * entries with a dlc/<folder> on disk - Steam only downloads those for
      content the account owns, so their presence is real evidence;
    * entries the catalogue knows but that ship no folder, marked
      `bundled` - content that became part of the base game and applies to
      everyone, so it defaults to on.

    `default_on` carries that judgement so the caller doesn't repeat it.
    """
    on_disk = installed(base_game)
    seen = {entry["name"] for entry in on_disk}
    out = list(on_disk)
    for entry in out:
        entry["bundled"] = False
        entry["default_on"] = True
    for name in sorted(catalogue(base_game) - seen):
        out.append({"name": name, "category": "expansion", "path": None,
                    "bundled": True, "default_on": True})
    out.sort(key=lambda d: (d["category"] != "expansion", d["name"]))
    return out


def installed(base_game):
    """[{'name', 'category', 'path'}] for every dlc/<folder>/*.dlc present,
    sorted so expansions (the ones that gate tech folders) come first."""
    out = []
    for descriptor in glob.glob(os.path.join(base_game, "dlc", "*", "*.dlc")):
        try:
            with open(descriptor, "r", encoding="utf-8-sig", errors="ignore") as handle:
                text = handle.read()
        except OSError:
            continue
        name = _NAME_RE.search(text)
        if not name:
            continue
        category = _CATEGORY_RE.search(text)
        out.append({
            "name": name.group(1),
            "category": category.group(1) if category else "",
            "path": os.path.dirname(descriptor),
        })
    out.sort(key=lambda d: (d["category"] != "expansion", d["name"]))
    return out


def folder_rules(roots):
    """{folder_name: {'require': [dlc], 'exclude': [dlc]}} from every root's
    common/technology_tags/*.txt, later roots overriding earlier ones so a
    mod can redefine a folder's availability the way the game lets it."""
    rules = {}
    for root in roots:
        if not root:
            continue
        tag_dir = os.path.join(root, "common", "technology_tags")
        for path in sorted(glob.glob(os.path.join(tag_dir, "*.txt"))):
            try:
                with open(path, "r", encoding="utf-8-sig", errors="ignore") as handle:
                    text = scan.strip_comments(handle.read())
            except OSError:
                continue
            block = scan.first_block(text, "technology_folders")
            if not block:
                continue
            for name, inner in scan.iter_named_blocks(block):
                available = scan.first_block(inner, "available")
                rules[name] = _parse_available(available)
    return rules


def parse_condition(text):
    """{'require': [dlc], 'exclude': [dlc]} for any small availability
    block - a technology folder's `available`, or a focus's `allow_branch`,
    both of which gate content on `has_dlc` the same way."""
    return _parse_available(text)


def focus_gates(focuses):
    """{focus id: condition} for every focus whose branch is DLC-gated, plus
    the set of DLC names involved, as (gates, names)."""
    gates, names = {}, set()
    for focus in focuses:
        raw = focus.get("allow_branch_raw") or ""
        if "has_dlc" not in raw:
            continue
        rule = parse_condition(raw)
        if rule["require"] or rule["exclude"]:
            gates[focus["id"]] = rule
            names.update(rule["require"] + rule["exclude"])
    return gates, names


def hidden_focuses(gates, active):
    """Focus ids the game would not show with exactly `active` DLC on."""
    return {focus_id for focus_id, rule in gates.items()
            if not _matches(rule, active)}


def _matches(rule, active):
    active = set(active or ())
    if any(name not in active for name in rule["require"]):
        return False
    return all(name not in active for name in rule["exclude"])


def gating_dlc(rules):
    """Every DLC name that decides whether some folder is shown."""
    return {name for rule in rules.values()
            for name in rule["require"] + rule["exclude"]}


def _parse_available(available):
    """A folder's `available` is small in practice - a bare has_dlc, or one
    wrapped in NOT - so the DLC named inside a NOT block is read as an
    exclusion and everything else as a requirement, rather than pretending
    to evaluate arbitrary trigger script."""
    rule = {"require": [], "exclude": []}
    if not available:
        return rule

    # carve the NOT blocks out by index rather than by string replace, so
    # two identical NOT blocks can't collapse into one
    spans = []
    for match in re.finditer(r"\bNOT\s*=\s*\{", available, re.IGNORECASE):
        close = scan.find_matching_brace(available, match.end() - 1)
        if close == -1:
            continue
        spans.append((match.start(), match.end(), close))

    remainder, cursor = [], 0
    for start, inner_start, close in spans:
        remainder.append(available[cursor:start])
        rule["exclude"] += _HAS_DLC_RE.findall(available[inner_start:close])
        cursor = close + 1
    remainder.append(available[cursor:])

    rule["require"] += _HAS_DLC_RE.findall(" ".join(remainder))
    return rule


def folder_available(rules, folder, active):
    """Whether the game would show `folder` with exactly `active` DLC on."""
    rule = rules.get(folder)
    return True if not rule else _matches(rule, active)


def gfx_roots(base_game, active, entries=None):
    """dlc/<folder> paths for the active DLC, to be appended to the base
    game when building a sprite index so DLC-era tech art resolves. Bundled
    DLC contributes no path - its art is already in the base game."""
    active = set(active or ())
    return [entry["path"] for entry in (entries if entries is not None else installed(base_game))
            if entry["name"] in active and entry.get("path")]
