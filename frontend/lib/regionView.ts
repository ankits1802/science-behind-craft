import { formatRange, formatMeasure } from "@/lib/measure";
import {
  INHERITED_REASON,
  layerClassOf,
  REGION_FACETS,
  type CraftRegion,
  type MapLayer,
  type MapLayerList,
  type RegionDataset,
  type RegionFacet,
  type RegionFacetName,
  type RegionPlace,
  type RegionValue
} from "@/lib/regionContract";
import { ShapeError } from "@/lib/shape";

export const FACET_LABEL: Record<RegionFacetName, string> = {
  SOIL: "Soil",
  CLIMATE: "Climate",
  WATER: "Water",
  FOREST: "Forest",
  LAND_COVER: "Land cover",
  TERRAIN: "Terrain",
  GEOLOGY: "Geology"
};

const STAT_LABEL: Record<RegionValue["stat"], string> = {
  DISTRICT_MEAN: "District mean",
  DISTRICT_P10: "District 10th percentile",
  DISTRICT_P90: "District 90th percentile",
  UNCERTAINTY_Q05_MEAN: "Lower uncertainty bound (5%)",
  UNCERTAINTY_Q95_MEAN: "Upper uncertainty bound (95%)",
  SHARE: "Share of district area",
  CLASS: "District class",
  NORMAL: "Climate normal",
  DISTRICT_MIN: "District minimum",
  DISTRICT_MAX: "District maximum",
  TOTAL: "District total",
  DENSITY: "District density",
  DISTANCE: "Distance",
  COUNT: "Count in district",
  TREND_PER_DECADE: "Trend per decade (Sen's slope)",
  TREND_P_VALUE: "Trend significance (Mann–Kendall)"
};

const STATE_AGGREGATION_LABEL: Record<Exclude<RegionValue["aggregation"], "DISTRICT">, string> = {
  STATE_AREA_MEAN: "State mean, area-weighted",
  STATE_SUM: "State total",
  STATE_MIN: "State minimum",
  STATE_MAX: "State maximum"
};

const VARIABLE_LABEL: Record<string, string> = {
  phh2o: "Soil pH (in water)",
  soc: "Soil organic carbon",
  cec: "Cation exchange capacity",
  annual_mean_temperature: "Annual mean temperature",
  max_temperature_warmest_month: "Warmest-month maximum temperature",
  min_temperature_coldest_month: "Coldest-month minimum temperature",
  annual_precipitation_cv: "Year-to-year precipitation variation",
  monsoon_share_jjas: "Monsoon share, June–September",
  distance_centroid_to_major_river: "Distance to a major river",
  max_strahler_order: "Largest river order",
  max_discharge: "Largest river discharge",
  treecover2000: "Tree cover in 2000",
  mineral_occurrences: "Mineral sites",
  lithology: "Rock type",
  bare_sparse_vegetation: "Bare or sparse vegetation",
  built_up: "Built-up",
  snow_ice: "Snow and ice",
  moss_lichen: "Moss and lichen"
};

const LAND_COVER_PREFIX = "landcover_";

function sentenceCase(code: string): string {
  const words = code.replace(/_+/g, " ").trim();
  return words ? words.charAt(0).toUpperCase() + words.slice(1) : code;
}

export function variableLabel(variable: string): string {
  const code = variable.startsWith(LAND_COVER_PREFIX) ? variable.slice(LAND_COVER_PREFIX.length) : variable;
  return VARIABLE_LABEL[code] ?? sentenceCase(code);
}

export function depthText(depth: string): string {
  return depth.replace(/^(\d+)-(\d+)cm$/, "$1–$2 cm");
}

export function valueLabel(value: Pick<RegionValue, "variable" | "depth">): string {
  return value.depth ? `${variableLabel(value.variable)}, ${depthText(value.depth)}` : variableLabel(value.variable);
}

export function valueReading(value: RegionValue): string {
  if (value.valueText !== null) return value.value === null ? value.valueText : `${value.valueText} · ${formatMeasure(value.value, value.unit)}`;
  if (value.value === null) throw new ShapeError(`value ${value.datasetCode}.${value.variable}`, "a value or a value text");
  return formatMeasure(value.value, value.unit);
}

export function statCaption(value: RegionValue): string {
  if (value.aggregation === "DISTRICT") return STAT_LABEL[value.stat];
  const label = STATE_AGGREGATION_LABEL[value.aggregation];
  if (value.districtCount === null || value.districtTotal === null) return label;
  return `${label} of ${value.districtCount} of ${value.districtTotal} districts`;
}

export function valueProvenance(value: RegionValue, dataset: RegionDataset): string {
  return [statCaption(value), dataset.title, value.resolution, value.period].join(" · ");
}

export const STATE_PLACE_NOTE = "Practised across the state";

export function placeSubtitle(place: RegionPlace): string {
  if (place.scope === "STATE") return STATE_PLACE_NOTE;
  return place.districtName ? `${place.districtName} district · ${place.stateName}` : place.stateName;
}

