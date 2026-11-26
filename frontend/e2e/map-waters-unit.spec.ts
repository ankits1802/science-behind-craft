import { readFileSync } from "node:fs";
import { join } from "node:path";

import { expect, test } from "@playwright/test";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";

import { nearBlocksLoaded } from "@/components/answer/nearBlock";
import type { NeighbourFile } from "@/components/map/basemap";
import type { BordersFile } from "@/components/map/borderGeometry";
import { codedStillBase } from "@/components/map/codedStillCut";
import { mapLayerFrame } from "@/components/map/mapLayerFrame";
import { stillLayers, type HeldWaters, type StillFiles } from "@/components/map/mapStillCut";
import { frameShare } from "@/components/map/placesMapLabels";
import { project, VIEW_BOX } from "@/components/map/projection";
import type { ShapesFile } from "@/components/map/shapeGeometry";
import type { MapStill } from "@/components/map/timelineMapStill";
import { heldTile, tilesInFrame } from "@/components/map/waterLayer";
import { COMPONENT_VIEWS } from "@/components/monograph/componentViews";
import { CodedStill } from "@/components/monograph/kinds/science/CodedStill";
import { mapLayerSpecShape } from "@/lib/componentSpecsGeneral";
import { codedFigureShape, type CodedFigureSpec } from "@/lib/componentSpecsScienceCoded";
import type { ComponentView } from "@/lib/componentViewContract";
import { parseKindFixtures } from "@/lib/kindFixtures";
import { kindPreviewDocument } from "@/lib/kindPreview";
import { layerCredits, type MineralsFile, type ReliefFile, type RiversFile } from "@/lib/mapPhysical";
import type { WatersIndex, WatersTile } from "@/lib/mapWaters";
import { parsedMapLayer } from "@/lib/regionView";
import { codedBasedDocument, codedMaps } from "@/lib/server/codedMapStills";
import { stillOfPlaces } from "@/lib/server/mapStills";
import { parseShape } from "@/lib/shape";

test.beforeAll(() => nearBlocksLoaded());

const FRONTEND = join(__dirname, "..");
const REPO = join(FRONTEND, "..");
const read = <T>(...parts: string[]): T => JSON.parse(readFileSync(join(...parts), "utf8")) as T;
const FILES: StillFiles = {
  relief: read<ReliefFile>(FRONTEND, "public", "layers", "relief.json"),
  rivers: read<RiversFile>(FRONTEND, "public", "layers", "rivers.json"),
  minerals: read<MineralsFile>(FRONTEND, "public", "layers", "minerals.json"),
  shapes: read<ShapesFile>(FRONTEND, "public", "boundaries", "district-shapes.json"),
  neighbours: read<NeighbourFile>(FRONTEND, "public", "boundaries", "neighbours.json"),
  stateBorders: read<BordersFile>(FRONTEND, "public", "boundaries", "state-borders.json")
};
const LAYERS = stillLayers(FILES);
const INDEX = read<WatersIndex>(FRONTEND, "public", "layers", "waters.json");
const tile = (id: string) => read<WatersTile>(FRONTEND, "public", "layers", "waters", `${id}.json`);
const NEEDED = ["e068n22", "e070n22", "e074n26"];
const HELD: HeldWaters = { tiles: NEEDED.map((id) => heldTile(tile(id))), credits: layerCredits(INDEX.datasets) };
const BOUNDARY = parsedMapLayer(read<unknown>(REPO, "shared", "region.layer.golden.json")).boundary;
const KACHCHH = 449;
const JAIPUR = 102;
const TAPPAR = "Tappar Reservoir";
const STILL_CHARS_MOST = 40_000;
const TEXTS: Record<string, string> = {
  u0001: "Dhamadka and the dam upstream",
  u0002: "The Suran ran past Dhamadka until a dam at Tapar stopped it.",
  u0003: "Dhamadka",
  u0004: "Dhamadka was served by the River Suran.",
  u0005: "Tapar",
  u0006: "A dam was built upstream at Tapper village."
};
const KUTCH = {
  head: { title: "u0001", caption: "u0002" },
  places: [
    { name: "u0003", value: null, reading: "u0004", latitude: 23.3, longitude: 70.12 },
    { name: "u0005", value: null, reading: "u0006", latitude: 23.24, longitude: 70.13 }
  ],
  valueLabel: null,
  emphasis: { layers: [], rivers: ["Suran"], dams: [TAPPAR] }
};
const SANGANERI = {
  head: { title: "u0001", caption: "u0002" },
  places: [
    { name: "u0003", value: null, reading: "u0004", latitude: 26.82, longitude: 75.79 },
    { name: "u0005", value: null, reading: "u0006", latitude: 26.92, longitude: 75.82 }
  ],
  valueLabel: null,
  emphasis: { layers: [], rivers: ["Amanisha River"] }
};

