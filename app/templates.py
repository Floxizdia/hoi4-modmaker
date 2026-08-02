"""A handful of ready-to-edit starting points for the three generator tabs.

These are not meant to be used as-is - they exist so "I want a focus that
starts a civil war" begins from a working skeleton with the right blocks in
the right places, instead of a blank form and a wiki tab. Every template
takes `prefix` and `tag` and drops them into the id/effects, matching the
`{PREFIX}_something` / `TAG` convention real mods use.
"""

FOCUS_TEMPLATES = [
    {
        "name": "Propaganda Campaign",
        "hint": "Political power gain + a temporary popular-support idea.",
        "build": lambda prefix, tag: {
            "id": f"{prefix}_propaganda_campaign", "title": "Propaganda Campaign",
            "desc": "Flood the airwaves and the newspapers with our message.",
            "icon": "GFX_goal_generic_propaganda", "x": 0, "y": 0, "cost": 10,
            "prerequisite": [], "prerequisite_groups": [],
            "available": "", "bypass": "", "select_effect": "",
            "completion_reward": "add_political_power = 50\nadd_ideas = temporary_propaganda_spirit",
            "ai_will_do_raw": "factor = 5",
        },
    },
    {
        "name": "Civil War Trigger",
        "hint": "The focus that flips a country into civil war between two factions.",
        "build": lambda prefix, tag: {
            "id": f"{prefix}_the_reckoning", "title": "The Reckoning",
            "desc": "Tensions boil over - the country splits.",
            "icon": "GFX_goal_generic_political_pressure", "x": 0, "y": 0, "cost": 15,
            "prerequisite": [], "prerequisite_groups": [],
            "available": "", "bypass": "", "select_effect": "",
            "completion_reward": (
                f"start_civil_war = {{\n\tideology = despotism\n\tsize = 0.5\n}}\n"
                f"country_event = {{ id = {prefix}_events.1 }}"
            ),
            "ai_will_do_raw": "factor = 1",
        },
    },
    {
        "name": "Alliance Proposal",
        "hint": "Add the completing country to the player's faction (needs the player to have one).",
        "build": lambda prefix, tag: {
            "id": f"{prefix}_propose_alliance", "title": "Propose an Alliance",
            "desc": "Formalise our friendship with paper and signatures.",
            "icon": "GFX_goal_generic_allies_build_infantry", "x": 0, "y": 0, "cost": 10,
            "prerequisite": [], "prerequisite_groups": [],
            "available": "has_war = no", "bypass": "", "select_effect": "",
            "completion_reward": f"add_to_faction = {tag or 'TAG'}",
            "ai_will_do_raw": "factor = 3",
        },
    },
    {
        "name": "Research Bonus",
        "hint": "A flat research-speed idea for a set period.",
        "build": lambda prefix, tag: {
            "id": f"{prefix}_scientific_council", "title": "Establish a Scientific Council",
            "desc": "Centralise our brightest minds under one roof.",
            "icon": "GFX_goal_generic_scientific_exchange", "x": 0, "y": 0, "cost": 10,
            "prerequisite": [], "prerequisite_groups": [],
            "available": "", "bypass": "", "select_effect": "",
            "completion_reward": "add_ideas = temporary_research_bonus_spirit",
            "ai_will_do_raw": "factor = 4",
        },
    },
    {
        "name": "Heavy Industry Drive (Industry)",
        "hint": "Political power plus an industry-boost idea - the classic 'build up the factories' branch opener.",
        "build": lambda prefix, tag: {
            "id": f"{prefix}_heavy_industry_drive", "title": "Heavy Industry Drive",
            "desc": "Steel and concrete before guns and butter.",
            "icon": "GFX_goal_generic_construct_civ_factory", "x": 0, "y": 0, "cost": 12,
            "prerequisite": [], "prerequisite_groups": [],
            "available": "", "bypass": "", "select_effect": "",
            "completion_reward": "add_political_power = 30\nadd_ideas = temporary_industrial_focus_spirit",
            "ai_will_do_raw": "factor = 5",
        },
    },
    {
        "name": "War Economy (Industry)",
        "hint": "Switches production priorities toward the war effort - usually placed deep in an industry branch.",
        "build": lambda prefix, tag: {
            "id": f"{prefix}_war_economy_focus", "title": "Transition to a War Economy",
            "desc": "Every factory now answers to the war ministry.",
            "icon": "GFX_goal_generic_production", "x": 0, "y": 0, "cost": 15,
            "prerequisite": [], "prerequisite_groups": [],
            "available": "", "bypass": "", "select_effect": "",
            "completion_reward": "add_ideas = temporary_war_economy_spirit",
            "ai_will_do_raw": "factor = 3",
        },
    },
    {
        "name": "Officer Corps Expansion (Military)",
        "hint": "Flat army experience gain - a cheap early branch opener for a military tree.",
        "build": lambda prefix, tag: {
            "id": f"{prefix}_officer_corps_expansion", "title": "Expand the Officer Corps",
            "desc": "More academies, more graduates, more competent commanders.",
            "icon": "GFX_goal_generic_military_high_command", "x": 0, "y": 0, "cost": 10,
            "prerequisite": [], "prerequisite_groups": [],
            "available": "", "bypass": "", "select_effect": "",
            "completion_reward": "army_experience = 30",
            "ai_will_do_raw": "factor = 4",
        },
    },
    {
        "name": "Naval Buildup (Military)",
        "hint": "Flat navy experience gain - the naval-branch equivalent of Officer Corps Expansion.",
        "build": lambda prefix, tag: {
            "id": f"{prefix}_naval_buildup", "title": "Naval Buildup Program",
            "desc": "Keels laid down the length of the coast.",
            "icon": "GFX_goal_generic_navy_bonus_dockyard", "x": 0, "y": 0, "cost": 10,
            "prerequisite": [], "prerequisite_groups": [],
            "available": "", "bypass": "", "select_effect": "",
            "completion_reward": "navy_experience = 30",
            "ai_will_do_raw": "factor = 3",
        },
    },
    {
        "name": "Non-Aggression Pact (Diplomacy)",
        "hint": "Improves relations with a chosen country - swap in a real opinion modifier defined in the mod.",
        "build": lambda prefix, tag: {
            "id": f"{prefix}_non_aggression_pact", "title": "Propose a Non-Aggression Pact",
            "desc": "Better a signature now than a border skirmish later.",
            "icon": "GFX_goal_generic_scientific_exchange", "x": 0, "y": 0, "cost": 10,
            "prerequisite": [], "prerequisite_groups": [],
            "available": "has_war = no", "bypass": "", "select_effect": "",
            "completion_reward": (
                f"{tag or 'TAG'} = {{\n\tadd_opinion_modifier = {{\n\t\ttarget = ROOT\n"
                "\t\tmodifier = temporary_nap_signed\n\t}\n}"
            ),
            "ai_will_do_raw": "factor = 3",
        },
    },
]

