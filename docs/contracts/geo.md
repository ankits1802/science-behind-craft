# Geo contract (lane: geo)

The geo lane owns `etl/geo/`, `.github/workflows/geo-etl.yml` and `docs/DATA_SOURCES.md`. It writes per-district environment statistics to `etl/geo/out/` and `etl/geo/load.py` upserts them into the backend tables below. This file lists what `load.py` assumes about those tables and the backend changes it needs.

## Backend changes required

Rows 1 and 2 are done: `ENV_STATS` and the `EnvStat` type in migration 0001 carry the six values, and `DistrictGeology` has `UniqueConstraint("districtLgd", "datasetId", "lithology")`, so `load.py` takes the `ON CONFLICT` path. Rows 3 and 5 are done by migration `0005_region_profile` (decision 0016), which also adds `DistrictEnvValue.resolution` (now loaded) and fills the grid of earlier WorldCover and Copernicus DEM rows and the names of earlier GLiM rows. Row 4 is still open.

| # | Where | Change | Why |
|---|---|---|---|
| 1 | `backend/app/models/enums.py` `ENV_STATS` plus an Alembic migration (`ALTER TYPE "EnvStat" ADD VALUE ...`) | Add `DISTRICT_MIN`, `DISTRICT_MAX`, `TOTAL`, `DENSITY`, `DISTANCE`, `COUNT` | The layers emit them (`geo_etl/rows.py` `STATS`). Without them the copy into the staging table fails on the enum cast and the whole load rolls back. |
| 2 | `DistrictGeology` model and migration | `UniqueConstraint("districtLgd", "datasetId", "lithology")` | `load.py` uses `ON CONFLICT ("districtLgd", "datasetId", "lithology")`. Without the constraint it falls back to delete-then-insert in the same transaction, which works but is not safe against a concurrent load. |
| 3 | `DistrictGeology` model and migration (optional) | `lithologyName: String(300) NULL`, `method: Text NULL` | The geology parquet carries both. `load.py` writes only columns that exist, so they are dropped silently until added. |
| 4 | `DistrictEnvValue.pixelCount` | Keep `Integer`, or change to `Numeric(18, 3)` | The layers emit coverage-weighted pixel counts as floats. `load.py` rounds them to integers (`fit_values`), so `Integer` works today; `Numeric` would keep the fractional coverage. |
| 5 | `EnvDataset` (optional) | `url: Text NULL` | Every dataset row carries a landing URL; it is skipped while the column is absent. |

## Tables load.py assumes

Column names are the quoted camelCase names in Postgres. `load.py` reads `information_schema.columns` and writes only the columns present, but stops with a pointer to this file when a required column or table is missing.

### EnvDataset

- Required: `code` (unique), `title`, `licence`. `ON CONFLICT (code)` upserts and `RETURNING id, code` maps codes to ids.
- Written when present: `publisher`, `edition`, `period`, `nativeResolution`, `crs`, `licenceUrl`, `attribution`, `redistributable`, `retrievedAt`, `sha256`, `citation`, `url`, `createdAt`, `updatedAt` (`updatedAt` set to `now()` on update).
- Rows come from the summary JSON: `boundaries` (code `DR_DISTRICT_SHAPES`, with `sha256` of the shapes file) and every entry of `datasets`.

### DistrictEnvValue

- Key and unique constraint (already in the model): `districtLgd`, `datasetId`, `variable`, `depthOrPeriod`, `stat`.
- Required: the key plus `value`. Written when present: `valueText`, `unit`, `method`, `resolution`, `pixelCount`, `createdAt`, `updatedAt`.
- `depthOrPeriod` is never null; layers without a depth or period write `""`, matching the column's server default.
- `id` is filled with `gen_random_uuid()`.

### DistrictGeology

- Key: `districtLgd`, `datasetId`, `lithology`. Required: the key.
- Written when present: `lithologyName`, `areaShare`, `mineralOccurrences` (JSON text into `JSONB`), `method`, `createdAt`, `updatedAt`.

### AdminDistrict

