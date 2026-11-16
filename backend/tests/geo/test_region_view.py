import dataclasses
import logging

import pytest
from pydantic import ValidationError

from app.core.errors import InvalidInput
from app.geo.places import region_places
from app.geo.records import Coverage, SeriesTotals, ValueRecord
from app.geo.region_view import craft_region
from app.schemas.region import CraftRegion

from ..contracts.golden import dumped, golden_text
from .golden_region import (
    GOLDEN_CRAFT,
    GUJARAT,
    KACHCHH,
    VAV_THARAD,
    WORLDCOVER_READ,
    golden_region_records,
    location,
)

SOIL_METHOD = "ISRIC WCS zonal mean"


def totals(**changes: object) -> SeriesTotals:
    fields: dict[str, object] = {
        "state_lgd": GUJARAT.lgd,
        "dataset_code": "SOILGRIDS_2_0",
        "variable": "phh2o",
        "depth_or_period": "0-5cm",
        "stat": "DISTRICT_MEAN",
        "unit": "pH",
        "value_text": None,
        "districts": 2,
        "weighted_sum": 3 * 7.0 + 1 * 8.0,
        "area": 4.0,
        "total": 15.0,
        "low": 7.0,
        "high": 8.0,
        "resolutions": (None,),
        "methods": (SOIL_METHOD,),
    }
    return SeriesTotals(**(fields | changes))


def inherited_records(*series: SeriesTotals, coverage: tuple[Coverage, ...] = ()):
    vav = location(id="location-vav", district_lgd=VAV_THARAD, district_name="Vav-Tharad", has_polygon=False)
    return dataclasses.replace(
        golden_region_records(),
        places=region_places([vav], []),
        district_values=(),
        state_totals=series,
        coverage=coverage,
        district_totals={GUJARAT.lgd: 34},
    )


def test_stored_kachchh_rows_build_the_golden_region() -> None:
    assert dumped(CraftRegion, craft_region(golden_region_records())) == golden_text(GOLDEN_CRAFT)


def test_values_without_their_own_grid_carry_the_datasets_native_grid() -> None:
    region = craft_region(golden_region_records())
    grids = {v.dataset_code: v.resolution for f in region.places[0].facets for v in f.values}
    assert grids["SOILGRIDS_2_0"] == "250 m"
    assert grids["ESA_WORLDCOVER_2021_V200"] == WORLDCOVER_READ


def test_a_district_without_a_polygon_shows_its_states_area_weighted_mean_and_says_why() -> None:
    region = craft_region(inherited_records(totals()))
    [place] = region.places
    assert (place.key, place.values_from, place.inherited_reason) == (
        f"district-{VAV_THARAD}",
        "STATE",
        "NO_DISTRICT_POLYGON",
    )
    [value] = place.facets[0].values
    assert (value.aggregation, value.value, value.district_count, value.district_total) == (
        "STATE_AREA_MEAN",
        7.25,
        2,
        34,
    )
    assert (value.depth, value.period, value.resolution, value.method) == (
        "0-5cm",
        "modelled, 2020 release",
        "250 m",
        SOIL_METHOD,
    )


def test_a_state_only_craft_is_practised_across_the_state_with_its_aggregates() -> None:
    records = dataclasses.replace(
        inherited_records(totals(stat="TOTAL", variable="soc", unit="t")), places=region_places([], [GUJARAT])
    )
    [place] = craft_region(records).places
    assert (place.key, place.scope, place.basis.kind, place.basis.level) == (
        "state-24",
        "STATE",
        "MASTER_LIST",
        "REVIEWED",
    )
    assert place.facets[0].values[0].model_dump(include={"aggregation", "value"}) == {
        "aggregation": "STATE_SUM",
        "value": 15.0,
    }


def test_a_state_aggregate_lists_every_grid_its_districts_were_read_at() -> None:
    series = totals(
        dataset_code="ESA_WORLDCOVER_2021_V200",
        variable="landcover_cropland",
        depth_or_period="2021",
        stat="SHARE",
        unit="fraction",
        resolutions=(None, WORLDCOVER_READ),
    )
    value = craft_region(inherited_records(series)).places[0].facets[0].values[0]
    assert value.resolution == f"10 m (1/12000 degree); {WORLDCOVER_READ}"


