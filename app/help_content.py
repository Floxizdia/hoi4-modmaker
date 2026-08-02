"""Per-tab help copy shown by the "?" button in every PageHeader (see
ui_kit.HelpDialog). Keyed by the same key each tab uses in main.py's
SECTIONS list. Keep entries honest and concrete - a real example beats a
paragraph of description.
"""

HELP = {
    "open_mod": {
        "title": "Open Mod",
        "what": "The mod-loading screen and the visual focus tree canvas editor in one place. "
                "Whatever mod is open here is what every other tab in the app reads from and "
                "writes to - there's no separate 'active project' concept, this tab IS the "
                "active project. The same canvas is what shows up under the 'Focus Tree' entry "
                "in the sidebar too, so you're never looking at two different editors for the "
                "same thing.",
        "how": [
            "Pick a mod from the 'Mod' dropdown - it's auto-filled from your Steam Workshop "
            "folder - or click 'Folder...' to browse to any mod folder on disk (your own "
            "in-progress mod, or one you unpacked manually).",
            "Click 'Load' next to the mod picker. This scans the whole mod in a background "
            "thread - focus trees, events, ideas, characters, and every .gfx icon reference - "
            "so the window stays responsive even on a huge total-conversion mod.",
            "Once loaded, pick a focus tree file from the 'Tree' dropdown and click 'Load' again "
            "next to it, then type a country tag to preview the tree as that country.",
            "The canvas shows every focus as a card: icon, title, cost in days, and how many "
            "prerequisites it has. Drag a card to reposition it (only works when Layout is set "
            "to 'mod coordinates', not 'auto').",
            "The Mode row (SELECT / LINK / ADD / PAN) changes what a click on the canvas does: "
            "SELECT picks/moves a focus, LINK draws a new prerequisite between two focuses you "
            "click in order, ADD opens the new-focus dialog at wherever you click, PAN lets you "
            "drag anywhere to scroll instead of interacting with focuses.",
            "Nothing is written to disk until you use one of the bottom-bar actions: 'Save Moved' "
            "(writes new x/y for focuses you dragged), 'Export New Focuses' (writes any focus you "
            "added), or 'Play in HOI4...' (copies the whole mod into your game's mod folder so "
            "you can actually launch it).",
        ],
    },
    "map": {
        "title": "Map",
        "what": "A clickable, colour-by-owner render of the entire game map, built directly from "
                "the mod's own map/provinces.bmp and history/states files - not a static image, "
                "so it reflects whatever states this mod actually defines, including states you "
                "haven't given an owner yet.",
        "how": [
            "Click 'Load Map' - this decodes provinces.bmp and every state file into one image, "
            "which takes a few seconds on a big map. 'Detail: high' looks sharper but takes "
            "longer to load and pan.",
            "Click a state to select it (click again to deselect); you can select several states "
            "at once before acting on them.",
            "Type a 3-letter tag into 'Give to tag' and click 'Give Selected States' to change "
            "ownership. If a selected state's file still lives in the base game (never touched by "
            "this mod), it's copied into the mod first with a .bak-style safety net - the real "
            "game install is never edited.",
            "Double-click a single state (or select exactly one and click 'Edit State...') to "
            "open its full editor: manpower, building slots, state category, resource amounts, "
            "and victory points per province.",
            "Right-drag pans the view; Shift+scroll-wheel scrolls sideways. Dark olive patches are "
            "real land with no state assigned yet - not sea, just unfinished map data - and "
            "aren't clickable until a state file claims them.",
        ],
    },
    "settings": {
        "title": "Settings",
        "what": "Where a mod starts existing: descriptor.mod (name, version, which HOI4 version "
                "it supports, Workshop tags) plus the safety-net features that don't belong to "
                "any one content tab - snapshots, auto-snapshot timing, starter content, and "
                "reopening the first-run tour.",
        "how": [
            "To start a brand new mod: fill in the mod name, pick/create an empty folder, add "
            "tags, then click the scaffold button - this writes descriptor.mod and creates the "
            "common/, history/, events/, localisation/ folder structure the game expects.",
            "'Starter Content' drops in a minimal working focus/event/decision set for one "
            "country tag, so a brand new mod has something visible to test immediately instead "
            "of an empty tree.",
            "Snapshots: 'Take Snapshot' zips every script/localisation/interface file (not "
            "textures - those would make snapshots huge) with a timestamp. 'Restore Selected' "
            "unpacks a chosen one back over the mod, overwriting current files - take a fresh "
            "snapshot first if you might want to undo the restore itself.",
            "'Changelog vs Selected...' compares the mod's current state against an older "
            "snapshot and lists every focus/event/decision/idea added, removed or changed - "
            "handy for writing a Steam Workshop update description without doing it by hand.",
            "Auto-snapshot takes one automatically every N minutes and keeps the newest 8 so old "
            "ones don't pile up - manual snapshots you took yourself are never auto-deleted.",
        ],
    },
    "stats": {
        "title": "Dashboard",
        "what": "The mod's health at a glance: how much content it has, what Validate currently "
                "flags as broken, which files were touched most recently, and the raw "
                "descriptor.mod - the same four things you'd otherwise have to open four "
                "different tabs to piece together.",
        "how": [
            "Click 'Scan Mod' - this counts every focus/event/decision/idea, runs the full "
            "Validate pass, checks file modification times, and reads descriptor.mod, all in "
            "one pass.",
            "The four tiles at the top (FILES PARSED / FOCUSES / WARNINGS / ERRORS) are the "
            "same counts Validate would show - warnings and errors are colour-coded so a mod "
            "that's currently broken is obvious at a glance.",
            "'Unresolved references' lists the 15 most severe issues Validate found - the exact "
            "same engine as the Validate tab, just surfaced here so you don't have to switch "
            "tabs to see if anything's on fire.",
            "'Recent edits' is sorted by actual file modification time on disk, so it reflects "
            "edits made outside this tool too (hand-editing a file in a text editor still shows "
            "up here).",
            "'Profile Performance...' times each individual scan step (parsing focus trees, "
            "events, building the icon index, running Validate) separately, so on a very large "
            "mod you can see which specific step is slow instead of just 'the tool feels "
            "sluggish'.",
        ],
    },
    "focus": {
        "title": "Focus Tree",
        "what": "This is the same canvas editor as 'Open Mod' under the sidebar - visual editor "
                "for a country's national focus tree. Drag focuses around, wire up prerequisites "
                "either by dragging or with Link mode, and give each focus an icon, cost and a "
                "completion_reward effect. See the 'Open Mod' help entry for the full walkthrough "
                "of the canvas, modes, and toolbar.",
        "how": [
            "Load a tree (or start a 'New empty tree') and type a country tag to preview it as.",
            "In SELECT mode, drag a focus to reposition it (needs Layout set to 'mod "
            "coordinates'); double-click a focus to open its full properties on the right.",
            "In LINK mode, click one focus then a second - the first becomes a prerequisite of "
            "the second. In ADD mode, click empty canvas to place a brand new focus there.",
            "'Add New Focus' and 'From Template...' both open the same properties dialog, one "
            "blank and one pre-filled with a common pattern (industry push, army effort, "
            "political focus...).",
            "'Tidy Tree' recomputes every focus's x/y from the prerequisite structure and writes "
            "that clean, overlap-free grid back as the real coordinates - what you want after a "
            "tree has been hand-edited into a mess. It tells you how many would move first, and "
            "says so instead of acting if the tree is already tidy.",
            "Nothing is saved to disk until you click 'Save Moved' (positions), 'Export New "
            "Focuses' (new additions), or edit-and-save an existing focus's properties.",
        ],
        "example": 'focus = {\n\tid = my_focus\n\ticon = GFX_goal_generic_construction\n\tx = 0  y = 0\n\tcost = 10\n\tprerequisite = { focus = my_earlier_focus }\n\tavailable = { always = yes }\n\tcompletion_reward = {\n\t\tadd_political_power = 50\n\t}\n}',
    },
    "tree_diff": {
        "title": "Tree Diff",
        "what": "Focus-level comparison between two focus trees - your mod's current tree "
                "against a saved snapshot, or two different files entirely. Unlike a raw text "
                "diff, moving a focus 40 pixels shows up as one 'changed: x, y' entry instead of "
                "a wall of shifted text lines, because it compares parsed focus fields "
                "(id, title, icon, cost, x, y, prerequisite), not file bytes.",
        "how": [
            "Pick the two things to compare - typically 'current mod' on one side and a "
            "snapshot .zip on the other.",
            "Run the comparison; results split into Added (new focus ids), Removed (ids that "
            "used to exist), and Changed (same id, different fields) - each Changed entry lists "
            "exactly which fields differ.",
            "Use this before publishing an update to sanity-check that a big refactor (like "
            "re-running auto-layout) didn't accidentally rewrite prerequisites you didn't mean "
            "to touch.",
        ],
    },
    "events": {
        "title": "Events",
        "what": "Create and edit events - country_event, news_event, state_event - the pop-up "
                "windows the game shows the player with a title, description, optional picture, "
                "and one or more clickable options. Namespace + number together form the event's "
                "real id (e.g. germany.14), matching exactly how the base game organizes its own "
                "event files.",
        "how": [
            "Load an existing event file from the mod (its dominant namespace becomes editable "
            "here) or start a fresh namespace with 'New empty file'.",
            "Click 'Add Event' or 'From Template...' - the second pre-fills a common shape (a "
            "2-choice news event, a flag-setting event, a leader succession event...).",
            "Fill in title/description as raw display text (not a loc key) - the tool writes the "
            "actual localisation entries for you when you save.",
            "Add options: each is a button the player sees, with its own name text, optional "
            "ai_chance factor (how likely the AI is to pick it), and an effect written as raw "
            "script or built with the Effect Wizard.",
            "The table on the left is dense: ID / TYPE / TITLE / OPT (option count) / TRIGGERED. "
            "Click a row to see its full detail on the right - options list, and quick Edit/"
            "Preview buttons.",
            "'Preview in game style' renders the event exactly like the in-game pop-up before "
            "you commit to exporting - catches a too-long title or a missing picture before the "
            "player would ever see it.",
            "'Save to mod' writes add_namespace plus every event in this namespace into one "
            "events/<namespace>.txt file - if the source file you loaded held other namespaces "
            "too, it writes a new file instead of overwriting the shared one.",
        ],
        "example": 'add_namespace = my_events\n\ncountry_event = {\n\tid = my_events.1\n\ttitle = my_events.1.t\n\tdesc = my_events.1.d\n\tpicture = GFX_report_event_generic_meeting\n\tis_triggered_only = yes\n\n\toption = {\n\t\tname = my_events.1.a\n\t\tadd_political_power = 20\n\t}\n}',
    },
    "event_chain": {
        "title": "Event Chains",
        "what": "Traces which events fire which other events - via trigger_event and "
                "random_events buried inside immediate/option effects - and lays the whole "
                "storyline out as one flow diagram instead of forcing you to open file after "
                "file to follow the thread by hand.",
        "how": [
            "Run the scan once per mod session - it walks every parsed event's effect text "
            "looking for trigger_event/random_events references.",
            "Pick a starting event; the chain view shows everything it can lead to, several "
            "steps deep, with branches for events that fire more than one follow-up.",
            "Useful for two things: confirming a story you're building actually connects the way "
            "you think it does, and finding orphaned events (defined but never referenced by "
            "anything) that might be dead content.",
        ],
    },
    "decisions": {
        "title": "Decisions",
        "what": "Create and edit decisions - the buttons that show up in the in-game Decisions "
                "panel. A decision has a cost (political power, stability, whatever you gate it "
                "on), a visible/available trigger controlling when it can even be attempted, and "
                "an effect that runs once it completes.",
        "how": [
            "Pick a decision category from the dropdown - if none fits, go make one in Decision "
            "Categories first, then come back here.",
            "Click 'Add Decision' or 'From Template...' (propaganda push, purge the army, "
            "diplomatic pressure - common patterns already wired up).",
            "Set the icon (from the icon library or a composed custom one), cost fields, and the "
            "trigger blocks: 'visible' controls whether the button shows at all, 'available' "
            "controls whether it's clickable, 'allowed' is a one-time gate checked when the game "
            "starts.",
            "The effect (complete_effect in vanilla terms) is what actually happens when the "
            "decision finishes - write it raw or build it with the Effect Wizard.",
            "Export writes the decision into common/decisions/<category-file>.txt inside the "
            "right category block, alongside anything else already in that category.",
        ],
        "example": 'my_decision = {\n\ticon = generic_construction\n\tcost = 50\n\tdays_re_enable = 30\n\n\tvisible = { always = yes }\n\tavailable = { has_political_power = 50 }\n\n\tcomplete_effect = {\n\t\tadd_political_power = -50\n\t\tadd_stability = 0.05\n\t}\n}',
    },
    "ideas": {
        "title": "Ideas / Spirits",
        "what": "Create and edit ideas - national spirits, country/political advisors, high "
                "command, industrial concerns, and every other 'idea' slot category the game "
                "has. Every idea is fundamentally the same shape: an id, a picture, an allowed "
                "trigger, and a modifier block - only the category (which slot it fills) changes "
                "what fields make sense.",
        "how": [
            "Pick a category - 'country' is where national spirits and generic country-wide "
            "ideas both live; the advisor slots (political_advisor, army_chief, etc.) are the "
            "classic specialist categories.",
            "Click 'Add Idea' or 'From Template...' (a temporary war-effort spirit, a permanent "
            "penalty/bonus idea, an advisor pattern).",
            "Set the picture (an icon reference), removal_cost if it should be hard to remove "
            "once added, an 'allowed' trigger gating who can ever have it, and the modifier "
            "block itself - the actual gameplay effect.",
            "Export writes into the mod's common/ideas/<file>.txt under the right category "
            "block, alongside any other ideas already in that category.",
        ],
        "example": 'my_national_spirit = {\n\tpicture = generic_united\n\tallowed = { always = yes }\n\tremoval_cost = -1\n\n\tmodifier = {\n\t\tstability_factor = 0.1\n\t\twar_support_factor = 0.05\n\t}\n}',
    },
    "idea_gallery": {
        "title": "Idea Gallery",
        "what": "A browsable icon grid of every idea already defined - across the base game and "
                "this mod together - so you can see at a glance what already exists before "
                "accidentally inventing a near-duplicate national spirit, or find one to copy as "
                "a starting point.",
        "how": [
            "Filter by category or search by name/id to narrow a genuinely huge list (the base "
            "game alone has hundreds of ideas).",
            "Click an entry to see its full modifier block and where it's defined - useful as a "
            "reference for 'what values are normal' when writing your own.",
        ],
    },
    "country": {
        "title": "Country",
        "what": "Create a brand new playable country tag from scratch: display name, adjective, "
                "map colour, graphical culture, starting ruling party and its popularity split, "
                "a starting leader, and the actual history/countries/<TAG>.txt file the game "
                "reads when the game starts.",
        "how": [
            "Pick a 3-letter tag - the hint next to it tells you immediately if that tag is "
            "already taken by the base game or another part of this mod.",
            "Fill in the Identity card: display name, map colour (colour picker), capital state "
            "id, and a flag image (auto-resized to the game's 82x52/41x26/10x7 TGA sizes). "
            "'Pick on map...' next to the capital field opens a clickable map so you don't "
            "have to look a state id up by hand.",
            "Fill in Starting Politics: ruling ideology and its popularity percentage, leader "
            "name and portrait, and optional ideology-specific display names (e.g. 'German "
            "Reich' under fascism vs. 'Germany' under anything else).",
            "The 'Generated script' panel on the right updates live as you type, so you can see "
            "exactly what will be written before you commit.",
            "Click 'Create Country' - this writes the country file, portrait, flag TGAs, "
            "starting leader character entry, and localisation. The country owns zero territory "
            "afterward; give it the capital state (or others) via the Map tab or a focus/decision.",
        ],
    },
    "flags": {
        "title": "Flags",
        "what": "Draws a country flag - tricolor, cross, canton, or a custom emblem layered on a "
                "plain field - from colours you pick, and writes the real large/medium/small "
                ".tga sizes (82x52 / 41x26 / 10x7) the game actually expects in gfx/flags/.",
        "how": [
            "Type the 3-letter country tag and pick an ideology suffix - leave it blank for the "
            "base flag, or pick one to make an ideology-specific variant (shown when that "
            "ideology is ruling).",
            "Pick a pattern (tricolor, cross, etc.) and up to 3 colours; optionally browse to "
            "your own emblem PNG to layer on top instead of a generated symbol.",
            "The preview updates live as you change colours/pattern. Click 'Create Flag' to "
            "write all three real sizes at once - you never have to make the medium/small "
            "versions by hand.",
        ],
    },
    "ideology": {
        "title": "Ideologies",
        "what": "Define a custom ideology or sub-ideology beyond the base game's four "
                "(democratic/fascism/communism/neutrality) - its own colour, icon, and the "
                "specific political parties that belong to it, for mods that want their own "
                "political systems (syndicalism, a custom fascist variant, etc.).",
        "how": [
            "Pick whether you're adding a whole new top-level ideology or a sub-ideology under "
            "an existing one (most mods want the latter - it's simpler and inherits more "
            "built-in game support).",
            "Set the colour and icon, then add at least one party under it with its own name and "
            "the country-name overrides it should apply when ruling.",
            "This feeds the 'Ruling ideology' dropdown everywhere else in the app - once "
            "created, it shows up as a normal option in Country, Decisions, Ideas, and so on.",
        ],
    },
    "factions": {
        "title": "Factions",
        "what": "Faction templates - the Allies/Axis/Comintern-style alliance structures - "
                "including their join/leave rules and the faction icon shown in-game. A faction "
                "here is a reusable template a country can form or join, not a specific instance "
                "of Germany-and-Italy-are-now-allied (that's handled by focuses/effects).",
        "how": [
            "Add a faction template: name, icon, and the rules (triggers) controlling who can "
            "join or must leave.",
            "Reference the faction's name from a focus or decision's effect (e.g. "
            "create_faction / add_to_faction) to actually form it during play - this tab defines "
            "the template, not the moment it's created.",
        ],
    },
    "ai_strategy": {
        "title": "AI Strategy",
        "what": "Tunes how the AI for a specific country tag behaves - which other tags it wants "
                "to ally with, invade, or build up military strength against, and by how much. "
                "This is what actually drives AI decision-making beyond the vanilla defaults; "
                "without entries here a custom country's AI has no opinion on anyone.",
        "how": [
            "Pick or type the country tag whose AI you're tuning.",
            "Add strategy entries: a type (alliance, antagonize, invasion, etc.), a target tag, "
            "a value (how strongly the AI weighs this), and optionally a date range so the "
            "priority can change over the course of a playthrough.",
            "Higher values push harder toward that behavior; the AI still weighs this against "
            "every other strategy entry and the vanilla AI logic, so one huge number doesn't "
            "guarantee the outcome, just biases toward it.",
        ],
        "example": 'ai_strategy = {\n\tid = alliance\n\ttype = alliance\n\tally = TAG\n\tvalue = 100\n}',
    },
    "diplo_action": {
        "title": "Diplomatic Actions",
        "what": "Define a brand new diplomatic action button - something like a custom 'Request "
                "Alliance' entry in the diplomacy panel - with its own political-power cost, the "
                "triggers that decide when it's possible, and what happens when it's accepted or "
                "declined.",
        "how": [
            "Give the action an id, cost, and the triggers controlling when it can be attempted "
            "(both from the actor's and the target's side).",
            "Write the effects for both outcomes - what happens if the target accepts, and "
            "separately what happens if they decline - these are genuinely different effect "
            "blocks, not one effect with a condition inside it.",
        ],
    },
    "opinion_modifier": {
        "title": "Opinion Modifiers",
        "what": "Named opinion swings - the kind decisions, events, focuses and diplomatic "
                "actions grant via add_opinion_modifier - with a value, an optional duration, "
                "and a decay rate for ones that should fade back to zero on their own rather "
                "than staying forever.",
        "how": [
            "Pick an id (this is the name every add_opinion_modifier reference will use) and a "
            "value - positive for goodwill, negative for a grudge.",
            "Leave duration blank for a permanent modifier that only your own effects can remove "
            "later, or set months + a decay rate for one that fades on a timer without any extra "
            "script.",
        ],
        "example": 'temporary_nap_signed = {\n\tvalue = 25\n\tmonths = 24\n\tdecay = 1\n}',
    },
    "on_action": {
        "title": "On Actions",
        "what": "Hooks a custom effect onto a real game moment - war declared, a country "
                "capitulates, a peace conference starts, and around 74 other known trigger "
                "points the engine fires internally - without needing the game to call your "
                "specific event by name.",
        "how": [
            "Pick the on_action token you want to hook (e.g. on_declare_war, "
            "on_civil_war_end) from the known list, and write the effect that should run every "
            "time that moment happens.",
            "This is additive by design: adding a hook to on_declare_war never overwrites "
            "another mod's hook on the same token, so two mods' on-action effects both run "
            "instead of one silently replacing the other.",
        ],
    },
    "peace_modifier": {
        "title": "Peace Conference",
        "what": "Tunes how expensive a peace conference action is under conditions you set - "
                "take states, puppet, liberate, or force a government change. The 4 action types "
                "themselves are fixed by the engine and can't be added to by script; what you "
                "can control is the cost math (base cost, per-state cost, modifiers) for using "
                "them under specific circumstances.",
        "how": [
            "Pick which of the 4 fixed action types you're tuning, then add cost modifiers "
            "keyed to triggers - e.g. cheaper to take states from a country you're at war with, "
            "more expensive to liberate a country with high war support.",
        ],
    },
    "state_edit": {
        "title": "States",
        "what": "Edit an existing state's resources, building slots, state category (which caps "
                "how many building slots it has), and victory points per province - or build a "
                "brand new state from provinces the map shows as unclaimed (relevant mostly if "
                "you've added custom map territory that has no state yet).",
        "how": [
            "'Edit Existing': pick a state from the list, change manpower/category/buildings/"
            "resources/victory points, and click Apply. If the state file still lives in the "
            "base game, it's copied into your mod first - the original install is never touched.",
            "'Create New State': pick the provinces the map shows as unclaimed land (dark olive "
            "patches, not sea), then fill in the new state's id, name, category, and initial "
            "buildings/resources.",
            "Victory points must reference a province id that's actually inside the state's own "
            "province list - the editor validates this so you don't write a value the game will "
            "silently ignore.",
            "'Pick province on map...' opens a map zoomed to the state you're editing, so you "
            "click the province instead of hunting for its id.",
        ],
    },
    "war_goal": {
        "title": "War Goals",
        "what": "Define a new casus belli type - what a war is being fought to achieve (take "
                "states, puppet the loser, liberate a country, topple a government, full annex) "
                "- along with its base cost, per-state cost, and how much threat declaring it "
                "generates internationally.",
        "how": [
            "Give the war goal an id and pick which sub-triggers apply (take_states/puppet/"
            "liberate/force_government), since these decide what actually happens when the war "
            "is won.",
            "Set generate_base_cost (flat AI-weight cost to declare) and "
            "generate_per_state_cost (scales with how many states are being taken) - together "
            "these are what makes demanding half a continent costlier than demanding one "
            "border state.",
        ],
        "example": 'my_wargoal = {\n\twar_name = MY_WAR\n\ttake_states = { }\n\tgenerate_base_cost = 100\n\tthreat = 1\n}',
    },
    "decision_category": {
        "title": "Decision Categories",
        "what": "Define a new tab/folder for the in-game Decisions panel - its own icon, sort "
                "priority, and a visibility trigger - so your decisions get their own home "
                "instead of all piling into an existing base-game category.",
        "how": [
            "Give the category an id, icon, and priority (lower numbers generally sort earlier "
            "among tabs); the 'visible' trigger controls whether the whole tab shows for a "
            "given country at all.",
            "Once created, this category immediately shows up as a pickable option in the "
            "Decisions tab's category dropdown.",
        ],
    },
    "equipment": {
        "title": "Equipment",
        "what": "Adds a new upgrade tier to an existing equipment archetype - infantry weapons, "
                "tank chassis, plane airframes, ship hulls - by inheriting stats from a parent "
                "tier and overriding only what changed. Brand new archetypes (a whole new unit "
                "category) need 3D models this tool can't generate, so this is specifically for "
                "the 'later-war upgrade' pattern the base game itself uses everywhere (infantry_"
                "equipment_0 through _4, and so on).",
        "how": [
            "Pick the archetype you're extending and a parent tier to inherit unset stats from - "
            "you only need to type the stats that actually differ from the parent.",
            "After creating, paste the shown id into a technology's enable_equipments block "
            "(the exact line to paste is shown right after you create the tier) so researching "
            "that tech is what unlocks it.",
        ],
    },
    "agency_upgrade": {
        "title": "Agency Upgrades",
        "what": "Adds an entry to a country's intelligence agency upgrade tree - one of the "
                "5 branches (intelligence, defense, operation, operative, crypto) - each with "
                "its own AI weight for how much the AI wants to research it, and a separate "
                "modifier block per completed level, since agency upgrades apply a bigger bonus "
                "each time you level them up rather than one flat effect.",
        "how": [
            "Pick the branch and give the upgrade a picture and ai_will_do weight.",
            "Add one modifier block per level - level 1's modifier applies once that level "
            "completes, level 2's modifier applies (usually stacking) once that level "
            "completes, and so on - matching exactly how the base game's own agency upgrades "
            "scale.",
        ],
    },
    "characters": {
        "title": "Characters",
        "what": "Country leaders, generals/admirals, and advisors for a country - portraits, "
                "traits, and the actual history/characters/<TAG>.txt entries the game reads on "
                "start. A leader gallery shows every character a country already has as a "
                "portrait grid so you can add a new one or swap an existing portrait without "
                "hand-editing the file.",
        "how": [
            "Pick a country tag to see its existing characters; click one to edit its name, "
            "portrait, role (leader/general/admiral/advisor), and traits.",
            "'Add New Leader' opens a dialog for a brand new character - id, name, ideology, and "
            "a portrait you can browse to or compose from the built-in art pack.",
            "'Bulk Import Portraits...' lets you pick several image files at once; each is "
            "matched to a character by filename (e.g. TUR_ataturk.png matches the character id "
            "TUR_ataturk) and auto-resized to the game's real portrait size.",
        ],
    },
    "traits": {
        "title": "Traits",
        "what": "A browsable library of every leader/general/admiral/advisor trait already "
                "defined - across the base game and this mod - so you can see what's available "
                "before inventing a duplicate, or clone an existing one as a starting point for "
                "your own.",
        "how": [
            "Filter by role (country leader, corps commander, etc.) or search by name.",
            "Click a trait to see its full modifier block - useful as a sanity check for what "
            "values are 'normal' for a given trait tier before you write your own.",
        ],
    },
    "tech": {
        "title": "Tech",
        "what": "Edit a technology tree category - individual technologies, their prerequisites, "
                "research cost (in weeks), and the equipment/bonuses each one unlocks once "
                "researched.",
        "how": [
            "Pick the tech category (infantry, land_doctrine, etc.) to see its technologies laid "
            "out with prerequisite arrows, similar to the focus tree canvas.",
            "Add or edit a technology: id, icon, cost in research weeks, prerequisite techs, and "
            "what it unlocks - either equipment (paste an equipment tier's id here) or a raw "
            "effect for bonuses that aren't equipment.",
        ],
    },
    "units": {
        "title": "Units",
        "what": "Browse and edit unit types - the underlying regiment/ship-hull/air-wing "
                "categories that equipment attaches to - across both the base game and this "
                "mod. This is the layer below Equipment: a unit type defines what a regiment "
                "fundamentally is (infantry, medium tank, destroyer...), while Equipment defines "
                "which specific gear fills its equipment slots.",
        "how": [
            "Filter by category (land/air/naval) to browse what already exists.",
            "Most mods won't need to add a brand new unit type (that needs matching 3D/2D "
            "assets); this tab is mainly for confirming what stats an existing unit type has "
            "before building Equipment tiers or OOB templates around it.",
        ],
    },
    "oob": {
        "title": "Starting Forces",
        "what": "Order of battle: a country's starting divisions, the division templates "
                "(regiments + support companies) those divisions are built from, starting air "
                "wings, and starting naval fleets - written as the real history/units/<TAG>_"
                "1936*.txt files the base game itself uses, split into Land/Air/Naval sub-tabs.",
        "how": [
            "Type the country tag and an OOB name (e.g. '1936') at the top - this becomes part "
            "of the output filename and the reference line you paste into the country's history "
            "file afterward.",
            "Land: build a division template by adding regiment rows (infantry, artillery, "
            "etc.) and optional support rows (engineer, recon...), then list division groups "
            "with a name, location (province id), and how many identical copies to place.",
            "Air: add wing rows - a location, an equipment id, and an amount; wings sharing the "
            "same location are grouped under one airbase automatically.",
            "Naval: name the fleet, set its home naval base (a province id), and add ship rows "
            "with a name, hull type, equipment loadout, and amount.",
            "Every location field has a 'Pick location on map...' button next to it (or above "
            "the row list) - it opens a map zoomed to just this country's own territory (using "
            "the tag typed at the top), so you click the actual state/province you want instead "
            "of looking up a province id by hand. Clicking shows which state and owner that "
            "province belongs to before you confirm.",
            "After creating, the exact oob = / set_air_oob = / set_naval_oob = line to paste "
            "into the country's history/countries file is shown - this tool deliberately doesn't "
            "auto-edit that file, since it already has real content and guessing where to splice "
            "a line in is exactly the kind of edit that corrupts a file quietly.",
        ],
    },
    "game_setup": {
        "title": "Game Setup",
        "what": "Bookmarks/scenarios - the games a player can pick from the main menu, each with "
                "a start date, a description, and which countries are 'featured' (shown "
                "prominently, usually the majors of that scenario).",
        "how": [
            "Add a bookmark: id, start date, name/description loc text, and the list of "
            "featured country tags.",
            "Most total-conversion mods only need one bookmark (their own start date); "
            "alternate-history mods sometimes add several for different starting points in the "
            "same timeline.",
        ],
    },
    "music": {
        "title": "Music",
        "what": "Add music tracks to the mod's playlist - the .asset/.txt entries the game reads "
                "to know what music exists and when it's allowed to play - without hand-editing "
                "the music definition files' particular nested structure.",
        "how": [
            "Browse to one or more audio files; each becomes a track entry with a name and "
            "optional trigger for when it's allowed to play (peacetime only, a specific "
            "ideology's music, etc.).",
            "The actual audio files still need converting to the game's expected format/bitrate "
            "separately - this tab writes the script that references them, not the audio "
            "conversion itself.",
        ],
    },
    "code": {
        "title": "Code",
        "what": "A raw file-tree code editor with HOI4 script syntax highlighting (braces, "
                "keys, string values, comments all colour-coded), for anything the visual tabs "
                "don't have a dedicated editor for yet, or for making a surgical hand-edit "
                "faster than clicking through a wizard.",
        "how": [
            "Browse the mod's folder tree on the left; click a file to open it in the editor on "
            "the right.",
            "Standard find, and save-in-place - every save still goes through the same "
            "undo-history mechanism as the visual tabs, so Ctrl+Z can undo a hand-edit made here "
            "too.",
        ],
    },
    "loc": {
        "title": "Localisation",
        "what": "Every localisation key used anywhere in the mod, in one big searchable table "
                "you can edit directly - writes real localisation/<language>/*.yml files with "
                "the game's exact l_english: header and quoting rules.",
        "how": [
            "Search or filter to find a specific key (by the focus/event/decision id it "
            "belongs to, or by text content).",
            "Edit the text inline; saving writes straight back to whichever .yml file that key "
            "actually lives in.",
            "The 'Localisation Factory' style bulk generation (if this mod supports multiple "
            "languages) can also copy English text into other language files as a placeholder "
            "so nothing shows as a missing key, ready for real translation later.",
        ],
    },
    "loc_coverage": {
        "title": "Loc Coverage",
        "what": "Cross-references every loc key your mod's focuses/events/decisions/ideas "
                "actually reference against what's defined in localisation/*.yml, and lists "
                "exactly which ones are missing - a focus or event with no localisation shows "
                "its raw internal id in-game instead of readable text, which is one of the "
                "most common 'why does this look broken' issues in a new mod.",
        "how": [
            "Run the scan; results are grouped by content type (focuses, events, decisions, "
            "ideas) so you can knock out one category at a time.",
            "Click a missing entry to jump straight to writing its localisation text without "
            "leaving this tab.",
            "'Fix Untranslated Keys (english)' handles the more severe case: a key the mod "
            "references that NO language defines, so it shows as a raw id for everyone, english "
            "players included. It writes readable placeholder text (GER_four_year_plan -> "
            "'Four Year Plan') into its own file so your real loc files are never touched.",
        ],
    },
    "validate": {
        "title": "Validate",
        "what": "Runs real structural checks across the entire mod at once: unbalanced braces "
                "(a single missing '}' can silently break every file after it), duplicate ids "
                "(two files defining the same focus/event/decision/idea, where the game keeps "
                "only one), dangling references (a focus/effect pointing at an id that doesn't "
                "exist), missing localisation, missing icons, and focus-tree prerequisite cycles "
                "that could never actually unlock.",
        "how": [
            "Click 'Run Validation' - this is a real scan of every relevant file, so it takes a "
            "few seconds on a large mod (the Dashboard's Performance Profile can show exactly "
            "how long each step takes if it feels slow).",
            "Results are severity-coded: error (the game will visibly misbehave or refuse to "
            "load something), warning (probably wrong but won't crash anything), info (worth a "
            "look, often expected in a submod that extends another mod).",
            "Filter by severity with the radio buttons; the category breakdown line above the "
            "table shows which kind of problem is most common at a glance.",
            "Findings are honest warnings, not verdicts - a submod that extends another mod will "
            "show 'missing' for things the parent mod provides, since Validate only sees this "
            "mod's own files.",
            "Two checks worth knowing about: 'missing_files' catches a .gfx sprite whose "
            "texture isn't on disk in this mod or the base game (it renders as a blank box in "
            "game), and 'oob' catches a starting division/fleet pointing at a province id the "
            "map never defines - that unit simply never deploys, with no error anywhere.",
        ],
    },
    "icon_coverage": {
        "title": "Icon Coverage",
        "what": "Every icon/picture reference across focuses, ideas, decisions and events, "
                "checked against sprites actually registered in .gfx files - this is what "
                "predicts exactly which icons would render as a blank square or red-X texture "
                "in game, before you ever have to launch HOI4 to find out.",
        "how": [
            "Run the scan; it walks every icon = / picture = reference and checks it against "
            "the combined base-game + mod .gfx sprite index.",
            "A flagged reference means either the sprite name is misspelled, or the .gfx file "
            "registering it was never written - click a result to see exactly which file and "
            "line the reference comes from.",
        ],
    },
    "diff": {
        "title": "What Changed?",
        "what": "Compares the mod's current files against a snapshot (or another folder "
                "entirely) and shows a plain file-by-file text diff of what's actually different "
                "- the raw-text sibling of Tree Diff, which compares at the focus level instead.",
        "how": [
            "Pick the two things to compare (current mod vs. a snapshot, or two folders).",
            "Changed files are listed with a line count of the diff; click one to see the "
            "actual added/removed lines side by side.",
        ],
    },
    "replace": {
        "title": "Find & Replace",
        "what": "Search-and-replace across every script file in the mod at once, with a "
                "mandatory preview step before anything is written - Find always runs first and "
                "shows exactly which files and how many hits, and Replace re-confirms that same "
                "count before touching a single byte.",
        "how": [
            "Type the text (or, with Regex checked, a pattern) to search for and click 'Find in "
            "Mod' - this only reads files, nothing is changed yet.",
            "Review the file list and hit counts; if it looks right, type the replacement and "
            "click 'Replace All'.",
            "Every changed file gets a one-time .bak backup first, so a bad replace is exactly "
            "as recoverable as a bad manual edit would have been.",
            "Handy for fixing a misspelled focus id across every file that references it, in one "
            "pass instead of hunting each one down.",
            "For renaming a country tag specifically, use 'Rename a country tag...' instead of "
            "a plain replace: it also renames the files that carry the tag in their filename "
            "(TUR - Turkey.txt, gfx/flags/TUR.tga), follows ids that start with the tag "
            "(TUR_1936), and refuses to touch words that merely contain the letters (TURN, "
            "SOV_TUR_pact). A plain three-letter replace gets all of that wrong.",
        ],
    },
    "compat": {
        "title": "Compatibility",
        "what": "Checks this mod against other installed mods for file-level overwrite "
                "conflicts - if two mods ship the exact same relative path (e.g. both define "
                "common/ideas/00_ideas.txt), the game's load order silently decides which one "
                "wins and the other's changes to that file simply don't apply, with no error "
                "shown to the player.",
        "how": [
            "Pick another installed mod to compare against (from the Workshop folder or by "
            "browsing).",
            "Conflicting files are listed by path; this only detects that both mods touch the "
            "same file; it can't know whether the actual content inside genuinely conflicts, so "
            "treat results as 'worth checking by hand', not a final verdict.",
            "'Check vs Installed Game Version' answers a different question: after a HOI4 "
            "patch, does this mod still reference vanilla ideas/technologies/focuses that the "
            "installed game actually defines? Paradox renames and removes ids between patches "
            "and the game reports nothing when a mod asks for one that's gone - the effect just "
            "quietly does nothing, which is the most common way a working mod breaks.",
        ],
    },
    "error_log": {
        "title": "Error Log",
        "what": "Reads the game's own logs/error.log from your last play session - actual "
                "crashes, failed events, and script errors HOI4 itself reported while running, "
                "not just what static file checks like Validate can predict in advance. Some "
                "problems (a broken AI script, a bad targeted effect at runtime) only ever "
                "surface here, because they depend on what actually happens during a playthrough.",
        "how": [
            "Launch the mod in HOI4 and play for a bit (or just let it reach the main menu - "
            "plenty of errors happen during game startup itself).",
            "Come back here and click 'Read Log Now' - it reads the real log file from your "
            "Documents/Paradox Interactive/Hearts of Iron IV/logs folder, not a copy.",
            "Check 'Only show errors touching this mod's files' to cut vanilla/base-game noise "
            "out entirely; a row highlighted green means the message references one of this "
            "mod's own script files by path.",
            "Click a row to see a plain-language hint for common error patterns (e.g. 'No valid "
            "option for event' usually means every option's trigger failed, so the game had "
            "nothing to show the player).",
        ],
        "example": 'events/WW1_Latvia.txt:100: create_ship equipment_variant does not exist for the creator country\n(read literally: line 100 of that file tried to create a ship with an\nequipment variant id the creator country doesn\'t actually have)',
    },
    "load_order": {
        "title": "Load Order",
        "what": "Manage which mods load in what order for a play session, and see every id/file "
                "collision across the whole set at once (not just one pair at a time like "
                "Compatibility) - load order matters because when two mods touch the same file "
                "or define the same id, whichever loads last usually wins.",
        "how": [
            "Refresh the installed-mods list, check 2 or more mods you want to compare "
            "together, and click 'Check Selected'.",
            "The 'Suggested order' tab gives a heuristic ordering (mods with fewer script files "
            "suggested to load last, so their smaller/patch-sized content wins any collision) - "
            "always defer to a mod's own Workshop page if it explicitly says 'load after X'.",
            "The 'Collisions' tab lists every colliding pair and, when you select one, the exact "
            "ids/files both mods define - this never edits any mod, it's read-only analysis.",
        ],
    },
}
