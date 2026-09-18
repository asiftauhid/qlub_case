# Verano Bay Data Pack — Data Dictionary

Three extracts, pulled 2026-08-03 from three different systems that were never designed to
join cleanly. Nothing has been cleaned for you.

All names, places, phone numbers, websites and POS vendors in this pack are fictional.

---

## 1. `verano_bay_restaurants_scraped.csv` — raw scrape output

One row **per platform listing**, not per restaurant. The same restaurant appears on
multiple platforms.

| Column | Notes |
|---|---|
| `source_row_id` | Unique per row. Not a restaurant identifier. |
| `source_platform` | roamly · dineline · tablefind · civicpages · bookwell · atlasmaps |
| `scraped_date` | |
| `name` | As it appeared on the platform. Formatting varies by platform. |
| `address`, `city`, `postcode` | |
| `neighbourhood` | Legacy column name; we say "area" everywhere else. |
| `phone` | Free-text. Format varies by platform. Sometimes empty. |
| `website` | Empty where the platform had none. |
| `cuisine`, `price_band`, `rating`, `review_count` | Ratings and counts are per platform. |
| `fullservice_keyword_filter` | Stage-1 keyword blocklist. Recall-first, deliberately loose. |
| `fullservice_llm_filter` | Stage-2 LLM verdict. The precision gate. |
| `fullservice_llm_confidence` | 0–1 |
| `pos_system` | Raw string from website fingerprinting. Not canonicalised. |
| `pos_signal` | `website_fingerprint` where a POS was detected, else `none`. |
| `pos_eligibility` | Cached verdict written by an earlier pipeline run. |
| `chain_size_bucket` | SME (1–5 locations) · mid-cap (6–15) · large (16+). Counts the operator's **total** locations, not just those in this market. |
| `restaurant_group` | Populated where a group was identified. Often blank. |

## 2. `call_log_events.csv` — call activity

**Append-only event log.** One row per call attempt. A restaurant can appear many times.

| Column | Notes |
|---|---|
| `call_id`, `call_date` | |
| `caller_type` | `ai` (automated dialler) or `human` (Dubai calling team) |
| `agent_name` | |
| `restaurant_name` | Typed by the agent or passed by the dialler. Not normalised. |
| `phone` | |
| `outcome` | Not reached · No Answer · POS Validated · Data capture incomplete · Callback · Gatekeeper |
| `pos_captured` | POS reported by whoever answered. Free text. |
| `poc_name`, `poc_role` | Point of contact, where the agent got one. |
| `availability_window` | When they said to call back. |
| `poc_email` | Rarely captured. |

## 3. `crm_deals_export.csv` — CRM export

One row per deal record.

| Column | Notes |
|---|---|
| `deal_id`, `deal_name` | |
| `deal_stage` | Eligible → Walked-in → Gatekeeper Demo → KDM Demo → Verbal Yes → Closed Won / Closed Lost / Not Qualified |
| `deal_owner` | **The Qlub sales representative assigned to the deal.** |
| `amount` | |
| `create_date`, `last_activity_date` | |
| `associated_contact` | Linked contact record, where one exists. |
| `company_phone` | |
| `deal_description` | Free-text notes typed by reps. No schema. |
| `pos_from_crm` | POS as recorded in the CRM. |
| `source` | How the deal entered the pipeline. |
| `city` | |

---

**Reference:** `pos_eligibility_rules.md` — the authoritative POS eligibility list.
