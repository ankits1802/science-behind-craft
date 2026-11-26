from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from maplayers.fetch import FetchFailed, fetch_all, map_downloads, url_opener

DESCRIPTION = (
    "Download what the map layers build reads: the four Natural Earth zips (unzipped beside themselves), "
    "the ETOPO1 grid, the USGS mineral sites and the OpenStreetMap India extract. Each is tried at its own "
    "address and then at each mirror, each address up to four times with a growing wait, and checked "
    "before it is kept; a file already present and whole (the ETOPO1 grid the cache keeps) is not "
    "downloaded again. The address each file came from is noted in fetched.json, which the build records. "
    "Fails, naming every address and why, only when every address of a file fails."
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=DESCRIPTION)
    parser.add_argument("downloads", type=Path, help="folder to download into")
    parser.add_argument(
        "--only",
        nargs="+",
        metavar="NAME",
        help="download only these: rivers, lakes, regions, peaks, etopo1, mrds, osm",
    )
    options = parser.parse_args(argv)
    try:
        done = fetch_all(
            map_downloads(options.only), options.downloads, opener=url_opener(), sleep=time.sleep
        )
    except FetchFailed as failed:
        print(f"::error::{failed}")
        return 1
    for each in done:
        print(f"{each.file}: {'kept from an earlier run' if each.address is None else each.address}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
