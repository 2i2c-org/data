"""Sanity-check the MAU CSVs before we publish them.

This is intentionally simple! As we run into clear data problems,
we should add new checks to this file to guard against them.

Checks below have a `--- [Check] ---` separator comment and a brief description.

NOTE: When a reference date falls out of the 24-month rolling window, we'll need
to replace it with an updated date.
"""

import subprocess
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).parent.parent.parent / "data"
# Stash the previously-published dataset here so GHA (and repeat local runs)
# have a stable, writable target instead of a system tempdir.
PREV_DIR = Path(__file__).parent.parent.parent / "docs" / "_build" / "old_data"

print(f"Loading CSVs from {DATA_DIR}/ ...")
by_hub = pd.read_csv(DATA_DIR / "maus-by-hub.csv")
unique = pd.read_csv(DATA_DIR / "maus-unique-by-cluster.csv")
print(f"  maus-by-hub.csv:             {len(by_hub)} rows")
print(f"  maus-unique-by-cluster.csv:  {len(unique)} rows")


# --- [Schema] ----------------------------------------------------------------
# Both CSVs have exactly the columns we expect (no missing, no extras).
print("Checking schema...")
assert set(by_hub.columns) == {"date", "hub", "users", "cluster"}, \
    f"maus-by-hub.csv has unexpected columns: {sorted(by_hub.columns)}"
assert set(unique.columns) == {"date", "cluster", "unique_users"}, \
    f"maus-unique-by-cluster.csv has unexpected columns: {sorted(unique.columns)}"


# --- [Recency] ---------------------------------------------------------------
# Both CSVs should have at least one row within the last 7 days. If not, the
# download probably failed silently or Grafana returned nothing.
print("Checking recency (latest row within 7 days)...")
today = pd.Timestamp.now(tz="UTC").tz_localize(None).normalize()
recency_cutoff = today - pd.Timedelta(days=7)
assert pd.to_datetime(by_hub["date"]).max() >= recency_cutoff, \
    "maus-by-hub.csv has no rows in the last 7 days"
# The unique CSV's newest row is the current month, dated at its month-end,
# so a fresh download always has a row dated today or later.
assert pd.to_datetime(unique["date"]).max() >= today, \
    "maus-unique-by-cluster.csv has no current-month row"


# --- [No duplicate keys] -----------------------------------------------------
print("Checking for duplicate keys...")
dups_hub = by_hub.duplicated(subset=["date", "cluster", "hub"]).sum()
assert dups_hub == 0, \
    f"maus-by-hub.csv has {dups_hub} duplicate (date, cluster, hub) rows"
dups_unique = unique.duplicated(subset=["date", "cluster"]).sum()
assert dups_unique == 0, \
    f"maus-unique-by-cluster.csv has {dups_unique} duplicate (date, cluster) rows"


# --- [Non-negative counts] ---------------------------------------------------
print("Checking counts are non-negative...")
assert (by_hub["users"].dropna() >= 0).all(), \
    "maus-by-hub.csv has negative users"
assert (unique["unique_users"] >= 0).all(), \
    "maus-unique-by-cluster.csv has negative unique_users"


# --- [Reference value: utoronto 2025-12-31] ----------------------------------
# Known-good historical unique_users count. Catches silent drift of old data.
# 2309 = distinct non-staff usernames on utoronto during calendar December 2025.
print("Checking reference value (utoronto, 2025-12-31)...")
EXPECTED = 2309
ref = unique.query("date == '2025-12-31' and cluster == 'utoronto'")
assert len(ref) == 1, \
    "Reference row (utoronto, 2025-12-31) missing"
actual = int(ref.iloc[0]["unique_users"])
assert actual == EXPECTED, \
    f"utoronto unique_users on 2025-12-31 drifted: expected {EXPECTED}, got {actual}"


# --- [Drift vs. published data] ----------------------------------------------
# Closed months are historical facts: a fresh download should match what's
# currently in the `cloud` release (published by the previous run). If it
# doesn't, something upstream broke and we want to fail loudly instead of
# silently rewriting history.
print("Checking drift vs. published data...")
print(f"  downloading previously published dataset to {PREV_DIR}/...")
PREV_DIR.mkdir(parents=True, exist_ok=True)
subprocess.run(
    [
        "gh", "release", "download", "cloud",
        "--repo", "2i2c-org/data",
        "--dir", str(PREV_DIR),
        "--pattern", "maus-unique-by-cluster.csv",
        "--clobber",
    ],
    check=True,
)
prev = pd.read_csv(PREV_DIR / "maus-unique-by-cluster.csv")

merged = unique.merge(
    prev, on=["date", "cluster"], suffixes=("_curr", "_prev")
)
# Only compare months that were already over when the baseline was published.
# The published file can't tell us which those are (it holds the then-open
# month and even a stub row for the next one), so go by the calendar instead:
# skip the current and previous month. With a daily publish, everything older
# was closed in both datasets; a publish gap longer than a month would break
# this assumption, but the finance dashboard's freshness check flags a frozen
# release within days — long before that.
closed_before = (today.replace(day=1) - pd.DateOffset(months=1)).strftime("%Y-%m-%d")
merged = merged[merged["date"] < closed_before]
drifted = merged[merged["unique_users_curr"] != merged["unique_users_prev"]]
print(f"  compared {len(merged)} overlapping rows, {len(drifted)} drifted")
assert drifted.empty, \
    f"Historical drift in {len(drifted)} of {len(merged)} rows:\n{drifted}"


print(f"maus: ok ({len(by_hub)} hub rows, {len(unique)} unique-user rows)")
