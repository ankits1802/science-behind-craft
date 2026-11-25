import { expect, test, type Page } from "@playwright/test";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";

import { SandboxFrame } from "@/components/answer/play/SandboxFrame";
import { FRAME_MOTION_GUARD, FRAME_STILLNESS, sandboxDocument, type FrameLook } from "@/lib/sandboxFrame";

import { phaseCBlock } from "./playFixture";

type Seen = { running: number; smil: number; drawnX: number; banner: number; counts: { frames: number; ticks: number; chained: number }; flag: string | null };

const TOKENS = { "--ink-1": "rgb(28, 26, 23)", "--sunk": "rgb(239, 233, 221)", "--font-ui": "sans-serif" };
const MOVING_LOOK: FrameLook = { tokens: TOKENS, reducedMotion: false };
const STILL_LOOK: FrameLook = { tokens: TOKENS, reducedMotion: true };
const ANIMATED = ["css", "loud", "waapi", "made"];
const MOVING = [
  "<style>@keyframes kv-turn{from{transform:rotate(0deg)}to{transform:rotate(360deg)}}",
  ".turn{display:inline-block;animation:kv-turn 2s linear infinite}#loud{display:inline-block;animation:kv-turn 2s linear infinite!important}</style>",
  '<svg viewBox="0 0 40 20" width="40" height="20"><rect id="smil" width="10" height="10" fill="var(--sunk)">',
  '<animate attributeName="x" values="0;30" dur="1s" repeatCount="indefinite"></animate></rect></svg>',
  '<p class="turn" id="css">Turning</p><p id="loud">Loud</p><p id="waapi">Faded</p><p id="made">Made</p>',
  '<marquee id="banner" scrollamount="12" scrolldelay="40">Moving words</marquee>',
  "<script>",
  "window.counts = { frames: 0, ticks: 0, chained: 0 };",
  "requestAnimationFrame(function frame() { window.counts.frames += 1; requestAnimationFrame(frame); });",
  "setInterval(function () { window.counts.ticks += 1; }, 40);",
  "setTimeout(function chain() { window.counts.chained += 1; setTimeout(chain, 40); }, 40);",
  'document.getElementById("waapi").animate([{ opacity: 1 }, { opacity: 0.5 }], { duration: 1000, iterations: Infinity });',
  'const effect = new KeyframeEffect(document.getElementById("made"), [{ opacity: 1 }, { opacity: 0.5 }], { duration: 1000, iterations: Infinity });',
  "new Animation(effect, document.timeline).play();",
  'document.getElementById("css").style.setProperty("animation", "kv-turn 2s linear infinite", "important");',
  'document.documentElement.removeAttribute("data-reduced-motion");',
  "</script>"
].join("");

async function bannerX(page: Page): Promise<number> {
  return page.evaluate(() => {
    const range = document.createRange();
    range.selectNodeContents(document.getElementById("banner")!);
    return Math.round(range.getBoundingClientRect().left);
  });
}

async function framed(page: Page, look: FrameLook | null): Promise<Seen> {
  await page.setContent(sandboxDocument(MOVING, [], look));
  await page.waitForTimeout(100);
  const before = await bannerX(page);
  await page.waitForTimeout(500);
  const banner = Math.abs((await bannerX(page)) - before);
  const seen = await page.evaluate((ids) => {
    const running = document.getAnimations().filter((animation) => {
      const target = (animation.effect as KeyframeEffect | null)?.target;
      return animation.playState === "running" && target instanceof Element && ids.includes(target.id);
    });
    const rect = document.getElementById("smil") as unknown as SVGRectElement;
    return {
      running: running.length,
      smil: document.querySelectorAll("animate").length,
      drawnX: rect.x.animVal.value,
      counts: (window as unknown as { counts: Seen["counts"] }).counts,
      flag: document.documentElement.getAttribute("data-reduced-motion")
    };
  }, ANIMATED);
  return { ...seen, banner };
}

function expectStill(seen: Seen): void {
  expect(seen.running).toBe(0);
  expect(seen.smil).toBe(0);
  expect(seen.drawnX).toBe(0);
  expect(seen.banner).toBe(0);
  expect(seen.counts).toEqual({ frames: 0, ticks: 0, chained: 1 });
  expect(seen.flag).toBe("true");
}

test("the frame the server draws is still before the page reads its look, and keeps its guard once it does", () => {
  const block = phaseCBlock("simulation", "s1.b1");
  const server = sandboxDocument(block.html, block.values);
  expect(server.startsWith('<!doctype html><html lang="en" data-reduced-motion="true"><head>')).toBe(true);
  expect(server).toContain(`<script>${FRAME_STILLNESS}</script><style>${FRAME_MOTION_GUARD}</style></head>`);
  const drawn = renderToStaticMarkup(createElement(SandboxFrame, { block }));
  expect(drawn).toContain('data-reduced-motion=&quot;true&quot;');
  const moving = sandboxDocument(block.html, block.values, MOVING_LOOK);
  expect(moving.startsWith('<!doctype html><html lang="en"><head>')).toBe(true);
  expect(moving).toContain(`<script>${FRAME_STILLNESS}</script>`);
  expect(moving).toContain(FRAME_MOTION_GUARD);
});

test("before the look is read nothing in the frame moves, whatever the explainer's script does", async ({ page }) => {
  expectStill(await framed(page, null));
});

test("under the site's switch nothing in the frame moves, whatever the explainer's script does", async ({ page }) => {
  expectStill(await framed(page, STILL_LOOK));
});

test("under the system's switch nothing in the frame moves, even with a look that allows motion", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  expectStill(await framed(page, MOVING_LOOK));
});

test("with neither switch on, the explainer's motion plays as it wrote it", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "no-preference" });
  const seen = await framed(page, MOVING_LOOK);
  expect(seen.running).toBe(ANIMATED.length);
  expect(seen.smil).toBe(1);
  expect(seen.drawnX).toBeGreaterThan(0);
  expect(seen.banner).toBeGreaterThan(0);
  expect(seen.counts.frames).toBeGreaterThan(0);
  expect(seen.counts.ticks).toBeGreaterThan(0);
  expect(seen.counts.chained).toBeGreaterThan(1);
  expect(seen.flag).toBeNull();
});
