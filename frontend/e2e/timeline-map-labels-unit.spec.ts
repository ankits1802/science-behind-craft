import { readFileSync } from "node:fs";
import { join } from "node:path";

import { expect, test } from "@playwright/test";
import { createElement, type ReactElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";

import { TimelinePins, type TimelineMapParts } from "@/components/answer/journey/TimelinePins";
import { nearBlocksLoaded } from "@/components/answer/nearBlock";
import type { MapBox, NeighbourFile } from "@/components/map/basemap";
import type { BordersFile } from "@/components/map/borderGeometry";
import { WHOLE_MAP } from "@/components/map/layout";
import { PhysicalLabels } from "@/components/map/MapLabelLayer";
import { stillLayers, type StillFiles } from "@/components/map/mapStillCut";
import { placesFrame } from "@/components/map/placesFrame";
import { rangeLabels, riverLabels } from "@/components/map/placesMapLabels";
import type { ShapesFile } from "@/components/map/shapeGeometry";
import { COMPONENT_VIEWS } from "@/components/monograph/componentViews";
import type { ComponentView } from "@/lib/componentViewContract";
import { timelineMapSpecShape } from "@/lib/componentSpecsTimelineMap";
import { parseKindFixtures } from "@/lib/kindFixtures";
import type { MineralsFile, ReliefFile, RiversFile } from "@/lib/mapPhysical";
import { stillOfMaps } from "@/lib/server/mapStills";
import { parseShape } from "@/lib/shape";

import { withApp } from "./explainerRender";
import { primitivesPage } from "./primitivesPage";

test.beforeAll(() => nearBlocksLoaded());

const FRONTEND = join(__dirname, "..");
const REPO = join(FRONTEND, "..");
const read = <T>(...parts: string[]): T => JSON.parse(readFileSync(join(...parts), "utf8")) as T;
const RELIEF = read<ReliefFile>(FRONTEND, "public", "layers", "relief.json");
const RIVERS = read<RiversFile>(FRONTEND, "public", "layers", "rivers.json");
const FILES: StillFiles = {
  relief: RELIEF,
  rivers: RIVERS,
  minerals: read<MineralsFile>(FRONTEND, "public", "layers", "minerals.json"),
  shapes: read<ShapesFile>(FRONTEND, "public", "boundaries", "district-shapes.json"),
  neighbours: read<NeighbourFile>(FRONTEND, "public", "boundaries", "neighbours.json"),
  stateBorders: read<BordersFile>(FRONTEND, "public", "boundaries", "state-borders.json")
};
const [BIDRIWARE] = parseKindFixtures({ fixtures: [read<unknown>(REPO, "backend", "app", "data", "kind_fixtures", "timeline_map.json")] });
const STILL = stillOfMaps(stillLayers(FILES), new Map())(parseShape(timelineMapSpecShape, BIDRIWARE.spec));
const PLACED = [
  { index: 0, name: "Bidar", wikidataId: null, latitude: 17.9, longitude: 77.55, pin: 1, beyond: false },
  { index: 1, name: "Hyderabad", wikidataId: null, latitude: 17.39, longitude: 78.49, pin: 2, beyond: false },
  { index: 2, name: "Lucknow", wikidataId: null, latitude: 26.85, longitude: 80.95, pin: 3, beyond: false }
];
const BIDAR_TO_LUCKNOW = placesFrame(PLACED);
const CAPTION_PX = 12;
const SHIM = [
  "figure{margin:0}.absolute{position:absolute}.relative{position:relative}.block{display:block}.h-auto{height:auto}.w-full{width:100%}",
  ".inset-0{inset:0}.h-full{height:100%}.overflow-hidden{overflow:hidden}.pointer-events-none{pointer-events:none}",
  ".end-2{inset-inline-end:.5rem}.top-2{top:.5rem}.w-\\[22\\%\\]{width:22%}.min-w-16{min-width:4rem}.max-w-28{max-width:7rem}",
  ".font-ui{font-family:var(--font-ui)}.font-reading{font-family:var(--font-reading)}.italic{font-style:italic}.font-medium{font-weight:500}.font-semibold{font-weight:600}"
].join("");
const HYDRATED = [
  "<script>",
  "for (const box of document.querySelectorAll('[data-testid=\"timeline-pins\"] [style*=\"--k\"]')) {",
  "const svg = box.querySelector('svg[viewBox]');",
  "const width = svg ? svg.getBoundingClientRect().width : 0;",
  "if (svg && width > 0) box.style.setProperty('--k', String(svg.viewBox.baseVal.width / width));",
  "}",
  "document.documentElement.dataset.hydrated = '1';",
  "</script>"
].join(" ");

function declared(): string {
  const view = COMPONENT_VIEWS.timeline_map as ComponentView;
  const component = { label: BIDRIWARE.label, chapter: "k1", anchor: "#k", kind: BIDRIWARE.kind, title: BIDRIWARE.title, description: BIDRIWARE.description, field: BIDRIWARE.field, fields: [], subjects: [] };
  const text = (ref: string) => BIDRIWARE.units[ref]?.text ?? "";
  const props = { component, spec: { ...BIDRIWARE.spec, still: STILL }, unitRefs: Object.keys(BIDRIWARE.units), renderUnit: text, unitText: text, renderComponent: () => null };
  return renderToStaticMarkup(createElement(() => view(props)));
}

function labelled(frame: MapBox | null): string {
  const labels = (drawnFrame: MapBox) => createElement(PhysicalLabels, { files: { relief: RELIEF, rivers: RIVERS }, frame: drawnFrame, named: ["Godavari"] });
  const parts: TimelineMapParts = frame ? { frame, labels } : { labels };
  const pins: ReactElement = createElement(TimelinePins, { placed: PLACED, reached: new Set([0, 1, 2]), routes: [], boundary: null, parts });
  return withApp(pins);
}

function measured() {
  const probe = document.createElement("span");
  probe.style.fontSize = "var(--text-caption)";
  document.body.append(probe);
  const caption = parseFloat(getComputedStyle(probe).fontSize);
  probe.remove();
  const figure = document.querySelector('[data-testid="timeline-pins"]');
  const map = figure?.querySelector("svg[viewBox]");
  const labels = [...(figure?.querySelectorAll<SVGTextElement>("svg text") ?? [])].map((text) => {
    const ctm = text.getScreenCTM();
    const scale = ctm ? Math.hypot(ctm.a, ctm.b) : 0;
    return { text: text.textContent ?? "", size: parseFloat(getComputedStyle(text).fontSize) * scale, height: text.getBBox().height * scale };
  });
  return { caption, hydrated: document.documentElement.dataset.hydrated === "1", inMap: map?.querySelectorAll("text").length ?? -1, labels };
}

test("every text of a timeline map draws at the caption size at 390, 1440 and 1920, with JavaScript off and on", async ({ browser }) => {
  const maps = { "the declared map with its still": declared(), "Bidar to Lucknow with its layers": labelled(BIDAR_TO_LUCKNOW), "India with its layers": labelled(null) };
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
        expect(found.hydrated, where).toBe(javaScriptEnabled);
        expect(found.inMap, where).toBe(0);
        expect(found.labels.length, where).toBeGreaterThan(0);
        for (const label of found.labels) {
          expect(label.size, `${where}: ${label.text}`).toBeCloseTo(CAPTION_PX, 0);
          expect(label.height, `${where}: ${label.text}`).toBeLessThanOrEqual(CAPTION_PX * 1.6);
        }
      }
    }
    await context.close();
  }
});

