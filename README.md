# 2i2c Data

This repository downloads public data about 2i2c's infrastructure and services, and publishes each dataset as a GitHub Release for easy re-use elsewhere.

## Datasets

Each dataset lives in its own folder under `scripts/` with two files:

- `download.py` (fetches data)
- `validate.py` (sanity-checks the output before publish).

Check out the README.md of each folder to learn about the dataset inside.

Each dataset is published to its own GitHub release.

## Usage

Download and validate all datasets:

```
nox -s download
```

Download a single dataset:

```
nox -s download -- cloud
```

## Where the data goes

Each dataset publishes its files to a **GitHub Release** with a dedicated tag (e.g., `cloud`). A daily GitHub Actions workflow keeps them up to date.

## Downloading this data from another repository

It's easiest to use the `gh` CLI to download release assets.
There's a separate release for each type of data so you can download them separately:

```bash
# Download all assets from a dataset's release
gh release download cloud --repo 2i2c-org/data --dir data/

# Download a specific file
gh release download cloud --repo 2i2c-org/data --pattern "maus-by-hub.csv" --dir data/
```
