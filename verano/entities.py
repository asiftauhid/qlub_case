"""Turn platform listings into one row per restaurant."""

import pandas as pd

from verano.clean import name_key, phone_key
from verano.load import MARKET


def add_keys(scraped):
    """Attach the keys we resolve identity with.

    The phone is the id: it is the only field the scrape, the call log and the
    CRM all carry, and no two restaurants in the pool share one.
    """
    rows = scraped.copy()
    rows["restaurant_id"] = rows["phone"].map(phone_key)
    rows["name_key"] = rows["name"].map(name_key)
    rows["area"] = rows["neighbourhood"].fillna("unknown")
    return rows


def link_by_phone(frame, phone_column):
    """Attach restaurant_id to the call log or the CRM, which only have a phone."""
    return frame.assign(restaurant_id=frame[phone_column].map(phone_key))


def fill_missing_ids(rows):
    """Give phone-less listings the id of their name+area twin.

    Every phone-less listing in the pool is a restaurant that another platform
    did publish a phone for, so name+area finds it instead of us inventing a
    second record for the same place.
    """
    known = rows.dropna(subset=["restaurant_id"]).drop_duplicates(["name_key", "area"])
    lookup = dict(zip(zip(known["name_key"], known["area"]), known["restaurant_id"]))
    guessed = [lookup.get(key) for key in zip(rows["name_key"], rows["area"])]
    return rows.assign(restaurant_id=rows["restaurant_id"].fillna(pd.Series(guessed, index=rows.index)))


def collapse(rows):
    """One row per restaurant, built from all the platforms that list it."""
    rows = rows.copy()
    rows["rating"] = pd.to_numeric(rows["rating"], errors="coerce")
    rows["review_count"] = pd.to_numeric(rows["review_count"], errors="coerce")

    # "first" skips nulls, so a field missing on one platform is filled by another.
    return rows.groupby("restaurant_id").agg(
        name=("name", "first"),
        area=("area", "first"),
        address=("address", "first"),
        cuisine=("cuisine", "first"),
        price_band=("price_band", "first"),
        chain_size=("chain_size_bucket", "first"),
        restaurant_group=("restaurant_group", "first"),
        website=("website", "first"),
        rating=("rating", "mean"),
        review_count=("review_count", "max"),
        platforms=("source_platform", "nunique"),
    ).round({"rating": 2})


def build_restaurants(scraped):
    """Returns (listings kept, restaurants, waterfall of what left at each step)."""
    steps = []

    def note(step, count):
        steps.append({"step": step, "rows": count})

    rows = add_keys(scraped)
    note("scraped listings", len(rows))

    rows = rows[rows["city"] == MARKET]
    note(f"in {MARKET}", len(rows))

    rows = rows[rows["fullservice_llm_filter"] == "pass"]
    note("full-service", len(rows))

    rows = fill_missing_ids(rows)
    rows = rows[rows["restaurant_id"].notna()]
    note("identifiable", len(rows))

    restaurants = collapse(rows)
    note("distinct restaurants", len(restaurants))

    waterfall = pd.DataFrame(steps)
    waterfall["dropped"] = -waterfall["rows"].diff().fillna(0).astype(int)
    return rows, restaurants, waterfall