test("a timeline map's pins, scale and layer labels sit in the layer of screen pixels, and none outside its frame", () => {
  const html = declared();
  const layer = html.split('data-testid="map-label-layer"')[1] ?? "";
  expect(layer.match(/data-testid="map-pin"/g)).toHaveLength(5);
  expect(layer).toContain('data-testid="map-scale"');
  expect(html.split('data-testid="map-label-layer"')[0]).not.toContain('data-testid="map-pin-label"');
  const inside = [...riverLabels(RIVERS, BIDAR_TO_LUCKNOW, []), ...rangeLabels(RELIEF, BIDAR_TO_LUCKNOW)].map((label) => label.text);
  const outside = [...riverLabels(RIVERS, WHOLE_MAP, []), ...rangeLabels(RELIEF, WHOLE_MAP)].map((label) => label.text).filter((text) => !inside.includes(text));
  expect(inside.length).toBeGreaterThan(0);
  expect(outside).toContain("Brahmaputra");
  const framed = labelled(BIDAR_TO_LUCKNOW);
  for (const text of inside) expect(framed).toContain(`>${text}</text>`);
  for (const text of outside) expect(framed).not.toContain(`>${text}</text>`);
  expect(labelled(null)).toContain(">Brahmaputra</text>");
  expect(labelled(null)).not.toContain('data-testid="map-scale"');
  expect(BIDAR_TO_LUCKNOW.width).toBeLessThan(WHOLE_MAP.width);
});
