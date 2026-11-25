import { expect, test, type Page } from "@playwright/test";

import { REST_UNREAD } from "../../lib/monographRestRead";

import { pageReadiness, readinessProblem, UNREAD_PROBLEM, WAITING_PROBLEM } from "./parityReady";
import { failures, type PassReport } from "./parityRun";

const SHORT_MS = 400;
const KIT = "<script>window.KV = {};</script>";
const HOLDER = '<div data-kv-deferred="" aria-busy="true" style="min-height:300vh"></div>';
const SANGANERI = "https://kalavigyan.vercel.app/crafts/Sanganeri-Hand-Block-Printing";

async function runOf(page: Page): Promise<PassReport> {
  const problem = readinessProblem(await pageReadiness(page, SHORT_MS));
  return { results: [], sanity: problem === null ? [] : [{ label: `${SANGANERI} page`, problem }], chapters: [] };
}

test("a page whose rest is drawn and whose kit is bound is ready", async ({ page }) => {
  await page.setContent(`<main id="kv-main"><section id="chem"><p>Chemistry</p></section></main>${KIT}`);
  expect(await pageReadiness(page, SHORT_MS)).toBe("ready");
});

test("a page whose rest arrives while the spec waits is ready once it is drawn", async ({ page }) => {
  const later = `<script>setTimeout(() => { document.querySelector("[data-kv-deferred]").replaceWith(Object.assign(document.createElement("section"), { id: "chem" })); window.KV = {}; }, 150);</script>`;
  await page.setContent(`<main id="kv-main">${HOLDER}</main>${later}`);
  expect(await pageReadiness(page, 5_000)).toBe("ready");
});

test("a page that says its rest could not be read is unread, not ready", async ({ page }) => {
  await page.setContent(`<main id="kv-main"><p role="status">${REST_UNREAD}</p></main>${KIT}`);
  expect(await pageReadiness(page, SHORT_MS)).toBe("unread");
});

test("a page still holding its rest is still waiting, its kit bound or not", async ({ page }) => {
  await page.setContent(`<main id="kv-main">${HOLDER}</main>${KIT}`);
  expect(await pageReadiness(page, SHORT_MS)).toBe("waiting");
});

test("a page whose rest is drawn but whose kit is not bound is still waiting", async ({ page }) => {
  await page.setContent('<main id="kv-main"><section id="chem"></section></main>');
  expect(await pageReadiness(page, SHORT_MS)).toBe("waiting");
});

test("only a ready page passes, and the others are named in words", () => {
  expect(readinessProblem("ready")).toBeNull();
  expect(readinessProblem("unread")).toBe(UNREAD_PROBLEM);
  expect(readinessProblem("waiting")).toBe(WAITING_PROBLEM);
  expect(WAITING_PROBLEM).toBe("the rest of the page was not drawn and its kit not bound within 60 s");
});

test("a page drawn at a version a removal dropped, its rest drawn from the current one, passes the run", async ({ page }) => {
  const drawn = '<section class="kv-ch" id="intro" data-version="94"></section><section class="kv-ch" id="chem" data-version="95"><p>Chemistry</p></section>';
  await page.setContent(`<main id="kv-main" data-version="94">${drawn}</main>${KIT}`);
  expect(failures(await runOf(page))).toEqual([]);
});

test("a page whose rest route fails for its current version still fails the run, named with that cause", async ({ page }) => {
  await page.setContent(`<main id="kv-main" data-version="95"><section class="kv-ch" id="intro"></section><p role="status">${REST_UNREAD}</p></main>${KIT}`);
  expect(failures(await runOf(page))).toEqual([`${SANGANERI} page: ${UNREAD_PROBLEM}`]);
});
