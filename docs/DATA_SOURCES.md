# Data sources

Every per-district environment value in KalaVigyan comes from one of the open datasets below. The table mirrors `etl/geo/geo_etl/catalog.py` `ALL`, which is the source of truth: each row of `district_env.parquet` repeats its dataset's `source`, `version`, `resolution` and `licence`, and `etl/geo/load.py` writes the full record to `EnvDataset`. If this page and `catalog.py` disagree, `catalog.py` wins and this page is stale.

Owner direction: open datasets only, nothing that needs registration or a login. Heavy downloads run in GitHub Actions (`.github/workflows/geo-etl.yml`), never on a laptop.

## Datasets

| Code | Title | Publisher | Edition | Period | Native resolution | CRS |
|---|---|---|---|---|---|---|
| `DR_DISTRICT_SHAPES` | District shapes as drawn by the Designer Portal | Kaggle adityaradha007/indian-districts-geojson, joined to LGD by the Designer Portal | 791efb62cc30cf5d | 2026-10-17 | simplified to 0.01 degree, 0.001 degree coordinate grid | EPSG:4326 |
| `SOILGRIDS_2_0` | SoilGrids 2.0 | ISRIC World Soil Information | 2.0 | modelled, 2020 release | 250 m | Interrupted Goode Homolosine (ESRI:54052) |
| `ESA_WORLDCOVER_2021_V200` | ESA WorldCover 10 m 2021 v200 | European Space Agency | v200 | 2021 | 10 m (1/12000 degree) | EPSG:4326 |
| `HANSEN_GFC_2025_V1_13` | Global Forest Change 2000-2025 | University of Maryland, Department of Geographical Sciences | GFC-2025-v1.13 | 2000-2025 | 1 arc-second (about 30 m) | EPSG:4326 |
| `CHELSA_2_1_1981_2010` | CHELSA V2.1 climatologies 1981-2010 | Swiss Federal Institute for Forest, Snow and Landscape Research WSL | V2.1 | 1981-2010 | 30 arc-seconds (about 1 km) | EPSG:4326 |
| `CHIRPS_3_0` | Climate Hazards Center InfraRed Precipitation with Stations v3.0 | Climate Hazards Center, UC Santa Barbara | 3.0 | set per run (last 10 complete years by default) | 0.05 degree | EPSG:4326 |
| `COPERNICUS_DEM_GLO90` | Copernicus DEM GLO-90 | European Space Agency, Copernicus Programme | 2021_1 (AWS Open Data COG) | 2011-2015 acquisitions | 3 arc-seconds (about 90 m) | EPSG:4326 (EGM2008 heights) |
| `HYDRORIVERS_1_0` | HydroRIVERS v1.0 (Asia) | WWF HydroSHEDS | v10 | static | 15 arc-second network (reaches with upstream area >= 10 km2 or discharge >= 0.1 m3/s) | EPSG:4326 |
| `USGS_MRDS` | Mineral Resources Data System | U.S. Geological Survey | WFS snapshot at retrieval | compiled to 2011, no longer updated | point locations | EPSG:4326 |
| `GLIM_1_0_05DEG` | Global Lithological Map Database v1.0 (gridded to 0.5 degree) | Universitat Hamburg, via PANGAEA | 1.0 | 2012 | 0.5 degree | EPSG:4326 |

## Licence, attribution and redistribution

"Redistributable" means the derived district values may be shown publicly and exported. A dataset marked No may be used for internal analysis but its values or geometry must not be republished until its licence is confirmed.

