"""Task-level guides over the editor screens.

There are 46 screens, each of which does its own job well. What none of
them can say is which *other* screens a real job needs, and in what order:
"add a country that joins the Axis" is five screens, and knowing that is
the difference between a newcomer getting somewhere and giving up.

This is deliberately a layer on top rather than a reorganisation. The
screens keep their keys, because global search routing, the help entries,
the rail icons and the Ctrl+1..9 shortcuts are all keyed off them - moving
them around to make a tidier list would break four things to fix one.

Each step names a screen by that same key. `GUIDES` is plain data so it can
be checked against the real screen list by a test rather than by hope.
"""

#: (title, why it matters, [(step text, screen key, what to do there)])
GUIDES = [
    (
        "Add a brand-new country",
        "A country needs more than a tag: without history and a flag it exists on paper "
        "but shows up blank and owns nothing.",
        [
            ("Create the tag and its basic country file", "country",
             "Pick a 3-letter tag, a name and a starting ideology."),
            ("Draw or pick a flag", "flags",
             "A country with no flag shows an empty shield everywhere in game."),
            ("Give it land", "map",
             "Select states on the map and hand them over — this also gives it cores."),
            ("Set what it starts with", "oob",
             "Starting divisions, ships and planes. Without this it fields nothing."),
            ("Give it a focus tree", "focus",
             "Optional, but a country with no tree has nothing to do all game."),
        ],
    ),
    (
        "Give a country a focus tree",
        "The tree is where most of a mod's content hangs, and the parts that make it "
        "look finished live on other screens.",
        [
            ("Build the tree", "focus",
             "Add focuses, drag them into place and connect prerequisites."),
            ("Make the icons", "icon_coverage",
             "Find focuses still using a placeholder icon."),
            ("Write the text", "loc",
             "Every focus needs a name and description or it shows as a raw id."),
            ("Check it holds together", "validate",
             "Catches focuses pointing at prerequisites that don't exist."),
        ],
    ),
    (
        "Make a focus fire an event",
        "This is the most common way content connects, and it crosses two screens in a "
        "specific order.",
        [
            ("Write the event first", "events",
             "Give it a namespace and id — the focus has to reference something that exists."),
            ("Reward the focus with it", "focus",
             "In the focus's completion reward, insert the event reference."),
            ("Write the event's text", "loc",
             "Title, description and each option."),
            ("Test that it actually fires", "error_log",
             "Test Play in debug mode reports an event that silently failed."),
        ],
    ),
    (
        "Add a national spirit",
        "A spirit is an idea plus the thing that hands it out — an idea nobody grants "
        "never appears in game.",
        [
            ("Create the idea", "ideas",
             "Set its modifiers and pick an icon."),
            ("See how it will look", "idea_gallery",
             "Check the icon and text as the player will see them."),
            ("Hand it out", "focus",
             "Add the idea in a focus's reward, or from an event or decision."),
        ],
    ),
    (
        "Add a decision",
        "Decisions need a category before they have anywhere to appear.",
        [
            ("Make a category", "decision_category",
             "Decisions with no category never show up in the panel."),
            ("Write the decision", "decisions",
             "Cost, conditions, and what it does."),
            ("Write its text", "loc",
             "Name, description and the tooltip."),
        ],
    ),
    (
        "Reshape the map",
        "State ownership is only the first layer; supply is what decides whether an "
        "army can actually fight there.",
        [
            ("Edit states and ownership", "map",
             "Owners, cores and claims, manpower, buildings and victory points."),
            ("Connect supply", "railways",
             "Railways and supply nodes — new states with no rail line starve."),
            ("Check nothing broke", "validate",
             "Catches states referencing provinces that don't exist."),
        ],
    ),
    (
        "Translate the mod",
        "English is written first everywhere in this tool; the other languages are a "
        "separate pass.",
        [
            ("Find what's missing", "loc_coverage",
             "Which keys exist in English but nowhere else."),
            ("Translate them", "translation",
             "English on the left, your language on the right."),
        ],
    ),
    (
        "Rename or delete something safely",
        "Changing content that already exists is where mods break, because a missed "
        "reference doesn't crash anything — it just quietly stops working.",
        [
            ("See what uses it", "refactor",
             "Preview shows every line that would change before anything is written."),
            ("Fix what's left dangling", "code",
             "Deleting reports references it won't touch; those are yours to fix."),
            ("Confirm the mod still loads", "validate",
             "Then Test Play to see what the game itself says."),
        ],
    ),
    (
        "Ship it",
        "The order matters: publishing something that fails to load is much harder to "
        "walk back than catching it first.",
        [
            ("Validate", "validate",
             "Fix errors before anything else."),
            ("Play it in debug mode", "error_log",
             "Test Play launches the game and reads back what it reported."),
            ("Check mod conflicts", "compat",
             "If it's meant to run alongside other mods."),
            ("Export and publish", "settings",
             "Export puts it where the launcher looks; the publish helper takes it to "
             "the Workshop."),
        ],
    ),
]


def screen_keys():
    """Every screen key the guides point at, for validation."""
    return {key for _title, _why, steps in GUIDES for _text, key, _hint in steps}
