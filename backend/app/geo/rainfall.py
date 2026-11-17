from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from app.geo.datasets import region_dataset
from app.geo.records import DatasetRecord
from app.research.blocks_place import DistrictRef, MonthlyRain
from app.research.calendar import MONTHS
from app.research.datasets import DatasetRef

__all__ = [
    "RAINFALL_DATASET_CODE",
    "RAINFALL_STAT",
    "RAINFALL_UNIT",
    "RAINFALL_VARIABLE",
    "DistrictRainfall",
    "MonthValue",
    "month_periods",
    "rainfall_from",
]

RAINFALL_DATASET_CODE = "CHIRPS_3_0"
RAINFALL_VARIABLE = "monthly_precipitation"
RAINFALL_STAT = "NORMAL"
RAINFALL_UNIT = "mm/month"


@dataclass(frozen=True)
class MonthValue:
    depth_or_period: str
    value: float | None
    unit: str | None


@dataclass(frozen=True)
class DistrictRainfall:
    rain: MonthlyRain
    dataset: DatasetRef


def month_periods(period: str) -> list[str]:
    return [f"{period}-{month:02d}" for month in range(1, MONTHS + 1)]


def rainfall_from(
    district: DistrictRef, dataset: DatasetRecord, values: Iterable[MonthValue]
) -> DistrictRainfall | None:
    if dataset.code != RAINFALL_DATASET_CODE or not dataset.period:
        return None
    stored = {value.depth_or_period: value for value in values}
    months = [stored.get(key) for key in month_periods(dataset.period)]
    if not all(_usable(month) for month in months):
        return None
    rain = MonthlyRain(
        district=district,
        dataset_code=dataset.code,
        period=dataset.period,
        millimetres=[month.value for month in months if month is not None and month.value is not None],
    )
    return DistrictRainfall(rain=rain, dataset=region_dataset(dataset))


def _usable(month: MonthValue | None) -> bool:
    return month is not None and month.value is not None and month.value >= 0 and month.unit == RAINFALL_UNIT
