import { readFileSync } from "node:fs";
import { join } from "node:path";

import { expect, test } from "@playwright/test";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";

import { TimelinePins } from "@/components/answer/journey/TimelinePins";
import { nearBlocksLoaded } from "@/components/answer/nearBlock";
import { viewBoxOf, type MapBox, type NeighbourFile } from "@/components/map/basemap";
import { WHOLE_MAP } from "@/components/map/layout";
import { KM_PER_DEGREE_LATITUDE, ringRadii, SCALE_SHARE, SCALE_STEPS, scaleBar } from "@/components/map/mapDistance";
import { framedPoints, mapLayerFrame } from "@/components/map/mapLayerFrame";
import { placesFrame } from "@/components/map/placesFrame";
import { rangeLabels, riverLabels } from "@/components/map/placesMapLabels";
import { PlacesOverlay } from "@/components/map/PlacesOverlay";
import { stillLayers, type StillFiles } from "@/components/map/mapStillCut";
import { indiaOutlinePath, project } from "@/components/map/projection";
import type { ShapesFile } from "@/components/map/shapeGeometry";
import { COMPONENT_VIEWS } from "@/components/monograph/componentViews";
import { mapLayerSpecShape, parsedSpec, type MapLayerSpec } from "@/lib/componentSpecsGeneral";
import { homeDistrictsOf, shownMarks, valueClasses, valueClassOf } from "@/lib/componentSpecsMapLayer";
import type { ComponentView } from "@/lib/componentViewContract";
import { parseKindFixtures } from "@/lib/kindFixtures";
import { kindPreviewDocument } from "@/lib/kindPreview";
import type { MineralsFile, ReliefFile, RiversFile } from "@/lib/mapPhysical";
import { parsedMapLayer } from "@/lib/regionView";
import { placesMaps, placesStilledDocument, stillOfPlaces } from "@/lib/server/mapStills";
import { parseShape } from "@/lib/shape";

import { attribute, shownText, withApp } from "./explainerRender";
import { primitivesPage } from "./primitivesPage";

test.beforeAll(() => nearBlocksLoaded());

