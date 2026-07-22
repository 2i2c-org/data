"""Download MAU data from Grafana/Prometheus.

Produces two CSV files in data/:
- maus-by-hub.csv: monthly active users per hub, sampled daily
- maus-unique-by-cluster.csv: distinct users per cluster per calendar month

The "unique MAUs" definition is documented in docs/cloud.md.

All query timestamps are anchored to UTC so that the output doesn't depend on the
time that this script was run.


Notes
---
- Requires a GRAFANA_TOKEN environment variable with access to our Grafana API!
- Requires `gh` auth that can read 2i2c-org/data-private (for the team list)!
- The unique MAUs query will take a little while to run!
"""

import io
import os
import re
import subprocess
import requests
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime, timedelta, timezone
from prometheus_pandas.query import Prometheus
import pandas as pd
from rich.progress import track

load_dotenv(override=False)
GRAFANA_TOKEN = os.environ["GRAFANA_TOKEN"]
GRAFANA_URL = "https://grafana.pilot.2i2c.cloud"

DATA_DIR = Path(__file__).parent.parent.parent / "data"

# Service accounts excluded from unique-user counts, alongside the
# 2i2c team members from get_team_usernames().
IGNORED_USERNAMES = {"deployment-service-check"}

# Anchor every query timestamp to UTC midnight to keep the results deterministic.
NOW = datetime.now(timezone.utc).replace(
    hour=0, minute=0, second=0, microsecond=0
)


def get_prometheus_datasources():
    """List the Prometheus datasources available in Grafana."""
    datasources = requests.get(
        f"{GRAFANA_URL}/api/datasources",
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {GRAFANA_TOKEN}",
        },
    )
    df = pd.DataFrame.from_dict(datasources.json())
    return df.query("type == 'prometheus'")


def get_pandas_prometheus(prometheus_uid: str):
    """Create a Prometheus client for a given datasource uid."""
    session = requests.Session()
    session.headers = {"Authorization": f"Bearer {GRAFANA_TOKEN}"}
    proxy_url = f"{GRAFANA_URL}/api/datasources/proxy/uid/{prometheus_uid}/"
    return Prometheus(proxy_url, session)


def fix_known_bugs(activity):
    """Apply corrections for known upstream data bugs.

    Add new entries as comment-labelled blocks below as we find them.
    """
    # --- utoronto/highmem double-counting (Feb 6 – Apr 2, 2025) ------------
    # The highmem hub was mis-configured for a period in early 2025 such
    # that users from other utoronto hubs counted as active on `highmem`.
    # We drop the whole `highmem` cluster because it was a short-term experiment.
    # https://github.com/2i2c-org/meta/issues/2818
    activity = activity[
        ~((activity["cluster"] == "utoronto") & (activity["hub"] == "highmem"))
    ]

    return activity


def download_hub_activity(datasources):
    """Download monthly active users per hub across all clusters."""
    # This uses the JupyterHub MAUs metric, so double-counts users across hubs
    query = """
        max(jupyterhub_active_users{period="30d", namespace=~".*"}) by (namespace)
    """

    path = DATA_DIR / "maus-by-hub.csv"
    print(f"Downloading hub activity data to {path}...")

    activity = []
    errors = []
    # Loop through clusters and query MAUs per hub
    for uid, idata in track(list(datasources.groupby("uid"))):
        cluster_name = idata["name"].squeeze()
        try:
            prometheus = get_pandas_prometheus(uid)
            result = prometheus.query_range(
                query,
                NOW - timedelta(days=730),
                NOW,
                "1d",
            )
            # Extract hub name from column labels like '{namespace="hubname"}'
            result.columns = [re.findall(r'[^"]+', col)[1] for col in result.columns]
            result.columns.name = "hub"
            result.index.name = "date"
            result.index = result.index.floor("D")

            # Reshape to tidy format
            result = result.stack("hub").to_frame("users").reset_index()
            result["cluster"] = cluster_name
            activity.append(result)
        except Exception as err:
            # We track clusters that errored in case we want to fix them in the future.
            # Some clusters seem to be "known broken" while others might not be.
            errors.append(f"{cluster_name}: {err!r}")

    activity = pd.concat(activity)
    activity = fix_known_bugs(activity)
    activity.to_csv(path, index=False)
    print(f"Finished: {path}")
    return errors