EVENT_TEMPLATES = [
    {
        "name": "Milestone Event (\"big moment\")",
        "hint": "A dramatic, fires-once turning point with a bigger picture and a country-wide flag - "
                "the closest thing to a \"super event\" HOI4 actually supports without a custom .gui: "
                "one real event, played for weight instead of a routine news item.",
        "build": lambda prefix, tag: {
            "number": "1", "type": "country_event", "title": "A Nation at the Crossroads",
            "desc": "What happens next will define this country for a generation.",
            "picture": "GFX_report_event_generic_meeting",
            "is_triggered_only": True, "trigger": "", "immediate": "",
            "options": [
                {"name": "Seize the moment", "ai_factor": "50",
                 "effect": f"set_country_flag = {prefix}_milestone_seized\nadd_political_power = 100\nadd_stability = 0.05"},
                {"name": "Hold back", "ai_factor": "50",
                 "effect": f"set_country_flag = {prefix}_milestone_declined\nadd_war_support = 0.05"},
            ],
        },
    },
    {
        "name": "News Event (2 choices)",
        "hint": "A triggered news-desk event with two options, the most common event shape.",
        "build": lambda prefix, tag: {
            "number": "1", "type": "country_event", "title": "A Difficult Choice",
            "desc": "The situation calls for a decision.", "picture": "GFX_report_event_generic_meeting",
            "is_triggered_only": True, "trigger": "", "immediate": "",
            "options": [
                {"name": "Option A", "ai_factor": "50", "effect": "add_political_power = 20"},
                {"name": "Option B", "ai_factor": "50", "effect": "add_stability = 0.02"},
            ],
        },
    },
    {
        "name": "Country Flag Event",
        "hint": "Sets a flag on completion - useful as a marker other triggers check for.",
        "build": lambda prefix, tag: {
            "number": "1", "type": "country_event", "title": "A Turning Point",
            "desc": "History will remember this moment.", "picture": "GFX_report_event_generic_meeting",
            "is_triggered_only": True, "trigger": "", "immediate": "",
            "options": [
                {"name": "Continue", "ai_factor": "100",
                 "effect": f"set_country_flag = {prefix}_turning_point_flag"},
            ],
        },
    },
    {
        "name": "Leader Succession",
        "hint": "One leader steps down, another (already defined as a character) takes over.",
        "build": lambda prefix, tag: {
            "number": "1", "type": "country_event", "title": "A New Leader",
            "desc": "The old guard steps aside.", "picture": "GFX_report_event_generic_meeting",
            "is_triggered_only": True, "trigger": "", "immediate": "",
            "options": [
                {"name": "So it begins", "ai_factor": "100",
                 "effect": f"{tag or 'TAG'} = {{\n\tpromote_character = {prefix}_new_leader\n}}"},
            ],
        },
    },
    {
        "name": "Cabinet Reshuffle (Political, 3 choices)",
        "hint": "A political event with three factional choices, each nudging stability/war support differently.",
        "build": lambda prefix, tag: {
            "number": "2", "type": "country_event", "title": "Cabinet Reshuffle",
            "desc": "The government must be rebuilt - who gets the key ministries?",
            "picture": "GFX_report_event_generic_meeting",
            "is_triggered_only": True, "trigger": "", "immediate": "",
            "options": [
                {"name": "Favor the hardliners", "ai_factor": "33",
                 "effect": "add_stability = -0.03\nadd_war_support = 0.05"},
                {"name": "Favor the moderates", "ai_factor": "34",
                 "effect": "add_stability = 0.05"},
                {"name": "Favor the technocrats", "ai_factor": "33",
                 "effect": "add_political_power = 40"},
            ],
        },
    },
    {
        "name": "Industrial Accident (Negative)",
        "hint": "A setback event - stability/factory hit, useful as a random or triggered complication.",
        "build": lambda prefix, tag: {
            "number": "3", "type": "country_event", "title": "Industrial Accident",
            "desc": "A factory floor turns into a disaster site.",
            "picture": "GFX_report_event_generic_factory_sabotage",
            "is_triggered_only": True, "trigger": "", "immediate": "",
            "options": [
                {"name": "Launch an inquiry", "ai_factor": "60", "effect": "add_stability = -0.02"},
                {"name": "Cover it up", "ai_factor": "40",
                 "effect": "add_stability = -0.01\nadd_war_support = -0.02"},
            ],
        },
    },
    {
        "name": "Foreign Intervention Offer (Diplomacy)",
        "hint": "Accept/decline shape for a proposal from another power - pair with an opinion or faction effect.",
        "build": lambda prefix, tag: {
            "number": "4", "type": "country_event", "title": "An Offer From Abroad",
            "desc": "A foreign power extends a hand - conditions attached, of course.",
            "picture": "GFX_report_event_generic_diplomacy",
            "is_triggered_only": True, "trigger": "", "immediate": "",
            "options": [
                {"name": "Accept", "ai_factor": "50",
                 "effect": f"{tag or 'TAG'} = {{\n\tadd_opinion_modifier = {{\n\t\ttarget = ROOT\n"
                           "\t\tmodifier = temporary_offer_accepted\n\t}\n}"},
                {"name": "Decline", "ai_factor": "50", "effect": "add_political_power = 10"},
            ],
        },
    },
]

