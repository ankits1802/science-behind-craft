import importlib.util
import uuid
from collections.abc import AsyncIterator, Iterable
from pathlib import Path
from types import ModuleType
from typing import Any

import httpx
import pytest
from geoalchemy2 import WKTElement
from sqlalchemy import delete, func, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_engine, get_session
from app.core.deps import get_current_user
from app.main import app
from app.models import (
    AdminDistrict,
    Craft,
    CraftLocation,
    DistrictEnvValue,
    DistrictGeology,
    EnvDataset,
    Source,
    User,
)
from app.schemas.region import CraftRegion, MapLayer, MapLayerList

from ..contracts.golden import dumped, golden_text
from ..geo.golden_region import (
    GI_JOURNAL,
    GOLDEN_CRAFT,
    GOLDEN_LAYER,
    GOLDEN_LAYERS,
    KACHCHH,
    KACHCHH_ROWS,
    SOIL_PH,
    VAV_THARAD,
    WORLDCOVER_READ,
    golden_datasets,
    golden_methods,
)

pytestmark = pytest.mark.db

AHMEDABAD = 438
GUJARAT_DISTRICTS = 34
GLIM = "GLIM_1_0_05DEG"
GLIM_DATASET = {
    "code": GLIM,
    "title": "Global Lithological Map Database v1.0 (gridded to 0.5 degree)",
    "publisher": "Universitat Hamburg, via PANGAEA",
    "edition": "1.0",
    "period": "2012",
    "nativeResolution": "0.5 degree",
    "licence": "CC BY 3.0",
}


@pytest.fixture
async def session() -> AsyncIterator[AsyncSession]:
    async with get_engine().connect() as connection:
        transaction = await connection.begin()
        try:
            session = AsyncSession(bind=connection, expire_on_commit=False, autoflush=False)
            await session.execute(delete(EnvDataset))
            yield session
            await session.close()
        finally:
            await transaction.rollback()


async def ajrakh(session: AsyncSession) -> Craft:
    craft = (await session.execute(select(Craft).where(Craft.slug == "Kutch-Ajrakh"))).scalar_one()
    await session.execute(delete(CraftLocation).where(CraftLocation.craftId == craft.id))
    return craft


async def store_datasets(session: AsyncSession, *extra: dict[str, Any]) -> dict[str, uuid.UUID]:
    ids: dict[str, uuid.UUID] = {}
    for record in golden_datasets().values():
        ids[record.code] = uuid.uuid4()
        session.add(
            EnvDataset(
                id=ids[record.code],
                code=record.code,
                title=record.title,
                publisher=record.publisher,
                edition=record.edition,
                period=record.period,
                nativeResolution=record.native_resolution,
                licence=record.licence,
                licenceUrl=record.licence_url,
                attribution=record.attribution,
                citation=record.citation,
                url=record.url,
            )
        )
    for row in extra:
        ids[row["code"]] = uuid.uuid4()
        session.add(EnvDataset(id=ids[row["code"]], **row))
    await session.flush()
    return ids


def env_row(
    ids: dict[str, uuid.UUID], lgd: int, row: tuple[Any, ...], method: str | None = None
) -> DistrictEnvValue:
    code, variable, stored, stat, value, unit, grid = row
    return DistrictEnvValue(
        districtLgd=lgd,
        datasetId=ids[code],
        variable=variable,
        depthOrPeriod=stored,
        stat=stat,
        value=value,
        unit=unit,
        resolution=grid,
        method=method,
    )


async def locate(session: AsyncSession, craft: Craft, **fields: Any) -> None:
    session.add(CraftLocation(id=uuid.uuid4(), craftId=craft.id, evidenceLevel="PROVISIONAL", **fields))
    await session.flush()


async def areas(session: AsyncSession, lgds: Iterable[int]) -> dict[int, float]:
    statement = select(AdminDistrict.lgd, func.ST_Area(func.geography(AdminDistrict.geom), False)).where(
        AdminDistrict.lgd.in_(list(lgds))
    )
    return {lgd: float(area) for lgd, area in (await session.execute(statement)).all()}


async def fetched(session: AsyncSession, path: str, **headers: str) -> httpx.Response:
    async def this_session() -> AsyncIterator[Any]:
        yield session

    reader = User(id=uuid.uuid4(), name="Reader", email="reader@example.com", role="STUDENT")
    app.dependency_overrides[get_session] = this_session
    app.dependency_overrides[get_current_user] = lambda: reader
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.get(path, headers=headers)
    finally:
        app.dependency_overrides.pop(get_session, None)
        app.dependency_overrides.pop(get_current_user, None)


async def region(session: AsyncSession) -> CraftRegion:
    response = await fetched(session, "/api/crafts/Kutch-Ajrakh/region")
    assert response.status_code == 200, response.text
    return CraftRegion.model_validate(response.json())


