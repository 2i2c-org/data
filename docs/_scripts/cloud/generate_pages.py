"""Render one MyST page per cluster, plus per-cluster CSV slices.

For each cluster we do the following:

- Render _scripts/cloud/cluster_page.md.j2 -> cloud/<cluster>.md.
- Write three per-cluster CSVs alongside the page, each matching the
  data shown in one of the page's plots:
    * cloud/<cluster>-by-hub.csv    (12mo active users by hub)
    * cloud/<cluster>-unique.csv    (12mo unique users for the cluster)
    * cloud/<cluster>-month-end.csv (12mo month-end unique MAUs)
- Write _scripts/cloud/_clusters_list.md - this is a list of all clusters
  we can embed in the docs.
"""

import pandas as pd
from jinja2 import Template
from pathlib import Path

DATA = Path("_data")
CLOUD = Path("cloud")
TEMPLATE = Path("_scripts/cloud/cluster_page.md.j2")
CLUSTERS_LIST = Path("_scripts/cloud/_clusters_list.md")

YEAR_AGO = pd.Timestamp.utcnow().tz_localize(None).normalize() - pd.Timedelta(days=365)


def drop_clusters(df):
    """Remove clusters that shouldn't be published on the docs site.

    Add new cluster names (or patterns) here as the need comes up.
    """
    return df[~df["cluster"].str.contains("prometheus")]


def main():
    # Load + clean both CSVs once so each per-cluster slice is a straight
    # filter-by-cluster. Note: utoronto/highmem is already dropped upstream
    # in scripts/cloud/download.py.
    full_hub = drop_clusters(pd.read_csv(DATA / "maus-by-hub.csv"))
    full_hub["date"] = pd.to_datetime(full_hub["date"])
    # Drop staging hubs in plots because these are just for dev
    full_hub = full_hub[~full_hub["hub"].astype(str).str.contains("staging", na=False)]
    # Drop datapoints with missing users
    full_hub = full_hub.dropna(subset=["users"])

    # Drop clusters that we know shouldn't be published (usually dev clusters)
    full_unique = drop_clusters(pd.read_csv(DATA / "maus-unique-by-cluster.csv"))
    full_unique["date"] = pd.to_datetime(full_unique["date"])
    full_unique = full_unique[full_unique["unique_users"] > 0]

    # Publish any cluster with a non-zero point in the last 12 months in either CSV.
    recent_hub = full_hub[full_hub["date"] >= YEAR_AGO]
    recent_unique = full_unique[full_unique["date"] >= YEAR_AGO]
    clusters = sorted(set(recent_hub["cluster"]) | set(recent_unique["cluster"]))
    print(f"Generating pages for {len(clusters)} clusters: {clusters}")

    tmpl = Template(TEMPLATE.read_text())
    CLOUD.mkdir(parents=True, exist_ok=True)
    for name in clusters:
        (CLOUD / f"{name}.md").write_text(tmpl.render(cluster_name=name))

        hub = full_hub[(full_hub["cluster"] == name) & (full_hub["date"] >= YEAR_AGO)]
        unique = full_unique[
            (full_unique["cluster"] == name) & (full_unique["date"] >= YEAR_AGO)
        ]
        hub.to_csv(CLOUD / f"{name}-by-hub.csv", index=False)
        unique.sort_values("date").to_csv(CLOUD / f"{name}-unique.csv", index=False)
        unique[unique["date"].dt.is_month_end].sort_values("date").to_csv(
            CLOUD / f"{name}-month-end.csv",
            index=False,
        )

    # Puts this in _scripts/cloud/ so the MyST TOC doesn't pick it up as a page.
    lines = [f"- [{name}](cloud/{name}.md)" for name in clusters]
    CLUSTERS_LIST.write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
