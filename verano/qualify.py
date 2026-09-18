"""Which restaurants belong on the target list, and why the rest don't."""

import pandas as pd

from verano.load import AS_OF

# Dead ends rank below the live stages, so a restaurant carrying one dead deal
# and one live deal is judged on the live one.
STAGES = [
    "Not Qualified",
    "Closed Lost",
    "Eligible",
    "Walked-in",
    "Gatekeeper Demo",
    "KDM Demo",
    "Verbal Yes",
    "Closed Won",
]
DEAD_ENDS = ("Not Qualified", "Closed Lost")

# Each gate, and the label for what survives it. Ineligible goes first because
# it is a fact; not-known-yet is only a gap in our research.
GATES = [
    ("POS not ruled out", "POS we cannot integrate with"),
    ("POS confirmed eligible", "POS not known yet"),
    ("not already a customer", "already a customer"),
]


def deal_history(crm):
    """One row per restaurant the CRM holds a deal for."""
    deals = crm.dropna(subset=["restaurant_id"]).copy()
    deals["stage"] = pd.Categorical(deals["deal_stage"], STAGES, ordered=True)
    deals["activity"] = pd.to_datetime(deals["last_activity_date"], errors="coerce")

    history = deals.groupby("restaurant_id").agg(
        deals=("deal_id", "size"),
        owners=("deal_owner", "nunique"),
        stage=("stage", "max"),
        last_activity=("activity", "max"),
    )
    history["days_idle"] = (AS_OF - history["last_activity"]).dt.days
    return history


def status_of(stage):
    """What the furthest stage a restaurant reached means for us now."""
    if pd.isna(stage):
        return "never in CRM"
    if stage == "Closed Won":
        return "customer"
    if stage in DEAD_ENDS:
        return "written off"
    return "open deal"


def blocker_of(verdict, status):
    """Why this restaurant is not a target, or None if it is one.

    Written off is deliberately not a blocker. A rep binning a restaurant is an
    opinion; the POS rules are the fact, and they changed on 2026-06-22.
    """
    if verdict == "ineligible":
        return "POS we cannot integrate with"
    if verdict in ("unknown", "ambiguous"):
        return "POS not known yet"
    if status == "customer":
        return "already a customer"
    return None


def qualify(restaurants, crm):
    """Attach CRM context and the pass/fail decision to every restaurant."""
    out = restaurants.join(deal_history(crm))
    out["status"] = out["stage"].astype(object).map(status_of)
    out["blocker"] = [blocker_of(v, s) for v, s in zip(out["verdict"], out["status"])]
    out["qualified"] = out["blocker"].isna()
    return out


def qualification_waterfall(restaurants):
    """Restaurant-level accounting: what each gate removes."""
    steps = [{"step": "distinct restaurants", "rows": len(restaurants)}]
    left = restaurants
    for label, blocker in GATES:
        left = left[left["blocker"] != blocker]
        steps.append({"step": label, "rows": len(left)})

    waterfall = pd.DataFrame(steps)
    waterfall["dropped"] = -waterfall["rows"].diff().fillna(0).astype(int)
    return waterfall
