"""Download the latest `cloud` release assets into docs/_data/.

Run from the `docs/` directory. Always overwrites existing files.
Requires the `gh` CLI and GH_TOKEN (or gh auth) to reach the release.
"""

import json
import subprocess
from pathlib import Path

REPO = "2i2c-org/data"
TAG = "cloud"
DATA_DIR = Path("_data")


def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    subprocess.run(
        [
            "gh",
            "release",
            "download",
            TAG,
            "--repo",
            REPO,
            "--dir",
            str(DATA_DIR),
            "--clobber",
        ],
        check=True,
    )

    # Record release publishedAt so pages can show a "last updated" line.
    meta = subprocess.check_output(
        ["gh", "release", "view", TAG, "--repo", REPO, "--json", "publishedAt"],
        text=True,
    )
    published = json.loads(meta)["publishedAt"]
    (DATA_DIR / "release_metadata.yml").write_text(f"publishedAt: {published}\n")
    print(f"Fetched `{TAG}` release (publishedAt: {published}) into {DATA_DIR}/")


if __name__ == "__main__":
    main()
