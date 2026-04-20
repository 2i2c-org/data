"""Sanity-check the MAU CSVs before we publish them.

This is intentionally simple! As we run into clear data problems,
we should add new checks to this file to guard against them.

Checks below have a `--- [Check] ---` separator comment and a brief description.

NOTE: When a reference date falls out of the 24-month rolling window, we'll need
to replace it with an updated date.

TODO: It might be better to download the latest release and run a check to
ensure that older data hasn't changed.
"""

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


# --- [Reference value: utoronto 2025-12-31] ----------------------------------
# Known-good historical unique_users count. This makes sure the old data isn't changing.
EXPECTED = 2096
ref = unique.query("date == '2025-12-31' and cluster == 'utoronto'")
assert len(ref) == 1, \
    "Reference row (utoronto, 2025-12-31) missing"
actual = int(ref.iloc[0]["unique_users"])
assert actual == EXPECTED, \
    f"utoronto unique_users on 2025-12-31 drifted: expected {EXPECTED}, got {actual}"


print(f"maus: ok ({len(by_hub)} hub rows, {len(unique)} unique-user rows)")
