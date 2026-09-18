"""Which POS each restaurant runs, and whether we can integrate with it."""

import pandas as pd

from verano.clean import pos_key

# Weakest evidence first, so the last row per restaurant is the one to trust.
# Someone who phoned and asked beats a website scan.
SOURCE_RANK = ["website", "crm notes", "crm field", "ai call", "human call"]


def read_pos(value, rules):
    """(vendor, verdict) for one raw POS string.

    A string the rules don't list is unknown, never ineligible: "-", "not found"
    and a blank cell are missing data, not a reason to discard a restaurant.
    """
    return rules.get(pos_key(value), (None, "unknown"))


def first_field(note):
    """The POS out of a note like "vellum pos, Raj Patel (Owner), 1 location".

    126 deals have an empty pos_from_crm but name the POS in the notes. The
    notes are comma-separated and the POS is always first, so this stays an
    exact lookup rather than a search for vendor names in free text.
    """
    return str(note).split(",")[0]


def collect_mentions(listings, calls, crm, rules):
    """Every POS any system named, one row per mention."""
    crm = crm.assign(pos_in_notes=crm["deal_description"].map(first_field))
    mentions = pd.concat(
        [
            _shape(listings, "pos_system", "scraped_date", "website"),
            _shape(calls, "pos_captured", "call_date",
                   calls["caller_type"].map({"human": "human call", "ai": "ai call"})),
            _shape(crm, "pos_from_crm", "last_activity_date", "crm field"),
            _shape(crm, "pos_in_notes", "last_activity_date", "crm notes"),
        ],
        ignore_index=True,
    )

    looked_up = mentions["pos_raw"].map(lambda value: read_pos(value, rules))
    mentions["pos"] = looked_up.str[0]
    mentions["verdict"] = looked_up.str[1]
    return mentions[mentions["pos"].notna() & mentions["restaurant_id"].notna()]


def _shape(frame, pos_column, date_column, source):
    return pd.DataFrame(
        {
            "restaurant_id": frame["restaurant_id"],
            "pos_raw": frame[pos_column],
            "source": source,
            "seen": frame[date_column],
        }
    )


def best_pos(mentions):
    """One POS per restaurant: specific reading first, then best source, then most recent.

    Specific comes before source because a bare "Meridian" is not evidence
    against a "Meridian Server" heard elsewhere, it is the same answer with less
    detail. Ambiguous only survives when nothing better was ever recorded, which
    is exactly when the restaurant should go to research.
    """
    ranked = mentions.assign(
        specific=mentions["verdict"] != "ambiguous",
        rank=pd.Categorical(mentions["source"], SOURCE_RANK, ordered=True),
    )
    ranked = ranked.sort_values(["specific", "rank", "seen"])
    winner = ranked.groupby("restaurant_id").tail(1).set_index("restaurant_id")
    return winner[["pos", "verdict", "source", "seen"]].rename(
        columns={"source": "pos_source", "seen": "pos_seen"}
    )
