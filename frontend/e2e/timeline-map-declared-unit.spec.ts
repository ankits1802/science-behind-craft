import { readFileSync } from "node:fs";
import { join } from "node:path";

import { expect, test } from "@playwright/test";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";

import { nearBlocksLoaded } from "../components/answer/nearBlock";
import { viewBoxOf } from "../components/map/basemap";
import { placesFrame } from "../components/map/placesFrame";
import { project, VIEW_BOX } from "../components/map/projection";
import { HomeHatch } from "../components/map/TimelineMapLayers";
import { COMPONENT_VIEWS } from "../components/monograph/componentViews";
import { declaredForm, foundPoints, homeDistricts, layerCredits, timelineMapSource, timelineMapSpecShape } from "../lib/componentSpecsTimelineMap";
import type { ComponentView } from "../lib/componentViewContract";
import { parseKindFixtures, type KindFixture } from "../lib/kindFixtures";
import { appDrawn } from "../lib/monographScopes";
import { parseShape } from "../lib/shape";
import { timelineEntries, timelineStops } from "../lib/timelineView";

import { attribute, FIXED_WIDE_WIDTH, gridTracks, SHRINKABLE_TRACK, shownText } from "./explainerRender";
import { primitivesPage } from "./primitivesPage";

test.beforeAll(() => nearBlocksLoaded());

const BACKEND_DATA = join(__dirname, "..", "..", "backend", "app", "data");
const FILED = JSON.parse(readFileSync(join(BACKEND_DATA, "kind_fixtures", "timeline_map.json"), "utf8")) as unknown;
const [BIDRIWARE] = parseKindFixtures({ fixtures: [FILED] });
const KUTCH = JSON.parse(readFileSync(join(BACKEND_DATA, "monographs", "Kutch-Ajrakh", "specs", "kutch-ajrakh__history__dated-record-timeline-map.json"), "utf8")) as Record<string, unknown>;
const NAMES = ["Bidar", "Hyderabad", "Purnia", "Murshidabad", "Lucknow"];
const SVG_FIT = "<style>svg{display:block;width:100%;height:auto}</style>";

function drawn(fixture: KindFixture, spec: Record<string, unknown> = fixture.spec): string {
  const view = COMPONENT_VIEWS.timeline_map as ComponentView;
  const component = { label: fixture.label, chapter: "k1", anchor: "#k", kind: fixture.kind, title: fixture.title, description: fixture.description, field: fixture.field, fields: [], subjects: [] };
  const props = { component, spec, unitRefs: Object.keys(fixture.units), renderUnit: (ref: string) => fixture.units[ref]?.text ?? "", unitText: (ref: string) => fixture.units[ref]?.text ?? "", renderComponent: () => null };
  return renderToStaticMarkup(createElement(() => view(props)));
}

test("a declared timeline map is the site's own drawing, and Kutch Ajrakh's route map keeps its authored view", () => {
  expect(declaredForm("timeline_map", BIDRIWARE.spec)).toBe(true);
  expect(declaredForm("timeline_map", KUTCH)).toBe(false);
  expect(appDrawn("timeline_map", BIDRIWARE.spec)).toBe(true);
  expect(appDrawn("timeline_map", KUTCH)).toBe(false);
  const authored = drawn(BIDRIWARE, KUTCH);
  expect(authored).toContain('class="tl-ctl"');
  expect(authored).not.toContain('data-testid="timeline-map"');
});

test("the server's placement reaches every place, and the page's own district is hatched", () => {
  const map = parseShape(timelineMapSpecShape, BIDRIWARE.spec);
  expect(map.places.map((place) => place.found?.districtLgd)).toEqual([529, 507, 214, 319, 162]);
  expect(map.places[0].found).toEqual({ latitude: 17.766, longitude: 77.144, districtLgd: 529 });
  expect(homeDistricts(map)).toEqual([529]);
  expect(layerCredits(map, "DR_DISTRICT_SHAPES").map((dataset) => dataset.code)).toEqual(["ETOPO1_ICE", "NATURAL_EARTH_10M_PHYSICAL"]);
  const shapes = [529, 507].map((lgd) => ({ lgd, stateLgd: 1, rings: [[[77, 17], [77.5, 17], [77.5, 18], [77, 17]] as [number, number][]], centroid: [77.2, 17.5] as [number, number] }));
  const hatch = renderToStaticMarkup(createElement("svg", null, createElement(HomeHatch, { shapes, home: homeDistricts(map) })));
  expect(attribute(hatch, "timeline-home", "class")).toEqual(["pointer-events-none"]);
  expect([...hatch.matchAll(/data-lgd="(\d+)"/g)].map((found) => found[1])).toEqual(["529"]);
  expect(hatch).toContain("fill-[url(#kv-map-place)] stroke-[var(--terracotta)]");
});

