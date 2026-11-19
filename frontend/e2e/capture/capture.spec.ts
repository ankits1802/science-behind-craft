import { mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { pathToFileURL } from "node:url";

import { test, type Page } from "@playwright/test";

const REPORT_DIR = process.env.E2E_REPORT_DIR ?? "capture-run";
const DEFAULT_PATHS = ["/", "/crafts", "/crafts/Kutch-Ajrakh", "/crafts/Bastar-Dhokra", "/crafts/Kasuti-Embroidery", "/categories/Textile-Craft-Category", "/map", "/login"];
const BOARD = pathToFileURL(join(__dirname, "..", "..", "..", "docs", "design", "master-board.html")).href;
const BOARD_SCREENS = ["landing", "atlas", "craft", "answer", "uncurated", "urdu"];
const MAX_HEIGHT_PX = 6000;
const SETTLE_MS = 1200;

function screenPaths(): string[] {
  const asked = (process.env.E2E_SCREEN_PATHS ?? "").split(",").map((path) => path.trim()).filter(Boolean);
  return asked.length ? asked : DEFAULT_PATHS;
}

function fileName(path: string): string {
  return (path === "/" ? "landing" : path.replace(/^\/+/, "").replace(/[^A-Za-z0-9-]+/g, "_")) + ".png";
}

function save(name: string, image: Buffer): void {
  const folder = join(REPORT_DIR, test.info().project.name);
  mkdirSync(folder, { recursive: true });
  writeFileSync(join(folder, name), image);
}

async function settled(page: Page): Promise<void> {
  await page.evaluate(async () => {
    for (let y = 0; y < Math.min(document.body.scrollHeight, 6000); y += window.innerHeight) {
      window.scrollTo(0, y);
      await new Promise((resolve) => setTimeout(resolve, 40));
    }
    window.scrollTo(0, 0);
  });
  await page.waitForTimeout(SETTLE_MS);
}

async function capture(page: Page, top: number, height: number): Promise<Buffer> {
  const width = page.viewportSize()?.width ?? 0;
  return page.screenshot({ fullPage: true, animations: "disabled", clip: { x: 0, y: top, width, height: Math.min(height, MAX_HEIGHT_PX) } });
}

for (const path of screenPaths()) {
  test(`the page ${path} as a reader sees it`, async ({ page }) => {
    await page.goto(path, { waitUntil: "networkidle" });
    await settled(page);
    const height = await page.evaluate(() => document.documentElement.scrollHeight);
    save(fileName(path), await capture(page, 0, height));
  });
}

test("the master board's screens at this width and theme", async ({ page }, info) => {
  const dark = info.project.name.endsWith("-dark");
  await page.addInitScript((theme) => localStorage.setItem("kv-theme", theme), dark ? "dark" : "light");
  await page.goto(BOARD, { waitUntil: "load" });
  await settled(page);
  for (const id of BOARD_SCREENS) {
    const box = await page.locator(`section.screen#${id}`).boundingBox();
    if (!box) continue;
    const top = box.y + (await page.evaluate(() => window.scrollY));
    save(`board-${id}.png`, await capture(page, top, box.height));
  }
});