const FRONTEND = join(__dirname, "..");
const REPO = join(FRONTEND, "..");
const read = <T>(...parts: string[]): T => JSON.parse(readFileSync(join(...parts), "utf8")) as T;
const FILES: StillFiles = {
  relief: read<ReliefFile>(FRONTEND, "public", "layers", "relief.json"),
  rivers: read<RiversFile>(FRONTEND, "public", "layers", "rivers.json"),
  minerals: read<MineralsFile>(FRONTEND, "public", "layers", "minerals.json"),
  shapes: read<ShapesFile>(FRONTEND, "public", "boundaries", "district-shapes.json"),
  neighbours: read<NeighbourFile>(FRONTEND, "public", "boundaries", "neighbours.json")
};
const LAYERS = stillLayers(FILES);
const RELIEF = read<ReliefFile>(FRONTEND, "public", "layers", "relief.json");
const RIVERS = read<RiversFile>(FRONTEND, "public", "layers", "rivers.json");
const BOUNDARY = parsedMapLayer(read<unknown>(REPO, "shared", "region.layer.golden.json")).boundary;
const STILL_OF = stillOfPlaces(LAYERS, BOUNDARY);
const JAIPUR = 102;
const SUBJECTS = ["craft:Sanganeri-Hand-Block-Printing", `place:lgd:${JAIPUR}`];
const TEXTS: Record<string, string> = {
  u0001: "Sanganer, Jaipur and the places around them",
  u0002: "Sanganer lies south of Jaipur.",
  u0003: "Sanganer",
  u0004: "The GI's area of production.",
  u0005: "Jaipur",
  u0006: "Kishanpol Bazaar sells the prints.",
  u0007: "Bagru",
  u0008: "Bagru prints are set apart from Sanganeri.",
  u0009: "Amber",
  u0010: "The prince who founded Sanganer ruled from Amber.",
  u0011: "Printers moved from Sanganer to Bagru.",
  u0012: "The printers worked within 20 km of Sanganer.",
  u0013: "Sanganer and Jaipur were the first centres.",
  u0014: "The printers then moved out to Bagru.",
  u0015: "Rain a year, mm",
  u0016: "Jaipur district receives 650 mm of rain a year.",
  u0017: "The district to the west receives 410 mm of rain a year."
};
const SANGANERI = {
  head: { title: "u0001", caption: "u0002" },
  places: [
    { name: "u0003", value: null, reading: "u0004", latitude: 26.82, longitude: 75.79 },
    { name: "u0005", value: null, reading: "u0006", latitude: 26.92, longitude: 75.82 },
    { name: "u0007", value: null, reading: "u0008", latitude: 26.82, longitude: 75.55 },
    { name: "u0009", value: null, reading: "u0010", latitude: 26.99, longitude: 75.85 }
  ],
  valueLabel: null
};
const PARTS = {
  ...SANGANERI,
  routes: [{ start: 0, end: 2, text: "u0011" }],
  rings: [{ place: 0, radiusKm: 20, text: "u0012" }],
  sequence: [
    { text: "u0013", places: [0, 1], routes: [], rings: [], districts: false },
    { text: "u0014", places: [], routes: [0], rings: [0], districts: false }
  ]
};
const SHIM = [
  "figure{margin:0}.absolute{position:absolute}.relative{position:relative}.block{display:block}.h-auto{height:auto}.w-full{width:100%}",
  ".inset-0{inset:0}.h-full{height:100%}.overflow-hidden{overflow:hidden}",
  ".end-2{inset-inline-end:.5rem}.top-2{top:.5rem}.w-\\[22\\%\\]{width:22%}.min-w-16{min-width:4rem}.max-w-28{max-width:7rem}.p-1{padding:.25rem}",
  ".bg-raised{background:var(--raised)}.border{border:1px solid var(--rule)}.rounded-plate{border-radius:2px}.pointer-events-none{pointer-events:none}",
  ".font-ui{font-family:var(--font-ui)}.font-reading{font-family:var(--font-reading)}.italic{font-style:italic}.font-medium{font-weight:500}.font-semibold{font-weight:600}",
  ".fill-\\[url\\(\\#kv-map-place\\)\\]{fill:url(#kv-map-place)}.stroke-\\[var\\(--terracotta\\)\\]{stroke:var(--terracotta)}.\\[stroke-width\\:1\\.25px\\]{stroke-width:1.25px}",
  ".stroke-\\[var\\(--map-border-district\\)\\]{stroke:var(--map-border-district)}",
  [1, 2, 3, 5, 6].map((step) => `.fill-\\[var\\(--density-${step}\\)\\]{fill:var(--density-${step})}`).join("")
].join("");

function stilled(spec: Record<string, unknown>): Record<string, unknown> {
  const map = parseShape(mapLayerSpecShape, spec);
  const still = STILL_OF({ label: "sanganeri/geography/map", spec, map, home: homeDistrictsOf(SUBJECTS) });
  return still ? { ...spec, still } : spec;
}

function drawn(spec: Record<string, unknown>): string {
  const view = COMPONENT_VIEWS.map_layer as ComponentView;
  const component = { label: "sanganeri/geography/map", chapter: "why", anchor: "#m", kind: "map_layer", title: "Map", description: "A map", field: "GEOGRAPHY", fields: [], subjects: SUBJECTS };
  const text = (ref: string) => TEXTS[ref] ?? "";
  const props = { component, spec, unitRefs: Object.keys(TEXTS), renderUnit: text, unitText: text, renderComponent: () => null };
  return renderToStaticMarkup(createElement(() => view(props)));
}