DECISION_TEMPLATES = [
    {
        "name": "Diplomatic Action",
        "hint": "Costs political power, needs no war - the classic diplomacy decision shape.",
        "build": lambda prefix, tag: {
            "id": f"{prefix}_send_envoy", "title": "Send a Diplomatic Envoy",
            "desc": "Open a formal channel with our neighbours.",
            "icon": "GFX_decision_generic", "cost": 100, "days_re_enable": "",
            "allowed": "always = yes", "visible": "", "available": "has_war = no",
            "effect": "add_political_power = -50\nadd_opinion_modifier = {\n\ttarget = TAG\n\tmodifier = envoy_sent\n}",
            "ai_factor": "", "ai_will_do_raw": "factor = 5",
        },
    },
    {
        "name": "Economic Mobilization",
        "hint": "A recurring decision that trades political power for a temporary economy boost.",
        "build": lambda prefix, tag: {
            "id": f"{prefix}_mobilize_economy", "title": "Mobilize the Economy",
            "desc": "Redirect factories and workers toward the war effort.",
            "icon": "GFX_decision_generic", "cost": 150, "days_re_enable": "180",
            "allowed": "always = yes", "visible": "", "available": "",
            "effect": "add_ideas = temporary_economic_mobilization_spirit",
            "ai_factor": "", "ai_will_do_raw": "factor = 2",
        },
    },
    {
        "name": "Purge the Officer Corps (Military)",
        "hint": "A one-time, risky military decision - army experience loss but a stability/loyalty gain.",
        "build": lambda prefix, tag: {
            "id": f"{prefix}_purge_officer_corps", "title": "Purge the Officer Corps",
            "desc": "Loyalty over competence, for now.",
            "icon": "GFX_decision_generic", "cost": 100, "days_re_enable": "",
            "allowed": "always = yes", "visible": "", "available": "",
            "effect": "army_experience = -20\nadd_stability = 0.05",
            "ai_factor": "", "ai_will_do_raw": "factor = 1",
        },
    },
    {
        "name": "National Rearmament Day (Military)",
        "hint": "A recurring decision that grants a flat army experience trickle - simple, always-safe filler content.",
        "build": lambda prefix, tag: {
            "id": f"{prefix}_rearmament_day", "title": "National Rearmament Day",
            "desc": "A yearly parade doubles as a training exercise.",
            "icon": "GFX_decision_generic", "cost": 50, "days_re_enable": "365",
            "allowed": "always = yes", "visible": "", "available": "",
            "effect": "army_experience = 10",
            "ai_factor": "", "ai_will_do_raw": "factor = 3",
        },
    },
]