- Read only: `select lgd`. Values and geology rows for districts not in this table are skipped and reported on stderr, so the foreign keys never fail. When the table does not exist, nothing is filtered. When it exists but is empty, `load.py` rolls back and exits 3.
- Filled by the backend: `python -m app.scripts.seed_districts` (in `backend/`, `app/services/district_seed.py`) upserts `AdminState` and `AdminDistrict` from `backend/app/data/lgd_register.json` and `district-shapes.json` (byte-identical to `etl/geo/data/`, sha256-checked). `backend-checks.yml` runs it after the migrations and `infra/deploy/blue_green.sh` runs it on every release after `seed_crafts` and `seed_claims`, so production has all districts before a `geo-etl` load.

## Output files

All in `etl/geo/out/` (or `--out`).

### district_env.parquet (`geo_etl/rows.py` `COLUMNS`)

| Column | Type | Loaded into |
|---|---|---|
| `districtLgd` | int | `DistrictEnvValue.districtLgd` |
| `stateLgd` | int | not loaded |
| `districtName` | str | not loaded |
| `datasetCode` | str | mapped to `DistrictEnvValue.datasetId` through `EnvDataset.code` |
| `variable` | str | `variable` |
| `depthOrPeriod` | str | `depthOrPeriod` |
| `stat` | str, one of `EnvStat` | `stat` |
| `value` | float or null | `value` |
| `valueText` | str or null | `valueText` |
| `unit` | str | `unit` |
| `method` | str | `method` |
| `pixelCount` | float or null | `pixelCount`, rounded |
| `resolution` | str | `resolution`: the grid the value was read at (WorldCover at its overview factor) |
| `source`, `version`, `licence` | str | not loaded; carried per row for audit and duplicated in `EnvDataset` |

`EnvStat` values the layers emit: `DISTRICT_MEAN`, `DISTRICT_P10`, `DISTRICT_P90`, `DISTRICT_MIN`, `DISTRICT_MAX`, `UNCERTAINTY_Q05_MEAN`, `UNCERTAINTY_Q95_MEAN`, `SHARE`, `CLASS`, `NORMAL`, `TOTAL`, `DENSITY`, `DISTANCE`, `COUNT`.

### district_geology.parquet (`geo_etl/layers/geology.py` `GEOLOGY_COLUMNS`)

`districtLgd`, `stateLgd`, `districtName`, `datasetCode`, `lithology`, `lithologyName`, `areaShare`, `mineralOccurrences` (list of objects), `method`, `source`, `version`, `resolution`, `licence`. Only `districtLgd`, `datasetCode` (as `datasetId`), `lithology`, `lithologyName`, `areaShare`, `mineralOccurrences` and `method` are loaded. The file is optional; `load.py` skips geology when it is absent.

### district_env_summary.json

`generatedAt`, `boundaries` (one dataset row), `datasets` (dataset rows with `code`, `title`, `publisher`, `edition`, `period`, `nativeResolution`, `crs`, `licence`, `licenceUrl`, `attribution`, `redistributable`, `citation`, `url`, `retrievedAt`), `layers` (per layer and shard: rows, geology rows, seconds, notes, options, failures, `districtsWithoutValues`, `districtsWithoutCells` (those of them measured with no valid cell) and `lostStates`, decision 0027 and its addendum), `rows`, `geologyRows`, `districts`, `variables` (distinct variables per dataset code), `districtsWithoutShapes`.

## Running load.py

```
python etl/geo/load.py --dry-run
python etl/geo/load.py
python etl/geo/load.py --prune
```

- Reads the database URL from the env var `DATABASE_URL` (override the name with `--dsn-env`). Never pass the value on the command line.
- `--out` points at another output directory (default `etl/geo/out`).
- `--dry-run` reads and validates the files (dataset codes known, no duplicate keys, every row has a value or text, geology keys unique) and prints the counts without connecting.
- `--prune` deletes rows for each `(datasetId, districtLgd)` pair in this load that are no longer in the files. Districts and datasets absent from the load are untouched.
- Exit codes: 0 loaded, 1 validation failed, 2 env var not set, 3 `AdminDistrict` empty. Everything runs in one transaction; any failure rolls back.
- Needs `psycopg` (v3) and `pandas` with `pyarrow`, all in `etl/geo/pyproject.toml`.