def test_a_facet_with_no_stored_value_is_left_out() -> None:
    records = dataclasses.replace(
        golden_region_records(),
        district_values=tuple(
            v for v in golden_region_records().district_values if v.dataset_code == "USGS_MRDS"
        ),
    )
    region = craft_region(records)
    assert [f.facet for f in region.places[0].facets] == ["GEOLOGY"]
    assert [d.code for d in region.datasets] == ["USGS_MRDS"]


def test_a_place_with_no_stored_values_has_no_facets_and_cites_no_dataset() -> None:
    region = craft_region(dataclasses.replace(golden_region_records(), district_values=()))
    assert (region.places[0].facets, region.datasets) == ([], [])


def test_a_value_of_a_dataset_without_a_facet_is_left_out_and_logged(
    caplog: pytest.LogCaptureFixture,
) -> None:
    stray = ValueRecord(KACHCHH, "IMD_GRIDDED", "rainfall", "", "NORMAL", 1.0, None, "mm", None, None)
    records = golden_region_records()
    records = dataclasses.replace(records, district_values=(*records.district_values, stray))
    with caplog.at_level(logging.WARNING):
        region = craft_region(records)
    assert "IMD_GRIDDED" not in {d.code for d in region.datasets}
    assert "IMD_GRIDDED has no region facet" in caplog.text


def test_soil_depths_read_from_the_surface_down() -> None:
    records = golden_region_records()
    deeper = [
        dataclasses.replace(records.district_values[1], depth_or_period=depth, value=value)
        for depth, value in (("15-30cm", 8.4), ("5-15cm", 8.2))
    ]
    region = craft_region(dataclasses.replace(records, district_values=(*records.district_values, *deeper)))
    soil = [(v.variable, v.depth) for v in region.places[0].facets[0].values]
    assert soil == [("clay", "0-5cm"), ("phh2o", "0-5cm"), ("phh2o", "5-15cm"), ("phh2o", "15-30cm")]


def test_a_stored_value_without_a_unit_fails_loudly() -> None:
    records = golden_region_records()
    broken = dataclasses.replace(records.district_values[0], unit=None)
    with pytest.raises(InvalidInput, match="has no unit"):
        craft_region(dataclasses.replace(records, district_values=(broken,)))


def test_a_value_citing_a_dataset_with_no_row_fails_loudly() -> None:
    records = golden_region_records()
    datasets = {code: row for code, row in records.datasets.items() if code != "SOILGRIDS_2_0"}
    with pytest.raises(InvalidInput, match="SOILGRIDS_2_0"):
        craft_region(dataclasses.replace(records, datasets=datasets))


def test_a_state_aggregate_needs_the_states_district_count() -> None:
    records = dataclasses.replace(inherited_records(totals()), district_totals={})
    with pytest.raises(InvalidInput, match="no district count"):
        craft_region(records)


def test_a_dataset_row_without_an_edition_is_refused_by_the_contract() -> None:
    records = golden_region_records()
    soil = dataclasses.replace(records.datasets["SOILGRIDS_2_0"], edition=None)
    with pytest.raises(ValidationError):
        craft_region(dataclasses.replace(records, datasets={**records.datasets, "SOILGRIDS_2_0": soil}))


def test_a_located_place_brings_its_source_and_a_state_of_practice_brings_none() -> None:
    located = craft_region(golden_region_records())
    assert [source.id for source in located.sources] == [located.places[0].basis.source_id]
    state_only = craft_region(
        dataclasses.replace(golden_region_records(), places=region_places([], [GUJARAT]))
    )
    assert state_only.sources == []


def test_a_place_source_that_was_not_loaded_fails_loudly() -> None:
    with pytest.raises(InvalidInput, match="were not loaded"):
        craft_region(dataclasses.replace(golden_region_records(), sources={}))
