"""Starter template: one click writes a tiny but complete, wired-together
slice of mod content - a 3-focus tree whose last focus fires an event, a
decision, and a national spirit the event can add - so a beginner sees how
the pieces reference each other instead of starting from blank files."""

import os

from app import mod_export

FOCUS_TREE = """focus_tree = {{
	id = {p}_tree
{country_scope}
	default = no
	focus = {{
		id = {p}_first_steps
		icon = GFX_goal_generic_demand_territory
		x = 5
		y = 0
		cost = 5
		completion_reward = {{
			add_political_power = 100
		}}
	}}
	focus = {{
		id = {p}_build_industry
		icon = GFX_goal_generic_construct_civ_factory
		x = 5
		y = 1
		cost = 7
		prerequisite = {{ focus = {p}_first_steps }}
		completion_reward = {{
			add_tech_bonus = {{
				bonus = 0.5
				uses = 1
				category = industry
			}}
		}}
	}}
	focus = {{
		id = {p}_moment_of_destiny
		icon = GFX_goal_generic_political_pressure
		x = 5
		y = 2
		cost = 10
		prerequisite = {{ focus = {p}_build_industry }}
		completion_reward = {{
			country_event = {{ id = {p}_starter.1 days = 1 }}
		}}
	}}
}}
"""

EVENTS = """add_namespace = {p}_starter

country_event = {{
	id = {p}_starter.1
	title = {p}_starter.1.t
	desc = {p}_starter.1.d
	picture = GFX_report_event_generic_sign_treaty
	is_triggered_only = yes
	option = {{
		name = {p}_starter.1.a
		add_ideas = {p}_national_awakening
	}}
	option = {{
		name = {p}_starter.1.b
		add_political_power = 50
	}}
}}
"""

DECISIONS = """{p}_starter_category = {{
	{safe_visibility}
	decisions = {{
		{p}_rally_the_nation = {{
			icon = GFX_decision_generic_political_rally
			cost = 50
			days_re_enable = 180
			allowed = {{
				tag = {tag}
			}}
			complete_effect = {{
				add_war_support = 0.05
			}}
		}}
	}}
}}
"""

IDEAS = """ideas = {{
	country = {{
		{p}_national_awakening = {{
			picture = generic_victors_of_ww1
			allowed = {{
				always = no
			}}
			removal_cost = -1
			modifier = {{
				stability_factor = 0.05
				political_power_factor = 0.10
			}}
		}}
	}}
}}
"""

LOC = """l_english:
 {p}_tree:0 "Starter Tree"
 {p}_first_steps:0 "First Steps"
 {p}_first_steps_desc:0 "Every journey begins with a single step."
 {p}_build_industry:0 "Build Our Industry"
 {p}_build_industry_desc:0 "Factories win wars before soldiers do."
 {p}_moment_of_destiny:0 "Moment of Destiny"
 {p}_moment_of_destiny_desc:0 "The hour has come to decide our path."
 {p}_starter.1.t:0 "The Nation Stirs"
 {p}_starter.1.d:0 "Crowds gather in the capital. The mood is electric — what direction shall we give this energy?"
 {p}_starter.1.a:0 "A national awakening!"
 {p}_starter.1.b:0 "Calm, order, and quiet progress."
 {p}_national_awakening:0 "National Awakening"
 {p}_national_awakening_desc:0 "The people believe in something bigger than themselves again."
 {p}_starter_category:0 "National Efforts"
 {p}_rally_the_nation:0 "Rally the Nation"
"""