export function inheritedNote(place: RegionPlace): string | null {
  if (place.scope !== "DISTRICT" || place.valuesFrom !== "STATE") return null;
  const whole = `Values for ${place.stateName} as a whole`;
  if (place.inheritedReason === INHERITED_REASON && place.districtName) return `${whole}; ${place.districtName} has no district outline.`;
  return `${whole}.`;
}

export function shownFacets(place: RegionPlace): RegionFacet[] {
  return place.facets.slice().sort((a, b) => REGION_FACETS.indexOf(a.facet) - REGION_FACETS.indexOf(b.facet));
}

export function datasetIndex(datasets: readonly RegionDataset[]): Map<string, RegionDataset> {
  return new Map(datasets.map((dataset) => [dataset.code, dataset]));
}

export function datasetOf(index: Map<string, RegionDataset>, code: string): RegionDataset {
  const dataset = index.get(code);
  if (!dataset) throw new ShapeError(`dataset ${code}`, "a dataset listed with the values");
  return dataset;
}

export function checkedRegion(region: CraftRegion): CraftRegion {
  const index = datasetIndex(region.datasets);
  const sourceIds = new Set(region.sources.map((source) => source.id));
  for (const place of region.places) {
    if (place.basis.sourceId && !sourceIds.has(place.basis.sourceId)) throw new ShapeError(`source ${place.basis.sourceId}`, "a source listed with the places");
    for (const facet of place.facets) {
      for (const value of facet.values) {
        datasetOf(index, value.datasetCode);
        valueReading(value);
      }
    }
  }
  return region;
}

export function datasetMethods(region: CraftRegion): Map<string, string[]> {
  const methods = new Map<string, string[]>();
  for (const place of region.places) {
    for (const facet of place.facets) {
      for (const value of facet.values) {
        if (!value.method) continue;
        const known = methods.get(value.datasetCode) ?? [];
        if (!known.includes(value.method)) methods.set(value.datasetCode, [...known, value.method]);
      }
    }
  }
  return methods;
}

export function toneIndex(classIndex: number, classCount: number, toneCount: number): number {
  if (classCount < 1 || classIndex < 0 || classIndex >= classCount) throw new RangeError(`class ${classIndex} of ${classCount}`);
  if (classCount === 1) return Math.floor((toneCount - 1) / 2);
  return Math.round((classIndex * (toneCount - 1)) / (classCount - 1));
}

export type RegionHighlight = { districts: Set<number>; states: Set<number> };

export function regionHighlight(region: CraftRegion): RegionHighlight {
  const districts = new Set<number>();
  const states = new Set<number>();
  for (const place of region.places) {
    if (place.scope === "DISTRICT" && place.valuesFrom === "DISTRICT" && place.districtLgd !== null) districts.add(place.districtLgd);
    else states.add(place.stateLgd);
  }
  return { districts, states };
}

export function checkedLayer(layer: MapLayer): MapLayer {
  if (layer.layer.datasetCode !== layer.dataset.code) throw new ShapeError(`layer ${layer.layer.id}.dataset`, `dataset ${layer.layer.datasetCode}`);
  if (Object.keys(layer.values).length === 0) throw new ShapeError(`layer ${layer.layer.id}.values`, "at least one district value");
  layerFills(layer);
  return layer;
}

export function layerFills(layer: MapLayer): Map<number, number> {
  return new Map(Object.entries(layer.values).map(([lgd, value]) => [Number(lgd), layerClassOf(layer, value)]));
}

export const NO_DATA_LABEL = "No data";

export function districtReading(layer: MapLayer, lgd: number): string {
  const value = layer.values[String(lgd)];
  return value === undefined ? NO_DATA_LABEL : formatMeasure(value, layer.layer.unit);
}

export function layerClassLabels(layer: MapLayer): string[] {
  return layer.classes.map((band) => formatRange(band.min, band.max, layer.layer.unit) ?? "");
}

export function layerSummary(layer: MapLayer): string {
  const values = Object.values(layer.values);
  const count = values.length;
  const span = formatRange(Math.min(...values), Math.max(...values), layer.layer.unit);
  return `${layer.layer.title}: ${count} ${count === 1 ? "district" : "districts"}, ${span}.`;
}

export function layerOptions(list: MapLayerList): { value: string; label: string; group: string; hint: string }[] {
  return list.layers
    .map((layer, at) => ({ layer, at }))
    .sort((a, b) => REGION_FACETS.indexOf(a.layer.facet) - REGION_FACETS.indexOf(b.layer.facet) || a.at - b.at)
    .map(({ layer }) => ({ value: layer.id, label: layer.title, group: FACET_LABEL[layer.facet], hint: layer.period }));
}

export function layerCaption(layer: MapLayer): string {
  return [STAT_LABEL[layer.layer.stat], layer.dataset.title, layer.resolution, layer.layer.period].join(" · ");
}
