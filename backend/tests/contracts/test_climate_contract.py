import ast

from app.geo.climate import MEAN_STAT, P_VALUE_STAT, P_VALUE_UNIT, SLOPE_STAT, TREND_DATASETS
from app.models.enums import ENV_STATS
from app.research.blocks_insight import TREND_SIGNIFICANCE, TREND_UNITS, TREND_YEARS_MIN
from app.schemas.region import DATASET_FACETS

from .phase_b_golden import catalog_dataset
from .test_river_contract import GEO_ETL, constants

TREND = GEO_ETL / "geo_etl" / "trend.py"
LAYERS = GEO_ETL / "geo_etl" / "layers"


def test_the_etl_writes_trends_by_the_contract_s_rules_and_units() -> None:
    etl = constants(TREND)
    assert (etl["TREND_YEARS_MIN"], etl["TREND_SIGNIFICANCE"]) == (TREND_YEARS_MIN, TREND_SIGNIFICANCE)
    assert {variable: tuple(units) for variable, units in etl["TREND_UNITS"].items()} == dict(TREND_UNITS)
    assert (etl["SLOPE_STAT"], etl["P_VALUE_STAT"], etl["P_VALUE_UNIT"]) == (
        SLOPE_STAT,
        P_VALUE_STAT,
        P_VALUE_UNIT,
    )


def test_every_stat_the_etl_writes_is_a_stored_stat() -> None:
    etl_stats = constants(GEO_ETL / "geo_etl" / "rows.py")["STATS"]
    assert set(etl_stats) == set(ENV_STATS)
    assert {MEAN_STAT, SLOPE_STAT, P_VALUE_STAT} <= set(ENV_STATS)


def test_each_trend_dataset_is_an_etl_dataset_of_the_climate_facet() -> None:
    for code in TREND_DATASETS.values():
        assert catalog_dataset(code)["code"] == code
        assert DATASET_FACETS[code] == "CLIMATE"


def test_the_temperature_layer_writes_the_variable_the_reader_reads() -> None:
    layer = constants(LAYERS / "ghcncams.py")
    assert layer["TEMPERATURE"] == "annual_mean_temperature" in TREND_DATASETS
    assert layer["UNIT"] == TREND_UNITS["annual_mean_temperature"][0]
    assert TREND_DATASETS["annual_precipitation"] == "CHIRPS_3_0"


def test_the_chirps_layer_writes_the_annual_series_it_tests_for_a_trend() -> None:
    tree = ast.parse((LAYERS / "chirps.py").read_text(encoding="utf-8"))
    series = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "AnnualSeries"
        and isinstance(node.args[0], ast.Constant)
    ]
    assert [node.args[0].value for node in series] == ["annual_precipitation"]
