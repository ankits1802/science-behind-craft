import math

import geopandas as gpd
import numpy as np
import pytest
from rasterio.crs import CRS
from rasterio.transform import from_origin
from shapely.geometry import LineString, box

from geo_etl import catalog, raster
from geo_etl.layers import Options, chelsa, hydrorivers

INTERNAL_WORDS = (
    "Designer Portal",
    "designer-portal",
    "adityaradha007",
    "joined to LGD",
    "not confirmed",
    "unconfirmed",
)
READER_FIELDS = ("title", "publisher", "edition", "period", "licence", "attribution", "citation")
CHELSA_DOI_URL = "https://doi.org/10.1038/sdata.2017.122"
ENGINEERING_WORDS = ("exactextract", "area_spherical_km2", "GeoTIFF", "65535", "no data")
KM_PER_DEGREE = 111.32


@pytest.mark.parametrize("dataset", list(catalog.ALL.values()), ids=list(catalog.ALL))
def test_no_dataset_text_a_reader_sees_names_an_internal_system_or_admits_a_gap(dataset: catalog.Dataset) -> None:
    shown = " ".join(str(getattr(dataset, field) or "") for field in READER_FIELDS).casefold()
    assert [word for word in INTERNAL_WORDS if word.casefold() in shown] == []


def test_the_district_boundaries_are_named_in_reader_words() -> None:
    assert catalog.BOUNDARIES.title == "Indian district boundaries, matched to LGD codes"
    assert catalog.BOUNDARIES.attribution == "District boundaries are indicative."
    assert (catalog.BOUNDARIES.licenceUrl, catalog.BOUNDARIES.citation) == (None, None)


def test_chelsa_is_credited_by_its_paper_named_once_beside_the_full_citation() -> None:
    assert (catalog.CHELSA.licence, catalog.CHELSA.licenceUrl) == ("Karger et al. 2017", CHELSA_DOI_URL)
    assert catalog.CHELSA.attribution == "CHELSA V2.1"
    assert catalog.CHELSA.citation.startswith("Karger, D. N.")
    assert catalog.CHELSA.citation.endswith(CHELSA_DOI_URL)


def test_every_chelsa_value_carries_the_reader_method(tmp_path, monkeypatch) -> None:
    district = gpd.GeoDataFrame(
        {"districtLgd": [449], "stateLgd": [24], "districtName": ["Kachchh"]},
        geometry=[box(70.0, 23.0, 71.0, 24.0)],
        crs="EPSG:4326",
    )
    grid = raster.Grid(np.full((4, 4), 26.5, dtype="float32"), from_origin(69.5, 24.5, 0.5, 0.5), CRS.from_epsg(4326))
    monkeypatch.setattr(raster, "read", lambda *args, **kwargs: grid)
    result = chelsa.run(district, Options(cache=tmp_path, chelsa_bio=("bio1",), chelsa_months=False))
    assert result.failures == []
    assert set(result.values["method"]) == {chelsa.METHOD}
    assert set(result.values["stat"]) == {"NORMAL", "DISTRICT_P10", "DISTRICT_P90"}
    assert [word for word in ENGINEERING_WORDS if word.casefold() in chelsa.METHOD.casefold()] == []


def test_every_river_value_carries_the_reader_method_measured_from_the_districts_centre(tmp_path, monkeypatch) -> None:
    district = gpd.GeoDataFrame(
        {
            "districtLgd": [449],
            "stateLgd": [24],
            "districtName": ["Kachchh"],
            "centroidLon": [70.5],
            "centroidLat": [23.5],
        },
        geometry=[box(70.0, 23.0, 71.0, 24.0)],
        crs="EPSG:4326",
    )
    rivers = gpd.GeoDataFrame(
        {
            "HYRIV_ID": [1],
            "ORD_STRA": [5],
            "ORD_FLOW": [3],
            "DIS_AV_CMS": [500.0],
            "LENGTH_KM": [220.0],
            "UPLAND_SKM": [9000.0],
        },
        geometry=[LineString([(70.2, 22.5), (70.2, 24.5)])],
        crs="EPSG:4326",
    )
    monkeypatch.setattr(hydrorivers, "cached_archive", lambda cache: tmp_path / "rivers.zip")
    monkeypatch.setattr(hydrorivers, "load_rivers", lambda archive, bounds: rivers)
    result = hydrorivers.run(district, Options(cache=tmp_path))
    assert result.failures == []
    assert set(result.values["method"]) == {hydrorivers.METHOD}
    assert "distance from the district's centre" in hydrorivers.METHOD
    found = result.values.set_index("variable")["value"]
    across = 0.3 * KM_PER_DEGREE * math.cos(math.radians(23.5))
    assert found["distance_centroid_to_major_river"] == pytest.approx(across, abs=1.0)
