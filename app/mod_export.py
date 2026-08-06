"""Turn edits into something the HOI4 launcher will actually list.

Two shapes are supported:

* submod  - a small mod holding only the user's own files, meant to load
            after the original. Nothing is duplicated, and the original mod
            keeps receiving Workshop updates. This is the sane default.
* copy    - a full duplicate of the source mod with the edits baked in, for
            when the user wants one self-contained thing. Source mods run
            close to a gigabyte, so this is opt-in.
"""

import os
import re
import shutil

from app import game_paths

#: platform-aware; see game_paths for why this isn't a Documents path list
USER_DIR_CANDIDATES = game_paths.user_dir_candidates()

# Only these are copied for a submod - the folders this tool can write into.
SUBMOD_FOLDERS = [
    os.path.join("common", "national_focus"),
    os.path.join("common", "characters"),
    os.path.join("common", "decisions"),
    os.path.join("common", "ideas"),
    os.path.join("common", "country_tags"),
    os.path.join("common", "countries"),
    os.path.join("history", "countries"),
    os.path.join("history", "states"),
    os.path.join("gfx", "flags"),
    "events",
    os.path.join("localisation", "english"),
    "interface",
    os.path.join("gfx", "interface", "goals"),
    os.path.join("gfx", "leaders"),
]

SAFE_NAME = re.compile(r"[^A-Za-z0-9_\- ]+")

MANIFEST = ".hoi4modmaker_files.txt"


def record_created(mod_root, paths):
    """Remember files this tool created inside `mod_root`, so a submod
    export can ship exactly ours even when the filename carries no marker
    (country files, flags, colors.txt)."""
    manifest = os.path.join(mod_root, MANIFEST)
    existing = set()
    if os.path.isfile(manifest):
        with open(manifest, "r", encoding="utf-8") as f:
            existing = {line.strip() for line in f if line.strip()}
    for path in paths:
        try:
            rel = os.path.relpath(path, mod_root)
        except ValueError:
            continue
        if not rel.startswith(".."):
            existing.add(rel.replace("\\", "/"))
    with open(manifest, "w", encoding="utf-8") as f:
        f.write("\n".join(sorted(existing)) + "\n")


def recorded_files(mod_root):
    manifest = os.path.join(mod_root, MANIFEST)
    out = set()
    if os.path.isfile(manifest):
        with open(manifest, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    full = os.path.normpath(os.path.join(mod_root, line))
                    if os.path.isfile(full):
                        out.add(full)
    return out


def find_user_dir():
    for path in USER_DIR_CANDIDATES:
        if os.path.isdir(path):
            return path
    return None


def folder_name_for(mod_name):
    cleaned = SAFE_NAME.sub("", mod_name).strip().replace(" ", "_")
    return cleaned or "my_mod"


def _read_descriptor(mod_root):
    path = os.path.join(mod_root, "descriptor.mod")
    if not os.path.isfile(path):
        return ""
    with open(path, "r", encoding="utf-8-sig", errors="ignore") as f:
        return f.read()


def _replace_paths(descriptor_text):
    return re.findall(r'^\s*replace_path\s*=\s*"[^"]*"', descriptor_text, flags=re.MULTILINE)


def _source_tags(descriptor_text):
    match = re.search(r"\btags\s*=\s*\{(.*?)\}", descriptor_text, flags=re.DOTALL)
    if not match:
        return []
    return re.findall(r'"([^"]+)"', match.group(1))


def _descriptor_body(name, version, supported, tags, replace_paths):
    lines = list(replace_paths)
    lines.append("tags={")
    for tag in (tags or ["Gameplay"]):
        lines.append(f'\t"{tag}"')
    lines.append("}")
    lines.append(f'name="{name}"')
    lines.append(f'version="{version}"')
    lines.append(f'supported_version="{supported}"')
    return "\n".join(lines) + "\n"


def _copy_selected(src_root, dest_root, only_files=None):
    """Copy SUBMOD_FOLDERS from src to dest. `only_files` restricts the copy
    to a set of absolute paths, which is what keeps a submod small."""
    copied = 0
    for rel in SUBMOD_FOLDERS:
        src = os.path.join(src_root, rel)
        if not os.path.isdir(src):
            continue
        for dirpath, _, filenames in os.walk(src):
            for filename in filenames:
                abs_path = os.path.join(dirpath, filename)
                if only_files is not None and abs_path not in only_files:
                    continue
                rel_path = os.path.relpath(abs_path, src_root)
                target = os.path.join(dest_root, rel_path)
                os.makedirs(os.path.dirname(target), exist_ok=True)
                shutil.copy2(abs_path, target)
                copied += 1
    return copied


def export(mod_root, mod_name, mode="submod", own_files=None, tags=None,
           version="1.0.0", supported="1.16.*", user_dir=None, progress=None):
    """Write the mod into the HOI4 user mod folder.

    `own_files` is the set of absolute paths this tool created; a submod
    copies exactly those. Returns (mod_folder, mod_file_path, files_copied).
    """
    user_dir = user_dir or find_user_dir()
    if not user_dir:
        raise RuntimeError(
            "Could not find the Hearts of Iron IV user folder "
            "(Documents/Paradox Interactive/Hearts of Iron IV)."
        )

    mod_dir = os.path.join(user_dir, "mod")
    os.makedirs(mod_dir, exist_ok=True)

    folder = folder_name_for(mod_name)
    dest_root = os.path.join(mod_dir, folder)
    os.makedirs(dest_root, exist_ok=True)

    descriptor_text = _read_descriptor(mod_root)
    replace_paths = _replace_paths(descriptor_text) if mode == "copy" else []
    if not tags:
        # a full copy stands in for the original, so it should keep the
        # original's tags; a submod only carries what it actually adds
        tags = _source_tags(descriptor_text) if mode == "copy" else ["Gameplay", "National Focuses"]

    if mode == "copy":
        if progress:
            progress("Copying the whole mod, this can take a while...")
        for entry in os.listdir(mod_root):
            src = os.path.join(mod_root, entry)
            dst = os.path.join(dest_root, entry)
            if entry.lower() == "descriptor.mod":
                continue
            if os.path.isdir(src):
                shutil.copytree(src, dst, dirs_exist_ok=True)
            else:
                shutil.copy2(src, dst)
        copied = sum(len(f) for _, _, f in os.walk(dest_root))
    else:
        if progress:
            progress("Collecting your own files...")
        copied = _copy_selected(mod_root, dest_root, only_files=own_files)

    body = _descriptor_body(mod_name, version, supported, tags, replace_paths)

    with open(os.path.join(dest_root, "descriptor.mod"), "w", encoding="utf-8") as f:
        f.write(body)

    mod_file = os.path.join(mod_dir, f"{folder}.mod")
    with open(mod_file, "w", encoding="utf-8") as f:
        f.write(body + f'path="{dest_root.replace(os.sep, "/")}"\n')

    return dest_root, mod_file, copied
