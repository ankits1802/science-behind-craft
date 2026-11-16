# Region contract: a craft's environment and the map layers (lane: region profile, decision 0016)

What the region panel of a craft page and the map's choropleths receive. The models are
`backend/app/schemas/region.py`; the client's types and shapes `frontend/lib/regionContract.ts`;
the golden answers `shared/region.craft.golden.json`, `shared/region.layers.golden.json` and
`shared/region.layer.golden.json`. Change them together with
`backend/tests/contracts/test_region_contract.py` and `frontend/e2e/contracts-unit.spec.ts`.
Design choices: decision 0014; the producer: decision 0016 (`backend/app/geo/`,
`services/region_records.py`, `services/map_layer_store.py`). PLAN 8 is the specification, PLAN 0 overrides it, and the stored
tables are the geo lane's (`docs/contracts/geo.md`, `docs/DATA_SOURCES.md`).

Last reviewed: 2026-11-16.

Golden values are shapes for tests, not measurements: the district numbers in the fixtures are
written by hand. The dataset rows are the real `EnvDataset` rows from `etl/geo`. The layer file's
`classes` and `version` are what the server computes from those numbers (decision 0016).
`backend/tests/geo/` rebuilds all three from records and `backend/tests/db/test_region_db.py`
from stored rows.

## Routes

| Method | Path | Auth | Answer |
|---|---|---|---|
| GET | `/api/crafts/{slug}/region` | signed in | `CraftRegion`; 404 for an unknown slug; a `MERGED` slug answers with its target's region |
| GET | `/api/map/layers` | signed in | `MapLayerList`; 404 while no `DR_DISTRICT_SHAPES` dataset row is stored (nothing could cite the boundary) |
| GET | `/api/map/layers/{layer}` | signed in | `MapLayer`; 404 for an unknown or empty layer, or without the boundary row. `ETag: "<version>"`; a matching `If-None-Match` answers 304 |

`Cache-Control: private, no-cache` on all three (CloudFront never caches `/api`, PLAN 15).
Nothing is queried live: every value is a stored per-district aggregate (PLAN 17.1).

## CraftRegion

```
CraftRegion {schemaVersion: 1, craft: CraftRef, places: RegionPlace[], datasets: RegionDataset[],
             sources: SourceRef[]}
RegionPlace {key, scope: DISTRICT|STATE, stateLgd, stateName, districtLgd|null, districtName|null,
             placeLabel, basis: PlaceBasis, valuesFrom: DISTRICT|STATE, inheritedReason|null,
             facets: RegionFacet[]}
PlaceBasis {kind: CRAFT_LOCATION|MASTER_LIST, sourceId|null, label, level}
RegionFacet {facet, values: RegionValue[] (>=1)}
RegionValue {datasetCode, variable, depth|null, period, stat, aggregation, value|null, valueText|null,
             unit, resolution, method|null, districtCount|null, districtTotal|null}
RegionDataset {code, title, publisher|null, edition, period, nativeResolution, licence,
               licenceUrl|null, attribution|null, citation|null, url|null}
```

### Places

