import { expect, test, type Page } from "@playwright/test";

import { drawingLimits, drawingReview, type DrawingPlan } from "./drawingChecks";
import { sanityProblems } from "./parityComponent";

const PHONE = { width: 390, height: 844 };
const SWATCH = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='4' height='3'%3E%3Crect width='4' height='3' fill='%23888'/%3E%3C/svg%3E";
const BASE = "<style>body{margin:0;font:16px/1.4 sans-serif}@keyframes turn{to{transform:rotate(1turn)}}</style>";
const MASTHEAD = `<div data-component="test/masthead"><img src="${SWATCH}" alt="A swatch" style="display:block;width:390px;height:200px"></div>`;

async function opened(page: Page, body: string): Promise<void> {
  await page.setViewportSize(PHONE);
  await page.setContent(`${BASE}${body}`);
}

async function sanityOf(page: Page, label: string) {
  const root = await page.$(`[data-component="${label}"]`);
  if (!root) throw new Error(`${label} is not on the fixture page`);
  return sanityProblems(page, label, root);
}

async function problemsOf(page: Page, label: string): Promise<string[]> {
  return (await sanityOf(page, label)).map((found) => found.problem);
}

test("the release's drawing checks read their limits from the one shared copy", async ({ page }) => {
  await page.setContent("<p>limits</p>");
  expect(await drawingLimits(page)).toEqual({ iconView: 32, iconLeast: 8, iconWidth: 64, figureText: 96, svgText: 48 });
});

test("parity names an oversized icon, oversized text, a tall SVG label and a component of no size as before", async ({ page }) => {
  await opened(
    page,
    [
      '<div data-component="test/icon"><svg viewBox="0 0 24 24" style="display:block;width:239px;height:239px"><path d="M0 0h24v24H0z"></path></svg></div>',
      '<div data-component="test/text"><p style="margin:0;font-size:120px;line-height:1">Big</p></div>',
      '<div data-component="test/label"><svg viewBox="0 0 400 300" style="display:block;width:400px;height:300px"><text x="0" y="200" font-size="150">A</text></svg></div>',
      '<div data-component="test/none" style="width:0;height:0"></div>'
    ].join("")
  );
  expect(await problemsOf(page, "test/icon")).toEqual(["an icon of 24 units draws 239px wide"]);
  expect(await problemsOf(page, "test/text")).toEqual(["p text draws at 120px"]);
  const label = await problemsOf(page, "test/label");
  expect(label).toContain("text text draws at 150px");
  expect(label.some((problem) => /^an SVG label draws \d+px tall$/.test(problem))).toBe(true);
  expect(await problemsOf(page, "test/none")).toEqual(["draws 0 by 0"]);
  expect(await sanityOf(page, "test/icon")).toEqual([{ label: "about:blank test/icon", problem: "an icon of 24 units draws 239px wide" }]);
});

const BROKEN: DrawingPlan = {
  masthead: "test/masthead",
  chapters: [],
  components: [
    { label: "test/masthead", role: "picture", placed: true },
    { label: "test/icon", role: "figure", placed: true },
    { label: "test/empty", role: "figure", placed: true },
    { label: "test/wide", role: "figure", placed: true },
    { label: "test/bare-chart", role: "chart", placed: true },
    { label: "test/loading", role: "interactive", placed: true },
    { label: "test/spinning", role: "interactive", placed: true },
    { label: "test/flat-bars", role: "chart", placed: true },
    { label: "test/tiles", role: "figure", placed: true },
    { label: "test/gone", role: "interactive", placed: true },
    { label: "test/unplaced", role: "map", placed: false }
  ]
};

