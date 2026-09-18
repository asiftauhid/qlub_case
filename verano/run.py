"""The pipeline. Run with: python -m verano.run"""

import pandas as pd

from verano.diagnose import report
from verano.entities import build_restaurants, link_by_phone
from verano.load import OUTPUT, TOP_N, load_pos_rules, load_raw
from verano.pos import best_pos, collect_mentions
from verano.qualify import qualify, qualification_waterfall
from verano.score import rank_targets, research_queue


def build():
    """Everything the report and the target list are built from."""
    scraped, calls, crm = load_raw()
    rules = load_pos_rules()

    listings, restaurants, listing_waterfall = build_restaurants(scraped)
    calls = link_by_phone(calls, "phone")
    crm = link_by_phone(crm, "company_phone")

    mentions = collect_mentions(listings, calls, crm, rules)
    restaurants = restaurants.join(best_pos(mentions))
    restaurants["verdict"] = restaurants["verdict"].fillna("unknown")
    restaurants = qualify(restaurants, crm)

    waterfall = pd.concat(
        [
            listing_waterfall.assign(counting="platform listings"),
            qualification_waterfall(restaurants).assign(counting="restaurants"),
        ],
        ignore_index=True,
    )

    parts = {
        "listings": listings,
        "restaurants": restaurants,
        "waterfall": waterfall,
        "mentions": mentions,
        "calls": calls,
        "crm": crm,
        "targets": rank_targets(restaurants, calls),
        "research": research_queue(restaurants, calls),
    }
    parts["findings"] = report(parts)
    return parts


def main():
    parts = build()

    # The restaurant lists are keyed on restaurant_id, the two reports are not.
    # qualified_targets is what a rep gets handed; the all_ file is the full
    # working list behind it, so any cut of the top 50 can be checked.
    outputs = [
        ("waterfall", parts["waterfall"], False),
        ("findings", parts["findings"], False),
        ("all_qualified_targets", parts["targets"], True),
        ("qualified_targets", parts["targets"].head(TOP_N), True),
        ("research_queue", parts["research"], True),
    ]

    OUTPUT.mkdir(exist_ok=True)
    for name, frame, keep_index in outputs:
        frame.to_csv(OUTPUT / f"{name}.csv", index=keep_index)
        print(f"wrote {name}.csv  ({len(frame)} rows)")

    print()
    print(parts["waterfall"].to_string(index=False))

    print(f"\n{len(parts['targets'])} qualified targets, by where the CRM left them:")
    print(parts["targets"]["status"].value_counts().to_string())

    print("\ntop 10:")
    top = parts["targets"].head(10)
    print(top[["rank", "score", "name", "area", "pos", "status"]].to_string(index=False))
    print("\nwhy number one:")
    print(f"  {top.iloc[0]['name']} — {top.iloc[0]['reason']}")

    print()
    print(parts["findings"].to_string(index=False))


if __name__ == "__main__":
    main()
