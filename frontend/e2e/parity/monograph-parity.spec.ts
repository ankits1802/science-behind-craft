import { mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";

import { expect, test, type BrowserContext, type Page } from "@playwright/test";

import { chapterIds, lineDiff, pixelDifference, type PixelDifference } from "./parityMeasure";

const APPROVED = "/monographs/kutch-ajrakh/index.html";
const RENDERED = "/crafts/Kutch-Ajrakh/monograph";
const REPORT_DIR = process.env.E2E_REPORT_DIR ?? "parity-run";
const SETTLE_MS = 1500;
const PIXEL_TOLERANCE = 0.02;

async function opened(page: Page, path: string): Promise<void> {
  await page.goto(path, { waitUntil: "networkidle" });
  await page.evaluate(async () => {
    for (let y = 0; y < document.body.scrollHeight; y += window.innerHeight) {
      window.scrollTo(0, y);
      await new Promise((resolve) => setTimeout(resolve, 30));
    }
    window.scrollTo(0, 0);
  });
  await page.waitForTimeout(SETTLE_MS);
}

async function mainText(page: Page): Promise<string[]> {
  const text = await page.evaluate(() => (document.querySelector("main") ?? document.body).innerText);
  return text.split("\n").map((line) => line.replace(/\s+/g, " ").trim()).filter(Boolean);
}

function report(name: string, body: unknown): void {
  const folder = join(REPORT_DIR, test.info().project.name);
  mkdirSync(folder, { recursive: true });
  writeFileSync(join(folder, name), Buffer.isBuffer(body) ? body : JSON.stringify(body, null, 1));
}

async function bothPages(context: BrowserContext): Promise<{ approved: Page; rendered: Page }> {
  const approved = await context.newPage();
  const rendered = await context.newPage();
  await opened(approved, APPROVED);
  await opened(rendered, RENDERED);
  return { approved, rendered };
}

test("the React page reads exactly as the approved page", async ({ context }) => {
  const { approved, rendered } = await bothPages(context);
  const diff = lineDiff(await mainText(approved), await mainText(rendered));
  report("text.json", diff);
  expect(diff.onlyApproved.length + diff.onlyRendered.length, "lines that differ (see text.json)").toBe(0);
});

test("every chapter of the React page looks as the approved page does", async ({ context }) => {
  const { approved, rendered } = await bothPages(context);
  const ids = chapterIds(await approved.evaluate(() => [...document.querySelectorAll("main [id]")].map((element) => element.id)));
  const differences: Record<string, PixelDifference | "missing"> = {};
  for (const id of ids) {
    const selector = `[id="${id}"]`;
    if (!(await rendered.locator(selector).count())) {
      differences[id] = "missing";
      continue;
    }
    const before = await approved.locator(selector).first().screenshot({ animations: "disabled" });
    const after = await rendered.locator(selector).first().screenshot({ animations: "disabled" });
    const found = await pixelDifference(before, after);
    differences[id] = found;
    if (found.ratio > PIXEL_TOLERANCE) {
      report(`${id}.approved.png`, before);
      report(`${id}.rendered.png`, after);
    }
  }
  report("pixels.json", differences);
  const failing = Object.entries(differences).filter(([, found]) => found === "missing" || found.ratio > PIXEL_TOLERANCE);
  expect(failing.map(([id]) => id), "chapters that differ (see pixels.json)").toEqual([]);
});

test("a citation and the first figure answer as on the approved page", async ({ context }) => {
  const pages = { approved: await context.newPage(), rendered: await context.newPage() };
  const answers: Record<string, Record<string, string | null>> = {};
  for (const [name, page] of Object.entries(pages)) {
    await opened(page, name === "approved" ? APPROVED : RENDERED);
    const cite = page.locator("main .kcite").first();
    await cite.scrollIntoViewIfNeeded();
    await cite.click();
    const popover = page.locator("[role='dialog']:visible").first();
    const quote = (await popover.count()) ? await popover.innerText() : null;
    await page.keyboard.press("Escape");
    const dip = page.locator("#fig1 button").first();
    const before = await page.locator("#fig1").getAttribute("data-dips");
    if (await dip.count()) await dip.click();
    const after = await page.locator("#fig1").getAttribute("data-dips");
    answers[name] = { quote: quote?.replace(/\s+/g, " ").trim() ?? null, dipsBefore: before, dipsAfter: after };
  }
  report("interactions.json", answers);
  expect(answers.rendered).toEqual(answers.approved);
});
