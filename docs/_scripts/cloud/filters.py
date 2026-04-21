"""Filters for excluding dev/test clusters and hubs from published views.

We re-use these in a few places so defining in one place so we don't accidentally
drift the filters, and keep them explicit.

If we need to filter out more types of clusters or hubs, add them here.
"""


def drop_clusters(df):
    """Remove dev/test clusters from a dataframe with a `cluster` column."""
    return df[~df["cluster"].str.contains("prometheus")]


def drop_hubs(df):
    """Remove dev/test hubs (e.g., staging) from a dataframe with a `hub` column."""
    return df[~df["hub"].astype(str).str.contains("staging", na=False)]
