"""Rank the qualified targets, and say in plain words why each ranks where it does."""

"""
Review volume                25
Operator size                15
POS confidence               25
Sales availability           20
Named contact                10
Rating                        5
                           ----
TOTAL                       100

"""

import pandas as pd

from verano.diagnose import REACHED
from verano.pos import SOURCE_RANK

# Points out of 100. Volume and operator size are what the account is worth;
# confidence and runway are how likely a rep is to land it.
VOLUME = [(1500, 25), (1000, 19), (500, 13), (200, 7), (0, 3)]
OPERATOR = {"large": 15, "mid-cap": 10, "SME": 5}
RATING = [(4.5, 5), (4.0, 3), (0, 0)]
CONTACT = 10

# Same order the pipeline used to pick the POS, so the thing that decided the
# verdict is the thing that scores our confidence in it.
CONFIDENCE = {source: 5 * rank for rank, source in enumerate(SOURCE_RANK, start=1)}

EXPORT_COLUMNS = [
    "rank", "score", "name", "phone", "area", "address", "cuisine", "price_band",
    "chain_size", "rating", "review_count", "pos", "pos_source", "pos_seen",
    "status", "days_idle", "owners", "contact", "contact_role", "website", "reason",
]


def band(value, table):
    """Points for the first threshold this value clears."""
    for threshold, points in table:
        if value >= threshold:
            return points
    return 0


def runway_points(status, days_idle):
    """How much room a rep has here without colliding with a colleague."""
    if status == "never in CRM":
        return 20, "never contacted"
    if status == "written off":
        return 15, "written off under the old POS rules"
    if pd.notna(days_idle) and days_idle >= 30:
        return 10, f"deal idle {int(days_idle)} days"
    return 0, "a rep is working it now"


def named_contacts(calls):
    """The last person a call actually got the name of, per restaurant."""
    named = calls.dropna(subset=["poc_name"]).sort_values("call_date")
    return named.groupby("restaurant_id").agg(
        contact=("poc_name", "last"), contact_role=("poc_role", "last")
    )


def score_one(row):
    """(points, reason) for a single restaurant."""
    points, why = 0, []

    reviews = 0 if pd.isna(row["review_count"]) else int(row["review_count"])
    points += band(reviews, VOLUME)
    why.append(f"{reviews:,} reviews")

    points += OPERATOR.get(row["chain_size"], 0)
    if row["chain_size"] in ("mid-cap", "large"):
        why.append(f"{row['chain_size']} operator")

    points += CONFIDENCE.get(row["pos_source"], 0)
    why.append(f"{row['pos']} per {row['pos_source']} on {row['pos_seen']}")

    earned, phrase = runway_points(row["status"], row["days_idle"])
    points += earned
    why.append(phrase)

    if pd.notna(row["contact"]):
        points += CONTACT
        why.append(f"{row['contact']} ({row['contact_role']}) on file")

    rating = 0 if pd.isna(row["rating"]) else row["rating"]
    points += band(rating, RATING)
    if rating >= 4.5:
        why.append(f"rated {rating}")

    return points, " · ".join(why)


def phone_display(restaurant_id):
    """The id is the normalised phone. Give reps something dialable."""
    return f"({restaurant_id[:3]}) {restaurant_id[3:6]}-{restaurant_id[6:]}"


def rank_targets(restaurants, calls):
    """The qualified targets, best first, each with its score and reason."""
    targets = restaurants[restaurants["qualified"]].join(named_contacts(calls))
    scored = pd.DataFrame(
        [score_one(row) for _, row in targets.iterrows()],
        columns=["score", "reason"],
        index=targets.index,
    )

    out = targets.join(scored).sort_values(["score", "review_count"], ascending=False)
    out["rank"] = range(1, len(out) + 1)
    out["phone"] = [phone_display(i) for i in out.index]
    return out[EXPORT_COLUMNS]


def research_lane(has_website, reached, called):
    """The cheapest way left to get this restaurant's POS answer."""
    if has_website:
        return "desk"
    if called and not reached:
        return "visit"
    return "call"


def research_queue(restaurants, calls):
    """The restaurants we cannot qualify yet, biggest first.

    Ranked on review count alone: until someone finds out what POS they run,
    size is the only thing we know that predicts whether the answer matters.
    """
    unknown = restaurants[restaurants["blocker"] == "POS not known yet"].copy()
    reached = calls.groupby("restaurant_id")["outcome"].apply(lambda o: o.isin(REACHED).any())

    unknown["phone"] = [phone_display(i) for i in unknown.index]
    unknown["lane"] = [
        research_lane(pd.notna(site), bool(reached.get(i, False)), i in reached.index)
        for i, site in zip(unknown.index, unknown["website"])
    ]
    # Someone had these on the phone and the POS question never got answered.
    # That is a call script to fix, not research to buy.
    unknown["already_reached"] = [bool(reached.get(i, False)) for i in unknown.index]

    columns = ["lane", "already_reached", "name", "phone", "area", "address", "cuisine",
               "chain_size", "rating", "review_count", "status", "website"]
    return unknown.sort_values("review_count", ascending=False)[columns]
