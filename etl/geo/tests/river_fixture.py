import geopandas as gpd
from shapely.geometry import LineString

PLACEHOLDER_OUTLET = 3
PLACEHOLDER_PATH = [1, 2, 3]
PLACEHOLDER_REACHES = [
    (1, 2, 1, 140.0, [(69.60, 23.45), (69.66, 23.40), (69.70, 23.36)]),
    (2, 3, 2, 300.0, [(69.70, 23.36), (69.74, 23.31), (69.78, 23.27)]),
    (3, 0, 2, 420.0, [(69.78, 23.27), (69.85, 23.24), (69.92, 23.20)]),
    (4, 2, 1, 120.0, [(69.80, 23.48), (69.75, 23.40), (69.70, 23.36)]),
]


def placeholder_basin() -> gpd.GeoDataFrame:
    return gpd.GeoDataFrame(
        [
            {
                "hyrivId": hyriv_id,
                "nextDown": next_down,
                "mainRiv": PLACEHOLDER_OUTLET,
                "ordStra": order,
                "uplandSkm": upland,
                "disAvCms": 0.3,
                "lengthKm": 9.5,
                "geometry": LineString(coords),
            }
            for hyriv_id, next_down, order, upland, coords in PLACEHOLDER_REACHES
        ],
        geometry="geometry",
        crs="EPSG:4326",
    )
