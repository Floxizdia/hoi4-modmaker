"""Small helpers for emitting Paradox script (PDS) syntax without hand-
indenting strings everywhere."""


def indent_block(text, levels=1):
    """Indent every non-empty line of `text` by `levels` tabs."""
    pad = "\t" * levels
    lines = text.splitlines()
    return "\n".join(pad + line if line.strip() else line for line in lines)


def block(name, inner_text, levels=0):
    """Wrap `inner_text` in `name = { ... }` at the given indent level."""
    pad = "\t" * levels
    body = indent_block(inner_text, levels + 1)
    return f"{pad}{name} = {{\n{body}\n{pad}}}"


def kv(key, value, levels=0):
    pad = "\t" * levels
    return f"{pad}{key} = {value}"


def quoted(text):
    return '"' + text.replace('"', '\\"') + '"'
