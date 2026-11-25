import { expect, test } from "@playwright/test";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";

import { nearBlocksLoaded } from "../components/answer/nearBlock";
import { PREVIEW_TOKEN, previewApiPath, previewPagePath } from "../app/(reading)/preview/[token]/previewDocument";
import { COMPONENT_VIEWS } from "../components/monograph/componentViews";
import { DECLARED_VIEWS, VIEWS } from "../components/monograph/kinds/general";
import { linePoints, tickLabel } from "../components/monograph/kinds/general/ChartLine";
import { largestValue } from "../components/monograph/kinds/general/MapLayerView";
import {
  chartRange,
  chartSpecShape,
  drawingSource,
  drawingSpecShape,
  drawingViewBox,
  eraYear,
  GENERAL_KINDS,
  mapLayerSpecShape,
  parsedSpec,
  placeRadius,
  share,
  tableSpecShape,
  timelineSpecShape,
  type ChartSpec
} from "../lib/componentSpecsGeneral";
import { TIMELINE_MAP_KIND } from "../lib/componentSpecsTimelineMap";
import { isPlaying, nextStop, played, pointPositions, restingPlay, spreadPositions, type PlayAction } from "../lib/timelinePlay";
import type { ComponentView } from "../lib/componentViewContract";
import type { MonographComponent } from "../lib/monographDocument";

test.beforeAll(() => nearBlocksLoaded());

const HEAD = { title: "u0001", caption: "u0002" };
const SVG = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 60"><rect x="1" y="1" width="20" height="10" /></svg>';
const DRAWING = { head: HEAD, svg: SVG, alt: "u0003" };
const CHART: ChartSpec = {
  head: HEAD,
  form: "bars",
  valueLabel: "u0003",
  series: [
    {
      name: "u0004",
      points: [
        { label: "u0005", value: 50, reading: "u0006" },
        { label: "u0007", value: 100, reading: "u0008" }
      ]
    }
  ],
  emphasis: 1
};
const TABLE = {
  head: HEAD,
  columns: [
    { label: "u0003", numeric: false },
    { label: "u0004", numeric: true }
  ],
  rows: [{ cells: ["u0005", "u0006"] }, { cells: ["u0007", "u0008"] }]
};
const TIMELINE = {
  head: HEAD,
  events: [
    { year: 1868, when: "u0003", title: "u0004", text: "u0005" },
    { year: 1947, when: "u0006", title: "u0007", text: "u0008" }
  ]
};
const MAP = {
  head: HEAD,
  places: [
    { longitude: 69.67, latitude: 23.25, name: "u0003", reading: "u0004", value: 518 },
    { longitude: 75.79, latitude: 26.91, name: "u0005", reading: "u0006", value: 2072 }
  ],
  valueLabel: "u0007"
};

function component(kind: string): MonographComponent {
  return { label: `test-craft/process/${kind.replaceAll("_", "-")}`, chapter: "made", anchor: "#c", kind, title: "A component", description: "A component drawn in a test.", field: "PROCESS", fields: [], subjects: [] };
}

const GENERAL_VIEWS = { ...VIEWS, ...DECLARED_VIEWS };
const AUTHORED_TABLE = { id: "glance", numeral: 1, chapterNo: "u0001", title: "u0002", titleId: "glance-t", rows: [{ term: "u0003", value: "u0004" }] };

function render(view: ComponentView, kind: string, spec: object): string {
  const props = { component: component(kind), spec: spec as Record<string, unknown>, unitRefs: [], renderUnit: (ref: string) => `[${ref}]`, renderComponent: () => null };
  return renderToStaticMarkup(createElement(() => view(props)));
}

function drawn(kind: (typeof GENERAL_KINDS)[number], spec: object): string {
  return render(GENERAL_VIEWS[kind] as ComponentView, kind, spec);
}

test("the general group draws every general kind and the page's registry carries them", () => {
  expect(Object.keys(GENERAL_VIEWS).sort()).toEqual([...GENERAL_KINDS, TIMELINE_MAP_KIND].sort());
  expect(COMPONENT_VIEWS.drawing).toBe(VIEWS.drawing);
  for (const kind of GENERAL_KINDS) expect(COMPONENT_VIEWS[kind]).toBeDefined();
  expect(Object.keys(COMPONENT_VIEWS).filter((kind) => kind.startsWith("general_"))).toEqual([]);
});

