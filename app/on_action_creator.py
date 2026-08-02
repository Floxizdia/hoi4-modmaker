"""On_actions: script hooks the game fires itself (a war is declared, a
country capitulates, a peace conference starts...). Unlike most common/
files, on_actions from different files are additive - the game runs every
mod's `on_x = { effect = {...} }` for that hook rather than the last one
loaded winning - so a new file here is always safe to add alongside
whatever the base game or another mod already hooked.
"""

import os

from app import pds_scan as scan
from app.map_data import BASE_GAME

ON_ACTIONS_DIR = os.path.join("common", "on_actions")
FILENAME = "zzz_custom_on_actions.txt"

# From common/on_actions/_documentation.md's "List of possible on-actions"
# (as of the game version this was checked against).
ON_ACTION_TOKENS = [
    "on_startup", "on_daily", "on_daily_TAG", "on_weekly", "on_weekly_TAG",
    "on_monthly", "on_monthly_TAG", "on_nuke_drop", "on_pride_of_the_fleet_sunk",
    "on_naval_invasion", "on_paradrop",
    "on_coup_succeeded", "on_government_change", "on_ruling_party_change",
    "on_new_term_election", "on_before_peace_conference_start",
    "on_peaceconference_started", "on_peaceconference_ended",
    "on_send_volunteers", "on_recall_volunteers", "on_border_war_lost",
    "on_war_relation_added", "on_declare_war", "on_war", "on_peace",
    "on_capitulation", "on_capitulation_immediate", "on_uncapitulation", "on_annex",
    "on_civil_war_end_before_annexation", "on_civil_war_end", "on_puppet",
    "on_force_government", "on_liberate", "on_release_as_free", "on_release_as_puppet",
    "on_create_faction", "on_faction_formed", "on_offer_join_faction", "on_join_faction",
    "on_assume_faction_leadership", "on_leave_faction",
    "on_subject_annexed", "on_subject_free", "on_subject_autonomy_level_change",
    "on_government_exiled", "on_host_changed_from_capitulation", "on_exile_government_reinstated",
    "on_state_control_changed",
    "on_justifying_wargoal_pulse", "on_wargoal_expire",
    "on_unit_leader_created", "on_army_leader_daily", "on_army_leader_won_combat",
    "on_army_leader_lost_combat", "on_unit_leader_level_up", "on_army_leader_promoted",
    "on_deployed_leader_defeated",
    "on_ace_promoted", "on_ace_killed", "on_ace_killed_on_accident",
    "on_non_ace_killed_other_ace", "on_ace_killed_by_ace", "on_ace_killed_other_ace",
    "on_aces_killed_each_other",
    "on_operation_completed", "on_operative_detected_during_operation",
    "on_operative_on_mission_spotted", "on_operative_captured", "on_operative_created",
    "on_operative_death", "on_operative_recruited", "on_fully_decrypted_cipher",
    "on_activated_active_decryption_bonuses",
]


def list_hooks_used(mod_root):
    """{on_action_key: [source, ...]} - which hooks already have at least
    one effect block somewhere, base game or mod (informational only, since
    adding another one never overwrites the existing ones)."""
    out = {}
    for root, source in ((BASE_GAME, "vanilla"), (mod_root, "mod")):
        folder = os.path.join(root, ON_ACTIONS_DIR)
        if not os.path.isdir(folder):
            continue
        for name in sorted(os.listdir(folder)):
            if not name.endswith(".txt"):
                continue
            try:
                with open(os.path.join(folder, name), "r", encoding="utf-8-sig", errors="ignore") as f:
                    text = scan.strip_comments(f.read())
            except OSError:
                continue
            outer = scan.first_block(text, "on_actions")
            if outer is None:
                continue
            for key, _ in scan.iter_named_blocks(outer):
                out.setdefault(key, []).append(source)
    return out


def create_hook(mod_root, *, on_action_key, effect_raw, random_chance=None):
    """`random_chance` (0-100) wraps the effect in `random_list` if given -
    None means always run. Returns the file written (appended if it
    already exists in the mod)."""
    def indent(raw, depth=3):
        pad = "\t" * depth
        return "\n".join(pad + line.strip() for line in raw.strip().splitlines() if line.strip())

    if random_chance is not None:
        body = (
            "\t\trandom_list = {\n"
            f"\t\t\t{int(random_chance)} = {{\n{indent(effect_raw, 4)}\n\t\t\t}}\n"
            f"\t\t\t{100 - int(random_chance)} = {{\n\t\t\t}}\n"
            "\t\t}\n"
        )
    else:
        body = indent(effect_raw) + "\n"

    entry = f"\t{on_action_key} = {{\n\t\teffect = {{\n{body}\t\t}}\n\t}}\n"

    folder = os.path.join(mod_root, ON_ACTIONS_DIR)
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, FILENAME)
    if os.path.isfile(path):
        with open(path, "r", encoding="utf-8-sig", errors="ignore") as f:
            existing = f.read().rstrip()
        if existing.endswith("}"):
            content = existing[:-1].rstrip("\n") + "\n" + entry + "}\n"
        else:
            content = existing + "\n\n" + f"on_actions = {{\n{entry}}}\n"
    else:
        content = f"on_actions = {{\n{entry}}}\n"

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return path
