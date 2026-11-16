import dataclasses
import datetime as dt
import re
from functools import partial

import geopandas as gpd
import numpy as np
import pandas as pd
import requests

from geo_etl import raster
from geo_etl.catalog import CHIRPS
from geo_etl.layers import USER_AGENT, Measured, Options, Result, failure, with_retries
from geo_etl.rows import Rows, pick

BASE = "https://data.chc.ucsb.edu/products/CHIRPS/v3.0"
ANNUAL_DIR = f"{BASE}/annual/global/tifs/"
ANNUAL_FILE = re.compile(r"chirps-v3\.0\.(\d{4})\.tif(?![\w.])")
LOOKBACK_YEARS = 4
ABSENT = (404, 410)
PROBE_TIMEOUT_S = (10, 60)
RETRY_ON = (requests.RequestException,)
MONSOON = (6, 7, 8, 9)


def annual_url(year: int) -> str:
    return f"{BASE}/annual/global/tifs/chirps-v3.0.{year}.tif"


def monthly_url(year: int, month: int) -> str:
    return f"{BASE}/monthly/global/tifs/chirps-v3.0.{year}.{month:02d}.tif"


def latest_year(today: dt.date | None = None) -> int:
    newest = (today or dt.date.today()).year - 1
    candidates = list(range(newest, newest - LOOKBACK_YEARS, -1))
    try:
        return probed_year(candidates)
    except requests.RequestException as probe_error:
        try:
            return listed_year(candidates)
        except requests.RequestException as listing_error:
            raise RuntimeError(
                f"CHIRPS v3.0 annual files unreachable: probe {probe_error}; listing {listing_error}"
            ) from listing_error


def probed_year(candidates: list[int]) -> int:
    for year in candidates:
        response = with_retries(partial(answered, "HEAD", annual_url(year)), retry_on=RETRY_ON)
        if response.status_code not in ABSENT:
            return year
    raise RuntimeError(f"no CHIRPS v3.0 annual file for {candidates[-1]} to {candidates[0]}: every year is not found")


def listed_year(candidates: list[int]) -> int:
    response = with_retries(partial(answered, "GET", ANNUAL_DIR), retry_on=RETRY_ON)
    if response.status_code in ABSENT:
        raise RuntimeError(f"{ANNUAL_DIR} answered {response.status_code}")
    listed = {int(year) for year in ANNUAL_FILE.findall(response.text)} & set(candidates)
    if not listed:
        raise RuntimeError(f"{ANNUAL_DIR} lists no CHIRPS v3.0 annual file for {candidates[-1]} to {candidates[0]}")
    return max(listed)


def answered(method: str, url: str) -> requests.Response:
    response = requests.request(method, url, timeout=PROBE_TIMEOUT_S, headers={"User-Agent": USER_AGENT})
    if response.status_code not in ABSENT:
        response.raise_for_status()
    return response


def district_means(url: str, districts: gpd.GeoDataFrame, bounds, *, measured: Measured) -> pd.DataFrame:
    grid = raster.read([url], bounds, valid_min=0.0, dtype="float32")
    if grid is None:
        raise RuntimeError(f"{url} not reachable")
    table = measured.add(raster.zonal(grid, districts, raster.continuous_ops(grid)))
    return table.set_index("districtLgd")


def run(districts: gpd.GeoDataFrame, options: Options) -> Result:
    last = latest_year()
    first = last - options.chirps_years + 1
    period = f"{first}-{last}"
    dataset = dataclasses.replace(CHIRPS, period=period)
    rows = Rows(
        dataset,
        "exactextract coverage weight area_spherical_km2 on the native 0.05 degree grid; negative values treated as "
        "no data; normals are the mean of yearly district means",
    )
    failures: list[dict] = []
    measured = Measured()
    bounds = raster.bounds_in(districts, "EPSG:4326", 0.1)
    lookup = districts.set_index("districtLgd")
    annual: dict[int, pd.DataFrame] = {}
    for year in range(first, last + 1):
        try:
            annual[year] = district_means(annual_url(year), districts, bounds, measured=measured)
        except Exception as error:
            failures.append(failure(districts, f"chirps annual {year}", error))
    monthly: dict[tuple[int, int], pd.DataFrame] = {}
    if options.chirps_monthly:
        for year in range(first, last + 1):
            for month in range(1, 13):
                try:
                    monthly[(year, month)] = district_means(
                        monthly_url(year, month), districts, bounds, measured=measured
                    )
                except Exception as error:
                    failures.append(failure(districts, f"chirps monthly {year}-{month:02d}", error))
    for lgd in districts["districtLgd"]:
        district = lookup.loc[int(lgd)].copy()
        district["districtLgd"] = int(lgd)
        yearly = []
        for year, table in sorted(annual.items()):
            if lgd not in table.index:
                continue
            record = table.loc[lgd]
            value = float(pick(record, "mean"))
            yearly.append(value)
            pixels = float(record["pixels"])
            rows.add(district, "annual_precipitation", str(year), "DISTRICT_MEAN", value, "mm/year", pixels=pixels)
            rows.add(district, "annual_precipitation", str(year), "DISTRICT_P10", pick(record, "p10"), "mm/year")
            rows.add(district, "annual_precipitation", str(year), "DISTRICT_P90", pick(record, "p90"), "mm/year")
        finite = [v for v in yearly if np.isfinite(v)]
        if len(finite) == options.chirps_years:
            rows.add(district, "annual_precipitation", period, "NORMAL", float(np.mean(finite)), "mm/year")
            if len(finite) >= 2 and np.mean(finite) > 0:
                rows.add(
                    district,
                    "annual_precipitation_cv",
                    period,
                    "NORMAL",
                    float(np.std(finite) / np.mean(finite)),
                    "fraction",
                )
        by_month: dict[int, list[float]] = {}
        for (_, month), table in monthly.items():
            if lgd in table.index:
                value = float(pick(table.loc[lgd], "mean"))
                if np.isfinite(value):
                    by_month.setdefault(month, []).append(value)
        complete = all(len(by_month.get(m, [])) == options.chirps_years for m in range(1, 13))
        if options.chirps_monthly and complete:
            normals = {m: float(np.mean(by_month[m])) for m in range(1, 13)}
            for month, value in normals.items():
                rows.add(district, "monthly_precipitation", f"{period}-{month:02d}", "NORMAL", value, "mm/month")
            total = sum(normals.values())
            if total > 0:
                share = sum(normals[m] for m in MONSOON) / total
                rows.add(district, "monsoon_share_jjas", period, "NORMAL", share, "fraction of annual")
    return Result(
        dataset,
        rows.frame(),
        failures=failures,
        notes={"period": period},
        districts_without_cells=measured.without_cells(),
    )
