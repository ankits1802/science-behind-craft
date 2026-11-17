import { readFileSync } from "node:fs";
import { join } from "node:path";

import { expect, test } from "@playwright/test";

import type { CraftPage } from "@/lib/craftPageContract";
import { pageSourceNumbers, pageSourcesById, sourceGroups } from "@/lib/craftPageView";
import { chosenLayerId } from "@/lib/mapLayers";
import { craftRegionShape, mapLayerListShape, mapLayerShape, type CraftRegion, type MapLayer, type RegionPlace } from "@/lib/regionContract";
import {
  checkedLayer,
  checkedRegion,
  datasetIndex,
  datasetMethods,
  datasetOf,
  inheritedNote,
  layerCaption,
  layerClassLabels,
  layerFills,
  layerOptions,
  layerSummary,
  placeSubtitle,
  regionHighlight,
  shownFacets,
  statCaption,
  toneIndex,
  valueLabel,
  valueProvenance,
  valueReading
} from "@/lib/regionView";
import { parseShape, ShapeError } from "@/lib/shape";

const SHARED = join(__dirname, "..", "..", "shared");

function golden<T>(name: string): T {
  return JSON.parse(readFileSync(join(SHARED, name), "utf8")) as T;
}

function region(edit: (body: CraftRegion) => void = () => undefined): CraftRegion {
  const body = golden<CraftRegion>("region.craft.golden.json");
  edit(body);
  return checkedRegion(parseShape(craftRegionShape, body));
}

function layer(edit: (body: MapLayer) => void = () => undefined): MapLayer {
  const body = golden<MapLayer>("region.layer.golden.json");
  edit(body);
  return checkedLayer(parseShape(mapLayerShape, body));
}

function inherited(place: RegionPlace): RegionPlace {
  return {
    ...place,
    valuesFrom: "STATE",
    inheritedReason: "NO_DISTRICT_POLYGON",
    facets: [
      {
        facet: "SOIL",
        values: [{ ...place.facets[0].values[0], aggregation: "STATE_AREA_MEAN", value: 7.6, districtCount: 31, districtTotal: 33 }]
      }
    ]
  };
}

test("each Kachchh value reads with its unit", () => {
  const values = region().places[0].facets.flatMap((facet) => facet.values);
  expect(values.map((value) => [valueLabel(value), valueReading(value)])).toEqual([
    ["Clay, 0–5 cm", "27.4%"],
    ["Soil pH (in water), 0–5 cm", "pH 8.1"],
    ["Annual mean temperature", "26.6 °C"],
    ["Annual precipitation", "372.4 mm/year"],
    ["Bare or sparse vegetation", "31.2%"],
    ["Cropland", "23.6%"],
    ["Elevation", "52.3 m"],
    ["Mineral sites", "41 sites"]
  ]);
});

test("every value names its statistic, dataset, grid and period", () => {
  const body = region();
  const index = datasetIndex(body.datasets);
  const [soil, , , , cover] = body.places[0].facets.flatMap((facet) => facet.values);
  expect(valueProvenance(soil, datasetOf(index, soil.datasetCode))).toBe("District mean · SoilGrids 2.0 · 250 m · modelled, 2020 release");
  expect(valueProvenance(cover, datasetOf(index, cover.datasetCode))).toBe(
    "Share of district area · ESA WorldCover 10 m 2021 v200 · 40 m (overview read, factor 4, nearest) · 2021"
  );
});

test("a district place names its district and is highlighted alone", () => {
  const body = region();
  const place = body.places[0];
  expect(placeSubtitle(place)).toBe("Kachchh district · Gujarat");
  expect(inheritedNote(place)).toBeNull();
  expect(shownFacets(place).map((facet) => facet.facet)).toEqual(["SOIL", "CLIMATE", "LAND_COVER", "TERRAIN", "GEOLOGY"]);
  const highlight = regionHighlight(body);
  expect([...highlight.districts]).toEqual([449]);
  expect([...highlight.states]).toEqual([]);
});

test("facets arriving out of order are shown in the contract order", () => {
  const body = region((value) => value.places[0].facets.reverse());
  expect(shownFacets(body.places[0]).map((facet) => facet.facet)).toEqual(["SOIL", "CLIMATE", "LAND_COVER", "TERRAIN", "GEOLOGY"]);
});

test("a district without an outline shows its state's values and says so", () => {
  const body = region((value) => (value.places[0] = inherited(value.places[0])));
  const place = body.places[0];
  expect(inheritedNote(place)).toBe("Values for Gujarat as a whole; Kachchh has no district outline.");
  expect(statCaption(place.facets[0].values[0])).toBe("State mean, area-weighted of 31 of 33 districts");
  expect([...regionHighlight(body).states]).toEqual([24]);
  expect([...regionHighlight(body).districts]).toEqual([]);
});

test("a state of practice reads as practised across the state", () => {
  const body = region((value) => {
    value.places[0] = {
      ...value.places[0],
      key: "state-24",
      scope: "STATE",
      districtLgd: null,
      districtName: null,
      placeLabel: "Gujarat",
      basis: { kind: "MASTER_LIST", sourceId: null, label: "IIT Crafts Master List, 2026-10-20", level: "REVIEWED" },
      valuesFrom: "STATE",
      facets: []
    };
  });
  const place = body.places[0];
  expect(placeSubtitle(place)).toBe("Practised across the state");
  expect(inheritedNote(place)).toBeNull();
  expect(shownFacets(place)).toEqual([]);
  expect([...regionHighlight(body).states]).toEqual([24]);
});

