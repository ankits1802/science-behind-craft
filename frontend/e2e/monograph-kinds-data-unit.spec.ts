import { expect, test } from "@playwright/test";

import { barShare } from "@/components/monograph/kinds/data/ChartView";
import { conceptMeta } from "@/components/monograph/kinds/data/ConceptAtlasView";
import { VIEWS } from "@/components/monograph/kinds/data";
import { supportsLine } from "@/components/monograph/kinds/data/SourceListView";
import { axisEventName, pickName } from "@/components/monograph/kinds/data/TimelineAxisView";
import { VIEWS as PLATE_VIEWS } from "@/components/monograph/kinds/plates";
import { chartShape, componentsHeldBy, mapSequenceShape, pythonJson, sourceListShape, timelineMapShape } from "@/lib/componentSpecsData";
import type { ComponentViews } from "@/lib/componentViewContract";
import { parseShape, ShapeError } from "@/lib/shape";

import { anchorOf, anchorsHeldWithoutView, approvedMarkup, canonical, componentsOfKinds, drawnView, specOf } from "./monographKinds";

const DATA_KINDS = ["chart", "stat_tiles", "fact_table", "map_layer", "map_sequence", "timeline", "timeline_map", "concept_atlas", "related_crafts", "source_list", "source_disagreements", "citation_tool"];
const LANE_VIEWS: ComponentViews = { ...PLATE_VIEWS, ...VIEWS };
const SEQUENCE = "kutch-ajrakh/geography/suran-earthquake-ajrakhpur-cards";

test("the data group draws every one of its kinds", () => {
  expect(Object.keys(VIEWS).sort()).toEqual([...DATA_KINDS].sort());
});

for (const component of componentsOfKinds(DATA_KINDS)) {
  test(`${component.label} draws the approved page's markup from its spec`, () => {
    const view = VIEWS[component.kind];
    if (!view) throw new Error(`no view for ${component.kind}`);
    const approved = canonical(approvedMarkup(anchorOf(component), anchorsHeldWithoutView(component, LANE_VIEWS)));
    expect(canonical(drawnView(view, component, LANE_VIEWS))).toEqual(approved);
  });
}

test("the map sequence names the eight components its cards hold, in page order", () => {
  const labels = new Set(componentsOfKinds(["map_layer", "diagram", "stat_tiles", "swatch_pair"]).map((component) => component.label));
  expect(componentsHeldBy(specOf(SEQUENCE), labels)).toEqual([
    "kutch-ajrakh/geography/suran-flowing-north-map",
    "kutch-ajrakh/geography/suran-dry-below-tapar-dam-map",
    "kutch-ajrakh/geology/dhamadka-epicentre-circle-map",
    "kutch-ajrakh/history/dhamadka-to-ajrakhpur-move-map",
    "kutch-ajrakh/geology/ajrakhpur-borewell-depth",
    "kutch-ajrakh/ecology/effluent-treatment-stats",
    "kutch-ajrakh/geography/lower-sindh-ajrak-survey-stats",
    "kutch-ajrakh/chemistry/iron-on-purpose-and-by-accident"
  ]);
});

test("a container drawn without a renderer for what it holds leaves those places empty", () => {
  const sequence = componentsOfKinds(["map_sequence"])[0];
  if (!VIEWS.map_sequence) throw new Error("the map sequence has a view");
  const html = drawnView(VIEWS.map_sequence, sequence);
  expect(html).toContain('<li class="ws-card"><div class="ws-vis"></div><p class="when"><kv-slot unit="u0605"></kv-slot></p>');
  expect(html).not.toContain("b-ws-iron");
});

test("data attributes are written as the page's script reads them", () => {
  expect(pythonJson([[1981, 518], [1982, 331.5]])).toBe("[[1981, 518], [1982, 331.5]]");
  expect(pythonJson({ world: [0, 0, 1000, 546.71] })).toBe('{"world": [0, 0, 1000, 546.71]}');
  expect(pythonJson([{ title: "The priest-king’s trefoil", routes: [] }])).toBe('[{"title": "The priest-king\\u2019s trefoil", "routes": []}]');
});

test("copy the views compose reads as the page writes it", () => {
  expect(barShare(1000, 70000)).toBe("1.43%");
  expect(barShare(70000, 70000)).toBe("100%");
  expect(conceptMeta({ place: "Gujarat", family: "Textiles", sentences: 1 })).toBe("Gujarat · Textiles · named in 1 cited sentence");
  expect(conceptMeta({ place: "Bihar", family: "Painting, instruments and more", sentences: 14 })).toBe("Bihar · Painting, instruments and more · named in 14 cited sentences");
  expect(supportsLine(2)).toBe("Supports 2 sentences here");
  expect(axisEventName({ view: "world", routes: [], pins: [], when: "1868", title: "Alizarin made in a laboratory" })).toBe("1868, Alizarin made in a laboratory");
  expect(pickName({ view: "kutch", routes: [], pins: [], when: "2001", title: "Earthquake, and a new village" })).toBe("Show Earthquake, and a new village on the map");
});

test("specs breaking their shapes are refused", () => {
  const chart = specOf("kutch-ajrakh/society/khavda-khatris-2011-dots");
  expect(parseShape(chartShape, chart).dots?.marked).toBe(15);
  expect(() => parseShape(chartShape, { ...chart, form: "pie" })).toThrow(ShapeError);
  const sequence = specOf(SEQUENCE);
  expect(() => parseShape(mapSequenceShape, { ...sequence, first: [{ card: null, component: "Not A Label" }] })).toThrow(ShapeError);
  const listing = specOf("kutch-ajrakh/overview/kin-craft-sources");
  expect(() => parseShape(sourceListShape, { ...listing, setting: "table" })).toThrow(ShapeError);
  const timeline = specOf("kutch-ajrakh/history/dated-record-timeline-map");
  expect(() => parseShape(timelineMapShape, { ...timeline, views: { World: [0, 0, 1, 1] } })).toThrow(ShapeError);
});
