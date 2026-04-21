---
title: Cloud usage
kernelspec:
  name: python3
  display_name: Python 3
---

# Cloud usage across 2i2c clusters

This page shows aggregate cloud usage for all 2i2c-operated clusters.
Per-cluster pages are linked at the bottom. Data is pulled from the
[`cloud` GitHub release](https://github.com/2i2c-org/data/releases/tag/cloud).

```{code-cell} python
:tags: [remove-input]
import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import yaml

sys.path.insert(0, str(Path("_scripts/cloud").resolve()))
from filters import drop_clusters, drop_hubs

DATA = Path("_data")
meta = yaml.safe_load((DATA / "release_metadata.yml").read_text())

df_unique = pd.read_csv(DATA / "maus-unique-by-cluster.csv")
df_unique["date"] = pd.to_datetime(df_unique["date"])
df_unique = drop_clusters(df_unique)
df_unique = df_unique[df_unique["unique_users"] > 0]

df_hub = pd.read_csv(DATA / "maus-by-hub.csv")
df_hub["date"] = pd.to_datetime(df_hub["date"])
df_hub = drop_clusters(df_hub)
df_hub = drop_hubs(df_hub)
df_hub = df_hub.dropna(subset=["users"])
df_hub = df_hub[df_hub["users"] > 0]

n_clusters = df_unique["cluster"].nunique()
n_hubs = df_hub.groupby(["cluster", "hub"]).ngroups
last_updated = meta["publishedAt"].strftime("%Y-%m-%d %H:%M UTC")
```

**Last updated:** {eval}`last_updated`

| Total clusters | Total hubs |
|:---|:---|
| {eval}`n_clusters` | {eval}`n_hubs` |

## Unique monthly users by cluster

```{code-cell} python
:tags: [remove-input]
order = (
    df_unique.groupby("cluster")["unique_users"].mean()
    .sort_values(ascending=False).index.tolist()
)
fig = px.area(
    df_unique.sort_values("date"),
    x="date", y="unique_users", color="cluster",
    category_orders={"cluster": order},
    title="Unique monthly users across all 2i2c clusters",
    labels={"unique_users": "users"},
)
fig.show()
```

## Active hubs by cluster

```{code-cell} python
:tags: [remove-input]
hubs_per = (
    df_hub.groupby(["cluster", "date"])["hub"].nunique()
    .reset_index(name="hubs")
)
order_hubs = (
    hubs_per.groupby("cluster")["hubs"].max()
    .sort_values(ascending=False).index.tolist()
)
fig = px.area(
    hubs_per,
    x="date", y="hubs", color="cluster",
    category_orders={"cluster": order_hubs},
    title="Number of active hubs by cluster",
)
fig.show()
```

## Per-cluster pages

```{tableofcontents}
:kind: children
```

## Admin / maintainer section

::::{dropdown} Why are total and unique MAUs sometimes different?
On some pages, you'll notice that the "total MAUS" (the first plot) is different
from the "unique MAUs" (the second plot). This is beacuse we use two different
ways to calculate each. Total MAUs uses statistics generated _by JupyterHub_
(explained in this [blog post about MAUs](https://blog.jupyter.org/accurately-counting-daily-weekly-monthly-active-users-on-jupyterhub-6fbec6c6ce2f)). Unique MAUs uses a
custom PromQL query to our Grafana, allowing us to get a list of _usernames_ that
logged in and then count the number of unique values.

The JupyterHub statistic is a bit more conservative - it defines an active user based on additional criteria (like taking actions on the hub).
Ideally we'd use the same for unique MAUs, but for now this is the best we've got in order to detect username uniqueness.
::::

::::{dropdown} Clusters with errors
Clusters listed below had Grafana query failures on the most recent
download. Their data may be stale or missing.

```{code-cell} python
:tags: [remove-input]
errors = (DATA / "errors.txt").read_text().strip()
print(errors if errors else "No cluster errors in the latest run.")
```
::::
