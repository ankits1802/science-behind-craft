import { readFileSync } from "node:fs";
import { join } from "node:path";

import { expect, test, type Page } from "@playwright/test";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";

import { ChemEquation } from "@/components/answer/ChemEquation";
import { RenderedChemistryProvider } from "@/components/answer/RenderedChemistry";
import { renderChemistry } from "@/lib/chemistry";
import { chemistryAsks } from "@/lib/chemistryKeys";
import { isPlaying, played, restingPlay, type PlayAction } from "@/lib/playInView";
import { FRAME_IN_VIEW, FRAME_VIEW, FRAME_VIEW_EVENT, sandboxDocument } from "@/lib/sandboxFrame";
import { renderedChemistry } from "@/lib/server/renderedChemistry";

import { FRONTEND } from "./moduleGraph";

const KATEX_CSS = readFileSync(join(FRONTEND, "node_modules", "katex", "dist", "katex.min.css"), "utf8");
const FIGURE_CSS = readFileSync(join(FRONTEND, "app", "editorial-figure.css"), "utf8");
const UTILITIES = ".block{display:block}.inline{display:inline}.flow-root{display:flow-root}.inline-block{display:inline-block}.align-middle{vertical-align:middle}.max-w-full{max-width:100%}";
const PROMPT = readFileSync(join(FRONTEND, "..", "backend", "app", "composer", "simulation.py"), "utf8");
const LONG = "2 C16H10N2O2 + 4 NaOH + Na2S2O4 -> 2 C16H10N2O2Na2 + 2 Na2SO3 + 2 H2O";
const FORMULA = "C16H10N2O2";
const PHONE = 320;
const LANE = 288;
const FRAME_HTML = '<p id="seen">Watching</p><script>document.addEventListener("kv-view", function () { document.getElementById("seen").textContent = document.documentElement.dataset.inView; });</script>';

function chemistry(withRules: boolean): string {
  const rendered = renderedChemistry(chemistryAsks({ equation: LONG, formula: FORMULA }));
  const drawn = renderToStaticMarkup(
    createElement(RenderedChemistryProvider, { rendered }, createElement("div", null, createElement(ChemEquation, { equation: LONG }), createElement("p", null, createElement(ChemEquation, { equation: FORMULA, display: false }))))
  );
  const rules = withRules ? FIGURE_CSS : "";
  return `<style>${KATEX_CSS}</style><style>${UTILITIES}</style><style>${rules}</style><main style="margin:0 16px;font-size:19px"><div id="lane" style="width:${LANE}px">${drawn}</div></main>`;
}

async function lane(page: Page): Promise<{ scrolls: string[]; past: number; lines: number }> {
  return page.evaluate(() => {
    const box = document.getElementById("lane")!;
    const scrolls = [...box.querySelectorAll("*")].filter((node) => ["auto", "scroll"].includes(getComputedStyle(node).overflowX) || ["auto", "scroll"].includes(getComputedStyle(node).overflowY)).map((node) => node.className);
    const right = Math.max(...[...box.querySelectorAll(".katex")].map((node) => node.getBoundingClientRect().right));
    const terms = [...box.querySelectorAll('[data-testid="chem-terms"] .kv-chem-term')].map((node) => Math.round(node.getBoundingClientRect().top));
    return { scrolls, past: right - box.getBoundingClientRect().right, lines: new Set(terms).size };
  });
}

test("an answer's equation is set term by term and wraps inside its lane from 320px, with no scroll bar", async ({ page }) => {
  await page.setViewportSize({ width: PHONE, height: 700 });
  await page.setContent(chemistry(true));
  const shown = await lane(page);
  expect(shown.scrolls).toEqual([]);
  expect(shown.past).toBeLessThanOrEqual(1);
  expect(shown.lines).toBeGreaterThan(1);
  expect(await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth)).toBeLessThanOrEqual(0);
});

test("set whole in a scrolling box, as before, the same equation runs past its lane and its box scrolls", async ({ page }) => {
  await page.setViewportSize({ width: PHONE, height: 700 });
  const whole = renderChemistry(LONG, true);
  await page.setContent(`<style>${KATEX_CSS}</style><main style="margin:0 16px;font-size:19px"><div style="width:${LANE}px"><span id="old" style="display:block;overflow-x:auto">${whole}</span></div></main>`);
  expect(await page.evaluate(() => document.getElementById("old")!.scrollWidth - document.getElementById("old")!.clientWidth)).toBeGreaterThan(1);
});

test("the sandboxed frame tells its explainer when the reader can see it, and the explainer is asked to play only then", async ({ page }) => {
  await page.setViewportSize({ width: 800, height: 600 });
  const framed = sandboxDocument(FRAME_HTML, [], { tokens: {}, reducedMotion: false });
  await page.setContent(`<div style="height:1600px"></div><iframe id="frame" sandbox="allow-scripts" style="width:600px;height:200px;border:0" srcdoc="${framed.replace(/&/g, "&amp;").replace(/"/g, "&quot;")}"></iframe><div style="height:1600px"></div>`);
  const frame = page.frameLocator("#frame");
  await expect(frame.locator("html")).toHaveAttribute(FRAME_IN_VIEW, "false");
  await page.locator("#frame").scrollIntoViewIfNeeded();
  await expect(frame.locator("html")).toHaveAttribute(FRAME_IN_VIEW, "true");
  await expect(frame.locator("#seen")).toHaveText("true");
  await page.evaluate(() => window.scrollTo(0, 0));
  await expect(frame.locator("html")).toHaveAttribute(FRAME_IN_VIEW, "false");
  await expect(frame.locator("#seen")).toHaveText("false");
  expect(FRAME_VIEW).toContain(JSON.stringify(FRAME_VIEW_EVENT));
  expect(FRAME_IN_VIEW).toBe("data-in-view");
  expect(PROMPT).toContain("document.documentElement.dataset.inView");
  expect(PROMPT).toContain(`fires a ${FRAME_VIEW_EVENT} event on document`);
  expect(PROMPT).toContain("reads Pause while it plays");
});

test("a player plays only in view with motion allowed, loops, and a pressed step plays on from where it was pressed", () => {
  const run = (actions: PlayAction[]) => actions.reduce(played, restingPlay(0));
  const seen: PlayAction = { type: "seen", on: true, motion: true };
  expect(isPlaying(run([seen]), 4)).toBe(true);
  expect(isPlaying(run([{ type: "seen", on: true, motion: false }]), 4)).toBe(false);
  expect(isPlaying(run([seen, { type: "seen", on: false, motion: true }]), 4)).toBe(false);
  const looped = run([seen, { type: "start" }, ...Array.from({ length: 4 }, () => ({ type: "tick", count: 4 }) as PlayAction)]);
  expect(looped.at).toBe(0);
  const pressed = run([seen, { type: "start" }, { type: "choose", at: 2 }, { type: "tick", count: 4 }]);
  expect([pressed.at, isPlaying(pressed, 4)]).toEqual([3, true]);
  const paused = played(run([seen, { type: "start" }]), { type: "toggle", motion: true, count: 4 });
  expect(isPlaying(played(paused, { type: "choose", at: 1 }), 4)).toBe(false);
});
