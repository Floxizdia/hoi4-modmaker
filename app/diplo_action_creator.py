"""Diplomatic actions: custom entries in the diplomacy menu (beyond the
game's built-in guarantee/alliance/etc) - written to
common/scripted_diplomatic_actions/. The base game's own file for this is
entirely commented-out documentation (no vanilla mod actually ships one),
so this mirrors that template directly rather than a real example.
"""

import os

from app import loc_surgery

ACTION_DIR = os.path.join("common", "scripted_diplomatic_actions")
FILENAME = "zzz_custom_diplomatic_actions.txt"


def create_action(mod_root, *, action_id, display_name, cost=10, command_power=0,
                   requires_acceptance=True, icon=1,
                   allowed_raw="always = yes", visible_raw="always = yes",
                   selectable_raw="always = yes",
                   on_sent_effect_raw="", complete_effect_raw="", reject_effect_raw="",
                   send_description="", accept_feedback="", reject_feedback="",
                   ai_acceptance_raw="base = 100", ai_desire_raw="base = 0"):
    """Returns the files written. Loc keys are all derived from
    `action_id` so nothing needs typing twice."""
    def indent(raw, depth=2):
        pad = "\t" * depth
        return "\n".join(pad + line.strip() for line in raw.strip().splitlines() if line.strip())

    send_key = f"{action_id}_send_desc"
    accept_key = f"{action_id}_accept_desc"
    reject_key = f"{action_id}_reject_desc"

    parts = [f"{action_id} = {{"]
    parts.append("\tallowed = {\n" + indent(allowed_raw) + "\n\t}")
    parts.append("\tvisible = {\n" + indent(visible_raw) + "\n\t}")
    parts.append("\tselectable = {\n" + indent(selectable_raw) + "\n\t}")
    parts.append(f"\n\trequires_acceptance = {'yes' if requires_acceptance else 'no'}")
    parts.append(f"\tcost = {cost}")
    parts.append(f"\tcommand_power = {command_power}")
    parts.append(f"\ticon = {icon}")
    if on_sent_effect_raw.strip():
        parts.append("\n\ton_sent_effect = {\n" + indent(on_sent_effect_raw) + "\n\t}")
    if complete_effect_raw.strip():
        parts.append("\tcomplete_effect = {\n" + indent(complete_effect_raw) + "\n\t}")
    if reject_effect_raw.strip():
        parts.append("\treject_effect = {\n" + indent(reject_effect_raw) + "\n\t}")
    parts.append(f'\n\tsend_description = {send_key}')
    parts.append(f'\taccept_description = {accept_key}')
    parts.append(f'\treject_description = {reject_key}')
    parts.append("\n\tai_acceptance = {\n\t\tcondition = {\n" + indent(ai_acceptance_raw, 3) + "\n\t\t}\n\t}")
    parts.append("\tai_desire = {\n" + indent(ai_desire_raw) + "\n\t}")
    parts.append("}\n")
    entry_text = "\n".join(parts)

    folder = os.path.join(mod_root, ACTION_DIR)
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, FILENAME)
    if os.path.isfile(path):
        with open(path, "r", encoding="utf-8-sig", errors="ignore") as f:
            existing = f.read().rstrip()
        content = existing + "\n\n" + entry_text
    else:
        content = entry_text
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

    created = [path]
    created.append(loc_surgery.set_key(mod_root, action_id, display_name))
    created.append(loc_surgery.set_key(mod_root, send_key, send_description or f"Send {display_name}?"))
    created.append(loc_surgery.set_key(mod_root, accept_key, accept_feedback or f"{display_name} accepted."))
    created.append(loc_surgery.set_key(mod_root, reject_key, reject_feedback or f"{display_name} rejected."))
    return created