def get_team_usernames():
    """2i2c team usernames and emails, from team.csv in data-private's
    `team-latest` release. We exclude these from MAU counts."""
    team = pd.read_csv(io.BytesIO(subprocess.check_output([
        "gh", "release", "download", "team-latest",
        "--repo", "2i2c-org/data-private", "--pattern", "team.csv", "--output", "-",
    ])))
    return set(team["GitHub"].dropna()) | set(team["E-mail"].dropna())


def download_unique_users(datasources):
    """Download unique users per cluster per calendar month (deduplicated across hubs).

    A user counts as active in a month if their notebook server ran at any
    point that month. 2i2c team members and service accounts are excluded.
    The current month is a count-so-far, dated at the coming month-end.
    """
    # Ignore 2i2c team members and service accounts. PromQL regex matchers are
    # fully anchored, so this only excludes exact (case-insensitive) matches.
    # Backslashes are doubled because PromQL string literals process escapes.
    ignore = IGNORED_USERNAMES | get_team_usernames()
    ignore_regex = "(?i)(" + "|".join(sorted(re.escape(name) for name in ignore)) + ")"
    ignore_regex = ignore_regex.replace("\\", "\\\\")

    # Counts unique usernames across all hubs on a cluster by finding
    # all jupyter user pods in a calendar month and counting distinct usernames.
    query = """
        count(
          count by (annotation_hub_jupyter_org_username) (
            max_over_time(
              kube_pod_annotations{
                namespace=~".*",
                pod=~"jupyter-.*",
                annotation_hub_jupyter_org_username=~".+",
                annotation_hub_jupyter_org_username!~"IGNORE"
              }[DAYSd]
            )
          )
        )
    """.replace("IGNORE", ignore_regex)

    path = DATA_DIR / "maus-unique-by-cluster.csv"
    print(f"Downloading unique users per cluster to {path}...")

    # Build query dates: every month-end from 24 months ago through the
    # *current* month-end. The current month-end is in the future, so its
    # count only covers the month so far and grows until the month closes.
    start = NOW - timedelta(days=730)
    # Add a month-buffer to the end so date_range picks up the current
    # month-end even though it's after NOW.
    month_ends = pd.date_range(start=start, end=NOW + timedelta(days=32), freq="ME", tz="UTC")
    # Snap every sample to end-of-day UTC.
    query_dates = [
        d.to_pydatetime().replace(hour=23, minute=59, second=59, microsecond=0)
        for d in month_ends
    ]

    unique_users = []
    errors = []
    for uid, idata in track(list(datasources.groupby("uid"))):
        cluster_name = idata["name"].squeeze()
        prometheus = get_pandas_prometheus(uid)
        for qdate in query_dates:
            try:
                # A month-end's day number is the number of days in that month.
                result = prometheus.query(query.replace("DAYS", str(qdate.day)), qdate)
                count = int(result.iloc[0]) if not result.empty else 0
                unique_users.append(
                    {
                        "date": qdate.strftime("%Y-%m-%d"),
                        "cluster": cluster_name,
                        "unique_users": count,
                    }
                )
            except Exception as err:
                errors.append(f"{cluster_name}: {err!r}")

    pd.DataFrame(unique_users).to_csv(path, index=False)
    print(f"Finished: {path}")
    return errors


DATA_DIR.mkdir(exist_ok=True)
datasources = get_prometheus_datasources()
hub_errors = download_hub_activity(datasources)
unique_errors = download_unique_users(datasources)

# Save any errored clusters so we can publish them with the release
all_errors = sorted(set(hub_errors + unique_errors))
errors_path = DATA_DIR / "errors.txt"
if all_errors:
    print(f"Clusters with errors: {', '.join(sorted(set(all_errors)))}")
    errors_path.write_text("\n".join(all_errors) + "\n")
    print(f"Wrote {len(all_errors)} errored clusters to {errors_path}")
else:
    errors_path.write_text("")
    print("No cluster errors.")
