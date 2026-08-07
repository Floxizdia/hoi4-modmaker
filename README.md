# HOI4 Mod Maker

A local desktop mod maker and mod editor for **Hearts of Iron IV**, built with **Python, Tkinter and Pillow**.

HOI4 Mod Maker helps you create new mods, inspect existing vanilla or mod content, and edit supported files through visual tools instead of manually jumping between folders, script files and localisation entries.

The project is designed around a simple idea: make repetitive HOI4 modding tasks faster while keeping generated files readable, transparent and under your control.

> Just want to use the tool?
> Download the packaged build from the [Steam Workshop page](https://steamcommunity.com/sharedfiles/filedetails/?id=3776067569) instead of building from source.

## Features

### Focus Tree editor

- Visual canvas-based editing
- Automatic and mod-coordinate layouts
- Drag-and-drop node positioning
- Prerequisite and mutually exclusive links
- Search and navigation
- Tree outline and minimap
- Undo and redo support
- Vanilla-safe copying
- Draw.io import for focus nodes, positions and prerequisite links
- Import support for compressed `.drawio` files and regular XML diagrams
- Mod-only filtering to hide base-game focus trees

### Mod content editors

- Events and event chains
- Decisions and decision categories
- Ideas and national spirits
- Countries and ideologies
- Flags and factions
- Characters, leaders and advisors
- Technologies and doctrines
- States, buildings, cores and claims
- Starting forces and division templates
- Game setup and scenario tools
- Railways and supply networks
- Scripted effects, triggers and dynamic modifiers
- Translation and localisation tools
- Music and code editing tools
- Idea Gallery for browsing existing ideas and national spirits

### Testing and validation

- Integrated Test Play mode
- Launch Hearts of Iron IV with the open mod in debug mode
- Automatically export a mod before testing when necessary
- Restore the user's original launcher mod selection after testing
- Read and filter the complete `error.log`
- Group repeated errors and join multi-line messages
- Double-click validation results to open the relevant file and line
- Validate large mods before export

### Safe editing workflow

The tool is designed to avoid damaging existing mods:

- Base-game files are never edited directly
- ID renaming updates script references and localisation keys
- Definition deletion shows affected references before writing
- Changes are previewed before they are applied
- Existing IDs cannot be overwritten accidentally
- Modified files receive `.bak` backups
- Rename and delete operations can be undone with `Ctrl+Z`
- Files changed after a preview are skipped instead of being rewritten using stale line numbers

## Linux support

A Linux x86_64 build is included in the Steam Workshop package.

```bash
tar -xzf HOI4ModMaker-linux-x86_64.tar.gz
./HOI4ModMaker/HOI4ModMaker
```

The archive preserves executable permissions and required library symlinks. No manual `chmod` step is required.

A desktop session using X11 or Wayland is required.

## Run from source

### Requirements

- Python 3.9 or newer
- Tkinter
- Pillow

Install the Python dependencies listed by the project, then run:

```bash
python main.py
```

The packaged Windows and Linux builds are recommended for normal use.

## Project architecture

The application uses a modular Tkinter architecture based on composition rather than large monolithic screens.

Each screen is split into focused modules where practical:

- A composition root for assembling the screen
- A view layer for widget construction
- A controller for interaction and behaviour
- A data layer for filesystem and parsing work
- Separate reusable modules for toolbars, sidebars, inspectors, tables, canvases and themes

The Home screen is the architectural reference implementation. The Focus Tree screen follows the same layered approach and is the most performance-sensitive part of the application.

### Important files

- `main.py` — application entry point and screen registration
- `app/state.py` — shared application state and currently open mod
- `app/theme.py` — shared colours, spacing, fonts and ttk styles
- `app/version.py` — application version
- `app/pds_scan.py` — helpers for reading Paradox script files
- `app/mod_export.py` — generated mod output and descriptor handling
- `app/home*.py` — Home screen reference architecture
- `app/focus_tree*.py` — Focus Tree architecture and editor modules
- `tests/` — regression and parser tests
- `docs/` — project documentation and guides

## Performance principles

Performance is treated as a feature:

- Heavy filesystem scans are deferred or cached
- Large validation operations run outside the UI event loop where possible
- Large copy and export operations use background workers
- Canvas updates are kept incremental
- Widgets are not rebuilt unnecessarily
- Parsing and loading are separated from visual composition
- The application avoids synchronous work during startup and widget construction

## Project status

This is an actively developed project and a first project of this kind.

The current focus is improving reliability, expanding editor coverage and making large HOI4 mods easier to inspect and maintain.

Some advanced HOI4 systems may still require manual editing through the Code screen.

## Feedback, requests and bug reports

Bug reports, feature requests and real-world testing feedback are welcome.

When opening an issue, please include:

1. What you were trying to do
2. Which screen or tool you used
3. Which mod and game version you were using
4. What you expected to happen
5. What actually happened
6. Any relevant error message or log entry

For feature requests, examples of the desired HOI4 output are especially helpful.

## Contributing

Small fixes, parser improvements, documentation updates and reproducible bug reports are welcome.

Before submitting a change:

- Keep the existing Tkinter architecture
- Preserve keyboard shortcuts and existing workflows
- Avoid synchronous filesystem work during widget construction
- Keep changes focused and backwards-compatible
- Add or update tests where practical

## License

This project is licensed under the [MIT License](LICENSE).

The license applies to the project's original source code. Hearts of Iron IV, Paradox Interactive assets, game files and other third-party content remain the property of their respective owners.

HOI4 Mod Maker is an independent community project and is not affiliated with or endorsed by Paradox Interactive.