def write_starter(mod_root, prefix, tag, *, country_setup=True, include_focus_tree=True):
    """Write the whole starter set. Returns the created file paths."""
    p = prefix.strip().lower() or "starter"
    tag = tag.strip().upper() or "TAG"
    files = {
        os.path.join("events", f"{p}_starter.txt"): EVENTS,
        os.path.join("common", "decisions", f"{p}_starter.txt"): DECISIONS,
        os.path.join("common", "ideas", f"{p}_starter_ideas.txt"): IDEAS,
        os.path.join("localisation", "english", f"{p}_starter_l_english.yml"): LOC,
        os.path.join("common", "characters", f"{tag}.txt"): CHARACTERS,
        "STARTER_GUIDE.txt": GUIDE,
    }
    if include_focus_tree:
        files[os.path.join("common", "national_focus", f"{p}_starter.txt")] = FOCUS_TREE
    if country_setup:
        files[os.path.join("history", "countries", f"{tag} - Starter.txt")] = COUNTRY_HISTORY

    country_scope = ""
    if country_setup:
        country_scope = (
            "\tcountry = {\n"
            "\t\tfactor = 0\n"
            "\t\tmodifier = {\n"
            "\t\t\t# Vanilla country trees commonly use a score of 10 for their tag.\n"
            "\t\t\t# This starter must win deterministically when replacement is intentional.\n"
            "\t\t\tadd = 1000\n"
            f"\t\t\ttag = {tag}\n"
            "\t\t}\n"
            "\t}\n"
        )
    elif include_focus_tree:
        country_scope = "\t# Unassigned sample tree: it does not replace any vanilla country tree.\n"
    safe_visibility = ""
    if not country_setup:
        safe_visibility = f"visible = {{ has_country_flag = {p}_starter_enabled }}"

    created = []
    for rel, template in files.items():
        path = os.path.join(mod_root, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        content = template.format(
            p=p, tag=tag, country_scope=country_scope, safe_visibility=safe_visibility
        )
        encoding = "utf-8-sig" if rel.endswith(".yml") else "utf-8"
        with open(path, "w", encoding=encoding) as f:
            f.write(content)
        created.append(path)
    mod_export.record_created(mod_root, created)
    return created


CHARACTERS = """# Characters: leaders, generals and advisors.
# The game finds these by the `characters = {{ }}` wrapper; the id is what
# every other file references (recruit_character = {p}_leader).
characters = {{
	{p}_leader = {{
		name = {p}_leader
		portraits = {{
			civilian = {{
				large = GFX_portrait_unknown
			}}
		}}
		country_leader = {{
			ideology = despotism
			expire = "1965.1.1.1"
			traits = {{ }}
		}}
	}}
}}
"""

COUNTRY_HISTORY = """# Country history: the starting state of {tag} on the game's start date.
# This is where a country's opening politics, technologies and starting
# leader are set. `oob` names a file in history/units without its extension.
capital = 49

set_research_slots = 3
set_stability = 0.5
set_war_support = 0.3

set_politics = {{
	ruling_party = neutrality
	last_election = "1936.1.1"
	election_frequency = 48
	elections_allowed = no
}}

set_popularities = {{
	neutrality = 100
}}

recruit_character = {p}_leader
"""

GUIDE = """WHAT THE STARTER CONTENT JUST CREATED
=====================================

Every file below is real, working script - not a placeholder. Open them
alongside the matching tab in HOI4 Mod Maker to see how the form fields map
onto what the game actually reads.

common/national_focus/{p}_starter.txt
    A focus tree. `focus_tree` names the tree and says which country gets it;
    each `focus` inside is one clickable node. `x`/`y` are grid coordinates
    (not pixels), `cost` is in weeks, and `prerequisite` is what must be
    completed first. Edit visually in the Focus Tree tab.

events/{p}_starter.txt
    Events - the pop-ups the player sees. `add_namespace` at the top declares
    the id prefix; each event's real id is namespace.number (e.g. {p}.1).
    `is_triggered_only = yes` means it only fires when something explicitly
    calls it, which is what a focus or decision does. Edit in the Events tab.

common/decisions/{p}_starter.txt
    Decisions - buttons in the Decisions panel. `visible` controls whether the
    button appears at all, `available` whether it can be clicked, and
    `complete_effect` is what happens. Edit in the Decisions tab.

common/ideas/{p}_starter_ideas.txt
    Ideas / national spirits. The `country` category is where national
    spirits live. `modifier` is the actual gameplay effect. Edit in the
    Ideas / Spirits tab.

common/characters/{tag}.txt
    Characters - country leaders, generals, advisors. The id here is what
    `recruit_character` in the country history file refers to. Edit in the
    Characters tab.

history/countries/{tag} - Starter.txt
    The country's opening state: capital, politics, popularity split and
    which character leads it. Only applies on the game's start date.

localisation/english/{p}_starter_l_english.yml
    The readable text for every id above. A key missing from here shows the
    raw id on screen in game - the Loc Coverage tab finds those for you.

NEXT STEPS
----------
1. Open the Focus Tree tab and load the tree that was just created.
2. Change a focus's name, add one of your own, and click Export.
3. Use "Play in HOI4..." to copy the mod into your game folder and try it.
4. Run Validate before publishing - it catches broken references the game
   itself reports nothing about.
"""