test("a craft with no places has nothing to highlight", () => {
  const body = region((value) => (value.places = []));
  const highlight = regionHighlight(body);
  expect(highlight.districts.size + highlight.states.size).toBe(0);
});

test("a geology share reads as its rock type and share", () => {
  const body = region((value) => {
    value.places[0].facets[4].values = [{ ...value.places[0].facets[4].values[0], variable: "lithology", valueText: "Sandstone", value: 0.42, unit: "fraction", stat: "SHARE" }];
  });
  expect(valueReading(body.places[0].facets[4].values[0])).toBe("Sandstone · 42%");
  expect(valueLabel(body.places[0].facets[4].values[0])).toBe("Rock type");
});

test("each dataset lists its distinct methods once", () => {
  const methods = datasetMethods(region());
  expect(methods.get("CHELSA_2_1_1981_2010")).toHaveLength(1);
  expect(methods.get("SOILGRIDS_2_0")).toHaveLength(1);
  expect([...methods.keys()].sort()).toEqual(["CHELSA_2_1_1981_2010", "COPERNICUS_DEM_GLO90", "ESA_WORLDCOVER_2021_V200", "SOILGRIDS_2_0", "USGS_MRDS"]);
});

test("a location's source is numbered and linked even when no claim cites it", () => {
  const body = region();
  const [place] = body.places;
  const page: CraftPage = {
    schemaVersion: 1,
    craft: { slug: "Kutch-Ajrakh", name: "Kutch Ajrakh", path: "/crafts/Kutch-Ajrakh", id: "c", localName: null, categoryName: null, subCategoryName: null, giStatus: "GI", stateOfPractice: [], stateOfOrigin: [] },
    curated: false,
    curation: null,
    overview: { lede: [], keyFacts: [], sections: [] },
    sourcesDiffer: [],
    places: [],
    communities: [],
    process: { processId: null, stages: [], reactions: [] },
    glossary: [],
    pictures: [],
    openQuestions: [],
    evidence: { groups: [], hypotheses: [] },
    claims: [],
    sources: []
  };
  const numbers = pageSourceNumbers(page, body.sources);
  const byId = pageSourcesById(page, body.sources);
  expect(place.basis.kind).toBe("CRAFT_LOCATION");
  expect(numbers.get(place.basis.sourceId ?? "")).toBe(1);
  expect(byId.get(place.basis.sourceId ?? "")?.url).toBe("https://search.ipindia.gov.in/GIRPublicSearch/Application/Details/1050");
  expect(sourceGroups(byId.values(), numbers).flatMap((group) => group.sources.map((source) => source.id))).toEqual([place.basis.sourceId]);
});

test("the client refuses a place whose source is not listed", () => {
  expect(() => region((value) => (value.sources = []))).toThrow(ShapeError);
});

test("the client refuses a value whose dataset is not listed", () => {
  expect(() => region((value) => (value.datasets = value.datasets.filter((dataset) => dataset.code !== "USGS_MRDS")))).toThrow(ShapeError);
});

test("every district value falls in its quantile class", () => {
  const fills = layerFills(layer());
  expect(Object.fromEntries([...fills.entries()].map(([lgd, band]) => [String(lgd), band]))).toEqual({
    "438": 2,
    "441": 1,
    "444": 0,
    "447": 3,
    "449": 4,
    "455": 3,
    "459": 1,
    "460": 4,
    "462": 0
  });
});

test("the legend, caption and summary read from the layer", () => {
  const soil = layer();
  expect(layerClassLabels(soil)).toEqual(["pH 6.40–7.08", "pH 7.08–7.64", "pH 7.64–7.88", "pH 7.88–8.04", "pH 8.04–8.30"]);
  expect(layerCaption(soil)).toBe("District mean · SoilGrids 2.0 · 250 m · modelled, 2020 release");
  expect(layerSummary(soil)).toBe("Soil pH, 0-5 cm: 9 districts, pH 6.4–8.3.");
});

test("an empty layer or a mismatched dataset is refused", () => {
  expect(() => layer((value) => (value.values = {}))).toThrow(ShapeError);
  expect(() => layer((value) => (value.layer = { ...value.layer, datasetCode: "CHELSA_2_1_1981_2010" }))).toThrow(ShapeError);
});

test("layers are offered by facet and a requested id must be listed", () => {
  const list = parseShape(mapLayerListShape, golden("region.layers.golden.json"));
  expect(layerOptions(list).map((option) => [option.group, option.value, option.hint])).toEqual([
    ["Soil", "soil-ph-0-5cm", "modelled, 2020 release"],
    ["Climate", "annual-mean-temperature", "1981-2010"],
    ["Land cover", "cropland-share", "2021"]
  ]);
  expect(chosenLayerId(list, "cropland-share")).toBe("cropland-share");
  expect(chosenLayerId(list, "rainfall")).toBeNull();
  expect(chosenLayerId(list, null)).toBeNull();
  expect(chosenLayerId(null, "cropland-share")).toBeNull();
});

test("fewer classes spread across the colour ramp", () => {
  expect([0, 1, 2, 3, 4].map((band) => toneIndex(band, 5, 5))).toEqual([0, 1, 2, 3, 4]);
  expect(toneIndex(0, 1, 5)).toBe(2);
  expect([0, 1].map((band) => toneIndex(band, 2, 5))).toEqual([0, 4]);
  expect([0, 1, 2].map((band) => toneIndex(band, 3, 5))).toEqual([0, 2, 4]);
  expect(() => toneIndex(5, 5, 5)).toThrow(RangeError);
});