test("the preview's review fails each drawing a reader would see broken, naming the component and the problem", async ({ page }) => {
  await opened(
    page,
    [
      '<h1 style="margin:0;height:50px">Test craft</h1>',
      '<h2 style="margin:0;height:30px">Test craft</h2>',
      '<div style="height:900px"></div>',
      MASTHEAD,
      '<div data-component="test/icon"><p>Label</p><svg viewBox="0 0 24 24" style="display:block;width:239px;height:239px"><path d="M0 0h24v24H0z"></path></svg></div>',
      '<div data-component="test/empty" style="height:40px"></div>',
      '<div data-component="test/wide" style="width:300px"><p>Rows</p><table style="width:700px;border-collapse:collapse"><tbody><tr><td>a</td></tr></tbody></table></div>',
      '<div data-component="test/bare-chart"><p>Title only</p></div>',
      '<div data-component="test/loading" aria-busy="true"><button type="button">Play</button></div>',
      '<div data-component="test/spinning"><span style="display:inline-block;animation:turn 1s linear infinite">x</span></div>',
      '<div data-component="test/flat-bars"><p>Shares</p><span style="display:block;width:0;height:8px;background:#333"></span></div>',
      '<div style="position:relative"><div data-component="test/tiles" style="height:20px"><div style="position:absolute;inset:0 0 auto 0;height:200px"><p>315</p></div></div></div>'
    ].join("")
  );
  const review = await drawingReview(page, BROKEN);
  expect(review.problems).toEqual([
    { label: "page", problem: "the first 844px draw its name again in 1 more heading" },
    { label: "test/masthead", problem: "the masthead picture starts 980px down, below the first 844px" },
    { label: "page", problem: "is 310px wider than the 390px screen, so it scrolls sideways" },
    { label: "test/icon", problem: "an icon of 24 units draws 239px wide" },
    { label: "test/empty", problem: "draws empty" },
    { label: "test/wide", problem: "a table runs 400px past its column" },
    { label: "test/bare-chart", problem: "draws no marks" },
    { label: "test/loading", problem: "is still loading at rest" },
    { label: "test/spinning", problem: "still moves at rest (1 animations running)" },
    { label: "test/flat-bars", problem: "draws no marks: its 1 bars draw 0px wide" },
    { label: "test/tiles", problem: "a div is drawn against the page outside its slot, so the slot does not hold its height" },
    { label: "test/gone", problem: "is placed in the layout but the page does not draw it" }
  ]);
});

const WHOLE: DrawingPlan = {
  masthead: "test/masthead",
  chapters: ["made", "not-on-the-page"],
  components: [
    { label: "test/masthead", role: "picture", placed: true },
    { label: "test/chart", role: "chart", placed: true },
    { label: "test/bars", role: "chart", placed: true },
    { label: "test/map", role: "map", placed: true },
    { label: "test/player", role: "interactive", placed: true },
    { label: "test/table", role: "figure", placed: true },
    { label: "test/overlay", role: "figure", placed: true }
  ]
};

test("a page drawn whole passes the review, a scrolled table included, and its chapters are measured", async ({ page }) => {
  await opened(
    page,
    [
      '<h1 style="margin:0">Test craft</h1>',
      MASTHEAD,
      '<section id="made"><h2>How it is made</h2>',
      '<div data-component="test/chart"><p>Bars</p><svg viewBox="0 0 100 50" style="display:block;width:300px;height:150px"><rect x="0" y="10" width="80" height="10"></rect></svg></div>',
      '<div data-component="test/bars"><p>Shares</p><div style="width:120px;height:8px;background:#333"></div></div>',
      '<div data-component="test/map"><svg viewBox="0 0 100 100" style="display:block;width:200px;height:200px"><path d="M10 10L90 90" stroke="#000"></path></svg></div>',
      '<div data-component="test/player"><p>Step 1: the cloth goes in.</p><button type="button">Next</button></div>',
      '<div data-component="test/table"><div style="overflow-x:auto"><table style="width:700px"><tbody><tr><td>wide</td></tr></tbody></table></div></div>',
      '<div data-component="test/overlay"><div style="position:relative;height:60px"><span style="position:absolute;inset:0">A label on its own figure</span></div></div>',
      "</section>"
    ].join("")
  );
  const review = await drawingReview(page, WHOLE);
  expect(review.problems).toEqual([]);
  expect(review.chapters.map((chapter) => chapter.key)).toEqual(["made"]);
  expect(review.chapters[0].height).toBeGreaterThan(0);
});