test("the map is framed to its places and rests on its last year with every place pinned", () => {
  const map = parseShape(timelineMapSpecShape, BIDRIWARE.spec);
  const frame = placesFrame(foundPoints(map));
  expect(frame.width).toBeLessThan(VIEW_BOX.width);
  expect(frame.height / frame.width).toBeCloseTo(0.8, 2);
  for (const point of foundPoints(map)) {
    const at = project(point.longitude, point.latitude);
    expect(at.x).toBeGreaterThan(frame.x);
    expect(at.x).toBeLessThan(frame.x + frame.width);
    expect(at.y).toBeGreaterThan(frame.y);
    expect(at.y).toBeLessThan(frame.y + frame.height);
  }
  const source = timelineMapSource(map, (ref) => BIDRIWARE.units[ref]?.text ?? "");
  expect(timelineStops(timelineEntries(source))).toEqual([1422, 1701, 1801, 1956]);
  const html = shownText(drawn(BIDRIWARE));
  expect(attribute(html, "timeline-map", "data-year")).toEqual(["1956"]);
  expect(html).toContain(`viewBox="${viewBoxOf(frame)}"`);
  expect(html.match(/data-testid="map-pin"/g)).toHaveLength(5);
  expect(attribute(html, "timeline-entry", "data-state")).toEqual(["past", "past", "current"]);
  expect([...html.matchAll(/data-testid="timeline-years">([^<]+)</g)].map((found) => found[1])).toEqual(["1422–1436", "18th century", "18th century", "19th century", "1956"]);
});

test("the figure names its places, cites every sentence's unit and credits the boundary and the layers", () => {
  const html = shownText(drawn(BIDRIWARE));
  expect(html).toContain('<p class="kv-fig-no">Map</p>');
  expect(html).toContain("Where bidri was made, from Bidar to Lucknow");
  for (const unit of ["u0002", "u0008", "u0009", "u0010"]) expect(html).toContain(BIDRIWARE.units[unit].text);
  const listed = html.split('data-testid="timeline-places"')[1] ?? "";
  for (const name of NAMES) expect(listed).toContain(name);
  expect(html).toContain("External boundaries of India as depicted by Survey of India.");
  expect(html).toContain("Indian district boundaries, matched to LGD codes");
  expect(html.match(/data-testid="dataset-credit"/g)).toHaveLength(2);
  expect(html).not.toContain("Coordinates: Wikidata.");
  expect(html).toContain('aria-label="Through time"');
  expect(html).toContain('type="range"');
});

test("phone first: every grid track can shrink and the map fills its column at 360 and 1440px", async ({ page }) => {
  const html = drawn(BIDRIWARE);
  const tracks = gridTracks(html);
  expect(tracks.length).toBeGreaterThan(0);
  for (const track of tracks) expect(track).toMatch(SHRINKABLE_TRACK);
  expect(html).not.toMatch(FIXED_WIDE_WIDTH);
  expect(html).toContain("lg:grid-cols-[minmax(0,1.15fr)_minmax(0,1fr)]");
  const drawnWidths: number[] = [];
  for (const width of [360, 1440]) {
    await page.setViewportSize({ width, height: 900 });
    await page.setContent(primitivesPage(`${SVG_FIT}<main id="column" style="padding:0 16px">${html}</main>`));
    const sizes = await page.evaluate(() => {
      const map = document.querySelector('[data-testid="timeline-pins"] svg[viewBox]');
      const column = document.getElementById("column");
      return { map: map?.getBoundingClientRect().width ?? 0, column: column ? column.clientWidth - 32 : 0 };
    });
    expect(sizes.map, `at ${width}px`).toBeGreaterThan(0);
    expect(sizes.map, `at ${width}px`).toBeLessThanOrEqual(sizes.column);
    drawnWidths.push(sizes.map);
  }
  expect(drawnWidths[1]).toBeGreaterThan(drawnWidths[0]);
});
