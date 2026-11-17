from __future__ import annotations

from sqlalchemy import Float, cast, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.geo.rainfall import (
    RAINFALL_DATASET_CODE,
    RAINFALL_STAT,
    RAINFALL_VARIABLE,
    DistrictRainfall,
    MonthValue,
    month_periods,
    rainfall_from,
)
from app.models import DistrictEnvValue, EnvDataset
from app.research.blocks_place import DistrictRef

from .region_records import dataset_records

__all__ = ["district_rainfall"]


async def district_rainfall(session: AsyncSession, district: DistrictRef) -> DistrictRainfall | None:
    dataset = (await dataset_records(session, {RAINFALL_DATASET_CODE})).get(RAINFALL_DATASET_CODE)
    if dataset is None or not dataset.period:
        return None
    statement = (
        select(DistrictEnvValue.depthOrPeriod, cast(DistrictEnvValue.value, Float), DistrictEnvValue.unit)
        .join(EnvDataset, EnvDataset.id == DistrictEnvValue.datasetId)
        .where(
            EnvDataset.code == RAINFALL_DATASET_CODE,
            DistrictEnvValue.districtLgd == district.district_lgd,
            DistrictEnvValue.variable == RAINFALL_VARIABLE,
            DistrictEnvValue.stat == RAINFALL_STAT,
            DistrictEnvValue.depthOrPeriod.in_(month_periods(dataset.period)),
        )
    )
    rows = (await session.execute(statement)).all()
    values = [MonthValue(depth_or_period=period, value=value, unit=unit) for period, value, unit in rows]
    return rainfall_from(district, dataset, values)