- One `DISTRICT` place per `CraftLocation` of precision `DISTRICT`, and per `POINT` location (the
  district whose polygon covers the point, the lowest LGD when indicative polygons overlap, else
  the location's own `districtLgd`; a point in no district is not shown). `basis` is
  `CRAFT_LOCATION` with the location's `sourceId` and that source's title as `label`, and the
  location's `evidenceLevel`. A location without a source, or whose source is `RESTRICTED`, is not
  shown (every fact cites) and is logged. Two locations in one district are one place, cited by
  the stronger level (ties by location id).
- One `STATE` place per state in `Craft.stateOfPractice` that has no district place:
  `basis` `MASTER_LIST`, `sourceId` null, `label` `IIT Crafts Master List, 2026-10-20`
  (`MASTER_LIST_LABEL`), level `REVIEWED` (the profile's level for the master list,
  `geo/places.MASTER_LIST_LEVEL`). The client says "Practised across the state". A cited
  `CraftLocation` of precision `STATE` is a state place too, basis `CRAFT_LOCATION`; when the
  master list also names that state, the stronger level wins and a cited location wins a tie.
  `All India` is not a state; any other name without an LGD state is logged.
- `key` is `district-<lgd>` or `state-<lgd>` (`place_key`); each place appears once. Order:
  district places by state name, then district name; then state places by name.
- A craft with no state and no location has no places; the client then leaves the panel out.
- `sources` holds the `SourceRef` (the answer stream's shape) of every `basis.sourceId` once, in
  the order of the places (`schemas/region.basis_source_ids`); a state of practice adds none. The
  craft page numbers them after the profile's and the process's sources (`craftSources`), so a
  location's source always has its number, link and Sources entry even when no claim cites it
  (decision 0022).

### Values

- **District values** (`valuesFrom` `DISTRICT`): every `DistrictEnvValue` row of the district,
  `aggregation` `DISTRICT`, no district counts. Geology rows (`DistrictGeology`) with an area
  share become `variable` `lithology`, `valueText` the lithology name (its code when a row has no
  name), `value` the area share, `stat` `SHARE`, `unit` `fraction`. GLiM also stores each share as
  a `DistrictEnvValue` `lithology_<code>`; those twins are not read (`LITHOLOGY_TWIN_PREFIX`).
  Geology rows without a share (the MRDS occurrence list) are not values.
- **Order within a facet**: dataset code, variable, depth from the surface down, period,
  `ENV_STATS` order, value text (`geo/region_view.value_order`).
- **Inherited districts.** A district with no polygon (34 LGD districts and 9 pending ones today,
  `district_env_summary.json` `districtsWithoutShapes`) has no rows. Its place shows its state's
  aggregates, `valuesFrom` `STATE`, `inheritedReason` `NO_DISTRICT_POLYGON`, and the client says
  so (PLAN 8).
- **State aggregates** (`valuesFrom` `STATE`), over the state's districts with polygons that
  have the value, weighted by district area (`ST_Area` of `AdminDistrict.geom` on the sphere):
  `DISTRICT_MEAN`, `NORMAL`, `SHARE` and `DENSITY` become `STATE_AREA_MEAN`; `TOTAL` and `COUNT`
  `STATE_SUM`; `DISTRICT_MIN` `STATE_MIN`; `DISTRICT_MAX` `STATE_MAX` (`STATE_AGGREGATIONS`).
  Percentiles, uncertainty, `CLASS` and `DISTANCE` have no state aggregate and are left out.
  `districtCount` is how many districts contributed and `districtTotal` how many the state has.
  GLiM class shares and MRDS per-commodity counts are stored only where the class or commodity
  occurs, so for those (`ABSENT_MEANS_ZERO`) every district of the state holding any value of the
  dataset contributes, with zero where its row is absent. A state value's `resolution` lists
  every grid its districts were read at (`; ` between them) and `method` their distinct methods.
  Values are rounded to 6 decimals.
- **Depth and period.** `depthOrPeriod` is split by `split_depth_or_period`: a value like `0-5cm`
  (`DEPTH_PATTERN`) is the `depth` and the dataset's period is the `period`; any other non-empty
  value is the `period`; empty takes the dataset's period.
- **Resolution** is the grid the value was read at. For most rows that is the dataset's
  `nativeResolution`, but ESA WorldCover is read at 40 m from its 10 m grid. The ETL already
  writes it per row (`district_env.parquet` `resolution`) and `load.py` loads it into
  `DistrictEnvValue.resolution` (migration 0005, which also fills it for WorldCover and Copernicus
  DEM rows loaded earlier from their method text). A row without it is sent with the dataset's
  `nativeResolution`.
- Every value names its dataset by `datasetCode`; `datasets` lists each cited dataset once,
  sorted by code, so the client can show "District mean · CHELSA V2.1 30 arc-seconds · 1981-2010"
  and the licence and attribution.

### Facets

`REGION_FACETS` in this order: `SOIL`, `CLIMATE`, `WATER`, `FOREST`, `LAND_COVER`, `TERRAIN`,
`GEOLOGY`. A facet with no value for a place is left out, never sent empty (PLAN 8). The dataset
of a value decides its facet (`DATASET_FACETS`):

| Facet | Datasets |
|---|---|
| SOIL | `SOILGRIDS_2_0` |
| CLIMATE | `CHELSA_2_1_1981_2010`, `CHIRPS_3_0` |
| WATER | `HYDRORIVERS_1_0` |
| FOREST | `HANSEN_GFC_2025_V1_13` |
| LAND_COVER | `ESA_WORLDCOVER_2021_V200` |
| TERRAIN | `COPERNICUS_DEM_GLO90` |
| GEOLOGY | `USGS_MRDS`, `GLIM_1_0_05DEG` |

A test fails when `etl/geo/geo_etl/catalog.py` gains a dataset without a row here. At run time a
value of an unmapped dataset is left out and logged with its code.

## Map layers

```
MapLayerList {layers: MapLayerSummary[], datasets: RegionDataset[], boundary: BoundaryNote}
MapLayerSummary {id, facet, title, datasetCode, variable, depth|null, period, stat, unit}
MapLayer {layer: MapLayerSummary, dataset: RegionDataset, resolution, classes: LayerClass[] (1-5),
          values: {"<district lgd>": number}, version, boundary: BoundaryNote}
LayerClass {min, max}
BoundaryNote {caption, dataset}
```

- Layers are a registry (`geo/layers.MAP_LAYERS`, decision 0016), each one dataset, variable,
  stored depth or period and stat, with an id of lowercase words and hyphens (`soil-ph-0-5cm`),
  in facet order. Only layers with at least one district value are listed, in registry order.
  The unit is the stored rows' one unit; a CHIRPS layer's period is its dataset row's period.
  A layer's `resolution` lists every grid its values were read at.
- `values` maps each district LGD code (as a string) to its value; districts with no value are
  absent and drawn as no data.
- `classes`: at most `LAYER_CLASS_MAX` (5) and at most as many as there are distinct values,
  rising and contiguous (each `max` is the next `min`), from the lowest to the highest value. The
  inner breaks are Hyndman and Fan type 7 quantiles (`statistics.quantiles(..., method=
  "inclusive")`) at 3 significant figures, dropped when they fall on either end. A value belongs
  to the class with `min <= value < max`; the top class also holds its `max` (`layerClassOf`).
- `version` is the SHA-256 hex of the canonical JSON (sorted keys, separators `,` and `:`, UTF-8)
  of every other field of the body, sent as the ETag, so any change the body shows moves it.
- `boundary` is the caption PLAN 8 requires, word for word, `External boundaries of India as
  depicted by Survey of India. District boundaries are indicative.` (`BOUNDARY_CAPTION`), over
  the `DR_DISTRICT_SHAPES` dataset, drawn beneath every map. The DR outline is the only
  international border drawn; there is no tile basemap.
- Geography and environment data are open datasets only (PLAN 0).
