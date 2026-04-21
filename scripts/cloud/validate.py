"""Sanity-check the MAU CSVs before we publish them.

This is intentionally simple! As we run into clear data problems,
we should add new checks to this file to guard against them.

Checks below have a `--- [Check] ---` separator comment and a brief description.

NOTE: When a reference date falls out of the 24-month rolling window, we'll need
to replace it with an updated date.
"""

import subprocess
import tempfile
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).parent.parent.parent / "data"

by_hub = pd.read_csv(DATA_DIR / "maus-by-hub.csv")
unique = pd.read_csv(DATA_DIR / "maus-unique-by-cluster.csv")


# --- [Schema] ----------------------------------------------------------------
# Both CSVs have exactly the columns we expect (no missing, no extras).
assert set(by_hub.columns) == {"date", "hub", "users", "cluster"}, \
    f"maus-by-hub.csv has unexpected columns: {sorted(by_hub.columns)}"
assert set(unique.columns) == {"date", "cluster", "unique_users"}, \
    f"maus-unique-by-cluster.csv has unexpected columns: {sorted(unique.columns)}"


# --- [Recency] ---------------------------------------------------------------
# Both CSVs should have at least one row within the last 7 days. If not, the
# download probably failed silently or Grafana returned nothing.
today = pd.Timestamp.now(tz="UTC").tz_localize(None).normalize()
recency_cutoff = today - pd.Timedelta(days=7)
assert pd.to_datetime(by_hub["date"]).max() >= recency_cutoff, \
    "maus-by-hub.csv has no rows in the last 7 days"
assert pd.to_datetime(unique["date"]).max() >= recency_cutoff, \
    "maus-unique-by-cluster.csv has no rows in the last 7 days"


# --- [No duplicate keys] -----------------------------------------------------
dups_hub = by_hub.duplicated(subset=["date", "cluster", "hub"]).sum()
assert dups_hub == 0, \
    f"maus-by-hub.csv has {dups_hub} duplicate (date, cluster, hub) rows"
dups_unique = unique.duplicated(subset=["date", "cluster"]).sum()
assert dups_unique == 0, \
    f"maus-unique-by-cluster.csv has {dups_unique} duplicate (date, cluster) rows"


# --- [Non-negative counts] ---------------------------------------------------
assert (by_hub["users"].dropna() >= 0).all(), \
    "maus-by-hub.csv has negative users"
assert (unique["unique_users"] >= 0).all(), \
    "maus-unique-by-cluster.csv has negative unique_users"


# --- [Reference value: utoronto 2025-12-31] ----------------------------------
# Known-good historical unique_users count. Catches silent drift of old data.
EXPECTED = 2096
ref = unique.query("date == '2025-12-31' and cluster == 'utoronto'")
assert len(ref) == 1, \
    "Reference row (utoronto, 2025-12-31) missing"
actual = int(ref.iloc[0]["unique_users"])
assert actual == EXPECTED, \
    f"utoronto unique_users on 2025-12-31 drifted: expected {EXPECTED}, got {actual}"


print(f"maus: ok ({len(by_hub)} hub rows, {len(unique)} unique-user rows)")
