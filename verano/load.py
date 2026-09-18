"""Read the data pack, POS rules, and pipeline config."""

from pathlib import Path

import pandas as pd
import yaml

from verano.clean import pos_key

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "output"

_cfg = yaml.safe_load((ROOT / "config" / "pipeline.yml").read_text())
DATA = ROOT / _cfg["data_dir"]

# Re-exported so the rest of the code imports settings from one place.
MARKET = _cfg["market"]
AS_OF = pd.Timestamp(_cfg["as_of"])
TOP_N = _cfg["top_n"]


def load_raw():
    """Return the three extracts as (scraped, calls, crm).

    Read as text on purpose. Left to guess, pandas turns phone numbers into
    floats, and phone is the key that joins all three systems.
    """
    scraped = pd.read_csv(DATA / "verano_bay_restaurants_scraped.csv", dtype=str)
    calls = pd.read_csv(DATA / "call_log_events.csv", dtype=str)
    crm = pd.read_csv(DATA / "crm_deals_export.csv", dtype=str)
    return scraped, calls, crm


def load_pos_rules():
    """Return {pos_key: (canonical name, verdict)} from config/rules.yml.

    A POS string that isn't in here is unknown, not ineligible.
    """
    doc = yaml.safe_load((ROOT / "config" / "rules.yml").read_text())
    return {
        pos_key(alias): (vendor["canonical"], vendor["verdict"])
        for vendor in doc["vendors"]
        for alias in vendor["aliases"]
    }
