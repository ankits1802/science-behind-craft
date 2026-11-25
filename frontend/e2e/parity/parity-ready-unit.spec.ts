import { expect, test } from "@playwright/test";

import { REST_UNREAD } from "../../components/monograph/DeferredShellSlot";

import { pageReadiness, readinessProblem, UNREAD_PROBLEM, WAITING_PROBLEM } from "./parityReady";

const SHORT_MS = 400;
const KIT = "<script>window.KV = {};</script>";
const HOLDER = '<div data-kv-deferred="" aria-busy="true" style="min-height:300vh"></div>';

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
