import { readFileSync } from "node:fs";
import { join } from "node:path";

import { expect, test } from "@playwright/test";
import { createElement } from "react";

import { districtFrame, zoomedBox } from "@/components/answer/journey/journeyGeometry";
import { ZoomDistrictMap } from "@/components/answer/journey/ZoomDistrict";
import { SupplyPins } from "@/components/answer/place/SupplyPins";
import { WHOLE_MAP } from "@/components/map/layout";
import { frameShare } from "@/components/map/placesMapLabels";
import { project } from "@/components/map/projection";
import { decodeShapes, type ShapesFile } from "@/components/map/shapeGeometry";
import type { SupplyPin } from "@/lib/supplyView";

import { attribute, withApp } from "./explainerRender";
import { primitivesPage } from "./primitivesPage";

const SHAPES = decodeShapes(JSON.parse(readFileSync(join(__dirname, "..", "public", "boundaries", "district-shapes.json"), "utf8")) as ShapesFile);
const KACHCHH = 449;
const DISTRICT = { districtLgd: KACHCHH, name: "Kachchh", stateName: "Gujarat" };
const PINS: SupplyPin[] = [
  { key: "bhuj", origin: "Bhuj", materials: "alizarin", latitude: 23.25, longitude: 69.67, pin: 1, byDistrict: true },
  { key: "barmer", origin: "Barmer", materials: "indigo", latitude: 25.75, longitude: 71.39, pin: 2, byDistrict: false },
  { key: "sanganer", origin: "Sanganer", materials: "madder", latitude: 26.82, longitude: 75.79, pin: 3, byDistrict: false }
];
const CAPTION_PX = 12;
const SHIM = [
  "figure{margin:0}.absolute{position:absolute}.relative{position:relative}.block{display:block}.h-auto{height:auto}.w-full{width:100%}",
  ".inset-0{inset:0}.h-full{height:100%}.overflow-hidden{overflow:hidden}.pointer-events-none{pointer-events:none}",
  ".end-2{inset-inline-end:.5rem}.top-2{top:.5rem}.w-\\[22\\%\\]{width:22%}.min-w-16{min-width:4rem}.max-w-28{max-width:7rem}",
  ".font-ui{font-family:var(--font-ui)}.font-reading{font-family:var(--font-reading)}.italic{font-style:italic}.font-medium{font-weight:500}.font-semibold{font-weight:600}"
].join("");

const supply = () => withApp(createElement(SupplyPins, { pins: PINS, boundary: null }));
const zoom = (moving: boolean) => withApp(createElement(ZoomDistrictMap, { shapes: SHAPES, district: DISTRICT, boundary: null, moving }));

function measured(figureId: string) {
  const probe = document.createElement("span");
  probe.style.fontSize = "var(--text-caption)";
  document.body.append(probe);
  const caption = parseFloat(getComputedStyle(probe).fontSize);
  probe.remove();
  const figure = document.querySelector(`[data-testid="${figureId}"]`);
  const map = figure?.querySelector("svg[viewBox]");
  const labels = [...(figure?.querySelectorAll<SVGTextElement>("svg text") ?? [])].map((text) => {
    const ctm = text.getScreenCTM();
    const scale = ctm ? Math.hypot(ctm.a, ctm.b) : 0;
    return { text: text.textContent ?? "", size: parseFloat(getComputedStyle(text).fontSize) * scale };
  });
  return { caption, inMap: map?.querySelectorAll("text").length ?? -1, labels };
}

test("every pin and name of the answers' supply and zoom maps draws at the caption size at 390, 1440 and 1920, with JavaScript off and on", async ({ browser }) => {
  const maps = { "supply-pins": supply(), "zoom-district": zoom(true) };
  for (const javaScriptEnabled of [false, true]) {
    const context = await browser.newContext({ javaScriptEnabled });
    const page = await context.newPage();
    for (const [viewport, column] of [[390, 358], [1440, 718], [1920, 1000]] as const) {
      await page.setViewportSize({ width: viewport, height: 1200 });
      for (const [figureId, html] of Object.entries(maps)) {
        await page.setContent(primitivesPage(`<style>${SHIM}</style><main style="width:${column}px;margin:0 16px">${html}</main>`));
        const found = await page.evaluate(measured, figureId);
        const where = `${figureId} at ${viewport} with JavaScript ${javaScriptEnabled ? "on" : "off"}`;
        expect(found.caption, where).toBe(CAPTION_PX);
        expect(found.inMap, where).toBe(0);
        expect(found.labels.length, where).toBeGreaterThan(0);
        for (const label of found.labels) expect(label.size, `${where}: ${label.text}`).toBeCloseTo(CAPTION_PX, 0);
      }
    }
    await context.close();
  }
});

test("the supply map's pins sit in the layer of screen pixels, numbered, and none in the map's own drawing", () => {
  const html = supply();
  const [drawing, layer = ""] = html.split('data-testid="map-label-layer"');
  expect(layer.match(/data-testid="map-pin"/g)).toHaveLength(PINS.length);
  for (const pin of PINS) expect(layer).toContain(`data-testid="map-pin-label">${pin.pin}</text>`);
  expect(drawing).not.toContain('data-testid="map-pin-label"');
  expect(drawing).not.toContain("<text");
});

test("the zoom map names its district in the layer of screen pixels at the district's point, zoomed in and at rest", () => {
  const shape = SHAPES.find((entry) => entry.lgd === KACHCHH)!;
  const at = project(shape.centroid[0], shape.centroid[1]);
  for (const moving of [true, false]) {
    const html = zoom(moving);
    const [drawing, layer = ""] = html.split('data-testid="map-label-layer"');
    expect(layer).toContain(">Kachchh</text>");
    expect(drawing).not.toContain("<text");
    const shown = moving ? zoomedBox(districtFrame(shape)) : WHOLE_MAP;
    const share = frameShare(shown, at);
    expect(attribute(html, "district-tag", "x")).toEqual([share.x]);
    expect(attribute(html, "district-tag", "y")).toEqual([share.y]);
  }
  expect(zoomedBox({ scale: 1, x: "0%", y: "0%" })).toEqual(WHOLE_MAP);
  const zoomed = zoomedBox({ scale: 2, x: "-50%", y: "-25%" });
  expect(zoomed).toEqual({ x: WHOLE_MAP.width / 4, y: WHOLE_MAP.height / 8, width: WHOLE_MAP.width / 2, height: WHOLE_MAP.height / 2 });
});