test("a places map of the old shape draws on the site's base: relief, rivers, district lines, the home hatch, a scale and the India locator", () => {
  const spec = stilled(SANGANERI);
  const html = shownText(drawn(spec));
  for (const part of ["still-relief", "still-rivers", "still-district-lines", "places-home", "map-land", "map-salt", "map-scale", "india-locator", "india-locator-frame"]) expect(html, part).toContain(`data-testid="${part}"`);
  expect(html.match(/data-testid="map-place"/g)).toHaveLength(4);
  for (const name of ["Sanganer", "Jaipur", "Bagru", "Amber"]) expect(html).toContain(`>${name}</text>`);
  const frame = mapLayerFrame(parseShape(mapLayerSpecShape, spec));
  expect(attribute(html, "general-map", "viewBox")).toEqual([[frame.x, frame.y, frame.width, frame.height].map((value) => value.toFixed(1)).join(" ")]);
  expect(html).toContain("External boundaries of India as depicted by Survey of India.");
  expect(html.match(/data-testid="dataset-credit"/g)?.length).toBeGreaterThanOrEqual(2);
});

test("the Survey of India outline is always drawn, with a still and without one", () => {
  const outline = `d="${indiaOutlinePath()}"`;
  for (const spec of [SANGANERI, stilled(SANGANERI)]) {
    const html = drawn(spec);
    expect(html.split(outline).length - 1).toBeGreaterThanOrEqual(3);
  }
});

test("a map spec of the old shape still parses unchanged and draws; one sent without its parts draws them from nothing", () => {
  const parsed = parsedSpec(mapLayerSpecShape, SANGANERI) as MapLayerSpec;
  expect(parsed).toEqual(SANGANERI);
  const html = drawn(SANGANERI);
  expect(html).not.toContain('data-testid="map-route"');
  expect(html).not.toContain('data-testid="map-ring"');
  expect(html).not.toContain('data-testid="map-sequence"');
  expect(html.match(/data-testid="map-place"/g)).toHaveLength(4);
});

test("the still is small and cut to the frame the view draws, and a named frame is the district's own", () => {
  const spec = stilled(SANGANERI) as { still: { box: unknown } };
  expect(JSON.stringify(spec.still).length).toBeLessThan(40_000);
  expect(spec.still.box).toEqual(mapLayerFrame(parseShape(mapLayerSpecShape, SANGANERI)));
  const named = stilled({ ...SANGANERI, frame: { district: JAIPUR } }) as { still: { named: string; box: { x: number; y: number; width: number; height: number } } };
  expect(named.still.named).toBe(`district:${JAIPUR}`);
  const map = parseShape(mapLayerSpecShape, named);
  expect(mapLayerFrame(map)).toEqual(named.still.box);
  const jaipur = project(75.589, 26.817);
  expect(jaipur.x).toBeGreaterThan(named.still.box.x);
  expect(jaipur.x).toBeLessThan(named.still.box.x + named.still.box.width);
  expect(mapLayerFrame({ ...map, frame: { district: 110 } })).not.toEqual(named.still.box);
});

test("a route, a ring and a sequence are drawn only from the spec's own places, radius and steps, and a part off its shape draws nothing", () => {
  const html = shownText(drawn(stilled(PARTS)));
  expect(html.match(/data-testid="map-route"/g)).toHaveLength(1);
  expect(attribute(html, "map-ring", "data-km")).toEqual(["20"]);
  expect(html).toContain(">20 km</text>");
  expect(attribute(html, "map-step", "aria-pressed")).toEqual(["false", "true"]);
  expect(attribute(html, "places-map-figure", "data-step")).toEqual(["1"]);
  for (const ref of ["u0011", "u0012", "u0013", "u0014"]) expect(html).toContain(TEXTS[ref]);
  expect(html.match(/<li[^>]*aria-current="step"/g)).toHaveLength(3);
  expect(html).toContain("<span>Play</span>");
  expect(html.match(/data-current=""/g)).toHaveLength(2);
  for (const wrong of [{ routes: [{ start: 0, end: 2, text: "moved to Bagru" }] }, { rings: [{ place: 0, radiusKm: 0, text: "u0012" }] }, { sequence: [PARTS.sequence[0]] }]) {
    expect(parsedSpec(mapLayerSpecShape, { ...PARTS, ...wrong })).toBeNull();
    expect(drawn({ ...PARTS, ...wrong })).not.toContain('data-testid="places-map"');
  }
});

