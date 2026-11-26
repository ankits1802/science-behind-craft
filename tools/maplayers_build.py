from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from maplayers.layer_files import layer_text

REPO_ROOT = Path(__file__).resolve().parents[1]
INDIA = Path("frontend/components/map/indiaGeometry.ts")
DISTRICTS = Path("frontend/public/boundaries/district-shapes.json")
REGISTER = Path("etl/geo/data/lgd_register.json")
OUTPUT = Path("frontend/public/layers")
SHADE_FILE = "relief-shade.webp"
WATERS_FILE = "waters.json"
WATERS_MODULE = Path("frontend/lib/server/watersTiles.ts")
DESCRIPTION = (
    "Build the map's physical layers: rivers and lakes from Natural Earth 1:10m, relief bands and shaded "
    "relief from ETOPO1, mineral deposits from the USGS Mineral Resources Data System, and named small "
    "rivers and dams from OpenStreetMap in tiles of two degrees, each fitted to the Survey of India outline "
    "and mirrored into the API, which measures each craft place's ground from them. Needs numpy, rasterio, "
    "shapely and pyogrio (the etl/geo environment)."
)
DOWNLOADS_HELP = (
    "folder holding each Natural Earth zip and its unzipped folder, etopo1_india.asc, mrds-csv.zip, "
    "india-latest.osm.pbf and its osmium export india-waters.geojsonseq (see maplayers/sources.py for each URL)"
)


def _write(path: Path, body: dict[str, Any]) -> None:
    text = layer_text(body)
    path.write_text(text, encoding="utf-8", newline="\n")
    print(f"{path.as_posix()} written, {len(text.encode('utf-8'))} bytes")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=DESCRIPTION)
    parser.add_argument("downloads", type=Path, help=DOWNLOADS_HELP)
    parser.add_argument(
        "--root", type=Path, default=REPO_ROOT, help="repository root to read from and write into"
    )
    options = parser.parse_args(argv)
    from maplayers.geo import india
    from maplayers.minerals import Place, minerals_body, read_sites
    from maplayers.relief import read_grid, relief_body, shade_webp
    from maplayers.rivers import rivers_body
    from maplayers.sources import BOUNDS, MRDS, Downloads
    from maplayers.states import state_locator

    downloads = Downloads(options.downloads)
    outline = india((options.root / INDIA).read_text(encoding="utf-8"))
    folder = options.root / OUTPUT
    folder.mkdir(parents=True, exist_ok=True)
    _write(folder / "rivers.json", rivers_body(downloads, outline))
    grid = read_grid(downloads)
    shade_webp(grid, outline, folder / SHADE_FILE)
    _write(folder / "relief.json", relief_body(downloads, grid, outline, _shade(grid.bounds)))
    locate = state_locator(options.root / DISTRICTS, options.root / REGISTER)
    place = Place(BOUNDS, lambda x, y: outline.contains(_point(x, y)), locate)
    sites = read_sites(downloads.folder / MRDS.file, place)
    _write(folder / "minerals.json", minerals_body(sites, downloads.source(MRDS)))
    _waters(downloads, options.root)
    return _mirrored(folder, options.root)


def _waters(downloads: Any, root: Path) -> None:
    sys.path.append(str(root / "backend"))
    from app.data.district_register import load_district_codes
    from app.data.river_aliases import load_river_aliases

    from maplayers.sources import OSM_WATERS, WATERS_EXPORT
    from maplayers.states import district_polygons
    from maplayers.waters import read_features
    from maplayers.waters_body import district_finder, tiles_module, waters_build
    from maplayers.waters_names import WATERS_NAMES, WATERS_TILES
    from maplayers.waters_register import site_register

    read_on = downloads.read_on.isoformat()
    dataset = downloads.source(OSM_WATERS) | {"edition": read_on, "period": read_on}
    register = site_register(root, load_district_codes(), load_river_aliases())
    districts = district_finder(district_polygons(root / DISTRICTS))
    built = waters_build(read_features(downloads.folder / WATERS_EXPORT), register, districts, dataset)
    tiles = root / WATERS_TILES
    tiles.mkdir(parents=True, exist_ok=True)
    for stale in tiles.glob("*.json"):
        stale.unlink()
    for key, body in built.tiles.items():
        _write(tiles / f"{key}.json", body)
    _write(root / OUTPUT / WATERS_FILE, built.index)
    _write(root / WATERS_NAMES, built.names)
    module = root / WATERS_MODULE
    module.write_text(tiles_module(built.tiles), encoding="utf-8", newline="\n")
    print(f"{module.as_posix()} written, {len(built.tiles)} tiles")


def _shade(bounds: tuple[float, float, float, float]) -> dict[str, Any]:
    west, south, east, north = bounds
    return {"href": f"/layers/{SHADE_FILE}", "west": west, "south": south, "east": east, "north": north}


def _mirrored(folder: Path, root: Path) -> int:
    from maplayers.mirror import MEASURED_OUTPUT, mirror_measured

    for path in mirror_measured(folder, root / MEASURED_OUTPUT):
        print(f"{path.as_posix()} mirrored")
    return 0


def _point(longitude: float, latitude: float) -> Any:
    from shapely.geometry import Point

    return Point(longitude, latitude)


if __name__ == "__main__":
    sys.exit(main())
