# HOI4 Mod Maker — project conventions

Python + Tkinter desktop app. See `README.md` for what it does and how to run it.

## Screen architecture standard

Adopted after the Home screen grew into a single ~1000-line file and had to be
split apart (see `app/home*.py`, commit `c9731a1`). Every screen built from
here on follows this shape from the start — no screen should become a
monolithic file again.

**Reference implementation:** `app/home.py` + `app/home_view.py` +
`app/home_controller.py` + `app/home_data.py` + `app/home_table.py` +
`app/home_sidebar.py` + `app/home_inspector.py` + `app/home_theme.py`.
Read those before building a new screen — they're the pattern, not just prior art.

### Required structure

A screen named `<screen>` is a family of modules, not one file:

```
<screen>.py                 composition root only (thin: builds the
                             controller, exposes the handful of methods
                             other screens/main.py need to call in)
<screen>_view.py             static layout: builds child widgets, wires
                             their callbacks to controller methods, owns
                             no business logic
<screen>_controller.py       what every control does; owns the data layer
                             instance and whatever top-level state the
                             screen needs; the one file that should need
                             edits when behaviour changes
<screen>_data.py             (only if the screen loads/caches anything from
                             disk, the network, or another subsystem) pure
                             functions + a small class for async/caching;
                             no tkinter widget imports
<screen>_theme.py            (only if the screen needs tokens the shared
                             app/theme.py doesn't have — e.g. a redesigned
                             screen mid-rollout, like home_theme.py) colors/
                             spacing/fonts/ttk styles, screen-scoped style
                             names so it can't retheme other screens
<screen>_<panel>.py          one file per reusable region: toolbar, sidebar,
                             inspector, table, canvas, dialogs — whatever
                             panels the screen actually has. Each is a
                             widget class (usually a ttk.Frame subclass)
                             that owns exactly one region and nothing else.
```

(The flat `home_*.py` naming is what the app currently uses in place of a
`home/` package + `widgets/` subfolder, since the app is a single top-level
`app/` package with no per-screen subpackages yet. If/when a screen's panel
count grows enough to want real subfolders, mirror this same file list under
`app/<screen>/` with a `widgets/` subpackage — same names, just nested.)

### Rules

- **No monolithic screens.** If a screen file is doing layout, event
  handling, and data loading all at once, split it before it grows further —
  don't wait for it to hit a thousand lines like Home did.
- **Composition over inheritance.** Panels are constructed and wired
  together (view builds them, controller drives them via callbacks passed
  at construction) rather than built through subclassing a shared base
  screen class. A panel takes the data/callbacks it needs in its
  constructor and exposes a small public method surface (`set_mods()`,
  `show()`, `get_selected_paths()`, ...) — it should never reach up into a
  parent or sibling to get something itself.
- **`<screen>_data.py` owns caching and async, not the widgets.** Any
  filesystem scan, validator run, or other CPU/IO-heavy lookup goes through
  the data module's caching + `schedule`-deferred worker-thread pattern
  (see `HomeData` in `app/home_data.py`) — never inline in a widget's
  `_build()`. This is what keeps window-open, resize, and rebuild instant;
  regressing it reintroduces the perf bug fixed in commit `ecea708`.
- **Reusable widgets get shared, not copy-pasted.** If two screens need "a
  filterable table" or "a detail inspector," factor the common part out
  (e.g. into `app/ui_kit.py` or a new shared widgets module) instead of
  duplicating a panel file per screen. Screen-specific panels stay
  screen-specific; genuinely generic ones move to shared code.
- **The top `<screen>.py` file stays thin.** It's the composition root:
  build the controller (which builds the view into itself), and expose
  only the extra hook(s) other code needs to call in (see
  `HomeScreen.refresh_sidebar()`). Nothing else should need to know a
  screen is built out of several files instead of one.