function stilled(spec: Record<string, unknown>, home: number): { spec: Record<string, unknown>; still: MapStill } {
  const map = parseShape(mapLayerSpecShape, spec);
  const still = stillOfPlaces(LAYERS, BOUNDARY, new Map(), HELD)({ label: "kutch/map", spec, map, home: [home] }) as MapStill;
  return { spec: { ...spec, still }, still };
}

function drawn(spec: Record<string, unknown>, home: number): string {
  const view = COMPONENT_VIEWS.map_layer as ComponentView;
  const component = { label: "kutch/geography/map", chapter: "why", anchor: "#m", kind: "map_layer", title: "Map", description: "A map", field: "GEOGRAPHY", fields: [], subjects: [`place:lgd:${home}`] };
  const text = (ref: string) => TEXTS[ref] ?? "";
  const props = { component, spec, unitRefs: Object.keys(TEXTS), renderUnit: text, unitText: text, renderComponent: () => null };
  return renderToStaticMarkup(createElement(() => view(props)));
}

test("a small river named on a places map draws strong and labelled, and an unknown name draws nothing", () => {
  const kutch = stilled(KUTCH, KACHCHH);
  expect(kutch.still.waters?.d).toBeTruthy();
  expect(kutch.still.waters?.strong.map((river) => river.name)).toEqual(["Suran"]);
  const html = drawn(kutch.spec, KACHCHH);
  expect(html).toContain('data-testid="still-waters"');
  expect(html).toContain('data-name="Suran"');
  expect(html).toContain(">Suran</text>");
  const unknown = stilled({ ...KUTCH, emphasis: { layers: [], rivers: ["Dhamadka Creek"] } }, KACHCHH);
  expect(unknown.still.waters?.strong).toEqual([]);
  expect(drawn(unknown.spec, KACHCHH)).not.toContain(">Dhamadka Creek</text>");
  const sanganeri = stilled(SANGANERI, JAIPUR);
  expect(sanganeri.still.waters?.strong.map((river) => river.name)).toEqual(["Amanisha River"]);
  expect(JSON.stringify(sanganeri.still).length).toBeLessThan(STILL_CHARS_MOST);
});

test("a map names the Dravyavati through the register's cited alias and draws the way OpenStreetMap names Amanisha River", () => {
  const amanisha = tile("e074n26").rivers.find((river) => river.name === "Amanisha River");
  expect(amanisha?.agrees).toContainEqual({ name: "Dravyavati River", source: "RIVER_ALIASES:dravyavati" });
  const dravyavati = stilled({ ...SANGANERI, emphasis: { layers: [], rivers: ["Dravyavati"] } }, JAIPUR);
  const byDataset = stilled(SANGANERI, JAIPUR);
  expect(dravyavati.still.waters?.strong.map((river) => river.name)).toEqual(["Dravyavati"]);
  expect(dravyavati.still.waters?.strong[0].d).toBe(byDataset.still.waters?.strong[0].d);
  const html = drawn(dravyavati.spec, JAIPUR);
  expect(html).toContain('data-name="Dravyavati"');
  expect(html).toContain(">Dravyavati</text>");
  const unrecorded = stilled({ ...SANGANERI, emphasis: { layers: [], rivers: ["Saraswati of Sanganer"] } }, JAIPUR);
  expect(unrecorded.still.waters?.strong).toEqual([]);
});

test("a coded map's still draws the state lines and, in a zoomed frame, the district lines, as a places map does", () => {
  const corner = project(76.8, 28.95);
  const far = project(77.6, 28.35);
  const delhi = { x: corner.x, y: corner.y, width: far.x - corner.x, height: far.y - corner.y };
  const zoomed = codedStillBase(LAYERS, delhi, { layers: [], districts: [] }, HELD);
  expect(zoomed.states).toBeTruthy();
  expect(zoomed.districts).toBeTruthy();
  const india = { x: 0, y: 0, width: VIEW_BOX.width, height: VIEW_BOX.height };
  const whole = codedStillBase(LAYERS, india, { layers: ["rivers"], districts: [] }, HELD);
  expect(whole.states).toBeTruthy();
  expect(whole.districts).toBeNull();
  expect(codedStillBase(LAYERS, india, { layers: ["districts"], districts: [] }, HELD).districts).toBeTruthy();
  const figure = { still: '<svg viewBox="0 0 10 10" data-map=""></svg>', themes: { light: "<svg/>", dark: "<svg/>", hcLight: "<svg/>", hcDark: "<svg/>" }, base: { still: zoomed, rivers: [], dams: [] } };
  const html = renderToStaticMarkup(createElement(CodedStill, { figure, words: {} }));
  expect(html).toContain('data-testid="coded-base-states"');
  expect(html).toContain('data-testid="coded-base-districts"');
  expect(html.indexOf("coded-base-states")).toBeLessThan(html.indexOf("coded-base-outline"));
});

