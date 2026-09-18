import pandas as pd
import pytest

from verano.clean import name_key, phone_key, pos_key
from verano.diagnose import call_findings, report
from verano.entities import build_restaurants
from verano.load import AS_OF, MARKET, TOP_N, load_pos_rules, load_raw
from verano.run import build
from verano.score import CONFIDENCE, CONTACT, OPERATOR, RATING, VOLUME, runway_points


@pytest.fixture(scope="module")
def pipeline():
    return build()


def test_phone_key_survives_every_format_in_the_data():
    same = ["(555) 173-3531", "555-173-3531", "555.173.3531", "+1 555 173 3531", "5551733531"]
    assert {phone_key(v) for v in same} == {"5551733531"}


def test_phone_key_rejects_what_is_not_a_phone():
    assert phone_key("") is None
    assert phone_key("555-1234") is None
    assert phone_key(None) is None


def test_name_key_ignores_platform_decoration():
    same = ["Basil & Bone Grill", "Basil and Bone Grill", "BASIL & BONE GRILL - Palisade Park"]
    assert {name_key(v) for v in same} == {"basilbonegrill"}
    assert name_key("Tin Roof") != name_key("Tin Roof Kitchen")


def test_no_listing_is_lost_or_duplicated_in_the_waterfall():
    """Every listing is either explained by a filter or folded into a restaurant."""
    scraped, _, _ = load_raw()
    listings, restaurants, waterfall = build_restaurants(scraped)

    assert waterfall.iloc[0]["rows"] == len(scraped)
    assert len(restaurants) == listings["restaurant_id"].nunique()
    assert restaurants.index.is_unique


def test_every_restaurant_is_either_a_target_or_has_a_named_blocker(pipeline):
    """No restaurant may fall out of the list without a reason we can print."""
    restaurants = pipeline["restaurants"]
    assert (restaurants["qualified"] != restaurants["blocker"].notna()).all()


def test_qualification_is_eligible_pos_and_not_already_a_customer(pipeline):
    restaurants = pipeline["restaurants"]
    expected = (restaurants["verdict"] == "eligible") & (restaurants["status"] != "customer")
    assert restaurants["qualified"].equals(expected)


def test_a_rep_writing_a_restaurant_off_does_not_disqualify_it(pipeline):
    """The rules changed on 2026-06-22, so old Not Qualified verdicts are suspect."""
    written_off = pipeline["restaurants"].query("status == 'written off'")
    assert written_off["qualified"].sum() > 0


def test_the_two_halves_of_the_waterfall_meet(pipeline):
    waterfall = pipeline["waterfall"]
    listings = waterfall[waterfall["counting"] == "platform listings"]
    restaurants = waterfall[waterfall["counting"] == "restaurants"]
    assert listings.iloc[-1]["rows"] == restaurants.iloc[0]["rows"]


def test_every_finding_states_a_count(pipeline):
    findings = report(pipeline)
    assert findings["count"].notna().all()
    assert findings["finding"].is_unique


def test_avoidable_calls_are_not_double_counted(pipeline):
    """Two kinds of waste overlap, so the combined figure must be the smaller sum."""
    calls = call_findings(pipeline["calls"], pipeline["restaurants"]).set_index("finding")["count"]
    parts = calls.iloc[0] + calls.iloc[1]
    assert calls["avoidable calls, counting each call once"] <= parts


def test_the_score_cannot_leave_the_hundred_point_scale():
    """Every component's best case must add up to exactly 100, or the score lies."""
    best = max(p for _, p in VOLUME) + max(OPERATOR.values()) + max(CONFIDENCE.values())
    best += max(p for _, p in RATING) + CONTACT + runway_points("never in CRM", None)[0]
    assert best == 100


def test_every_target_is_ranked_and_explained(pipeline):
    targets = pipeline["targets"]
    assert list(targets["rank"]) == list(range(1, len(targets) + 1))
    assert targets["score"].between(0, 100).all()
    assert (targets["reason"].str.len() > 0).all()


def test_a_restaurant_a_rep_is_working_gets_no_runway_credit():
    """Handing a rep a lead their colleague touched last week causes collisions."""
    assert runway_points("open deal", 5)[0] == 0
    assert runway_points("open deal", 90)[0] > 0


def test_the_two_lists_together_account_for_every_unsold_restaurant(pipeline):
    restaurants = pipeline["restaurants"]
    covered = len(pipeline["targets"]) + len(pipeline["research"])
    ruled_out = (restaurants["blocker"].isin(["POS we cannot integrate with", "already a customer"])).sum()
    assert covered + ruled_out == len(restaurants)


def test_every_research_row_gets_exactly_one_lane(pipeline):
    """The brief quotes a cost per lane, so the lanes must partition the queue."""
    lanes = pipeline["research"]["lane"]
    assert lanes.notna().all()
    assert set(lanes) <= {"desk", "call", "visit"}
    assert lanes.value_counts().sum() == len(pipeline["research"])


def test_pipeline_settings_come_from_config():
    assert MARKET
    assert TOP_N > 0
    assert AS_OF is not None


def test_pos_key_collapses_spellings():
    assert pos_key("Salt Box") == pos_key("SALTBOX") == "saltbox"
    assert pos_key("Meridian (legacy)") == "meridianlegacy"


def test_cadence_is_eligible():
    """The 2026-06-22 rule change. The scrape's cached column still says fail."""
    rules = load_pos_rules()
    assert rules[pos_key("cadence flex")] == ("Cadence", "eligible")


def test_meridian_cloud_is_not_legacy_meridian():
    rules = load_pos_rules()
    assert rules[pos_key("Meridian Cloud")][1] == "eligible"
    assert rules[pos_key("Meridian Server")][1] == "ineligible"
    assert rules[pos_key("Meridian")][1] == "ambiguous"


def test_no_pos_spelling_in_the_data_is_unaccounted_for():
    """A vendor spelling we never anticipated would silently shrink the target
    count. Anything new must show up here rather than in the headline number."""
    scraped, calls, crm = load_raw()
    seen = pd.concat(
        [scraped["pos_system"], calls["pos_captured"], crm["pos_from_crm"]]
    ).dropna()

    means_no_signal = {"unknown", "notfound", "na", ""}
    known = set(load_pos_rules()) | means_no_signal
    unmapped = {v for v in seen.unique() if pos_key(v) not in known}
    assert not unmapped, f"POS spellings with no rule: {sorted(unmapped)}"
