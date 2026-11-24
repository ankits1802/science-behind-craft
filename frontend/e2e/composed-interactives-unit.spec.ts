import { readFileSync } from "node:fs";
import { join } from "node:path";

import { expect, test, type Page } from "@playwright/test";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";

import { AuthProvider } from "../components/AuthProvider";
import { MonographPage } from "../components/monograph/MonographPage";
import { ThemeProvider } from "../components/ThemeProvider";
import { parseShape } from "../lib/shape";
import { SPEC_SHAPES_SCIENCE, type ScienceKind } from "../lib/componentSpecsScience";

import { composedDocument, DYE, LAB, MOLECULE, MORDANT, PLAYER, DIP, REST_YAW_DEGREES } from "./composedInteractivesFixture";
import { FRONTEND } from "./moduleGraph";
import { PRIMITIVE_CSS } from "./primitivesPage";

const KIT_CSS = readFileSync(join(FRONTEND, "public", "monographs", "kit", "monograph.css"), "utf8");
const PAGE_CSS = readFileSync(join(FRONTEND, "components", "monograph", "documentPage.css"), "utf8");
const KIT_JS = readFileSync(join(FRONTEND, "public", "monographs", "kit", "monograph.js"), "utf8");
const WIDTHS = [360, 1440] as const;
const SWITCHES = ["system", "page"] as const;
const SSR_OXYGEN_CY = "0.27";
type Switch = (typeof SWITCHES)[number];

const pageHtml = () => renderToStaticMarkup(createElement(AuthProvider, null, createElement(ThemeProvider, null, createElement(MonographPage, { document: composedDocument() }))));

async function drawn(page: Page, width: number, motion: Switch): Promise<void> {
  await page.setViewportSize({ width, height: 900 });
  await page.emulateMedia({ reducedMotion: motion === "system" ? "reduce" : "no-preference" });
  const switched = motion === "page" ? ' data-reduced-motion="true"' : "";
  const head = `<meta charset="utf-8"><style>${PRIMITIVE_CSS}</style><style>${KIT_CSS}</style><style>${PAGE_CSS}</style>`;
  await page.setContent(`<!doctype html><html lang="en" data-theme="light"${switched}><head>${head}</head><body>${pageHtml()}</body></html>`, { waitUntil: "domcontentloaded" });
}

async function kitBound(page: Page): Promise<void> {
  await page.addScriptTag({ content: KIT_JS });
  for (const scope of ["chem", "pt"]) await expect(page.locator(`#${scope}-theme-toggle[aria-pressed]`)).toBeAttached();
  await page.locator(".mol[data-cid]").scrollIntoViewIfNeeded();
  await expect.poll(() => page.locator('.mol-dial [data-a="0"] circle').getAttribute("cy")).not.toBe(SSR_OXYGEN_CY);
  await expect(page.locator(".mol-dial")).toHaveAttribute("aria-valuetext", `Turned ${REST_YAW_DEGREES} degrees`);
  await expect(page.locator("figure.rp .rp-status")).toContainText("Step 2 of 2");
}

test("every composed spec parses as the view the site draws it with", () => {
  const document = composedDocument();
  for (const label of [PLAYER, DIP, MOLECULE, MORDANT, DYE, LAB]) {
    const kind = document.content.components.find((found) => found.label === label)?.kind as ScienceKind;
    expect(() => parseShape(SPEC_SHAPES_SCIENCE[kind], document.specs[label]), label).not.toThrow();
  }
});

test("on a generated page each interactive is whole at rest at phone and desktop width, with no sideways scroll", async ({ page }) => {
  for (const width of WIDTHS) {
    await drawn(page, width, "system");
    const run = `${width}`;
    expect(await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth), run).toBeLessThanOrEqual(0);
    await expect(page.locator("figure.rp"), run).toHaveAttribute("data-step", "2");
    await expect(page.locator("figure.rp .rp-step").nth(1), run).toBeVisible();
    await expect(page.locator("figure.rp .rp-step").first(), run).toBeHidden();
    await expect(page.locator("figure.vat .vs").last(), run).toHaveAttribute("aria-current", "step");
    expect(await page.locator(".mol .mol-dial svg g.mol-g > [data-a]").count(), run).toBe(3);
    await expect(page.locator('[data-comp="lab"] [data-exp="m01"]'), run).toBeVisible();
    await expect(page.locator('[data-comp="lab"] [data-exp="m03"]'), run).toBeHidden();
    await expect(page.locator('[data-comp="lab"] [data-res="m01"]'), run).toBeVisible();
  }
});

