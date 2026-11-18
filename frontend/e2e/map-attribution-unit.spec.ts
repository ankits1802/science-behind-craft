import { expect, test } from "@playwright/test";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";

import { BOUNDARY_ATTRIBUTION, DISTRICTS_INDICATIVE, MAP_CREDITS_LABEL, MapAttribution, OSM_COPYRIGHT_URL, OSM_CREDIT, SURVEY_OF_INDIA_CAPTION } from "@/components/map/MapAttribution";
import { BOUNDARY_DATASET_CODE, type BoundaryNote } from "@/lib/regionContract";

const CAPTION = "External boundaries of India as depicted by Survey of India. District boundaries are indicative.";
const PUBLISHER = "Indian districts GeoJSON on Kaggle";

const BOUNDARY: BoundaryNote = {
  caption: CAPTION,
  dataset: {
    code: BOUNDARY_DATASET_CODE,
    title: "Indian district boundaries, matched to LGD codes",
    publisher: PUBLISHER,
    edition: "2026",
    period: "2026",
    nativeResolution: "simplified to 0.01 degree, 0.001 degree coordinate grid",
    licence: "For reference only",
    licenceUrl: null,
    attribution: "District boundaries are indicative.",
    citation: null,
    url: "https://www.kaggle.com/datasets/adityaradha007/indian-districts-geojson"
  }
};

function inViewAndBehindCredits(html: string): [string, string] {
  const opened = html.indexOf('<details class="w-fit max-w-full" data-testid="map-credits">');
  expect(opened).toBeGreaterThan(-1);
  const closed = html.indexOf("</details>", opened);
  return [html.slice(0, opened) + html.slice(closed), html.slice(opened, closed)];
}

test("the Survey of India caption and the OpenStreetMap credit stay in view and the rest sits behind map credits", () => {
  const [inView, behind] = inViewAndBehindCredits(renderToStaticMarkup(createElement(MapAttribution, { boundary: BOUNDARY })));
  expect(inView).toContain(CAPTION);
  expect(inView).toContain(`href="${OSM_COPYRIGHT_URL}"`);
  expect(inView).toContain(OSM_CREDIT);
  expect(inView).not.toContain(BOUNDARY_ATTRIBUTION);
  expect(inView).not.toContain(BOUNDARY.dataset.title);
  expect(behind).toContain(`<summary`);
  expect(behind).toContain(MAP_CREDITS_LABEL);
  expect(behind).toContain(BOUNDARY_ATTRIBUTION);
  expect(behind).toContain(`>${BOUNDARY.dataset.title}</a>`);
  expect(behind).toContain(PUBLISHER);
});

test("without a stored boundary the plan caption and the OpenStreetMap credit still show", () => {
  const [inView, behind] = inViewAndBehindCredits(renderToStaticMarkup(createElement(MapAttribution, { districtsIndicative: false })));
  expect(inView).toContain(SURVEY_OF_INDIA_CAPTION);
  expect(inView).not.toContain(DISTRICTS_INDICATIVE);
  expect(inView).toContain(OSM_CREDIT);
  expect(behind).toContain(BOUNDARY_ATTRIBUTION);
});
