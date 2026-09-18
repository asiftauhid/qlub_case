"""What is wrong with the pipeline as it runs today, in numbers.

Every finding here is a count over a stated denominator, so a reader can check
any one of them against the raw extracts by hand.
"""

import pandas as pd

from verano.load import AS_OF

# Outcomes that mean a person actually spoke to us.
REACHED = ("POS Validated", "Callback", "Gatekeeper", "Data capture incomplete")


def _row(finding, count, of=None):
    share = f"{100 * count / of:.0f}%" if of else ""
    return {"finding": finding, "count": int(count), "of": of or "", "share": share}


def crm_findings(restaurants, crm):
    """How the deals that exist are being run."""
    deals = crm.dropna(subset=["restaurant_id"])
    idle = (AS_OF - pd.to_datetime(deals["last_activity_date"], errors="coerce")).dt.days
    verdict = deals["restaurant_id"].map(restaurants["verdict"])
    per_restaurant = deals.groupby("restaurant_id").agg(
        deals=("deal_id", "size"), owners=("deal_owner", "nunique")
    )
    n, r = len(deals), len(per_restaurant)

    return pd.DataFrame([
        _row("deals parked in the entry stage", (deals["deal_stage"] == "Eligible").sum(), n),
        _row("deals nobody has touched for 30+ days", (idle >= 30).sum(), n),
        _row("median days since anyone touched a deal", idle.median()),
        _row("deals on a POS we cannot integrate with", (verdict == "ineligible").sum(), n),
        _row("deals with no POS recorded anywhere", (verdict == "unknown").sum(), n),
        _row("restaurants carrying more than one deal", (per_restaurant["deals"] > 1).sum(), r),
        _row("restaurants whose deals sit with two or more owners", (per_restaurant["owners"] > 1).sum(), r),
    ])


def call_findings(calls, restaurants):
    """What the dialler and the calling team spent their attempts on."""
    n = len(calls)
    dated = calls.assign(date=pd.to_datetime(calls["call_date"], errors="coerce"))

    # The full-service filter ran before the calls did, so these were avoidable.
    off_target = ~dated["restaurant_id"].isin(restaurants.index)

    validated_on = dated.loc[dated["outcome"] == "POS Validated"].groupby("restaurant_id")["date"].min()
    after_validation = dated["date"] > dated["restaurant_id"].map(validated_on)

    ever_reached = dated.groupby("restaurant_id")["outcome"].apply(lambda o: o.isin(REACHED).any())
    never_reached = ~dated["restaurant_id"].map(ever_reached).fillna(False)

    return pd.DataFrame([
        _row("calls to venues the full-service filter had already rejected", off_target.sum(), n),
        _row("calls placed after that restaurant's POS was already validated", after_validation.sum(), n),
        _row("avoidable calls, counting each call once", (off_target | after_validation).sum(), n),
        _row("calls spent on restaurants nobody ever reached", never_reached.sum(), n),
    ])


def stale_rule_findings(listings, restaurants):
    """The cost of trusting a verdict cached before the 2026-06-22 rule change."""
    cached_pass = listings.loc[listings["pos_eligibility"] == "pass", "restaurant_id"].nunique()
    eligible = (restaurants["verdict"] == "eligible").sum()
    written_off = restaurants.query("status == 'written off' and qualified")

    return pd.DataFrame([
        _row("targets found by trusting the scrape's cached column", cached_pass, eligible),
        _row("targets found by recomputing from config/rules.yml", eligible, eligible),
        _row("restaurants a rep wrote off that run an eligible POS", len(written_off)),
        _row("of those, running Cadence, eligible since 2026-06-22",
             (written_off["pos"] == "Cadence").sum(), len(written_off)),
    ])


def constraint_findings(restaurants):
    """Is the team short of leads, or short of follow-through?"""
    targets = restaurants[restaurants["qualified"]]
    idle_targets = targets.query("status == 'open deal' and days_idle >= 30")
    n = len(targets)

    # Of the restaurants whose POS anyone has ever recorded, this share was
    # eligible. Applied to the unresearched pool it is an estimate, not a count:
    # a restaurant nobody could reach may well differ from one they could.
    decided = restaurants["verdict"].isin(["eligible", "ineligible"])
    hit_rate = (restaurants["verdict"] == "eligible").sum() / decided.sum()
    unresearched = (restaurants["blocker"] == "POS not known yet").sum()

    return pd.DataFrame([
        _row("qualified targets available today", n, n),
        _row("of those, never entered the CRM", (targets["status"] == "never in CRM").sum(), n),
        _row("of those, owned by a rep but idle 30+ days", len(idle_targets), n),
        _row("restaurants still unresearched", unresearched),
        _row("further targets research would likely find", round(unresearched * hit_rate)),
    ])


def report(parts):
    """Every finding in one table, ready to print or paste into the deck."""
    restaurants, listings = parts["restaurants"], parts["listings"]
    sections = {
        "CRM": crm_findings(restaurants, parts["crm"]),
        "calling": call_findings(parts["calls"], restaurants),
        "stale rules": stale_rule_findings(listings, restaurants),
        "constraint": constraint_findings(restaurants),
    }
    return pd.concat(
        [frame.assign(area=name) for name, frame in sections.items()], ignore_index=True
    )[["area", "finding", "count", "of", "share"]]