test("a reaction steps by rail, arrow keys and Play as on Kutch Ajrakh's page", async ({ page }) => {
  for (const width of WIDTHS) {
    await drawn(page, width, "system");
    await kitBound(page);
    const player = page.locator("figure.rp");
    const rail = player.locator(".rp-rail button");
    await rail.first().click();
    await expect(player).toHaveAttribute("data-step", "1");
    await expect(rail.first()).toHaveAttribute("aria-pressed", "true");
    await expect(player.locator(".rp-status")).toContainText("Step 1 of 2");
    await expect(player.locator('svg.scene [data-on="1"]')).not.toHaveClass(/off/);
    await expect(player.locator('svg.scene [data-on="2"]')).toHaveClass(/off/);
    await rail.first().press("End");
    await expect(player).toHaveAttribute("data-step", "2");
    await expect(rail.nth(1)).toBeFocused();
    await player.locator(".rp-play").click();
    await expect(player.locator(".rp-play")).toHaveAttribute("aria-pressed", "true");
    await expect(player).toHaveAttribute("data-step", "1");
  }
});

test("a molecule turns and zooms by keyboard, its model read from the page's own data", async ({ page }) => {
  for (const width of WIDTHS) {
    await drawn(page, width, "system");
    await kitBound(page);
    const dial = page.locator(".mol-dial");
    const oxygen = dial.locator('[data-a="0"] circle');
    const hydrogen = dial.locator('[data-a="1"] circle');
    const before = await hydrogen.getAttribute("cx");
    await dial.focus();
    await dial.press("ArrowRight");
    await expect(dial).toHaveAttribute("aria-valuenow", "38");
    await expect.poll(() => hydrogen.getAttribute("cx")).not.toBe(before);
    const radius = Number(await oxygen.getAttribute("r"));
    await dial.press("+");
    await expect(dial).toHaveAttribute("aria-valuetext", "Turned 38 degrees, shown at 125 per cent");
    expect(Number(await oxygen.getAttribute("r"))).toBeGreaterThan(radius);
    await dial.press("-");
    await expect(dial).toHaveAttribute("aria-valuetext", "Turned 38 degrees");
    await page.locator(".mol-turn").click();
    await expect(dial).toHaveAttribute("aria-valuenow", "128");
  }
});

test("under either reduced-motion switch each press of Dip again shows the next phase at once and says it", async ({ page }) => {
  for (const motion of SWITCHES) {
    await drawn(page, 360, motion);
    await kitBound(page);
    const dip = page.locator("figure.vat");
    const strip = dip.locator(".vs");
    await dip.locator(".vat-dip").click();
    await expect(dip).toHaveAttribute("data-dips", "1");
    await expect(strip.first()).toHaveAttribute("aria-current", "step");
    await expect(dip.locator(".vat-status")).toHaveText("Dip 1 of 2. Harda: Yellow");
    await expect(dip.locator(".dips li").first()).toHaveClass(/on/);
    await expect(dip.locator(".vat-scene svg rect").nth(1)).toHaveAttribute("fill", "var(--dye-harda)");
    await dip.locator(".vat-dip").click();
    await expect(strip.last()).toHaveAttribute("aria-current", "step");
    await expect(dip.locator(".vat-status")).toHaveText("Dip 1 of 2. Madder bath: Red where alum was printed");
    await expect(dip.locator(".vat-scene svg rect").nth(1)).toHaveAttribute("fill", "var(--dye-madder)");
  }
});

test("with motion allowed Dip again plays every phase in order and rests on the last", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.emulateMedia({ reducedMotion: "no-preference" });
  await page.setContent(`<!doctype html><html lang="en" data-theme="light"><head><style>${KIT_CSS}</style></head><body>${pageHtml()}</body></html>`);
  await kitBound(page);
  const dip = page.locator("figure.vat");
  await dip.locator(".vat-dip").click();
  await expect(dip).toHaveAttribute("data-dips", "1");
  await expect(dip.locator(".vs").last()).toHaveAttribute("aria-current", "step", { timeout: 5000 });
  await expect(dip.locator(".vat-status")).toHaveText("Dip 1 of 2. Madder bath: Red where alum was printed");
});

test("the what-if lab opens an experiment and shows the result of the option chosen", async ({ page }) => {
  for (const width of WIDTHS) {
    await drawn(page, width, "system");
    await kitBound(page);
    const lab = page.locator('[data-comp="lab"]');
    await lab.locator('[data-x="m03"]').click();
    await expect(lab.locator('[data-x="m03"]')).toHaveAttribute("aria-pressed", "true");
    await expect(lab.locator('[data-exp="m03"]')).toBeVisible();
    await expect(lab.locator('[data-exp="m01"]')).toBeHidden();
    const synthetic = lab.locator('[data-choice="m03"] button[data-v="m04"]');
    await synthetic.click();
    await expect(synthetic).toHaveAttribute("aria-pressed", "true");
    await expect(lab.locator('[data-choice="m03"] button[data-v="m03"]')).toHaveAttribute("aria-pressed", "false");
    await expect(lab.locator('[data-res="m04"]')).toBeVisible();
    await expect(lab.locator('[data-res="m03"]')).toBeHidden();
    await expect(lab.locator('[data-res="m01"]')).toBeAttached();
  }
});
