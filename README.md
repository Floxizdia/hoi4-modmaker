# HOI4 Mod Maker

A local desktop mod maker and mod editor for **Hearts of Iron IV**, built with
Python and Tkinter.

Use it to start a new mod from scratch, or open an existing mod and edit
supported content without constantly jumping between folders, text files and
the game.

This is a first project of this kind — still early, but the goal is simple:
make the repetitive parts of HOI4 modding easier while keeping generated
files readable and under your control.

> Just want to use it in-game? Get the packaged build from the
> [Steam Workshop page](https://steamcommunity.com/sharedfiles/filedetails/?id=3776067569)
> instead of building from source.

## What it currently includes

- Visual Focus Tree editor with canvas editing, minimap, drag and drop,
  search, undo/redo and vanilla-safe copying
- Events, event chains, decisions, ideas and national spirits
- Countries, ideologies, flags, characters and technologies
- Tools to view and edit supported vanilla or mod content
- Validation, localisation support and export helpers
- **Vanilla-safe workflow** — base-game files are never edited directly

## Run from source

```bash
python main.py
```

Requires Python 3.9+ (Tkinter and Pillow; see the imports at the top of
`main.py` for the full dependency list). Tested on Windows.

## Project layout

The app is a Tkinter Notebook-style tool: a left navigation rail switches
between generator/editor screens, each backed by its own module(s) under
`app/`.

Screens follow a layered architecture — split into a thin composition root,
a static view, a controller that owns behaviour, a data layer for
disk/cache work, and one file per reusable panel (toolbar, sidebar,
inspector, table, canvas). See `app/home*.py` and `app/focus_tree*.py` for
the reference implementations.

- `main.py` — app entry point, wires the navigation rail to each screen
- `app/state.py` — shared state: the currently open mod + collected
  localisation entries
- `app/theme.py` — shared colour/spacing/font tokens and ttk styles
- `app/pds_scan.py` — parsing helpers for reading existing Paradox script
- `app/mod_export.py` — writes generated content back out as a mod

## Feedback, requests and bugs

Bug reports, feature requests, and notes on how the tool holds up on a real
mod are all welcome — open an issue with what you were trying to do, which
screen/tool you used, and what happened.