| Code | Licence | Redistributable | Attribution to display | URL |
|---|---|---|---|---|
| `DR_DISTRICT_SHAPES` | Unconfirmed; indicative boundaries ([source](https://www.kaggle.com/datasets/adityaradha007/indian-districts-geojson)) | No | District boundaries are indicative. | https://www.kaggle.com/datasets/adityaradha007/indian-districts-geojson |
| `SOILGRIDS_2_0` | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) | Yes | SoilGrids 2.0, ISRIC World Soil Information | https://files.isric.org/soilgrids/latest/data/ |
| `ESA_WORLDCOVER_2021_V200` | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) | Yes | ESA WorldCover project 2021 / Contains modified Copernicus Sentinel data (2021) processed by ESA WorldCover consortium | https://esa-worldcover.s3.eu-central-1.amazonaws.com/v200/2021/map/ |
| `HANSEN_GFC_2025_V1_13` | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) | Yes | Hansen/UMD/Google/USGS/NASA | https://storage.googleapis.com/earthenginepartners-hansen/GFC-2025-v1.13/ |
| `CHELSA_2_1_1981_2010` | Open download without registration; licence text not confirmed on 2026-11-15 ([site](https://chelsa-climate.org/)) | No, until confirmed | CHELSA V2.1, Karger et al. | https://os.zhdk.cloud.switch.ch/chelsav2/GLOBAL/climatologies/1981-2010/ |
| `CHIRPS_3_0` | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) | Yes | Climate Hazards Center, UC Santa Barbara (CHIRPS3) | https://data.chc.ucsb.edu/products/CHIRPS/v3.0/ |
| `COPERNICUS_DEM_GLO90` | [Copernicus DEM licence (GLO-90 free worldwide)](https://registry.opendata.aws/copernicus-dem/) | Yes | Produced using Copernicus WorldDEM-90 (c) DLR e.V. 2010-2014 and (c) Airbus Defence and Space GmbH 2014-2018 provided under COPERNICUS by the European Union and ESA; all rights reserved | https://copernicus-dem-90m.s3.amazonaws.com/ |
| `HYDRORIVERS_1_0` | [HydroSHEDS License Agreement](https://www.hydrosheds.org/terms-of-use): free for non-commercial and commercial use, attribution required | Yes | HydroRIVERS, WWF HydroSHEDS (https://www.hydrosheds.org) | https://data.hydrosheds.org/file/HydroRIVERS/HydroRIVERS_v10_as_shp.zip |
| `USGS_MRDS` | [Public domain (U.S. Government work)](https://www.usgs.gov/information-policies-and-instructions/copyrights-and-credits) | Yes | U.S. Geological Survey Mineral Resources Data System | https://mrdata.usgs.gov/services/wfs/mrds |
| `GLIM_1_0_05DEG` | [CC BY 3.0](https://creativecommons.org/licenses/by/3.0/) | Yes | Hartmann and Moosdorf (2012), GLiM | https://doi.pangaea.de/10.1594/PANGAEA.788537?format=textfile |

## Citations

- `DR_DISTRICT_SHAPES`: designer-portal frontend/public/boundaries/district-shapes.json (shapesVersion 791efb62cc30cf5d).
- `SOILGRIDS_2_0`: Poggio, L., de Sousa, L. M., Batjes, N. H., et al. (2021). SoilGrids 2.0: producing soil information for the globe with quantified spatial uncertainty. SOIL 7, 217-240. https://doi.org/10.5194/soil-7-217-2021
- `ESA_WORLDCOVER_2021_V200`: Zanaga, D., Van De Kerchove, R., Daems, D., et al. (2022). ESA WorldCover 10 m 2021 v200. https://doi.org/10.5281/zenodo.7254221
- `HANSEN_GFC_2025_V1_13`: Hansen, M. C., Potapov, P. V., Moore, R., et al. (2013). High-Resolution Global Maps of 21st-Century Forest Cover Change. Science 342, 850-853. https://doi.org/10.1126/science.1244693. Data GFC-2025-v1.13.
- `CHELSA_2_1_1981_2010`: Karger, D. N., Conrad, O., Bohner, J., et al. (2017). Climatologies at high resolution for the earth's land surface areas. Scientific Data 4, 170122. https://doi.org/10.1038/sdata.2017.122
- `CHIRPS_3_0`: Climate Hazards Center InfraRed Precipitation with Stations version 3 (CHIRPS3) Data Repository (2025). https://doi.org/10.15780/G2JQ0P
- `COPERNICUS_DEM_GLO90`: European Space Agency (2024). Copernicus Global Digital Elevation Model. https://doi.org/10.5270/ESA-c5d3d65
- `HYDRORIVERS_1_0`: Lehner, B., Grill, G. (2013). Global river hydrography and network routing: baseline data and new approaches to study the world's large river systems. Hydrological Processes 27(15), 2171-2186. https://doi.org/10.1002/hyp.9740
- `USGS_MRDS`: U.S. Geological Survey. Mineral Resources Data System (MRDS). Reston, Virginia. https://mrdata.usgs.gov/mrds/
- `GLIM_1_0_05DEG`: Hartmann, J., Moosdorf, N. (2012). Global Lithological Map Database v1.0 (gridded to 0.5 degree spatial resolution). PANGAEA. https://doi.org/10.1594/PANGAEA.788537

## Live scholarly sources

Live research reads these services through `backend/app/sources/` (decision 0005) and cites each
work by DOI or the service's record URL; only short quoted passages are stored.

| Adapter | Service | Terms that bind us |
|---|---|---|
| `openalex` | OpenAlex works API | Metadata CC0; daily allowance per key or per IP |
| `crossref` | Crossref REST API, polite pool (`mailto`) | Metadata free to reuse; abstracts remain the publishers' |
| `semantic_scholar` | Semantic Scholar Academic Graph | API licence; publishers may elide abstracts |
| `core` | CORE API v3 | Key required; full texts keep their own licences |
| `europe_pmc` | Europe PMC REST | Per-article licence (the `licence` field) |
| `arxiv` | arXiv API | One request every 3 s; papers keep their own licences |
| `doaj` | DOAJ API v4 | Articles under their journals' licences |
| `elsevier`, `springer_nature` | Scopus, Springer Nature open access | Only with keys; quotes and DOI links, never a full copy (PLAN 17.1a) |
| Unpaywall (locator) | Unpaywall DOI API (`email`) | Open-access status and legal copy location only |

## Live reference sources

Read through `backend/app/sources/reference/` (decision 0006). Each item keeps its licence and
attribution; only short quoted passages are stored, with a link back.

| Adapter | Service | Licence and attribution |
|---|---|---|
| `wikipedia` | Wikipedia Action API (English and Indian-language wikis) | CC BY-SA 4.0, read live from each wiki's rightsinfo; attributed to "Wikipedia contributors" with the article title and revision |
| `wikidata` | Wikidata Action API and query service (SPARQL) | Structured data CC0 1.0; cited by item id and revision |
| `pubchem` | PubChem PUG REST and PUG View, National Library of Medicine | Compound properties: NCBI places no restrictions (https://www.ncbi.nlm.nih.gov/home/about/policies/). GHS hazards keep the reporting source's terms; for ECHA, non-commercial reuse with "Source: European Chemicals Agency, http://echa.europa.eu/" (https://echa.europa.eu/web/guest/legal-notice) |
| `wikimedia_commons` | Wikimedia Commons file metadata | Each file's own licence (short name and URL) and author, attributed "author, licence, via Wikimedia Commons" |

## Seeded reference passages (science engine)

The physical constants behind the stage envelopes (decision 0015) are claims in
`backend/app/data/science_seed.json`, each quoting one pinned Wikipedia revision (retrieved
2026-11-16; CC BY-SA 4.0, attributed "Wikipedia contributors" with title and revision).

| Constant | Article and revision | Value cited |
|---|---|---|
| Water boils at one atmosphere | Water, 1385775442 (Phase transitions) | 100 °C |
| Quartz α to β inversion | Quartz, 1383182792 (Crystal habit and structure) | 573 °C |
| Kaolinite dehydroxylation begins | Kaolinite, 1383311141 (Metakaolin) | 550–600 °C |
| Beeswax melts | Beeswax, 1382937264 (Physical characteristics) | 62 to 64 °C |
| Brass melts | Brass, 1382181158 (Properties) | 900 to 940 °C |

Seeded compounds are matched to PubChem records by `app/scripts/link_compounds` through the
`pubchem` adapter (terms above); each linked compound cites its PubChem record.

## Live web sources

Found through `backend/app/sources/web/` and read by the fetcher (decision 0007). A web page
keeps its own copyright: only short quoted passages are stored, each with the page title, site
name, final URL, fetch time and, when the page declares one, its licence; robots.txt is
honoured for the agent `KalaVigyan`.

| Adapter | Service | Terms |
|---|---|---|
| `searxng` | Self-hosted SearXNG metasearch on the box | Results come from the engines SearXNG queries; each hit links to its page |
| `brave` | Brave Web Search API (fallback, only with `BRAVE_SEARCH_API_KEY`) | Brave Search API terms; results are used to find pages, and the pages themselves are cited |

## Pictures from the web

Found through the image sources of decision 0034 and shown in an explainer's `images` block. A
picture is never copied into the media bucket: the reader's browser loads it from its own host,
with no referrer, and the card links to its page.

| Adapter | Service | Terms and credit |
|---|---|---|
| `wikimedia_commons` | Wikimedia Commons file search (`imageinfo`, 960 px thumbnails) | Each file's own licence; shown inline only under CC0, CC BY, CC BY-SA or public domain with its author, credited author, licence (linked) and Wikimedia Commons; otherwise a link card |
| `openverse` | Openverse image search (`api.openverse.org`, anonymous) | Only `by`, `by-sa`, `cc0` and `pdm` results with a creator; credited creator, licence and source site (Flickr, Wikimedia Commons, ...); the Openverse thumbnail is shown |
| `searxng` | SearXNG image results | No licence is known, so always a link card: the source site's own image as thumbnail, the page title and site, opening the page |

## Variables and statistics

Each row in `district_env.parquet` is one `(districtLgd, datasetCode, variable, depthOrPeriod, stat)`. Zonal statistics use exactextract with coverage-weighted, spherical-area cell weights, so partly covered edge cells count by the share inside the district. `depthOrPeriod` is `""` where it does not apply.

| Dataset (CLI layer) | Variable | depthOrPeriod | Stats | Unit |
|---|---|---|---|---|
| SoilGrids (`soilgrids`) | `clay`, `sand`, `silt` | `0-5cm`, `5-15cm`, `15-30cm` | `DISTRICT_MEAN`, `DISTRICT_P10`, `DISTRICT_P90`, `UNCERTAINTY_Q05_MEAN`, `UNCERTAINTY_Q95_MEAN` | % |
| | `soc` | same | same | g/kg |
| | `phh2o` | same | same | pH |
| | `cec` | same | same | cmol(c)/kg |
| | `bdod` | same | same | kg/dm3 |
| | `nitrogen` | same | same | g/kg |
| WorldCover (`worldcover`) | `landcover_tree_cover`, `landcover_shrubland`, `landcover_grassland`, `landcover_cropland`, `landcover_built_up`, `landcover_bare_sparse_vegetation`, `landcover_snow_ice`, `landcover_permanent_water`, `landcover_herbaceous_wetland`, `landcover_mangroves`, `landcover_moss_lichen` | `2021` | `SHARE` | fraction |
| Hansen GFC (`hansen`) | `treecover2000` | `2000` | `DISTRICT_MEAN` | % |
| | `forest_canopy30` | `2000` | `SHARE` | fraction of land |
| | `forest_canopy30_area` | `2000` | `TOTAL` | km2 |
| | `forest_loss_canopy30` | each year `2001` to `2025`, and `2001-2025` | `TOTAL` | km2 |
| | `forest_loss_canopy30_share` | `2001-2025` | `SHARE` | fraction of 2000 forest |
| CHELSA (`chelsa`) | `annual_mean_temperature` (bio1), `max_temperature_warmest_month` (bio5), `min_temperature_coldest_month` (bio6) | `1981-2010` | `NORMAL`, `DISTRICT_P10`, `DISTRICT_P90` | degC |
| | `annual_precipitation` (bio12) | `1981-2010` | same | mm/year |
| | `precipitation_seasonality` (bio15) | `1981-2010` | same | coefficient of variation % |
| | `mean_temperature` (tas) | `1981-2010-01` to `1981-2010-12` | same | degC |
| | `precipitation` (pr) | `1981-2010-01` to `1981-2010-12` | same | mm/month |
| CHIRPS (`chirps`) | `annual_precipitation` | each year of the run period | `DISTRICT_MEAN`, `DISTRICT_P10`, `DISTRICT_P90` | mm/year |
| | `annual_precipitation` | run period, e.g. `2016-2025` | `NORMAL` | mm/year |
| | `monthly_precipitation` | run period plus month, e.g. `2016-2025-07` | `NORMAL` | mm/month |
| | `monsoon_share_jjas` | run period | `NORMAL` | fraction of annual |
| Copernicus DEM (`copdem`) | `elevation` | | `DISTRICT_MEAN`, `DISTRICT_P10`, `DISTRICT_P90`, `DISTRICT_MIN`, `DISTRICT_MAX` | m |
| | `slope` | | `DISTRICT_MEAN`, `DISTRICT_P10`, `DISTRICT_P90` | degree |
| HydroRIVERS (`hydrorivers`) | `river_length`, `major_river_length` | | `TOTAL` | km |
| | `river_density` | | `DENSITY` | km/km2 |
| | `distance_centroid_to_major_river` | | `DISTANCE` | km |
| | `max_strahler_order` | | `DISTRICT_MAX` | Strahler order |
| | `max_discharge` | | `DISTRICT_MAX` | m3/s |
| USGS MRDS (`mrds`) | `mineral_occurrences`, and `mineral_occurrences_<commodity>` per commodity code found | | `COUNT` | sites |
| GLiM (`glim`) | `lithology_<code>` for each GLiM class present (`su`, `vb`, `ss`, `pb`, `sm`, `sc`, `va`, `mt`, `pa`, `vi`, `wb`, `py`, `pi`, `ev`, `nd`, `ig`) | | `SHARE` | fraction |

Method notes carried in each row's `method`:

- SoilGrids is read from the ISRIC WCS at native 250 m in Homolosine; stored integers are divided by the ISRIC conversion factor (10 for clay, sand, silt, soc, phh2o, cec; 100 for bdod and nitrogen). Uncertainty rows are the district mean of the Q0.05 and Q0.95 layers. SoilGrids masks built-up land, water and bare rock; a district masked throughout gets no SoilGrids rows and is listed under `districtsWithoutValues` and `districtsWithoutCells` in the summary (Mumbai, 482: 0 of 2,720 cells unmasked on 2026-11-17).
- WorldCover is read from the 3 degree COG tiles. The workflow can read an overview (`--worldcover-factor`, default 4, so about 40 m, nearest neighbour); the effective resolution is written to each row's `resolution`, loaded into `DistrictEnvValue.resolution` and sent with every region value and layer (decision 0016).
- Hansen forest is `treecover2000 >= 30%`; loss is counted only inside that 2000 forest, by `lossyear`.
- CHIRPS uses the last `--chirps-years` (default 10) complete years available; `monsoon_share_jjas` is June to September over the annual normal.
- Slope is computed from the DEM with central differences, using metres per degree at each row's latitude.
- HydroRIVERS lengths are reaches clipped to the district in WGS 84 / India NSF LCC. A major river is `ORD_FLOW <= 4` (long-term discharge of at least 100 m3/s). Distance is from the Designer Portal district centroid.

`district_geology.parquet` also gets one row per district per source: MRDS as `lithology = mineral_occurrences` with the matching sites as JSON in `mineralOccurrences`, and GLiM as one row per lithology class with `areaShare`.

## Choices and limits

### Geology: USGS MRDS points and GLiM at 0.5 degree

Geology uses two open sources only:

- **USGS MRDS** mineral occurrence points inside India, fetched from the public WFS by bounding box and assigned to districts by point-in-polygon. MRDS was compiled to 2011 and is no longer updated. Its India coverage is sparse and uneven, so a count of zero means "none recorded in MRDS", not "no deposits".
- **GLiM v1.0 gridded to 0.5 degree** (about 55 km), the GLiM product that downloads directly from PANGAEA as one small file. A district usually spans just a few cells, so lithology shares show the broad geological setting, not the rock under a given village. Lakshadweep (553) lies on no GLiM land cell, so it has no GLiM rows (Actions run 43949571146) and is listed under `districtsWithoutCells`.

These sources were considered and not used:

- **GSI Bhukosh / NGDR** (1:2M geology and mineral occurrences): downloads need a registered Bhukosh account, and there is no bulk download without logging in. That breaks the owner's no-registration rule. Revisit if GSI publishes an open bulk download; it would replace both MRDS and GLiM for India.
- **OneGeology**: a portal over national map services, with no bulk download for India. Reading it would mean scraping WMS tiles, which gives pictures, not attributes.

### Climate: CHELSA chosen over WorldClim

CHELSA V2.1 (1981-2010) was chosen over WorldClim 2.1 (1970-2000). It covers a more recent baseline at the same 30 arc-second resolution, and it handles terrain better through its orographic precipitation correction, which matters in the Himalayan and Western Ghats districts. Its GeoTIFFs are served as individual files from a public object store, so the workflow can read only the window it needs. WorldClim publishes zipped bundles that would have to be downloaded whole.

CHELSA's licence is **unconfirmed**. The files download openly without registration, but on 2026-11-15 we could not find a licence statement on the CHELSA site to cite. Until one is confirmed, `redistributable` is `false` and CHELSA values must stay internal: no public display, no export. If the licence turns out to be CC BY 4.0, change `redistributable` in `catalog.py`, re-run the load and update this page. CHIRPS v3.0 (CC BY 4.0) covers recent rainfall and can be shown publicly now.

### District boundaries are indicative and not redistributable

District polygons come from the Designer Portal's `district-shapes.json` (shapesVersion `791efb62cc30cf5d`), built from the Kaggle dataset `adityaradha007/indian-districts-geojson` and joined to LGD codes by `scripts/build_boundaries.py`. They are simplified and not the official Survey of India boundaries, and the Kaggle dataset states no licence. So:

- Every value here is a statistic over an **indicative** polygon. Districts created after the shapes were drawn have no polygon and are listed in the summary's `districtsWithoutShapes`.
- The polygons themselves **cannot be redistributed**: no download or export of the geometry. Showing them on a map in the portal must carry "District boundaries are indicative."
- The per-district numbers are derived from the open rasters, and their licence follows the source dataset in the tables above.