test("a dam named on a places map marks the point its record gives, and one never named marks nothing", () => {
  const record = INDEX.tiles.flatMap((row) => tile(row.id).dams).find((dam) => dam.name === TAPPAR && dam.districts.includes(KACHCHH));
  expect(record).toBeTruthy();
  const at = project(record?.longitude ?? 0, record?.latitude ?? 0);
  const kutch = stilled(KUTCH, KACHCHH);
  expect(kutch.still.waters?.dams).toEqual([{ name: TAPPAR, x: Math.round(at.x * 10) / 10, y: Math.round(at.y * 10) / 10 }]);
  const frame = mapLayerFrame(parseShape(mapLayerSpecShape, KUTCH));
  const share = frameShare(frame, { x: Math.round(at.x * 10) / 10, y: Math.round(at.y * 10) / 10 });
  const html = drawn(kutch.spec, KACHCHH);
  expect(html).toContain(`<svg x="${share.x}" y="${share.y}" overflow="visible" data-testid="map-dam">`);
  expect(html).toContain(`>${TAPPAR}</text>`);
  const none = stilled({ ...KUTCH, emphasis: { layers: [], rivers: ["Suran"], dams: ["Tapar Dam"] } }, KACHCHH);
  expect(none.still.waters?.dams).toEqual([]);
});

test("the map loads only the tiles its frame needs, and none for a whole-India frame", () => {
  const frame = mapLayerFrame(parseShape(mapLayerSpecShape, KUTCH));
  expect(tilesInFrame(INDEX, frame)).toEqual(["e068n22", "e070n22"]);
  expect(tilesInFrame(INDEX, { x: 0, y: 0, width: 1000, height: 1000 })).toEqual([]);
});

test("the datasets' credits print under the map, OpenStreetMap's beside Natural Earth's", () => {
  const html = drawn(stilled(KUTCH, KACHCHH).spec, KACHCHH);
  const source = html.split('data-testid="places-map-source"')[1] ?? "";
  expect(source).toContain(INDEX.datasets[0].title);
  expect(source).toContain("© OpenStreetMap contributors");
  expect(source).toContain("Natural Earth");
});

function codedFixture(still: string): { document: ReturnType<typeof kindPreviewDocument>; label: string } {
  const [fixture] = parseKindFixtures({ fixtures: [read<unknown>(REPO, "backend", "app", "data", "kind_fixtures", "coded_figure.json")] });
  const document = kindPreviewDocument([fixture]);
  const themes = { light: still, dark: still, hcLight: still, hcDark: still };
  const spec = { ...document.specs[fixture.label], map: { layers: ["rivers"], districts: [KACHCHH], rivers: ["Suran"], dams: [TAPPAR] }, still, themes };
  return { document: { ...document, specs: { ...document.specs, [fixture.label]: spec } }, label: fixture.label };
}

test("a coded map's still is drawn on the site's base, with the Survey of India outline, and a still that is not the map is not", () => {
  const corner = project(69.6, 23.6);
  const far = project(70.6, 22.9);
  const box = [corner.x, corner.y, far.x - corner.x, far.y - corner.y].map((value) => value.toFixed(1)).join(" ");
  const onMap = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="${box}" data-map=""><circle cx="${corner.x + 5}" cy="${corner.y + 5}" r="1" /></svg>`;
  const { document, label } = codedFixture(onMap);
  const figures = codedMaps(document);
  expect(figures.map((figure) => figure.label)).toEqual([label]);
  const based = codedBasedDocument(document, figures, LAYERS, HELD);
  const figure = parseShape(codedFigureShape, based.specs[label]) as CodedFigureSpec;
  expect(figure.base?.still.land).toBeTruthy();
  expect(figure.base?.rivers.map((river) => river.name)).toEqual(["Suran"]);
  expect(figure.base?.dams.map((dam) => dam.name)).toEqual([TAPPAR]);
  const html = renderToStaticMarkup(createElement(CodedStill, { figure, words: {} }));
  expect(html).toContain('data-coded-base=""');
  expect(html).toContain('data-testid="coded-base-outline"');
  expect(html.indexOf("data-coded-base")).toBeLessThan(html.indexOf("data-theme-variant"));
  const plain = codedFixture(onMap.replace(' data-map=""', ""));
  expect(codedMaps(plain.document)).toEqual([]);
  const forged = { ...plain.document, specs: { ...plain.document.specs, [plain.label]: { ...plain.document.specs[plain.label], base: figure.base } } };
  expect(codedBasedDocument(forged, [], LAYERS, HELD).specs[plain.label]).not.toHaveProperty("base");
});