async def test_the_region_route_reproduces_the_golden_region_from_stored_rows(session: AsyncSession) -> None:
    craft = await ajrakh(session)
    ids = await store_datasets(session)
    methods = golden_methods()
    session.add_all(env_row(ids, KACHCHH, row, methods[row[0]]) for row in KACHCHH_ROWS)
    await locate(
        session,
        craft,
        precision="DISTRICT",
        districtLgd=KACHCHH,
        placeLabel="Ajrakhpur, Kachchh",
        sourceId=uuid.UUID(GI_JOURNAL),
    )
    response = await fetched(session, "/api/crafts/Kutch-Ajrakh/region")
    assert response.status_code == 200, response.text
    assert response.headers["cache-control"] == "private, no-cache"
    assert dumped(CraftRegion, CraftRegion.model_validate(response.json())) == golden_text(GOLDEN_CRAFT)


async def test_the_layer_routes_reproduce_the_golden_list_and_layer(session: AsyncSession) -> None:
    ids = await store_datasets(session)
    soil = ("SOILGRIDS_2_0", "phh2o", "0-5cm", "DISTRICT_MEAN")
    session.add_all(env_row(ids, lgd, (*soil, value, "pH", None)) for lgd, value in SOIL_PH.items())
    session.add_all(
        env_row(ids, KACHCHH, row)
        for row in KACHCHH_ROWS
        if row[1] in {"annual_mean_temperature", "landcover_cropland"}
    )
    await session.flush()
    listed = await fetched(session, "/api/map/layers")
    assert listed.status_code == 200, listed.text
    assert dumped(MapLayerList, MapLayerList.model_validate(listed.json())) == golden_text(GOLDEN_LAYERS)
    layer = await fetched(session, "/api/map/layers/soil-ph-0-5cm")
    assert layer.status_code == 200, layer.text
    assert dumped(MapLayer, MapLayer.model_validate(layer.json())) == golden_text(GOLDEN_LAYER)
    again = await fetched(
        session, "/api/map/layers/soil-ph-0-5cm", **{"If-None-Match": layer.headers["etag"]}
    )
    assert again.status_code == 304
    assert (await fetched(session, "/api/map/layers/elevation")).status_code == 404


async def test_a_district_without_a_polygon_shows_gujarats_area_weighted_values(
    session: AsyncSession,
) -> None:
    craft = await ajrakh(session)
    ids = await store_datasets(session)
    soil = ("SOILGRIDS_2_0", "phh2o", "0-5cm")
    session.add_all(
        [
            env_row(ids, KACHCHH, (*soil, "DISTRICT_MEAN", 8.1, "pH", None)),
            env_row(ids, AHMEDABAD, (*soil, "DISTRICT_MEAN", 7.8, "pH", None)),
            env_row(ids, KACHCHH, (*soil, "DISTRICT_P10", 7.5, "pH", None)),
            env_row(ids, KACHCHH, ("USGS_MRDS", "mineral_occurrences", "", "COUNT", 41.0, "sites", None)),
            env_row(ids, AHMEDABAD, ("USGS_MRDS", "mineral_occurrences", "", "COUNT", 3.0, "sites", None)),
        ]
    )
    await locate(session, craft, precision="DISTRICT", districtLgd=VAV_THARAD, sourceId=uuid.UUID(GI_JOURNAL))
    weights = await areas(session, [KACHCHH, AHMEDABAD])
    expected = round(
        (weights[KACHCHH] * 8.1 + weights[AHMEDABAD] * 7.8) / (weights[KACHCHH] + weights[AHMEDABAD]), 6
    )
    [place] = (await region(session)).places
    assert (place.key, place.values_from, place.inherited_reason, place.place_label) == (
        f"district-{VAV_THARAD}",
        "STATE",
        "NO_DISTRICT_POLYGON",
        "Vav-Tharad",
    )
    found = {(v.variable, v.stat): v for f in place.facets for v in f.values}
    assert set(found) == {("phh2o", "DISTRICT_MEAN"), ("mineral_occurrences", "COUNT")}
    mean, sites = found["phh2o", "DISTRICT_MEAN"], found["mineral_occurrences", "COUNT"]
    assert (mean.aggregation, mean.value, mean.district_count, mean.district_total) == (
        "STATE_AREA_MEAN",
        expected,
        2,
        GUJARAT_DISTRICTS,
    )
    assert (sites.aggregation, sites.value, sites.resolution) == ("STATE_SUM", 44.0, "point locations")


