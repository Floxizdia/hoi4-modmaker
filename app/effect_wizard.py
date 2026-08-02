"""Effect/trigger/modifier wizard: build common Paradox script lines from a
menu instead of writing them by hand. Aimed at people who don't know the
script names yet - pick what you want from a list, fill in the blanks,
watch the script build up, then insert it into the raw text box.

The catalogs cover the everyday 90%: anything exotic can still be typed
into the raw box afterwards, which the wizard never overwrites - it only
appends.
"""

import tkinter as tk
from tkinter import ttk, messagebox

# (menu label, script key, [(param label, placeholder)], template)
# {0}, {1}... are replaced with the param values.
EFFECTS = [
    ("Political power +/-", "add_political_power", [("Amount", "100")], "add_political_power = {0}"),
    ("Stability +/-", "add_stability", [("Amount (-1..1)", "0.05")], "add_stability = {0}"),
    ("War support +/-", "add_war_support", [("Amount (-1..1)", "0.05")], "add_war_support = {0}"),
    ("Army experience", "army_experience", [("Amount", "25")], "army_experience = {0}"),
    ("Navy experience", "navy_experience", [("Amount", "25")], "navy_experience = {0}"),
    ("Air experience", "air_experience", [("Amount", "25")], "air_experience = {0}"),
    ("Manpower", "add_manpower", [("Amount", "10000")], "add_manpower = {0}"),
    ("Add national spirit / idea", "add_ideas", [("Idea id", "my_spirit")], "add_ideas = {0}"),
    ("Remove national spirit / idea", "remove_ideas", [("Idea id", "my_spirit")], "remove_ideas = {0}"),
    ("Add core on state", "add_state_core", [("State id", "49")], "{0} = {{ add_core_of = ROOT }}"),
    ("Transfer state to this country", "transfer_state", [("State id", "49")], "transfer_state = {0}"),
    ("Annex country", "annex_country", [("Country tag", "TAG")],
     "annex_country = {{ target = {0} transfer_troops = yes }}"),
    ("Declare war", "declare_war_on", [("Country tag", "TAG")],
     "declare_war_on = {{ target = {0} type = annex_everything }}"),
    ("Fire an event", "country_event", [("Event id", "my_events.1"), ("Days delay", "1")],
     "country_event = {{ id = {0} days = {1} }}"),
    ("Change ruling party", "set_politics", [("Ideology", "fascism")],
     "set_politics = {{ ruling_party = {0} elections_allowed = no }}"),
    ("Popularity +/-", "add_popularity", [("Ideology", "fascism"), ("Amount (-1..1)", "0.1")],
     "add_popularity = {{ ideology = {0} popularity = {1} }}"),
    ("Opinion of a country", "add_opinion_modifier", [("Country tag", "TAG"), ("Modifier", "friendly_embassy")],
     "{0} = {{ add_opinion_modifier = {{ target = ROOT modifier = {1} }} }}"),
    ("Create faction", "create_faction", [("Faction name (loc key)", "my_faction")], 'create_faction = "{0}"'),
    ("Invite to faction", "add_to_faction", [("Country tag", "TAG")], "add_to_faction = {0}"),
    ("Research bonus", "add_tech_bonus", [("Category", "infantry_weapons"), ("Bonus (0..1)", "0.5")],
     "add_tech_bonus = {{\n\tbonus = {1}\n\tuses = 1\n\tcategory = {0}\n}}"),
    ("Civilian factories in capital", "add_offsite_building",
     [("Amount", "2")], "add_offsite_building = {{ type = industrial_complex level = {0} }}"),
    ("Command power", "add_command_power", [("Amount", "30")], "add_command_power = {0}"),
]

TRIGGERS = [
    ("Is a specific country", "tag", [("Country tag", "TUR")], "tag = {0}"),
    ("Has a national spirit / idea", "has_idea", [("Idea id", "my_spirit")], "has_idea = {0}"),
    ("Has completed a focus", "has_completed_focus", [("Focus id", "my_focus")], "has_completed_focus = {0}"),
    ("Is at war", "has_war", [], "has_war = yes"),
    ("Is at war with", "has_war_with", [("Country tag", "TAG")], "has_war_with = {0}"),
    ("Date is after", "date", [("Date", "1936.6.1")], "date > {0}"),
    ("Stability above", "stability", [("Amount (0..1)", "0.5")], "stability > {0}"),
    ("Ruling party is", "has_government", [("Ideology", "fascism")], "has_government = {0}"),
    ("Owns a state", "owns_state", [("State id", "49")], "owns_state = {0}"),
    ("Country exists", "country_exists", [("Country tag", "TAG")], "country_exists = {0}"),
    ("Is in a faction", "is_in_faction", [], "is_in_faction = yes"),
    ("NOT wrapper (negate)", "NOT", [("Inner line", "tag = TUR")], "NOT = {{ {0} }}"),
]