IDEA_TEMPLATES = [
    {
        "name": "Temporary National Spirit",
        "hint": "A time-limited spirit with removal_cost -1 (can't be manually removed) - the shape most "
                "focus/event/decision completion_reward blocks grant.",
        "build": lambda prefix, tag: {
            "id": f"{prefix}_temporary_spirit", "category": "country",
            "title": "A Nation Rallies", "desc": "The mood in the country has shifted.",
            "picture": "GFX_idea_generic_propaganda", "removal_cost": "-1", "cost": "",
            "allowed": "always = yes", "allowed_civil_war": "", "available": "",
            "modifier": "stability_factor = 0.05\nwar_support_factor = 0.02",
            "research_modifier": "", "equipment_bonus": "", "targeted_modifier": "",
            "ai_will_do": "",
        },
    },
    {
        "name": "Permanent National Spirit",
        "hint": "No removal_cost set, so it's a normal (manually removable-if-scripted) permanent spirit - "
                "good for a country's defining trait.",
        "build": lambda prefix, tag: {
            "id": f"{prefix}_permanent_spirit", "category": "country",
            "title": "National Character", "desc": "This is simply who we are.",
            "picture": "GFX_idea_generic_national_unity", "removal_cost": "", "cost": "",
            "allowed": "always = yes", "allowed_civil_war": "", "available": "",
            "modifier": "stability_factor = 0.1",
            "research_modifier": "", "equipment_bonus": "", "targeted_modifier": "",
            "ai_will_do": "",
        },
    },
    {
        "name": "Political Advisor",
        "hint": "A country-picked advisor slot idea - swap the modifier for whatever the advisor should grant.",
        "build": lambda prefix, tag: {
            "id": f"{prefix}_political_advisor", "category": "political_advisor",
            "title": "A Trusted Advisor", "desc": "Their counsel shapes policy.",
            "picture": "GFX_idea_generic_political_advisor", "removal_cost": "150", "cost": "",
            "allowed": "always = yes", "allowed_civil_war": "", "available": "",
            "modifier": "political_power_factor = 0.1",
            "research_modifier": "", "equipment_bonus": "", "targeted_modifier": "",
            "ai_will_do": "factor = 1",
        },
    },
    {
        "name": "Industrial Concern",
        "hint": "An industry-slot idea granting a production bonus - the shape used for big domestic companies.",
        "build": lambda prefix, tag: {
            "id": f"{prefix}_industrial_concern", "category": "industrial_concern",
            "title": "A National Champion", "desc": "One firm now dominates the sector.",
            "picture": "GFX_idea_generic_industrial_concern", "removal_cost": "150", "cost": "",
            "allowed": "always = yes", "allowed_civil_war": "", "available": "",
            "modifier": "production_factory_efficiency_gain_factor = 0.1",
            "research_modifier": "", "equipment_bonus": "", "targeted_modifier": "",
            "ai_will_do": "factor = 1",
        },
    },
]


def substitute(build_fn, prefix, tag):
    prefix = prefix.strip() or "my"
    tag = tag.strip().upper()
    return build_fn(prefix, tag)