test("district values fill their districts by class, print each value at its centre and list each cited reading by rank", () => {
  const values = [{ district: 110, value: 410, reading: "u0017" }, { district: JAIPUR, value: 650, reading: "u0016" }];
  const html = shownText(drawn(stilled({ ...SANGANERI, districts: { valueLabel: "u0015", values } })));
  expect(html).toContain('data-testid="still-valued"');
  expect([...html.matchAll(/data-testid="still-valued"[\s\S]*?<\/g>/g)][0]?.[0].match(/data-lgd="(\d+)"/g)).toEqual(['data-lgd="110"', `data-lgd="${JAIPUR}"`]);
  for (const value of ["410", "650"]) expect(html).toContain(`>${value}</text>`);
  const listed = html.split('data-testid="map-district-list"')[1] ?? "";
  expect(listed.indexOf(TEXTS.u0016)).toBeLessThan(listed.indexOf(TEXTS.u0017));
  expect(listed).toContain(TEXTS.u0015);
});

test("a sequence reveals its steps' marks in order, and a mark no step names is shown throughout", () => {
  const map = parseShape(mapLayerSpecShape, PARTS);
  const first = shownMarks(map, 4, 0);
  expect([...first.places].sort()).toEqual([0, 1, 3]);
  expect([...first.current].sort()).toEqual([0, 1]);
  expect([...first.routes, ...first.rings]).toEqual([]);
  const last = shownMarks(map, 4, 1);
  expect([...last.places].sort()).toEqual([0, 1, 2, 3]);
  expect([...last.current].sort()).toEqual([0, 2]);
  expect([[...last.routes], [...last.rings]]).toEqual([[0], [0]]);
  expect(homeDistrictsOf(["craft:X", "place:lgd:102", "place:lgd:102", "place:state:8"])).toEqual([102]);
});

test("district values are classed by hand-countable groups and their ring and scale are true to the kilometre", () => {
  expect(valueClasses([410, 650]).map((band) => band.label)).toEqual(["410", "650"]);
  const five = valueClasses([213, 310, 332, 449, 468, 548, 568, 614, 650, 700]);
  expect(five.map((band) => [band.min, band.max])).toEqual([[213, 310], [332, 449], [468, 548], [568, 614], [650, 700]]);
  expect([valueClassOf(213, five), valueClassOf(449, five), valueClassOf(700, five)]).toEqual([0, 1, 4]);
  const unitsPerDegree = project(0, 0).y - project(0, 1).y;
  const radii = ringRadii({ longitude: 75.79, latitude: 26.82 }, 20);
  expect(radii.ry).toBeCloseTo((20 / KM_PER_DEGREE_LATITUDE) * unitsPerDegree, 6);
  expect(radii.rx / radii.ry).toBeGreaterThan(0.9);
  expect(radii.rx / radii.ry).toBeLessThan(1.1);
  const map = parseShape(mapLayerSpecShape, PARTS);
  expect(framedPoints(map)).toHaveLength(8);
  const frame = mapLayerFrame(map);
  const bar = scaleBar(frame);
  expect(SCALE_STEPS).toContain(bar.km);
  expect(bar.length / frame.width).toBeLessThanOrEqual(SCALE_SHARE);
  expect(bar.length / frame.width).toBeGreaterThan(SCALE_SHARE / 3);
});

test("a declared timeline map's frame carries the scale bar and the India locator, and an answer's whole-India map neither", () => {
  const placed = [{ index: 0, name: "Bidar", wikidataId: null, latitude: 17.9, longitude: 77.55, pin: 1, beyond: false }];
  const pins = (parts: { frame?: ReturnType<typeof placesFrame> }) => withApp(createElement(TimelinePins, { placed, reached: new Set([0]), routes: [], boundary: null, parts }));
  const framed = pins({ frame: placesFrame(placed) });
  expect(framed).toContain('data-testid="map-scale"');
  expect(framed).toContain('data-testid="india-locator-frame"');
  const whole = pins({});
  expect(whole).not.toContain('data-testid="map-scale"');
  expect(whole).not.toContain('data-testid="india-locator"');
});

