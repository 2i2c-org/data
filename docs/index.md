# 2i2c Data

Public views of the datasets published by
[`2i2c-org/data`](https://github.com/2i2c-org/data).
Each dataset is published as a GitHub Release; this site renders it so
community members can read it without leaving the browser.

## Datasets

- **[Cloud](cloud.md)** - monthly active users on each 2i2c cluster and hub.

## How to find raw data

This site is built with [MyST](https://mystmd.org), and raw data for
every plot is downloadable from the page that shows it. File names
include a content hash (e.g. `cloudbank-unique-[hash].csv`), so the
exact URL changes whenever the underlying data does. This means you
can't hard-code the link.

To resolve the current link, parse the page's MyST AST. Every rendered
page has a `.json` sibling at the same URL (e.g. `cloud.cloudbank.json`
for `/cloud/cloudbank/`). Each static-file link has a `urlSource`
property (the pre-hash filename) and a `url` property (the hashed path
actually served). To find a download link, walk the AST, match on `urlSource`, and return `url`. Here's a little example of a recursive function that does this in Python:

```python
import json
from urllib.request import urlopen

PAGE = "https://2i2c-org.github.io/data/cloud.cloudbank.json"
WANTED = "cloudbank-unique.csv"

def find_url(node, source):
    if isinstance(node, dict):
        # If we find the source, return its URL
        if node.get("urlSource") == source:
            return node["url"]
        # Iterate through dictionary values otherwise
        for v in node.values():
            found = find_url(v, source)
            if found:
                return found
    elif isinstance(node, list):
        # Iterate through list items if it's a list
        for item in node:
            found = find_url(item, source)
            if found:
                return found

ast = json.load(urlopen(PAGE))
print(find_url(ast, WANTED))
# /build/cloudbank-unique-<hash>.csv
```

Prefix with the site origin (e.g. `https://2i2c.org/data`) to
get the full download URL.