MODIFIERS = [
    ("Political power gain", "political_power_factor", [("Factor (-1..1)", "0.1")], "political_power_factor = {0}"),
    ("Stability", "stability_factor", [("Factor (-1..1)", "0.05")], "stability_factor = {0}"),
    ("War support", "war_support_factor", [("Factor (-1..1)", "0.05")], "war_support_factor = {0}"),
    ("Construction speed", "production_speed_buildings_factor", [("Factor", "0.1")],
     "production_speed_buildings_factor = {0}"),
    ("Factory output", "industrial_capacity_factory", [("Factor", "0.1")], "industrial_capacity_factory = {0}"),
    ("Dockyard output", "industrial_capacity_dockyard", [("Factor", "0.1")], "industrial_capacity_dockyard = {0}"),
    ("Consumer goods", "consumer_goods_factor", [("Factor (-1..1)", "-0.05")], "consumer_goods_factor = {0}"),
    ("Recruitable population", "conscription_factor", [("Factor", "0.05")], "conscription_factor = {0}"),
    ("Army attack", "army_attack_factor", [("Factor", "0.05")], "army_attack_factor = {0}"),
    ("Army defence", "army_defence_factor", [("Factor", "0.05")], "army_defence_factor = {0}"),
    ("Division training time", "training_time_army_factor", [("Factor", "-0.1")], "training_time_army_factor = {0}"),
    ("Research speed", "research_speed_factor", [("Factor", "0.05")], "research_speed_factor = {0}"),
    ("Division organisation", "army_org_factor", [("Factor", "0.05")], "army_org_factor = {0}"),
    ("Justify war goal time", "justify_war_goal_time", [("Factor", "-0.25")], "justify_war_goal_time = {0}"),
]

CATALOGS = {"effect": EFFECTS, "trigger": TRIGGERS, "modifier": MODIFIERS}


class EffectWizard(tk.Toplevel):
    """Build script lines; on OK they are appended to `target_text`."""

    def __init__(self, master, target_text, kind="effect"):
        super().__init__(master)
        self.title({"effect": "Effect wizard", "trigger": "Trigger wizard", "modifier": "Modifier wizard"}[kind])
        self.resizable(False, False)
        self.target_text = target_text
        self.catalog = CATALOGS[kind]
        self.param_vars = []
        self._build(kind)
        self.grab_set()

    def _build(self, kind):
        left = ttk.Frame(self, padding=10)
        left.grid(row=0, column=0, sticky="n")

        ttk.Label(left, text="Pick what you want to happen:" if kind == "effect"
                  else "Pick a condition:" if kind == "trigger" else "Pick a bonus/penalty:").pack(anchor="w")
        self.listbox = tk.Listbox(left, height=16, width=34, exportselection=False)
        for label, *_ in self.catalog:
            self.listbox.insert("end", " " + label)
        self.listbox.pack(pady=4)
        self.listbox.bind("<<ListboxSelect>>", lambda e: self._on_pick())

        right = ttk.Frame(self, padding=10)
        right.grid(row=0, column=1, sticky="n")

        self.params_frame = ttk.Frame(right)
        self.params_frame.pack(anchor="w")
        ttk.Button(right, text="Add ↓", command=self._add_line).pack(anchor="w", pady=6)

        ttk.Label(right, text="Script being built:").pack(anchor="w")
        self.out = tk.Text(right, width=46, height=12)
        self.out.pack(pady=4)

        btns = ttk.Frame(right)
        btns.pack(pady=6)
        ttk.Button(btns, text="Insert into form", style="Accent.TButton", command=self._insert).pack(side="left", padx=4)
        ttk.Button(btns, text="Cancel", command=self.destroy).pack(side="left", padx=4)

        self.listbox.selection_set(0)
        self._on_pick()

    def _on_pick(self):
        for child in self.params_frame.winfo_children():
            child.destroy()
        self.param_vars = []
        sel = self.listbox.curselection()
        if not sel:
            return
        _, _, params, _ = self.catalog[sel[0]]
        if not params:
            ttk.Label(self.params_frame, text="(no values needed)", style="Muted.TLabel").grid(row=0, column=0, sticky="w")
        for i, (label, placeholder) in enumerate(params):
            ttk.Label(self.params_frame, text=label).grid(row=i, column=0, sticky="w", pady=2)
            var = tk.StringVar(value=placeholder)
            ttk.Entry(self.params_frame, textvariable=var, width=22).grid(row=i, column=1, padx=6, pady=2)
            self.param_vars.append(var)

    def _add_line(self):
        sel = self.listbox.curselection()
        if not sel:
            return
        _, _, params, template = self.catalog[sel[0]]
        values = [v.get().strip() for v in self.param_vars]
        if any(not v for v in values):
            messagebox.showerror("Missing value", "Fill in every field first.", parent=self)
            return
        line = template.format(*values)
        current = self.out.get("1.0", "end").strip()
        self.out.delete("1.0", "end")
        self.out.insert("1.0", (current + "\n" + line).strip())

    def _insert(self):
        built = self.out.get("1.0", "end").strip()
        if not built:
            self.destroy()
            return
        existing = self.target_text.get("1.0", "end").strip()
        self.target_text.delete("1.0", "end")
        self.target_text.insert("1.0", (existing + "\n" + built).strip() if existing else built)
        self.destroy()


def add_wizard_button(parent_frame, text_widget, kind="effect"):
    """Drop a small 'Wizard...' button into an existing dialog row."""
    ttk.Button(
        parent_frame, text="Wizard...",
        command=lambda: EffectWizard(parent_frame.winfo_toplevel(), text_widget, kind),
    ).pack(side="left", padx=4)
