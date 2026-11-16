from __future__ import annotations

from collections.abc import Mapping, Sequence

from sqlalchemy import ColumnElement, Float, and_, cast, distinct, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.geo.layers import BOUNDARY_DATASET_CODE, MAP_LAYERS, layer_unit, stored_depth_or_period
from app.geo.records import DatasetRecord, LayerListing, LayerRow, LayerSpec, LayerValues, StoredLayer
from app.models import DistrictEnvValue, EnvDataset
from app.services.region_records import dataset_records

__all__ = ["layer_values", "listed_layers"]

LayerKey = tuple[str, str, str, str]


async def listed_layers(session: AsyncSession) -> LayerListing:
    datasets = await dataset_records(
        session, {spec.dataset_code for spec in MAP_LAYERS} | {BOUNDARY_DATASET_CODE}
    )
    keys = {spec.id: key for spec in MAP_LAYERS if (key := _key(spec, datasets)) is not None}
    units = await _stored_units(session, list(keys.values()))
    layers = tuple(
        StoredLayer(spec, layer_unit(spec, units[keys[spec.id]]))
        for spec in MAP_LAYERS
        if spec.id in keys and keys[spec.id] in units
    )
    used = {layer.spec.dataset_code for layer in layers}
    return LayerListing(
        layers=layers,
        datasets={code: datasets[code] for code in sorted(used)},
        boundary=datasets.get(BOUNDARY_DATASET_CODE),
    )


async def layer_values(session: AsyncSession, spec: LayerSpec) -> LayerValues | None:
    datasets = await dataset_records(session, {spec.dataset_code, BOUNDARY_DATASET_CODE})
    key = _key(spec, datasets)
    boundary = datasets.get(BOUNDARY_DATASET_CODE)
    if key is None or boundary is None:
        return None
    statement = (
        select(
            DistrictEnvValue.districtLgd,
            cast(DistrictEnvValue.value, Float),
            DistrictEnvValue.resolution,
            DistrictEnvValue.unit,
        )
        .join(EnvDataset, EnvDataset.id == DistrictEnvValue.datasetId)
        .where(_matches(key), DistrictEnvValue.value.is_not(None))
    )
    rows = (await session.execute(statement)).all()
    if not rows:
        return None
    return LayerValues(
        layer=StoredLayer(spec, layer_unit(spec, {unit for *_, unit in rows})),
        dataset=datasets[spec.dataset_code],
        rows=tuple(LayerRow(district_lgd=lgd, value=value, resolution=grid) for lgd, value, grid, _ in rows),
        boundary=boundary,
    )


def _key(spec: LayerSpec, datasets: Mapping[str, DatasetRecord]) -> LayerKey | None:
    dataset = datasets.get(spec.dataset_code)
    if dataset is None:
        return None
    stored = stored_depth_or_period(spec, dataset)
    return None if stored is None else (spec.dataset_code, spec.variable, stored, spec.stat)


def _matches(key: LayerKey) -> ColumnElement[bool]:
    code, variable, depth_or_period, stat = key
    return and_(
        EnvDataset.code == code,
        DistrictEnvValue.variable == variable,
        DistrictEnvValue.depthOrPeriod == depth_or_period,
        DistrictEnvValue.stat == stat,
    )


async def _stored_units(session: AsyncSession, keys: Sequence[LayerKey]) -> dict[LayerKey, set[str | None]]:
    if not keys:
        return {}
    series = (
        EnvDataset.code,
        DistrictEnvValue.variable,
        DistrictEnvValue.depthOrPeriod,
        DistrictEnvValue.stat,
    )
    statement = (
        select(*series, func.array_agg(distinct(DistrictEnvValue.unit)))
        .join(EnvDataset, EnvDataset.id == DistrictEnvValue.datasetId)
        .where(or_(*(_matches(key) for key in keys)), DistrictEnvValue.value.is_not(None))
        .group_by(*series)
    )
    return {
        (code, variable, depth_or_period, found_stat): set(units)
        for code, variable, depth_or_period, found_stat, units in (await session.execute(statement)).all()
    }
