import { expect, test } from "@playwright/test";

import { smokeApiAddress, TEMPLATE_CRAFT } from "./smokeApi";

const PATH = `/crafts/${TEMPLATE_CRAFT}/monograph`;
const CHUNKS = "**/_next/static/chunks/**";
const SMOKE_PROJECT = "desktop";
const REST_TIMEOUT_MS = 30_000;
const SCROLL_PAUSE_MS = 40;

test.beforeAll(() => {
  test.skip(test.info().project.name !== SMOKE_PROJECT || smokeApiAddress() === null, "runs once, against the local build with its API at a local address");
});

test("a Download list that does not arrive leaves the page and its button, says so, and opens when pressed again", async ({ page }) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto(PATH, { waitUntil: "networkidle" });
  await page.evaluate(async (pause) => {
    for (let y = 0; y < document.body.scrollHeight; y += window.innerHeight) {
      window.scrollTo(0, y);
      await new Promise((resolve) => setTimeout(resolve, pause));
    }
  }, SCROLL_PAUSE_MS);
  await page.locator("#kv-src-kin").waitFor({ state: "attached", timeout: REST_TIMEOUT_MS });
  await page.waitForLoadState("networkidle");
  const download = page.getByTestId("page-download");
  await download.scrollIntoViewIfNeeded();
  await page.route(CHUNKS, (route) => route.abort());
  await download.click();
  await expect(page.getByTestId("page-download-failed")).toContainText("did not load");
  await expect(page.locator("header.kv-open h1.kv-q")).toBeVisible();
  await expect(download).toBeVisible();
  await expect(download).toHaveAttribute("aria-expanded", "false");
  await page.unroute(CHUNKS);
  await download.click();
  await expect(page.getByTestId("page-download-items")).toBeVisible();
  await expect(page.getByTestId("download-item")).toHaveText(["PDF", "Word document"]);
  await expect(page.getByTestId("page-download-failed")).toHaveCount(0);
  expect(errors).toEqual([]);
});