test("one kind per job: a declared spec draws as the site's figure and an authored spec as its own view", () => {
  const declared = render(COMPONENT_VIEWS.fact_table as ComponentView, "fact_table", TABLE);
  expect(declared).toContain('data-general="fact_table"');
  const authored = render(COMPONENT_VIEWS.fact_table as ComponentView, "fact_table", AUTHORED_TABLE);
  expect(authored).not.toContain("data-general");
  expect(authored).toContain('<dl class="glance">');
  expect(render(COMPONENT_VIEWS.chart as ComponentView, "chart", CHART)).toContain('data-general="chart"');
});

test("each general spec parses with its shape and a spec off its shape draws nothing", () => {
  expect(parsedSpec(drawingSpecShape, DRAWING)?.alt).toBe("u0003");
  expect(parsedSpec(chartSpecShape, CHART)?.series[0].points).toHaveLength(2);
  expect(parsedSpec(tableSpecShape, TABLE)?.rows).toHaveLength(2);
  expect(parsedSpec(timelineSpecShape, TIMELINE)?.events[1].year).toBe(1947);
  expect(parsedSpec(mapLayerSpecShape, MAP)?.places[0].value).toBe(518);
  expect(parsedSpec(drawingSpecShape, { ...DRAWING, svg: "<script>alert(1)</script>" })).toBeNull();
  expect(parsedSpec(mapLayerSpecShape, { ...MAP, places: [{ ...MAP.places[0], longitude: 120 }] })).toBeNull();
  expect(parsedSpec(chartSpecShape, { ...CHART, series: [] })).toBeNull();
  expect(drawn("chart", { ...CHART, form: "pie" })).toBe("");
});

test("bars are drawn at their share of the largest value from zero and the titled mark is emphasised", () => {
  expect(chartRange(CHART)).toEqual({ low: 0, high: 100 });
  expect(share(50, { low: 0, high: 100 })).toBe(0.5);
  const html = drawn("chart", CHART);
  expect(html).toContain('style="width:50.00%"');
  expect(html).toContain('data-emph="true" style="width:100.00%"');
  expect(html).toContain("[u0006]");
  expect(html).not.toContain("All 2 values");
});

test("a line is drawn across the plot with every value behind All N values", () => {
  const line = { ...CHART, form: "line" as const, emphasis: null };
  expect(linePoints(line.series[0], { low: 50, high: 100 })).toEqual([
    { x: 56, y: 196 },
    { x: 624, y: 14 }
  ]);
  expect(tickLabel(1250.5)).toBe("1,250.5");
  const html = drawn("chart", line);
  expect(html).toContain("All 2 values");
  expect(html).toContain("<polyline");
});

test("a table puts each unit in its cell, the first as the row's header, numbers aligned to the end", () => {
  const html = drawn("fact_table", TABLE);
  expect(html.match(/<th scope="col"/g)).toHaveLength(2);
  expect(html.match(/<th scope="row"/g)).toHaveLength(2);
  expect(html).toContain("text-end [font-variant-numeric:lining-nums_tabular-nums]\">[u0006]</td>");
});

test("a timeline places its events by year as points to press, rests on the last and has Play, not a slider", () => {
  expect(pointPositions([1868, 1947])).toEqual([0, 100]);
  expect(pointPositions([1868, 1907.5, 1947])).toEqual([0, 50, 100]);
  expect(pointPositions([1900, 1900])).toEqual([50, 50]);
  expect(eraYear(-300)).toBe("300 BCE");
  const html = drawn("timeline", TIMELINE);
  expect(html).not.toContain('type="range"');
  expect(html).not.toContain("<input");
  const points = [...html.matchAll(/<button[^>]*data-testid="timeline-point"[^>]*>/g)].map((found) => found[0]);
  expect(points).toHaveLength(2);
  expect(points.map((point) => /aria-pressed="(\w+)"/.exec(point)?.[1])).toEqual(["false", "true"]);
  expect(points.map((point) => /aria-label="([^"]+)"/.exec(point)?.[1])).toEqual(["1868", "1947"]);
  expect(points.map((point) => /inset-inline-start:([\d.]+)%/.exec(point)?.[1])).toEqual(["0", "100"]);
  expect(html).toContain('data-testid="timeline-play"');
  expect(html).toMatch(/data-testid="timeline-play"[^>]*>.*?<span>Play<\/span>/);
  expect(html).toContain("<span>1868</span><span>1947</span>");
  expect(html.match(/<li /g)).toHaveLength(2);
  expect(html.match(/aria-current="step"/g)).toHaveLength(1);
  expect(html).toContain('data-testid="timeline-year">[u0006]</p>');
});

