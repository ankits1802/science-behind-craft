import { expect, test, type FrameLocator, type Page } from "@playwright/test";

import { explainerPieces, FRAME_IN_VIEW, FRAME_PLAY, NO_PIECES, sandboxDocument, speaksInView, type FrameLook, type FramePieces } from "@/lib/sandboxFrame";

const MOVING: FrameLook = { tokens: {}, reducedMotion: false };
const STILL: FrameLook = { tokens: {}, reducedMotion: true };
const SETTLE_MS = 400;

const TOGGLE = [
  '<button type="button" id="go">Play</button><button type="button" id="step">Step</button><p id="state">resting</p>',
  "<script>",
  'const go = document.getElementById("go");',
  'const state = document.getElementById("state");',
  'go.addEventListener("click", function () { const on = go.textContent === "Play"; go.textContent = on ? "Pause" : "Play"; state.textContent = on ? "playing" : "resting"; });',
  'document.getElementById("step").addEventListener("click", function () { state.textContent = "stepped"; });',
  "</script>"
].join("");

const TWO_BUTTONS = [
  '<button type="button" id="play" aria-label="Play the stages">▶</button><button type="button" id="pause" aria-label="Pause the stages">❚❚</button><p id="state">resting</p>',
  "<script>",
  'const state = document.getElementById("state");',
  'document.getElementById("play").addEventListener("click", function () { state.textContent = "playing"; });',
  'document.getElementById("pause").addEventListener("click", function () { state.textContent = "resting"; });',
  "</script>"
].join("");

const NEW_STYLE = '<p id="state">resting</p><script>document.addEventListener("kv-view", function () { document.getElementById("state").textContent = document.documentElement.dataset.inView; });</script>';
const NO_CONTROL = '<p id="state">resting</p><script>window.addEventListener("load", function () { document.getElementById("state").textContent = "loaded"; });</script>';

function escaped(html: string): string {
  return html.replace(/&/g, "&amp;").replace(/"/g, "&quot;");
}

async function framed(page: Page, html: string, look: FrameLook, pieces: FramePieces = explainerPieces(html)): Promise<FrameLocator> {
  await page.setViewportSize({ width: 800, height: 600 });
  const document = sandboxDocument(html, [], look, pieces);
  await page.setContent(`<div style="height:1600px"></div><iframe id="frame" sandbox="allow-scripts" style="width:600px;height:200px;border:0" srcdoc="${escaped(document)}"></iframe><div style="height:1600px"></div>`);
  return page.frameLocator("#frame");
}

async function seen(page: Page, frame: FrameLocator): Promise<void> {
  await page.locator("#frame").scrollIntoViewIfNeeded();
  await expect(frame.locator("html")).toHaveAttribute(FRAME_IN_VIEW, "true");
}

async function unseen(page: Page, frame: FrameLocator): Promise<void> {
  await page.evaluate(() => window.scrollTo(0, 0));
  await expect(frame.locator("html")).toHaveAttribute(FRAME_IN_VIEW, "false");
}

test("an explainer stored before the frame told it what is seen gets the shim, and one that listens does not", () => {
  expect(speaksInView(TOGGLE)).toBe(false);
  expect(speaksInView(NEW_STYLE)).toBe(true);
  expect(explainerPieces(TOGGLE).head).toBe(`<script>${FRAME_PLAY}</script>`);
  expect(explainerPieces(NEW_STYLE)).toBe(NO_PIECES);
  expect(sandboxDocument(TOGGLE, [], MOVING, explainerPieces(TOGGLE))).toContain(`<script>${FRAME_PLAY}</script><style>`);
  expect(sandboxDocument(TOGGLE, [], MOVING)).not.toContain(FRAME_PLAY);
});

test("in view its own Play is pressed, out of view its Pause, and a Step is never touched", async ({ page }) => {
  const frame = await framed(page, TOGGLE, MOVING);
  await expect(frame.locator("#state")).toHaveText("resting");
  await seen(page, frame);
  await expect(frame.locator("#state")).toHaveText("playing");
  await expect(frame.locator("#go")).toHaveText("Pause");
  await unseen(page, frame);
  await expect(frame.locator("#state")).toHaveText("resting");
  await expect(frame.locator("#go")).toHaveText("Play");
  await seen(page, frame);
  await expect(frame.locator("#state")).toHaveText("playing");
});

test("a reader's own Pause holds until they press Play, whatever the scrolling", async ({ page }) => {
  const frame = await framed(page, TOGGLE, MOVING);
  await seen(page, frame);
  await expect(frame.locator("#go")).toHaveText("Pause");
  await frame.locator("#go").click();
  await expect(frame.locator("#state")).toHaveText("resting");
  await unseen(page, frame);
  await seen(page, frame);
  await page.waitForTimeout(SETTLE_MS);
  await expect(frame.locator("#state")).toHaveText("resting");
  await frame.locator("#go").click();
  await expect(frame.locator("#state")).toHaveText("playing");
  await unseen(page, frame);
  await expect(frame.locator("#state")).toHaveText("resting");
});

test("separate Play and Pause buttons are each pressed in turn", async ({ page }) => {
  const frame = await framed(page, TWO_BUTTONS, MOVING);
  await seen(page, frame);
  await expect(frame.locator("#state")).toHaveText("playing");
  await unseen(page, frame);
  await expect(frame.locator("#state")).toHaveText("resting");
});

test("without the shim, or under either reduced-motion switch, the explainer rests until pressed", async ({ page }) => {
  const plain = await framed(page, TOGGLE, MOVING, NO_PIECES);
  await seen(page, plain);
  await page.waitForTimeout(SETTLE_MS);
  await expect(plain.locator("#state")).toHaveText("resting");
  const still = await framed(page, TOGGLE, STILL);
  await seen(page, still);
  await page.waitForTimeout(SETTLE_MS);
  await expect(still.locator("#state")).toHaveText("resting");
  await page.emulateMedia({ reducedMotion: "reduce" });
  const system = await framed(page, TOGGLE, MOVING);
  await seen(page, system);
  await page.waitForTimeout(SETTLE_MS);
  await expect(system.locator("#state")).toHaveText("resting");
});

test("an explainer with no Play control is left as it is", async ({ page }) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.setContent(sandboxDocument(NO_CONTROL, [], MOVING, explainerPieces(NO_CONTROL)));
  await expect(page.locator("#state")).toHaveText("loaded");
  await expect(page.locator("html")).toHaveAttribute(FRAME_IN_VIEW, "true");
  expect(errors).toEqual([]);
});
