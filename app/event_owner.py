"""Work out which country an event actually belongs to.

An event definition doesn't declare an owner. Only a minority gate
themselves with `trigger = { tag = TUR }`; the great majority are
`is_triggered_only` and get fired from a focus, a decision, or another
event. So ownership is inferred from three signals, strongest first:

1. tags named in the event's own trigger
2. tags of whatever fires it - a focus tree carries country tags, a
   decision carries `original_tag`, and firing chains propagate
3. the country prefix convention on the firing focus/decision id

This is inference, not ground truth: an event nothing references, or one
fired from generic shared script, ends up with no country. The UI labels
those "(unknown)" rather than guessing.
"""

import os
import re
from collections import defaultdict

from app import mod_loader as ml
from app import pds_scan as scan

TAG_RE = re.compile(r"\b(?:original_)?tag\s*=\s*([A-Z]{3})\b")
EVENT_REF_RE = re.compile(r"\bid\s*=\s*([A-Za-z_][A-Za-z0-9_]*\.\d+)")
ID_PREFIX_RE = re.compile(r"^([A-Z]{3})_")

PROPAGATION_PASSES = 3


def _tags_from_text(text):
    return set(TAG_RE.findall(text or ""))


def _refs_in(text):
    return set(EVENT_REF_RE.findall(text or ""))


def build_ownership(mod_root, progress=None):
    """Return {event_id: set(country tags)} for the whole mod."""
    owners = defaultdict(set)
    # who fires what, so ownership can flow along the chain
    fires = defaultdict(set)

    # --- focus trees -------------------------------------------------
    if progress:
        progress("Scanning focus trees...")
    for path in ml.find_focus_tree_files(mod_root):
        for tree in ml.parse_focus_trees(path):
            tree_tags = set(tree["country_tags"])
            for focus in tree["focuses"]:
                tags = set(tree_tags)
                prefix = ID_PREFIX_RE.match(focus["id"])
                if prefix:
                    tags.add(prefix.group(1))
                body = " ".join([
                    focus.get("completion_reward_raw", ""),
                    focus.get("select_effect_raw", ""),
                    focus.get("available_raw", ""),
                ])
                for ref in _refs_in(body):
                    owners[ref] |= tags

    # --- decisions ---------------------------------------------------
    if progress:
        progress("Scanning decisions...")
    for path in ml.find_decision_files(mod_root):
        for category in ml.parse_decisions(path):
            for decision in category["decisions"]:
                tags = _tags_from_text(decision.get("allowed", ""))
                tags |= _tags_from_text(decision.get("visible", ""))
                prefix = ID_PREFIX_RE.match(decision["id"])
                if prefix:
                    tags.add(prefix.group(1))
                body = " ".join([decision.get("effect", ""), decision.get("available", "")])
                for ref in _refs_in(body):
                    owners[ref] |= tags

    # --- events: own triggers, plus what each one fires ---------------
    if progress:
        progress("Scanning events...")
    all_ids = set()
    for path in ml.find_event_files(mod_root):
        try:
            _, events = ml.parse_events(path)
        except OSError:
            continue
        for e in events:
            eid = f"{e['namespace']}.{e['number']}"
            all_ids.add(eid)

            own = _tags_from_text(e.get("trigger", ""))
            if own:
                owners[eid] |= own

            body = " ".join(
                [e.get("immediate", "")] + [o.get("effect", "") for o in e["options"]]
            )
            for ref in _refs_in(body):
                if ref != eid:
                    fires[eid].add(ref)

    # --- propagate along firing chains -------------------------------
    for _ in range(PROPAGATION_PASSES):
        changed = False
        for source, targets in fires.items():
            tags = owners.get(source)
            if not tags:
                continue
            for target in targets:
                before = len(owners[target])
                owners[target] |= tags
                if len(owners[target]) != before:
                    changed = True
        if not changed:
            break

    for eid in all_ids:
        owners.setdefault(eid, set())

    return dict(owners)


def summarise(owners):
    counts = defaultdict(int)
    unknown = 0
    for tags in owners.values():
        if not tags:
            unknown += 1
        for tag in tags:
            counts[tag] += 1
    return dict(counts), unknown