test("crowded points are spread to stay apart and in the axis, in their order", () => {
  expect(spreadPositions([0, 1, 2, 100])).toEqual([0, 6, 12, 100]);
  expect(spreadPositions([0, 99, 100, 100])).toEqual([0, 88, 94, 100]);
  expect(spreadPositions(Array.from({ length: 21 }, () => 50))).toEqual(Array.from({ length: 21 }, (_, at) => at * 5));
  expect(spreadPositions([40])).toEqual([40]);
});

test("a timeline plays from its first event once seen, loops, jumps to a pressed point and pauses; reduced, Play steps one", () => {
  const run = (actions: PlayAction[], rest = 2) => actions.reduce(played, restingPlay(rest));
  expect([nextStop(0, 3), nextStop(2, 3), nextStop(0, 0)]).toEqual([1, 0, 0]);
  expect(isPlaying(restingPlay(2), true, 3)).toBe(false);
  const seen = run([{ type: "seen", on: true }, { type: "start" }]);
  expect([seen.at, isPlaying(seen, true, 3), isPlaying(seen, false, 3), isPlaying(seen, true, 1)]).toEqual([0, true, false, false]);
  expect(run([{ type: "seen", on: true }, { type: "start" }, { type: "tick", count: 3 }, { type: "tick", count: 3 }, { type: "tick", count: 3 }]).at).toBe(0);
  const jumped = run([{ type: "seen", on: true }, { type: "start" }, { type: "choose", at: 2 }, { type: "start" }]);
  expect([jumped.at, isPlaying(jumped, true, 3)]).toEqual([2, true]);
  const paused = played(jumped, { type: "toggle", motion: true, count: 3 });
  expect([paused.at, isPlaying(paused, true, 3)]).toEqual([2, false]);
  expect(isPlaying(played(paused, { type: "toggle", motion: true, count: 3 }), true, 3)).toBe(true);
  const away = played(seen, { type: "seen", on: false });
  expect(isPlaying(away, true, 3)).toBe(false);
  const still = played(restingPlay(2), { type: "toggle", motion: false, count: 3 });
  expect([still.at, still.wanted, isPlaying(still, false, 3)]).toEqual([0, true, false]);
});

test("a map layer marks each place on India's outline with a disc sized by its value and lists them", () => {
  expect(largestValue(MAP.places)).toBe(2072);
  expect(placeRadius(null, 2072)).toBe(7);
  expect(placeRadius(2072, 2072)).toBe(22);
  const html = drawn("map_layer", MAP);
  expect(html.match(/<circle /g)).toHaveLength(2);
  expect(html).not.toContain("StateLines");
  expect(html).toContain("[u0004]");
});

test("a drawing is drawn as an image of its cleaned SVG at its own aspect", () => {
  expect(drawingViewBox(SVG)).toEqual({ x: 0, y: 0, width: 120, height: 60 });
  expect(drawingSource("<svg/>")).toBe("data:image/svg+xml;charset=utf-8,%3Csvg%2F%3E");
  const html = drawn("drawing", DRAWING);
  expect(html).toContain('width="120" height="60"');
  expect(html).toContain('src="data:image/svg+xml;charset=utf-8,%3Csvg');
  expect(html).not.toContain("<rect");
});

test("a preview link is read from the API by its signed token and lives at its own page", () => {
  const token = `${"a".repeat(32)}.1795000000.${"b".repeat(64)}`;
  expect(PREVIEW_TOKEN.test(token)).toBe(true);
  expect(PREVIEW_TOKEN.test("kvpv_something")).toBe(false);
  expect(previewApiPath(token)).toBe(`/knowledge/pages/previews/${token}`);
  expect(previewPagePath(token)).toBe(`/preview/${token}`);
});
