import { readFileSync } from "node:fs";
import { join } from "node:path";

import { expect, test } from "@playwright/test";
import { createElement, type ReactElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";

import { nearBlocksLoaded } from "@/components/answer/nearBlock";
import { decodeRings, linesPath, ringsPath, viewBoxOf } from "@/components/map/basemap";
import { PLACE_TONE } from "@/components/map/DistrictLayer";
import { DRAWING_DISTRICT_VALUES, LayerStatus } from "@/components/map/MapLayerView";
import { cutStill, STILL_GRID, stillLayers, type StillFiles } from "@/components/map/mapStillCut";
import { decodeShapes, shapePath, type ShapesFile } from "@/components/map/shapeGeometry";
import { clippedLine, clippedRing, gridArea, relativePath, simplified } from "@/components/map/stillGeometry";
import { HomeOrStill, PhysicalKey, ReliefUnderOrStill, RiversUnderOrStill } from "@/components/map/TimelineMapLayers";
import { timelineMapFrame, timelineMapNames, type MapStill } from "@/components/map/timelineMapStill";
import { COMPONENT_VIEWS } from "@/components/monograph/componentViews";
import { parsedSpec } from "@/lib/componentSpecsGeneral";
import { timelineMapSpecShape } from "@/lib/componentSpecsTimelineMap";
import type { ComponentView } from "@/lib/componentViewContract";
import { parseKindFixtures, type KindFixture } from "@/lib/kindFixtures";
import { kindPreviewDocument } from "@/lib/kindPreview";
import { mineralSites, type MineralsFile, type ReliefFile, type RiversFile } from "@/lib/mapPhysical";
import type { MonographComponent, MonographDocument } from "@/lib/monographDocument";
import { layerLegend, parsedMapLayer, type LayerLegend } from "@/lib/regionView";
import { declaredMaps, stilledDocument, stillOfMaps, withMapStills } from "@/lib/server/mapStills";
import { parseShape } from "@/lib/shape";

import { clientBoundaries, dynamicImports, heavyChains, runtimeImports } from "./clientGraph";

test.beforeAll(() => nearBlocksLoaded());

const FRONTEND = join(__dirname, "..");
const REPO = join(FRONTEND, "..");
const read = <T>(...parts: string[]): T => JSON.parse(readFileSync(join(...parts), "utf8")) as T;
const RELIEF = read<ReliefFile>(FRONTEND, "public", "layers", "relief.json");
const RIVERS = read<RiversFile>(FRONTEND, "public", "layers", "rivers.json");
const MINERALS = read<MineralsFile>(FRONTEND, "public", "layers", "minerals.json");
const SHAPES = read<ShapesFile>(FRONTEND, "public", "boundaries", "district-shapes.json");
const FILES: StillFiles = { relief: RELIEF, rivers: RIVERS, minerals: MINERALS, shapes: SHAPES };
const LAYERS = stillLayers(FILES);
const [BIDRIWARE] = parseKindFixtures({ fixtures: [read<unknown>(REPO, "backend", "app", "data", "kind_fixtures", "timeline_map.json")] });
const KUTCH = read<Record<string, unknown>>(REPO, "backend", "app", "data", "monographs", "Kutch-Ajrakh", "specs", "kutch-ajrakh__history__dated-record-timeline-map.json");
const LAYER = parsedMapLayer(read<unknown>(REPO, "shared", "region.layer.golden.json"));
const BIDAR = 529;
const NO_LEGENDS = new Map<string, LayerLegend>();
const MAP = parseShape(timelineMapSpecShape, BIDRIWARE.spec);
const FRAME = timelineMapFrame(MAP);
const STILL = stillOfMaps(LAYERS, NO_LEGENDS)(MAP) as MapStill;
const WAITING = { data: null, failure: null, retry: () => undefined };
const NOTHING_LANDED = { relief: null, rivers: null, minerals: null, sites: [] };
const STILL_BYTES_MOST = 40_000;
const STILL_SOURCES = [
  "lib/server/mapStills.ts",
  "lib/server/mapLayerFiles.ts",
  "components/map/mapStillCut.ts",
  "components/map/stillGeometry.ts",
  "public/layers/relief.json",
  "public/layers/rivers.json",
  "public/layers/minerals.json",
  "public/boundaries/district-shapes.json"
];
const CRAFT_ROUTE = ["app/layout.tsx", "app/(reading)/layout.tsx", "app/(reading)/crafts/[slug]/page.tsx"];
const REST_CHUNKS = ["components/monograph/DeferredShell.tsx", "components/monograph/DeferredDocument.tsx"];
const NEAR_VIEWS = "components/monograph/kinds/nearViews.tsx";

function drawnView(spec: Record<string, unknown>, fixture: KindFixture = BIDRIWARE): string {
  const view = COMPONENT_VIEWS.timeline_map as ComponentView;
  const component = { label: fixture.label, chapter: "k1", anchor: "#k", kind: fixture.kind, title: fixture.title, description: fixture.description, field: fixture.field, fields: [], subjects: [] };
  const text = (ref: string) => fixture.units[ref]?.text ?? "";
  const props = { component, spec, unitRefs: Object.keys(fixture.units), renderUnit: text, unitText: text, renderComponent: () => null };
  return renderToStaticMarkup(createElement(() => view(props)));
}

function inSvg(node: ReactElement): string {
  return renderToStaticMarkup(createElement("svg", null, node));
}

function mapNaming(layers: string[], home: boolean): Record<string, unknown> {
  const places = MAP.places.map((place) => ({ ...place, home: home && place.home }));
  return { ...BIDRIWARE.spec, layers, places };
}

test("a still's geometry is clipped to its box, simplified within a step and written as short relative paths", () => {
  const box = { x: 0, y: 0, width: 10, height: 10 };
  const crossing = clippedRing([{ x: 5, y: 2 }, { x: 15, y: 2 }, { x: 15, y: 8 }, { x: 5, y: 8 }], box);
  expect(crossing).toEqual([{ x: 5, y: 2 }, { x: 10, y: 2 }, { x: 10, y: 8 }, { x: 5, y: 8 }]);
  expect(gridArea(crossing.map((point) => [point.x, point.y] as const))).toBe(30);
  expect(clippedRing([{ x: 20, y: 20 }, { x: 30, y: 20 }, { x: 30, y: 30 }], box)).toEqual([]);
  const line = [-20, -10, 2, 4, 20, 30].map((x) => ({ x, y: 5 }));
  expect(clippedLine(line, box)).toEqual([[{ x: -10, y: 5 }, { x: 2, y: 5 }, { x: 4, y: 5 }, { x: 20, y: 5 }]]);
  expect(clippedLine([{ x: 20, y: 20 }, { x: 30, y: 30 }], box)).toEqual([]);
  expect(simplified([{ x: 0, y: 0 }, { x: 1, y: 0.1 }, { x: 2, y: 0 }, { x: 3, y: 5 }], 0.5)).toEqual([{ x: 0, y: 0 }, { x: 2, y: 0 }, { x: 3, y: 5 }]);
  expect(relativePath([[1, 2], [4, 0], [4, 3]], true)).toBe("M1 2l3-2 0 3z");
  expect(relativePath([[12, -5], [15, -5]], false, 10)).toBe("M1.2-0.5l0.3 0");
  expect(gridArea([[0, 0], [2, 0], [2, 2], [0, 2]])).toBe(4);
});

test("the Bidriware map's still is cut to the frame its view draws, and is a small part of the layers it stands for", () => {
  expect(STILL.box).toEqual(FRAME);
  expect(STILL.grid).toBe(STILL_GRID);
  expect(STILL.relief).toHaveLength(RELIEF.bands.length + 1);
  expect(STILL.relief?.[0].length).toBeGreaterThan(0);
  expect(STILL.rivers?.length).toBeGreaterThan(0);
  expect(STILL.home?.length).toBeGreaterThan(0);
  expect([STILL.minerals, STILL.district]).toEqual([null, null]);
  const whole = [
    ...RELIEF.bands.map((band) => ringsPath(decodeRings(band.rings))),
    ...RIVERS.ranks.map((group) => linesPath(group.lines)),
    ringsPath(decodeRings(RIVERS.lakes)),
    ...decodeShapes(SHAPES)
      .filter((shape) => shape.lgd === BIDAR)
      .map(shapePath)
  ].join("").length;
  const bytes = JSON.stringify(STILL).length;
  console.log(`the Bidriware map's still: ${bytes} bytes, for ${whole} bytes of path data drawn whole`);
  expect(bytes).toBeLessThan(STILL_BYTES_MOST);
  expect(bytes * 10).toBeLessThan(whole);
});

test("at rest the map draws its relief, rivers and home hatch from the still, in the map tokens and beneath its pins", () => {
  const html = drawnView({ ...BIDRIWARE.spec, still: STILL });
  const map = html.slice(html.indexOf(`viewBox="${viewBoxOf(FRAME)}"`));
  expect(map).toContain(`transform="translate(${FRAME.x} ${FRAME.y}) scale(${(FRAME.width / STILL_GRID).toFixed(5)})" data-testid="still-relief"`);
  for (const step of [1, 2, 3]) expect(map).toContain(`fill="var(--elevation-${step})"`);
  expect(map).toContain('data-testid="still-rivers"');
  expect(map).toContain('stroke="var(--map-river)"');
  expect(map).toContain('data-testid="still-home"');
  expect(map).toContain(PLACE_TONE);
  expect(map.indexOf('data-testid="still-home"')).toBeLessThan(map.indexOf('data-testid="map-pin"'));
  const bare = drawnView(BIDRIWARE.spec);
  for (const part of ["still-relief", "still-rivers", "still-home"]) expect(bare).not.toContain(`data-testid="${part}"`);
  const elsewhere = drawnView({ ...BIDRIWARE.spec, still: { ...STILL, box: { ...STILL.box, x: STILL.box.x + 1 } } });
  expect(elsewhere).not.toContain('data-testid="still-relief"');
});

test("each layer takes the still's place when its file lands, in the same spot of the drawing", () => {
  expect(inSvg(createElement(ReliefUnderOrStill, { file: null, still: STILL }))).toContain('data-testid="still-relief"');
  const relief = inSvg(createElement(ReliefUnderOrStill, { file: RELIEF, still: STILL }));
  expect(relief).toContain('data-testid="relief-layer"');
  expect(relief).not.toContain("still-relief");
  expect(inSvg(createElement(RiversUnderOrStill, { file: null, still: STILL }))).toContain('data-testid="still-rivers"');
  const rivers = inSvg(createElement(RiversUnderOrStill, { file: RIVERS, still: STILL }));
  expect(rivers).toContain('data-testid="rivers-layer"');
  expect(rivers).not.toContain("still-rivers");
  expect(inSvg(createElement(HomeOrStill, { shapes: null, home: [BIDAR], still: STILL }))).toContain('data-testid="still-home"');
  const home = inSvg(createElement(HomeOrStill, { shapes: decodeShapes(SHAPES), home: [BIDAR], still: STILL }));
  expect(home).toContain(`data-lgd="${BIDAR}"`);
  expect(home).not.toContain("still-home");
  expect(inSvg(createElement(HomeOrStill, { shapes: null, home: [], still: STILL }))).toBe("<svg></svg>");
  expect(inSvg(createElement(ReliefUnderOrStill, { file: null, still: null }))).toBe("<svg></svg>");
});

test("the minerals key and a district legend draw at rest from the still exactly as they draw once their data lands", () => {
  const names = { physical: ["minerals"], district: null, home: [] };
  const geometry = cutStill(LAYERS, FRAME, names);
  const still = { ...STILL, minerals: geometry.minerals };
  const atRest = renderToStaticMarkup(createElement(PhysicalKey, { names, layers: NOTHING_LANDED, still }));
  const landed = renderToStaticMarkup(createElement(PhysicalKey, { names, layers: { ...NOTHING_LANDED, minerals: MINERALS, sites: mineralSites(MINERALS) } }));
  expect(atRest).toBe(landed);
  for (const entry of MINERALS.classes) expect(atRest).toContain(entry.label);
  expect(atRest).not.toContain("aria-busy");
  const legend = layerLegend(LAYER);
  const held = renderToStaticMarkup(createElement(LayerStatus, { layer: WAITING, shapes: WAITING, held: legend }));
  const drawn = renderToStaticMarkup(createElement(LayerStatus, { layer: { ...WAITING, data: LAYER }, shapes: { ...WAITING, data: [] } }));
  expect(held).toBe(drawn);
  expect(held).toContain(LAYER.layer.title);
  expect(held).not.toContain("aria-busy");
  expect(renderToStaticMarkup(createElement(LayerStatus, { layer: WAITING, shapes: WAITING }))).toContain(DRAWING_DISTRICT_VALUES);
});

test("a map naming a district layer holds its legend in the still and draws it at rest; a map naming nothing to wait for has no still", () => {
  const district = parseShape(timelineMapSpecShape, mapNaming([LAYER.layer.id], false));
  const legends = new Map([[LAYER.layer.id, layerLegend(LAYER)]]);
  const still = stillOfMaps(LAYERS, legends)(district) as MapStill;
  expect(still.district).toEqual(layerLegend(LAYER));
  expect([still.relief, still.rivers, still.home, still.minerals]).toEqual([null, null, null, null]);
  const html = drawnView({ ...mapNaming([LAYER.layer.id], false), still });
  expect(html).toContain(LAYER.layer.title);
  expect(html).not.toContain(DRAWING_DISTRICT_VALUES);
  expect(stillOfMaps(LAYERS, NO_LEGENDS)(district)).toBeNull();
  expect(stillOfMaps(LAYERS, legends)(parseShape(timelineMapSpecShape, mapNaming([], false)))).toBeNull();
  expect(timelineMapNames(district)).toEqual({ physical: [], district: LAYER.layer.id, home: [] });
});

test("the server's pass gives a declared map its own still, replaces one a spec brings, and leaves the authored map without one", () => {
  const document = kindPreviewDocument([BIDRIWARE]);
  const label = BIDRIWARE.label;
  const forged = { ...STILL, relief: ["M0 0l1 0 0 1z"] };
  const component = document.content.components.find((found) => found.label === label) as MonographComponent;
  const brought: MonographDocument = {
    ...document,
    content: { ...document.content, components: [...document.content.components, { ...component, label: "kutch" }] },
    specs: { ...document.specs, [label]: { ...document.specs[label], still: forged }, kutch: { ...KUTCH, still: forged } }
  };
  const maps = declaredMaps(brought);
  expect(maps.map((found) => found.label)).toEqual([label]);
  const stilled = stilledDocument(brought, maps, stillOfMaps(LAYERS, NO_LEGENDS));
  expect(stilled.specs[label].still).toEqual(STILL);
  expect(stilled.specs.kutch).toEqual(KUTCH);
  const nothing = stilledDocument(brought, maps, () => null);
  expect(nothing.specs[label]).not.toHaveProperty("still");
});

test("the read's pass cuts the still from the layer files bundled with the server, and leaves a page without a map as it was", async () => {
  const document = kindPreviewDocument([BIDRIWARE]);
  const stilled = await withMapStills(document);
  expect(stilled.specs[BIDRIWARE.label].still).toEqual(STILL);
  const plain = { ...document, content: { ...document.content, components: [] } };
  expect(await withMapStills(plain)).toBe(plain);
});

test("a still is read only in the shape the server writes it", () => {
  expect(parsedSpec(timelineMapSpecShape, { ...BIDRIWARE.spec, still: STILL })?.still).toEqual(STILL);
  expect(parsedSpec(timelineMapSpecShape, { ...BIDRIWARE.spec, still: { ...STILL, home: 'M0 0"/><script>' } })).toBeNull();
  expect(parsedSpec(timelineMapSpecShape, { ...BIDRIWARE.spec, still: { ...STILL, grid: 0 } })).toBeNull();
});

test("the still is cut only on the server: no chain from the page's client code reaches the cutter or the layer files", () => {
  const entries = [...clientBoundaries(CRAFT_ROUTE), ...REST_CHUNKS, ...dynamicImports(NEAR_VIEWS)];
  expect(entries).toContain("components/monograph/kinds/general/TimelineMapDeclaredView.tsx");
  const chains = entries.flatMap((entry) => heavyChains(entry, (node) => STILL_SOURCES.includes(node))).map((chain) => chain.join(" > "));
  expect(chains, chains.join("\n")).toEqual([]);
  expect(runtimeImports("lib/monographRenderServer.ts")).toContain("lib/server/mapStills.ts");
  expect(dynamicImports("lib/server/mapStills.ts")).toEqual(["lib/server/mapLayerFiles.ts"]);
  expect(runtimeImports("lib/server/mapLayerFiles.ts")).toEqual(expect.arrayContaining(STILL_SOURCES.filter((source) => source.startsWith("public/"))));
});