test("the server's pass gives a declared places map its still, replaces one a spec brings and leaves an authored map alone", () => {
  const fixture = parseKindFixtures({ fixtures: [read<unknown>(REPO, "backend", "app", "data", "kind_fixtures", "map_layer.json")] })[0];
  const document = kindPreviewDocument([fixture]);
  const brought = { ...document, specs: { ...document.specs, [fixture.label]: { ...document.specs[fixture.label], still: { forged: true } } } };
  const maps = placesMaps(brought);
  expect(maps.map((found) => found.label)).toEqual([fixture.label]);
  expect(maps[0].spec).not.toHaveProperty("still");
  const stilledDocument = placesStilledDocument(brought, maps, STILL_OF);
  expect(stilledDocument.specs[fixture.label].still).toEqual(STILL_OF(maps[0]));
  const bare = placesStilledDocument(brought, maps, () => null);
  expect(bare.specs[fixture.label]).not.toHaveProperty("still");
  const authored = { ...document, specs: { ...document.specs, [fixture.label]: { setting: "drawing", drawing: null, explorer: null } } };
  expect(placesMaps(authored)).toEqual([]);
});

test("at 390 and 1440 the map fills its column and stays inside it, and the renderer's still is kept for the comparison", async ({ page }, testInfo) => {
  const shown = { sanganeri: drawn(stilled(SANGANERI)), parts: drawn(stilled(PARTS)) };
  for (const [viewport, column] of [[390, 358], [1440, 718]] as const) {
    await page.setViewportSize({ width: viewport, height: 1200 });
    for (const [name, html] of Object.entries(shown)) {
      await page.setContent(primitivesPage(`<style>${SHIM}</style><main id="column" style="width:${column}px;margin:0 16px">${html}</main>`));
      const sizes = await page.evaluate(() => {
        const map = document.querySelector('[data-testid="general-map"]')?.getBoundingClientRect();
        const locator = document.querySelector('[data-testid="india-locator"]')?.getBoundingClientRect();
        return { width: map?.width ?? 0, right: map?.right ?? 0, inset: locator ? locator.right <= (map?.right ?? 0) && locator.top >= (map?.top ?? 0) : false };
      });
      expect(sizes.width, `${name} at ${viewport}`).toBeGreaterThan(column * 0.9);
      expect(sizes.right, `${name} at ${viewport}`).toBeLessThanOrEqual(16 + column + 1);
      expect(sizes.inset, `${name} at ${viewport}`).toBe(true);
      await page.locator('[data-testid="places-map"]').screenshot({ path: testInfo.outputPath(`places-map-${viewport}-${name}.png`) });
    }
  }
});

const CAPTION_PX = 12;
const PARITY_LABEL_MOST = 48;
const HYDRATED = [
  "<script>",
  "for (const svg of document.querySelectorAll('svg[data-fit]')) {",
  "const width = svg.getBoundingClientRect().width;",
  "if (width > 0 && svg.parentElement) svg.parentElement.style.setProperty('--k', String(svg.viewBox.baseVal.width / width));",
  "}",
  "</script>"
].join(" ");

function overlaid(spec: Record<string, unknown>, frame: MapBox): string {
  const map = parseShape(mapLayerSpecShape, spec);
  const overlay = createElement(PlacesOverlay, { spec: map, frame, marks: shownMarks(map, map.places.length, 0), values: [], files: { relief: RELIEF, rivers: RIVERS }, waters: null, named: [], nameOf: (ref: string) => TEXTS[ref] ?? "" });
  const base = `<svg viewBox="${viewBoxOf(frame)}" class="block h-auto w-full" data-fit="" data-testid="general-map"></svg>`;
  return `<div class="relative overflow-hidden" data-testid="places-map">${base}${renderToStaticMarkup(overlay)}</div>`;
}

