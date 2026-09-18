# Verano Bay: qualified target list

A pipeline that joins three messy extracts: scrape, call log, and CRM into one ranked list of
restaurants a representative can sell to immediately, along with a research queue for the ones we cannot qualify yet.

It is built to be re-run when the data or the rules change. Edit `config/rules.yml` and `config/pipeline.yml`, drop in fresh CSVs, run again.

## Run it

```bash
make setup     # creates .venv, installs dependencies, etc
make run       # raw CSVs to output/
make test      # pytest
```

Or, with the venv active: `python -m verano.run`.

## Inputs

Place the three extracts in the folder named by `data_dir` in `config/pipeline.yml`:

| File                                 | Expected grain               |
| ------------------------------------ | ---------------------------- |
| `verano_bay_restaurants_scraped.csv` | one row per platform listing |
| `call_log_events.csv`                | one row per call attempt     |
| `crm_deals_export.csv`               | one row per deal             |

POS eligibility lives in `config/rules.yml`, not in code. When a vendor moves between eligible and
ineligible, change the YAML and re-run.

## Outputs

Written to `output/` on every run. Row counts are printed to the terminal.

| File                        | What it is                                                           |
| --------------------------- | -------------------------------------------------------------------- |
| `qualified_targets.csv`     | top of the ranked list, size set by `top_n` in `config/pipeline.yml` |
| `all_qualified_targets.csv` | full ranked list the top file is cut from                            |
| `research_queue.csv`        | restaurants blocked only because no POS is on record yet             |
| `waterfall.csv`             | step-by-step accounting from raw listings to qualified targets       |
| `findings.csv`              | pipeline diagnosis                                                   |

`qualified_targets.csv` includes a plain-English `reason` per row.

## Pipeline

```
config/
  pipeline.yml            changeable variables
  rules.yml               POS eligibility
verano/
  clean.py                phone_key, name_key, pos_key
  load.py                 reads CSVs and both config files
  entities.py             listings to one row per restaurant
  pos.py                  stack POS mentions from all sources, pick one per restaurant
  qualify.py              qualification gates and named blockers
  diagnose.py             quantified findings for the current run
  score.py                rank targets; route the research queue
  run.py                  entry point
notebooks/
  01_explore.ipynb        read-only EDA. Here rule decisions were made
tests/
  test_verano.py          pipeline test scrips
```

Notebooks import logics from `verano/` and do not re-implement them.

## How it works

**Identity.** Phone number, normalised to ten digits, is the restaurant id. Listings with no phone
are linked to an existing restaurant by name + area when one exists.

**POS.** Every mention is collected from website scrape, CRM field, CRM notes, human call, and AI call. Then one reading is chosen per restaurant using source precedence and specificity (a bare
`Meridian` loses to `Meridian Server`).

**Qualification.** Three gates, in order:

1. POS is not ruled out (not ineligible)
2. POS is confirmed eligible (unknown and ambiguous go to research, not the bin)
3. Not already a closed-won customer

A rep marking a deal _Not Qualified_ or _Closed Lost_ does not remove the restaurant. POS rules
are the fact; a rep's verdict is an opinion that may pre-date a rule change.

**Scoring.** Targets are ranked out of 100 on review volume, POS evidence strength, room to work on
the account without colliding with a colleague, operator size, named contact on file, and rating.
Weights are in `verano/score.py`; a test checks in the scale of 100.

**Research queue.** Unresearched restaurants are sorted by review count and tagged with a lane:
`desk` (has a website), `call` (no website), or `visit` (calls already failed to reach anyone).

## Assumptions

Re-run of the pipeline should align with the following assumptions:

- Phone is unique per restaurant in the target market.
- Cached `pos_eligibility` on the scrape is ignored; verdicts are always recomputed from
  `config/rules.yml`.
- Unknown POS is a research gap, not a rejection.
- Idle deals are measured from `AS_OF`, not the system clock.

## Limitations

- Representative's observations are the only way to measure POS accuracy over time.
- POS spelling mistakes are not handled here, so they'll be treated as different POS.
- Multi-owner deals on the same restaurant are flagged in findings but not auto-resolved.
