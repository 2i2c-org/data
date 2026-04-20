# Cloud infrastructure - monthly active users

Monthly Active Users from 2i2c's hub infrastructure, pulled from Grafana/Prometheus.

Two CSVs are produced in `data/`:

- `maus-by-hub.csv`: monthly active users per hub, sampled daily. Uses the JupyterHub `jupyterhub_active_users` metric. This double-counts users who are active on more than one hub on the same cluster.
- `maus-unique-by-cluster.csv`: unique users per cluster, deduplicated across hubs.
  This provides counts at the end of each month (for billing purposes) and a few samples in between to plot smoother curves. It works by counting distinct `annotation_hub_jupyter_org_username` values observed on `jupyter-*` pods in rolling 30-day windows.

An `errors.txt` file lists clusters we couldn't query on the latest run.

Published as the `cloud` GitHub release.

## Requirements

`GRAFANA_TOKEN` environment variable with access to the 2i2c Grafana API.
