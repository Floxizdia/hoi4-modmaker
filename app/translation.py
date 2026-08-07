"""Side-by-side translation: English on the left, the target language on
the right, one row per key.

The Loc Coverage screen already finds keys a language is missing and can
bulk-copy the English text across so nobody sees a raw `TUR_focus_x` on
screen. That fills the gap but doesn't translate anything - and once the
English text has been copied in, "missing" stops being a useful measure,
because every key now technically exists.

So this module counts a key as untranslated when its text is missing OR
still character-for-character the English, which is exactly what a filled
placeholder looks like. Translations are written to one file per language
that this screen owns, so re-saving never disturbs hand-written files that
came from elsewhere.
"""

import os
import re

from app import loc_coverage
from app.localisation import HOI4_LANGUAGES

SUFFIX = "_translation"

#: The game loads a language folder's .yml files in alphabetical order and
#: the last definition of a key wins. Translating usually means replacing a
#: placeholder that already sits in another file, so this one has to sort
#: after it - without the prefix, a mod file named `t_l_french.yml` loads
#: after `my_mod_translation_l_french.yml` and the translation never shows.
PREFIX = "zzz_"


def target_path(mod_root, mod_name, lang):
    safe = re.sub(r"[^a-z0-9_]+", "_", mod_name.lower()).strip("_") or "my_mod"
    return os.path.join(mod_root, "localisation", lang,
                        f"{PREFIX}{safe}{SUFFIX}_l_{lang}.yml")


def load_pairs(mod_root, lang):
    """[(key, english, current)] for every English key, sorted by key.

    `current` is whatever that language has now, "" when it has nothing.
    """
    english = loc_coverage.scan_language(mod_root, "english")
    theirs = loc_coverage.scan_language(mod_root, lang)
    return [(key, english[key], theirs.get(key, "")) for key in sorted(english)]


def is_untranslated(english, current):
    """A key still needing work: nothing there, or the English verbatim.

    The second half is what makes this different from a coverage check -
    after a bulk fill every key exists, and the placeholder reads exactly
    like the English it was copied from.
    """
    return not current.strip() or current.strip() == english.strip()


def progress(pairs):
    """(translated, total) over `pairs`."""
    total = len(pairs)
    done = sum(1 for _k, english, current in pairs
               if not is_untranslated(english, current))
    return done, total


def format_file(lang, entries):
    """The .yml text for one language.

    HOI4 wants the `l_<lang>:` header, a leading space on every entry and
    the version number after the colon; the file also has to carry a BOM,
    which is the caller's job via the utf-8-sig encoding.
    """
    lines = [f"l_{lang}:"]
    for key in sorted(entries):
        text = entries[key].replace('"', '\\"')
        lines.append(f' {key}:0 "{text}"')
    return "\n".join(lines) + "\n"


def save(mod_root, mod_name, lang, entries):
    """Write the translations this screen owns for one language.

    Entries already in the file but absent from `entries` are kept: the
    screen may have been filtered to untranslated rows only, and dropping
    everything else would silently delete finished work.
    """
    path = target_path(mod_root, mod_name, lang)
    merged = {}
    if os.path.isfile(path):
        merged.update(_read_entries(path))
    merged.update({k: v for k, v in entries.items() if v.strip()})

    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8-sig") as handle:
        handle.write(format_file(lang, merged))
    return path


def _read_entries(path):
    try:
        with open(path, "r", encoding="utf-8-sig", errors="ignore") as handle:
            text = handle.read()
    except OSError:
        return {}
    return {key: value.replace('\\"', '"')
            for key, value in loc_coverage._KEY_RE.findall(text)}


def languages():
    return [lang for lang in HOI4_LANGUAGES if lang != "english"]
