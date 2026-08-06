"""Lightweight, read-only scanning helpers for real-world Paradox script
files. This intentionally is NOT a full PDS parser: mod files can be tens of
thousands of lines with arbitrary nested effects/triggers we don't need to
understand. Instead we strip comments, then use brace-matching + targeted
regexes to pull out just the fields the mod browser needs (id, icon,
position, prerequisites, and raw text for opaque effect/trigger blocks).
"""

import re

_COMMENT_RE = re.compile(r"#.*")


def strip_comments(text):
    return _COMMENT_RE.sub("", text)


#: only these characters can change brace depth or quote state; everything
#: between them can be skipped in one C-level jump
_BRACE_SCAN_RE = re.compile(r'[{}"\\]')


def find_matching_brace(text, open_index):
    """Given the index of a '{' in text, return the index of its matching
    '}', respecting quoted strings. Returns -1 if unmatched.

    Jumps between the characters that matter instead of stepping over every
    one: script files are mostly identifiers and whitespace, and walking
    them a character at a time in Python made this the single most
    expensive function in a whole-mod validation."""
    depth = 0
    in_quotes = False
    i = open_index
    n = len(text)
    search = _BRACE_SCAN_RE.search
    while i < n:
        match = search(text, i)
        if match is None:
            return -1
        i = match.start()
        ch = text[i]
        if in_quotes:
            if ch == "\\":
                i += 2
                continue
            if ch == '"':
                in_quotes = False
        elif ch == '"':
            in_quotes = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return -1


def iter_blocks(text, key):
    """Yield (start, end, inner_text) for every `key = { ... }` occurrence
    in text, at any nesting depth. `start`/`end` bound the whole match
    including the key and braces."""
    pattern = re.compile(r"\b" + re.escape(key) + r"\s*=\s*\{")
    for m in pattern.finditer(text):
        open_idx = m.end() - 1
        close_idx = find_matching_brace(text, open_idx)
        if close_idx == -1:
            continue
        yield m.start(), close_idx + 1, text[open_idx + 1:close_idx]


def first_block(text, key):
    for _, _, inner in iter_blocks(text, key):
        return inner
    return None


_NAMED_BLOCK_RE = re.compile(r"([A-Za-z_][A-Za-z0-9_.\-]*)\s*=\s*\{")


def iter_named_blocks(text):
    """Yield (name, inner_text) for every `name = { ... }` at the TOP level
    of `text` (nested blocks are skipped, since we jump past each closing
    brace). Used for containers whose child keys are arbitrary identifiers,
    e.g. `characters = { SOME_ID = { ... } ... }`."""
    i = 0
    n = len(text)
    while i < n:
        m = _NAMED_BLOCK_RE.search(text, i)
        if not m:
            return
        open_idx = m.end() - 1
        close_idx = find_matching_brace(text, open_idx)
        if close_idx == -1:
            return
        yield m.group(1), text[open_idx + 1:close_idx]
        i = close_idx + 1


def scalar(text, key, default=None):
    """First `key = value` scalar (bareword or quoted string), ignoring
    occurrences where value is a block."""
    pattern = re.compile(r"\b" + re.escape(key) + r"\s*=\s*(?!\{)(\"[^\"]*\"|\S+)")
    m = pattern.search(text)
    if not m:
        return default
    val = m.group(1)
    if val.startswith('"') and val.endswith('"'):
        val = val[1:-1]
    return val


def all_scalars(text, key):
    pattern = re.compile(r"\b" + re.escape(key) + r"\s*=\s*(?!\{)(\"[^\"]*\"|\S+)")
    out = []
    for m in pattern.finditer(text):
        val = m.group(1)
        if val.startswith('"') and val.endswith('"'):
            val = val[1:-1]
        out.append(val)
    return out
