import dataclasses

from app.geo.rainfall import MonthValue, month_periods, rainfall_from
from app.geo.records import DatasetRecord
from app.research.blocks_place import DistrictRef

KACHCHH = 449
KACHCHH_REF = DistrictRef(district_lgd=KACHCHH, name="Kachchh", state_name="Gujarat")
CHIRPS = DatasetRecord(
    code="CHIRPS_3_0",
    title="Climate Hazards Center InfraRed Precipitation with Stations v3.0",
    publisher="Climate Hazards Center, UC Santa Barbara",
    edition="3.0",
    period="2016-2025",
    native_resolution="0.05 degree",
    licence="CC BY 4.0",
    licence_url="https://creativecommons.org/licenses/by/4.0/",
    attribution="Climate Hazards Center, UC Santa Barbara (CHIRPS3)",
    citation="Climate Hazards Center InfraRed Precipitation with Stations version 3 (CHIRPS3) Data Repository (2025).",
    url="https://data.chc.ucsb.edu/products/CHIRPS/v3.0/",
)
KACHCHH_MM = [0.4, 0.9, 0.3, 0.2, 2.1, 38.5, 141.2, 112.6, 61.3, 9.8, 2.4, 0.6]


def months(millimetres: list[float], period: str = "2016-2025", unit: str = "mm/month") -> list[MonthValue]:
    return [
        MonthValue(depth_or_period=f"{period}-{month:02d}", value=value, unit=unit)
        for month, value in enumerate(millimetres, start=1)
    ]


def test_the_twelve_month_keys_follow_the_dataset_period() -> None:
    assert month_periods("2016-2025") == [f"2016-2025-{m:02d}" for m in range(1, 13)]


def test_twelve_stored_normals_become_the_district_s_rainfall_with_its_dataset_row() -> None:
    found = rainfall_from(KACHCHH_REF, CHIRPS, reversed(months(KACHCHH_MM)))
    assert found is not None
    assert found.rain.model_dump(by_alias=True) == {
        "district": {"districtLgd": KACHCHH, "name": "Kachchh", "stateName": "Gujarat"},
        "datasetCode": "CHIRPS_3_0",
        "period": "2016-2025",
        "millimetres": KACHCHH_MM,
    }
    assert (found.dataset.code, found.dataset.period, found.dataset.native_resolution) == (
        "CHIRPS_3_0",
        "2016-2025",
        "0.05 degree",
    )


def test_a_missing_month_leaves_the_district_without_rainfall() -> None:
    assert rainfall_from(KACHCHH_REF, CHIRPS, months(KACHCHH_MM)[:11]) is None
    gap = months(KACHCHH_MM)
    gap[6] = dataclasses.replace(gap[6], value=None)
    assert rainfall_from(KACHCHH_REF, CHIRPS, gap) is None


def test_rows_of_another_period_unit_or_dataset_are_not_read() -> None:
    assert rainfall_from(KACHCHH_REF, CHIRPS, months(KACHCHH_MM, period="2015-2024")) is None
    assert rainfall_from(KACHCHH_REF, CHIRPS, months(KACHCHH_MM, unit="mm/year")) is None
    chelsa = dataclasses.replace(CHIRPS, code="CHELSA_2_1_1981_2010", period="1981-2010")
    assert rainfall_from(KACHCHH_REF, chelsa, months(KACHCHH_MM, period="1981-2010")) is None
    assert rainfall_from(KACHCHH_REF, CHIRPS, months([-1.0, *KACHCHH_MM[1:]])) is None