function measured() {
  const probe = document.createElement("span");
  probe.style.fontSize = "var(--text-caption)";
  document.body.append(probe);
  const caption = parseFloat(getComputedStyle(probe).fontSize);
  probe.remove();
  const map = document.querySelector('[data-testid="general-map"]');
  const labels = [...document.querySelectorAll<SVGTextElement>('[data-testid="places-map"] text')].map((text) => {
    const ctm = text.getScreenCTM();
    const scale = ctm ? Math.hypot(ctm.a, ctm.b) : 0;
    return { text: text.textContent ?? "", size: parseFloat(getComputedStyle(text).fontSize) * scale, height: text.getBBox().height * scale, box: text.getBoundingClientRect().height };
  });
  return { caption, k: map?.parentElement ? getComputedStyle(map.parentElement).getPropertyValue("--k").trim() : "", inMap: map?.querySelectorAll("text").length ?? -1, labels };
}

test("every text of a places map draws at the caption size at 390, 1440 and 1920, with JavaScript off and on", async ({ browser }) => {
  const values = [{ district: 110, value: 410, reading: "u0017" }, { district: JAIPUR, value: 650, reading: "u0016" }];
  const sanganeri = parseShape(mapLayerSpecShape, SANGANERI);
  const maps = {
    sanganeri: drawn(stilled(SANGANERI)),
    parts: drawn(stilled({ ...PARTS, districts: { valueLabel: "u0015", values } })),
    "sanganeri with its layers": overlaid(SANGANERI, mapLayerFrame(sanganeri)),
    "India with its layers": overlaid(SANGANERI, WHOLE_MAP)
  };
  for (const javaScriptEnabled of [false, true]) {
    const context = await browser.newContext({ javaScriptEnabled });
    const page = await context.newPage();
    for (const [viewport, column] of [[390, 358], [1440, 718], [1920, 1000]] as const) {
      await page.setViewportSize({ width: viewport, height: 1200 });
      for (const [name, html] of Object.entries(maps)) {
        await page.setContent(primitivesPage(`<style>${SHIM}</style><main style="width:${column}px;margin:0 16px">${html}</main>${HYDRATED}`));
        const found = await page.evaluate(measured);
        const where = `${name} at ${viewport} with JavaScript ${javaScriptEnabled ? "on" : "off"}`;
        expect(found.caption, where).toBe(CAPTION_PX);
        expect(found.k === "", where).toBe(!javaScriptEnabled);
        expect(found.inMap, where).toBe(0);
        expect(found.labels.length, where).toBeGreaterThan(0);
        for (const label of found.labels) {
          expect(label.size, `${where}: ${label.text}`).toBeCloseTo(CAPTION_PX, 0);
          expect(label.height, `${where}: ${label.text}`).toBeLessThanOrEqual(CAPTION_PX * 1.6);
          if (!name.startsWith("India")) expect(label.box, `${where}: ${label.text}`).toBeLessThanOrEqual(PARITY_LABEL_MOST);
        }
      }
    }
    await context.close();
  }
});

test("a places map draws no layer label outside its frame, so a whole-India label never sits clipped in a town's map", () => {
  const frame = mapLayerFrame(parseShape(mapLayerSpecShape, SANGANERI));
  expect(riverLabels(RIVERS, frame, [])).toEqual([]);
  expect(rangeLabels(RELIEF, frame)).toEqual([]);
  expect(riverLabels(RIVERS, WHOLE_MAP, []).map((label) => label.text)).toContain("Brahmaputra");
  expect(rangeLabels(RELIEF, WHOLE_MAP).map((label) => label.text)).toContain("Western Ghats");
  const html = overlaid(SANGANERI, frame);
  for (const text of ["Western Ghats", "Eastern Ghats", "Brahmaputra", "Aravalli Range", "Indo-Gangetic Plain"]) expect(html).not.toContain(`>${text}</text>`);
  for (const name of ["Sanganer", "Jaipur", "Bagru", "Amber"]) expect(html).toContain(`>${name}</text>`);
});