async def test_a_point_belongs_to_the_district_whose_polygon_holds_it(session: AsyncSession) -> None:
    craft = await ajrakh(session)
    await store_datasets(session)
    inside = select(
        func.ST_X(func.ST_PointOnSurface(AdminDistrict.geom)),
        func.ST_Y(func.ST_PointOnSurface(AdminDistrict.geom)),
    )
    lon, lat = (await session.execute(inside.where(AdminDistrict.lgd == KACHCHH))).one()
    point = WKTElement(f"POINT({lon} {lat})", srid=4326)
    await locate(
        session, craft, precision="POINT", geom=point, districtLgd=AHMEDABAD, sourceId=uuid.UUID(GI_JOURNAL)
    )
    [place] = (await region(session)).places
    assert (place.key, place.district_name, place.values_from, place.facets) == (
        f"district-{KACHCHH}",
        "Kachchh",
        "DISTRICT",
        [],
    )


async def test_glim_rock_types_are_named_shares_and_an_absent_type_counts_as_none(
    session: AsyncSession,
) -> None:
    await ajrakh(session)
    ids = await store_datasets(session, GLIM_DATASET)
    shares = ((KACHCHH, "su", 0.6), (KACHCHH, "ss", 0.4), (AHMEDABAD, "su", 1.0))
    for lgd, code, share in shares:
        session.add(DistrictGeology(districtLgd=lgd, datasetId=ids[GLIM], lithology=code, areaShare=share))
        session.add(env_row(ids, lgd, (GLIM, f"lithology_{code}", "", "SHARE", share, "fraction", None)))
    await session.flush()
    await session.execute(
        update(DistrictGeology)
        .where(DistrictGeology.lithology == "ss")
        .values(lithologyName="Siliciclastic sedimentary rocks")
    )
    weights = await areas(session, [KACHCHH, AHMEDABAD])
    total = weights[KACHCHH] + weights[AHMEDABAD]
    [place] = (await region(session)).places
    assert (place.key, place.basis.kind) == ("state-24", "MASTER_LIST")
    [geology] = place.facets
    rocks = {v.value_text: (v.variable, v.stat, v.unit, v.value, v.district_count) for v in geology.values}
    assert rocks == {
        "Siliciclastic sedimentary rocks": (
            "lithology",
            "SHARE",
            "fraction",
            round(weights[KACHCHH] * 0.4 / total, 6),
            2,
        ),
        "su": (
            "lithology",
            "SHARE",
            "fraction",
            round((weights[KACHCHH] * 0.6 + weights[AHMEDABAD]) / total, 6),
            2,
        ),
    }


async def test_a_location_citing_a_restricted_source_is_not_shown(session: AsyncSession) -> None:
    craft = await ajrakh(session)
    await session.execute(
        update(Source).where(Source.id == uuid.UUID(GI_JOURNAL)).values(sensitivity="RESTRICTED")
    )
    await locate(session, craft, precision="DISTRICT", districtLgd=KACHCHH, sourceId=uuid.UUID(GI_JOURNAL))
    answered = await region(session)
    [place] = answered.places
    assert (place.key, place.basis.kind, place.facets, answered.sources) == (
        "state-24",
        "MASTER_LIST",
        [],
        [],
    )


async def test_before_any_geo_load_places_answer_without_facets_and_there_are_no_layers(
    session: AsyncSession,
) -> None:
    craft = await ajrakh(session)
    await locate(session, craft, precision="DISTRICT", districtLgd=KACHCHH, sourceId=uuid.UUID(GI_JOURNAL))
    answered = await region(session)
    assert ([p.key for p in answered.places], answered.places[0].facets, answered.datasets) == (
        [f"district-{KACHCHH}"],
        [],
        [],
    )
    assert (await fetched(session, "/api/map/layers")).status_code == 404
    assert (await fetched(session, "/api/map/layers/soil-ph-0-5cm")).status_code == 404


async def test_rows_loaded_before_the_migration_get_their_grid_and_rock_names(session: AsyncSession) -> None:
    ids = await store_datasets(session, GLIM_DATASET)
    cover = ("ESA_WORLDCOVER_2021_V200", "landcover_cropland", "2021", "SHARE", 0.236, "fraction", None)
    method = (
        f"exactextract class fractions, coverage weight area_spherical_km2, read at {WORLDCOVER_READ}; share"
    )
    session.add(env_row(ids, KACHCHH, cover, method))
    session.add(env_row(ids, AHMEDABAD, (*cover[:6], None), "zonal mean"))
    session.add(DistrictGeology(districtLgd=KACHCHH, datasetId=ids[GLIM], lithology="su", areaShare=1.0))
    await session.flush()
    for statement in migration("0005_region_profile").backfills():
        await session.execute(text(statement))
    grids = dict(
        (await session.execute(select(DistrictEnvValue.districtLgd, DistrictEnvValue.resolution))).all()
    )
    assert grids == {KACHCHH: WORLDCOVER_READ, AHMEDABAD: None}
    named = (await session.execute(select(DistrictGeology.lithologyName))).scalar_one()
    assert named == "Unconsolidated sediments"


def migration(name: str) -> ModuleType:
    path = Path(__file__).resolve().parents[2] / "migrations" / "versions" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"migration_{name}", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
