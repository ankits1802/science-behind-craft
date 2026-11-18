from __future__ import annotations

from collections.abc import Mapping, Sequence
from types import MappingProxyType
from typing import Annotated, ClassVar, Literal, Self

from pydantic import Field, model_validator

from .base import ContractModel, empty
from .blocks import SENTENCE, BlockBase, ExplainerSentence, SentenceSpec, require_facts
from .blocks_place import DistrictRef
from .datasets import DATASET_CODE_PATTERN, DatasetRef, dataset_codes_problems

__all__ = [
    "SERIES_YEARS_MAX",
    "TREND_METHOD",
    "TREND_PERIOD_PATTERN",
    "TREND_SIGNIFICANCE",
    "TREND_UNITS",
    "TREND_VARIABLES",
    "TREND_YEARS_MIN",
    "ClimateRiskBlock",
    "ClimateSeries",
    "ClimateTrend",
    "GroundwaterValue",
    "trend_years",
]

TREND_VARIABLES = ("annual_precipitation", "annual_mean_temperature")
TREND_UNITS: Mapping[str, tuple[str, str]] = MappingProxyType(
    {
        "annual_precipitation": ("mm/year", "mm/year per decade"),
        "annual_mean_temperature": ("degC", "degC per decade"),
    }
)
TREND_METHOD = "SEN_SLOPE_MANN_KENDALL"
TREND_SIGNIFICANCE = 0.05
TREND_YEARS_MIN = 30
TREND_PERIOD_PATTERN = r"^(\d{4})-(\d{4})$"
SERIES_YEARS_MAX = 200

TrendVariable = Literal[*TREND_VARIABLES]
DatasetCode = Annotated[str, Field(pattern=DATASET_CODE_PATTERN, max_length=80)]


def trend_years(period: str) -> tuple[int, int]:
    first, last = (int(year) for year in period.split("-"))
    return first, last


class ClimateTrend(ContractModel):
    district: DistrictRef
    variable: TrendVariable
    dataset_code: DatasetCode
    period: str = Field(pattern=TREND_PERIOD_PATTERN)
    resolution: str = Field(min_length=1, max_length=120)
    mean: float
    mean_unit: str
    slope_per_decade: float
    slope_unit: str
    p_value: float = Field(ge=0, le=1)
    significant: bool

    @model_validator(mode="after")
    def _a_long_series_tested_for_a_trend(self) -> Self:
        first, last = trend_years(self.period)
        if last - first + 1 < TREND_YEARS_MIN:
            raise ValueError(f"a trend spans at least {TREND_YEARS_MIN} years, not {self.period}")
        if (self.mean_unit, self.slope_unit) != TREND_UNITS[self.variable]:
            raise ValueError(f"{self.variable} is given in {' and '.join(TREND_UNITS[self.variable])}")
        if self.significant != (self.p_value < TREND_SIGNIFICANCE):
            raise ValueError(f"a trend is significant exactly when p < {TREND_SIGNIFICANCE}")
        return self


class GroundwaterValue(ContractModel):
    district: DistrictRef
    dataset_code: DatasetCode
    variable: str = Field(min_length=1, max_length=120)
    period: str = Field(min_length=1, max_length=80)
    value: float | None
    value_text: str | None = Field(min_length=1, max_length=200)
    unit: str | None = Field(min_length=1, max_length=40)
    resolution: str = Field(min_length=1, max_length=120)

    @model_validator(mode="after")
    def _a_number_or_a_class(self) -> Self:
        if self.value is None and self.value_text is None:
            raise ValueError(f"groundwater {self.variable} has a number, a text or both")
        if (self.value is None) != (self.unit is None):
            raise ValueError(f"groundwater {self.variable} gives a unit exactly with a number")
        return self


class ClimateSeries(ContractModel):
    district: DistrictRef
    variable: TrendVariable
    dataset_code: DatasetCode
    unit: str = Field(min_length=1, max_length=40)
    first_year: int = Field(ge=1800, le=2200)
    values: list[float | None] = Field(min_length=TREND_YEARS_MIN, max_length=SERIES_YEARS_MAX)

    @model_validator(mode="after")
    def _the_yearly_means_in_the_trend_unit(self) -> Self:
        if self.unit != TREND_UNITS[self.variable][0]:
            raise ValueError(f"the {self.variable} series is given in {TREND_UNITS[self.variable][0]}")
        if all(value is None for value in self.values):
            raise ValueError(f"the {self.variable} series of {self.district.name} has a reading")
        return self


class ClimateRiskBlock(BlockBase):
    SENTENCES: ClassVar[SentenceSpec] = (("meaning", [SENTENCE]),)

    kind: Literal["climate_risk"]
    version: Literal[1]
    trends: list[ClimateTrend]
    groundwater: list[GroundwaterValue]
    meaning: list[ExplainerSentence]
    datasets: list[DatasetRef] = Field(min_length=1)
    series: list[ClimateSeries] = Field(default_factory=list, exclude_if=empty)

    @model_validator(mode="after")
    def _dataset_values_and_what_they_mean(self) -> Self:
        if not self.trends and not self.groundwater:
            raise ValueError(f"climate {self.id} shows a trend or a groundwater value")
        require_facts(f"climate {self.id}", self.meaning)
        pairs = [(trend.district.district_lgd, trend.variable) for trend in self.trends]
        if len(set(pairs)) != len(pairs):
            raise ValueError(f"climate {self.id} gives each district's trend of a variable once")
        used = [value.dataset_code for value in (*self.trends, *self.groundwater)]
        problems = dataset_codes_problems(f"climate {self.id}", self.datasets, used)
        if {dataset.code for dataset in self.datasets} != set(used):
            problems.append(f"climate {self.id} cites only the dataset rows it draws")
        periods = {dataset.code: dataset.period for dataset in self.datasets}
        if any(periods.get(trend.dataset_code) != trend.period for trend in self.trends):
            problems.append(f"climate {self.id} reads each trend over its dataset row's period")
        problems += series_problems(self.id, self.trends, self.series)
        if problems:
            raise ValueError("; ".join(problems))
        return self

    def cites_datasets(self) -> bool:
        return bool(self.datasets)

    def shown_labels(self) -> list[str]:
        places = (value.district.name for value in (*self.trends, *self.groundwater))
        return list(dict.fromkeys(places))


def series_problems(
    block_id: str, trends: Sequence[ClimateTrend], series: Sequence[ClimateSeries]
) -> list[str]:
    behind = {(t.district.district_lgd, t.variable): t for t in trends}
    problems: list[str] = []
    seen: set[tuple[int, str]] = set()
    for item in series:
        key = (item.district.district_lgd, item.variable)
        trend = behind.get(key)
        if trend is None or key in seen:
            problems.append(f"climate {block_id} gives a series only behind a trend it shows, once each")
            continue
        seen.add(key)
        first, last = trend_years(trend.period)
        if (item.dataset_code, item.first_year, len(item.values)) != (
            trend.dataset_code,
            first,
            last - first + 1,
        ):
            problems.append(f"climate {block_id} series of {item.district.name} spans its trend's period")
    return problems
