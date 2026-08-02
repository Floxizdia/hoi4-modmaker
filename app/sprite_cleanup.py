"""Clean up .gfx sprite entries whose texture file isn't there.

Validate finds these; this removes them. Removing rather than repointing is
the honest fix: the tool has no way to know which image the author *meant*,
and silently substituting a placeholder would turn a visible "this icon is
broken" into an invisible "this icon is wrong", which is worse.

Removing the SpriteType makes the sprite name undefined, which is exactly
what it effectively already is - but now Icon Coverage can see and report
it, instead of the reference looking satisfied while rendering blank.
"""

import os
import re
import shutil

from app import mod_loader as ml
from app.map_data import BASE_GAME

# one SpriteType block, captured whole so it can be cut out cleanly
_SPRITE_BLOCK_RE = re.compile(
    r"[ \t]*(?:SpriteType|spriteType)\s*=\s*\{"      # opening
    r"(?:[^{}]|\{[^{}]*\})*"                          # body, one nesting level deep
    r"\}[ \t]*\r?\n?",
    re.IGNORECASE,
)
_NAME_RE = re.compile(r'\bname\s*=\s*"([^"]+)"', re.IGNORECASE)


def _texture_exists(path):
    """Same tolerance the game has: .tga/.dds/.png are interchangeable in a
    texturefile path."""
    if os.path.isfile(path):
        return True
    stem = os.path.splitext(path)[0]
    return any(os.path.isfile(stem + ext) for ext in (".dds", ".tga", ".png"))


def find_dead_sprites(mod_root):
    """{sprite_name: (gfx_file, texture_rel)} for sprites this mod declares
    whose texture is missing from both the mod and the base game."""
    mod_abs = os.path.abspath(mod_root)
    try:
        vanilla = set(ml.build_gfx_index([BASE_GAME]))
    except Exception:
        vanilla = set()

    dead = {}
    for sprite, texture_path in ml.build_gfx_index([mod_root]).items():
        if sprite in vanilla:
            continue   # the mod is overriding a vanilla sprite; art comes from there
        if not os.path.abspath(texture_path).startswith(mod_abs):
            continue
        rel = os.path.relpath(texture_path, mod_root)
        if _texture_exists(texture_path) or _texture_exists(os.path.join(BASE_GAME, rel)):
            continue
        dead[sprite] = rel
    return dead


def _gfx_files(mod_root):
    out = []
    for sub in ("interface", "gfx"):
        base = os.path.join(mod_root, sub)
        if not os.path.isdir(base):
            continue
        for dirpath, _dirnames, filenames in os.walk(base):
            for name in filenames:
                if name.lower().endswith(".gfx"):
                    out.append(os.path.join(dirpath, name))
    return out


def plan_removal(mod_root, sprite_names):
    """{gfx_path: [sprite_names_in_it]} without changing anything."""
    wanted = set(sprite_names)
    plan = {}
    for path in _gfx_files(mod_root):
        try:
            with open(path, "r", encoding="utf-8-sig", errors="ignore") as f:
                text = f.read()
        except OSError:
            continue
        hits = []
        for match in _SPRITE_BLOCK_RE.finditer(text):
            name_match = _NAME_RE.search(match.group(0))
            if name_match and name_match.group(1) in wanted:
                hits.append(name_match.group(1))
        if hits:
            plan[path] = hits
    return plan


def remove_sprites(mod_root, sprite_names):
    """Cut the matching SpriteType blocks out. Returns (files_changed,
    sprites_removed). Every touched file keeps a one-time .bak."""
    wanted = set(sprite_names)
    files_changed = 0
    removed = 0

    for path in _gfx_files(mod_root):
        try:
            with open(path, "r", encoding="utf-8-sig", errors="ignore") as f:
                text = f.read()
        except OSError:
            continue

        cut = 0

        def drop(match):
            nonlocal cut
            name_match = _NAME_RE.search(match.group(0))
            if name_match and name_match.group(1) in wanted:
                cut += 1
                return ""
            return match.group(0)

        new_text = _SPRITE_BLOCK_RE.sub(drop, text)
        if not cut:
            continue

        backup = path + ".bak"
        if not os.path.exists(backup):
            try:
                shutil.copy2(path, backup)
            except OSError:
                pass
        try:
            with open(path, "w", encoding="utf-8-sig") as f:
                f.write(new_text)
        except OSError:
            continue
        files_changed += 1
        removed += cut

    return files_changed, removed
