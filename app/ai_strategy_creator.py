"""AI strategy plans: the `common/ai_strategy/<TAG>.txt` blocks that steer
what a country's AI wants (who to ally, what to build, which fronts to
prioritize). Each block is a trigger-gated container of `ai_strategy = {
type = ... id = ... value = ... }` entries - dozens of possible `type`
tokens, each meaning something different to the AI, so this mirrors the
Traits/Ideology tabs' approach: pick the token from the game's own list,
free-type the id/value since those vary per token.
"""

import os

from app import pds_scan as scan
from app.map_data import BASE_GAME

STRATEGY_DIR = os.path.join("common", "ai_strategy")

# From common/ai_strategy/_documentation.md's "List of available strategy
# tokens" section (as of the game version this was checked against) -
# mods can and do add their own custom tokens read by scripted triggers,
# so this list is a helpful starting point, not a hard whitelist.
STRATEGY_TOKENS = [
    "alliance", "antagonize", "avoid_starting_wars", "asking_foreign_garrison", "befriend",
    "conquer", "consider_weak", "contain", "declare_war", "diplo_action_acceptance",
    "diplo_action_desire", "dont_join_wars_with", "ignore", "ignore_claim", "influence",
    "prepare_for_war", "protect", "send_lend_lease_desire", "send_volunteers_desire", "support",
    "area_priority", "dont_defend_ally_borders", "force_defend_ally_borders",
    "force_concentration_front_factor", "force_concentration_factor",
    "force_concentration_target_weight", "front_armor_score", "front_control",
    "front_unit_request", "garrison", "garrison_reinforcement_priority",
    "ignore_army_incompetence", "invasion_unit_request", "invade", "occupation_policy",
    "put_unit_buffers", "scorched_earth_prio", "spare_unit_factor",
    "theatre_distribution_demand_increase",
    "naval_avoid_region", "naval_convoy_raid_region", "naval_invasion_focus",
    "naval_invasion_dominance_weight", "naval_mission_threshold", "strike_force_home_base",
    "naval_dominance", "convoy_raiding_target",
    "activate_crypto", "agency_ai_base_num_factories_factor",
    "agency_ai_per_upgrade_factories_factor", "decrypt_target",
    "intelligence_agency_branch_desire_factor", "intelligence_agency_usable_factories",
    "operation_equipment_priority", "operative_mission", "operative_operation", "become_spymaster",
    "added_military_to_civilian_factory_ratio", "air_factory_balance", "build_airplane",
    "build_army", "build_building", "build_ship", "building_target",
    "convoy_efficiency_to_cancel_trades", "dockyard_to_military_factory_ratio",
    "equipment_production_factor", "equipment_variant_production_factor",
    "equipment_production_surplus_management", "equipment_production_min_factories",
    "equipment_production_min_factories_archetype", "equipment_stockpile_surplus_ratio",
    "equipment_market_spend_factories", "equipment_market_for_sale_threshold",
    "equipment_market_for_sale_factor", "equipment_market_max_for_sale",
    "equipment_market_min_for_sale", "equipment_market_buying_threshold", "equipment_market_buy",
    "equipment_market_trade_desire", "factory_build_score_factor", "force_build_armies",
    "fuel_buffer", "min_convoy_efficiency_factor_for_war_support_hit",
    "production_upgrade_desire_offset", "railway_gun_divisions_ratio", "research_tech",
    "research_weight_factor", "role_ratio", "save_equipment", "template_prio", "unit_ratio",
    "land_xp_spend_priority", "air_xp_spend_priority", "navy_xp_spend_priority",
    "pp_spend_amount", "pp_spend_priority", "min_wanted_supply_trucks", "wanted_supply_trucks",
    "min_wanted_supply_trains", "wanted_supply_trains", "ai_wanted_divisions_factor",
    "strategic_air_importance", "raid_target_country",
]


def list_strategy_files(mod_root):
    """{tag: source} - one entry per file, since a file is usually named
    after the country tag it targets (not enforced by the game, just
    convention this follows for the "existing" browse list)."""
    out = {}
    for root, source in ((BASE_GAME, "vanilla"), (mod_root, "mod")):
        folder = os.path.join(root, STRATEGY_DIR)
        if not os.path.isdir(folder):
            continue
        for name in sorted(os.listdir(folder)):
            if name.endswith(".txt") and not name.startswith("_"):
                out[name[:-4]] = source
    return out


def list_block_ids(mod_root, tag):
    """The named strategy-container ids already used in <tag>.txt, across
    base game + mod - so a new block picks a non-colliding name."""
    ids = set()
    for root in (BASE_GAME, mod_root):
        path = os.path.join(root, STRATEGY_DIR, f"{tag}.txt")
        if not os.path.isfile(path):
            continue
        try:
            with open(path, "r", encoding="utf-8-sig", errors="ignore") as f:
                text = scan.strip_comments(f.read())
        except OSError:
            continue
        for block_id, _ in scan.iter_named_blocks(text):
            ids.add(block_id)
    return ids


def create_strategy(mod_root, *, tag, block_id, allowed_raw, enable_raw, abort_raw, entries):
    """`entries` is [(type, id, value), ...] - `id` may be blank, `value`
    may be blank (some tokens, e.g. railway_gun_divisions_ratio, only need
    type + value with no id). Appends into <tag>.txt if it already exists
    in the mod, otherwise creates it."""
    def indent(raw, depth=2):
        pad = "\t" * depth
        return "\n".join(pad + line.strip() for line in raw.strip().splitlines() if line.strip())

    strategy_lines = []
    for typ, sid, value in entries:
        inner = [f"\t\ttype = {typ}"]
        if sid:
            inner.append(f"\t\tid = {sid}")
        if value != "":
            inner.append(f"\t\tvalue = {value}")
        strategy_lines.append("\tai_strategy = {\n" + "\n".join(inner) + "\n\t}")

    parts = [f"{block_id} = {{"]
    parts.append("\tallowed = {\n" + (indent(allowed_raw) if allowed_raw.strip()
                                      else f"\t\toriginal_tag = {tag}") + "\n\t}")
    parts.append("\tenable = {\n" + (indent(enable_raw) if enable_raw.strip()
                                     else "\t\talways = yes") + "\n\t}")
    if abort_raw.strip():
        parts.append("\tabort = {\n" + indent(abort_raw) + "\n\t}")
    parts.extend(strategy_lines)
    parts.append("}\n")
    entry_text = "\n".join(parts)

    folder = os.path.join(mod_root, STRATEGY_DIR)
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, f"{tag}.txt")
    if os.path.isfile(path):
        with open(path, "r", encoding="utf-8-sig", errors="ignore") as f:
            existing = f.read().rstrip()
        content = existing + "\n\n" + entry_text
    else:
        content = entry_text
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return path
