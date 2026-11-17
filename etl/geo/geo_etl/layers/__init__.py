import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from pathlib import Path

import geopandas as gpd
import pandas as pd
import requests

from geo_etl import raster
from geo_etl.catalog import CLIMATE_FIRST_YEAR, Dataset

USER_AGENT = "kalavigyan-geo-etl/0.0.1"
ATTEMPTS = 4
BACKOFF_S = 5.0


@dataclass
class Options:
    cache: Path
    worldcover_factor: int = 4
    hansen_factor: int = 1
    dem_factor: int = 1
    soil_vars: tuple[str, ...] = ("clay", "sand", "silt", "soc", "phh2o", "cec", "bdod", "nitrogen")
    soil_depths: tuple[str, ...] = ("0-5cm", "5-15cm", "15-30cm")
    soil_uncertainty: bool = True
    chelsa_months: bool = True
    chelsa_bio: tuple[str, ...] = ("bio1", "bio5", "bio6", "bio12", "bio15")
    climate_first_year: int = CLIMATE_FIRST_YEAR
    chirps_monthly: bool = True
    download_striped: bool = False


@dataclass
class Result:
    dataset: Dataset
    values: pd.DataFrame
    geology: pd.DataFrame | None = None
    failures: list[dict] = field(default_factory=list)
    notes: dict = field(default_factory=dict)
    districts_without_cells: list[int] = field(default_factory=list)


@dataclass
class Measured:
    districts: set[int] = field(default_factory=set)
    with_cells: set[int] = field(default_factory=set)

    def add(self, table: pd.DataFrame) -> pd.DataFrame:
        for lgd, pixels in zip(table["districtLgd"], table["pixels"], strict=True):
            self.districts.add(int(lgd))
            if raster.has_cells(pixels):
                self.with_cells.add(int(lgd))
        return table

    def without_cells(self) -> list[int]:
        return sorted(self.districts - self.with_cells)


def by_state(districts: gpd.GeoDataFrame) -> Iterator[gpd.GeoDataFrame]:
    for _, group in districts.groupby("stateLgd", sort=True):
        yield group


def by_district(districts: gpd.GeoDataFrame) -> Iterator[gpd.GeoDataFrame]:
    for i in range(len(districts)):
        yield districts.iloc[[i]]


def failure(group: gpd.GeoDataFrame, step: str, error: Exception) -> dict:
    return {
        "step": step,
        "districtLgds": [int(v) for v in group["districtLgd"]],
        "error": f"{type(error).__name__}: {error}"[:500],
    }


def with_retries[T](call: Callable[[], T], *, retry_on: tuple[type[Exception], ...], attempts: int = ATTEMPTS) -> T:
    for attempt in range(attempts - 1):
        try:
            return call()
        except retry_on:
            time.sleep(BACKOFF_S * (attempt + 1))
    return call()


def download(url: str, target: Path) -> Path:
    if target.exists() and target.stat().st_size > 0:
        return target
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_suffix(target.suffix + ".part")
    with requests.get(url, stream=True, timeout=300, headers={"User-Agent": USER_AGENT}) as response:
        response.raise_for_status()
        with partial.open("wb") as handle:
            for chunk in response.iter_content(chunk_size=1 << 20):
                handle.write(chunk)
    partial.replace(target)
    return target
