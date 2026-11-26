import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { join } from "node:path";

import { expect, test, type Locator, type Page } from "@playwright/test";

import { STEP_SECONDS } from "@/lib/reactionPlayer";
import { TIMELINE_STEP_MS } from "@/lib/timelinePlay";

import { FRONTEND } from "./moduleGraph";

const VIEW = readFileSync(join(FRONTEND, "..", "backend", "app", "data", "design", "answer-view.html"), "utf8");
const THEME = readFileSync(join(FRONTEND, "app", "tokens.css"), "utf8");
const FIGURES = JSON.parse(readFileSync(join(FRONTEND, "..", "shared", "mcp.ask-figures.golden.json"), "utf8")) as { sections: { sentences: { text: string }[] }[] };
const SCRIPT = /<script>([\s\S]*?)<\/script>/;
const QUIET_MS = 4600;
const PLAYED_MS = 9000;
const ANSWER = {
  question: "How do the red, the black and the blue come about in Kutch Ajrakh?",
  crafts: [{ slug: "Kutch-Ajrakh", name: "Kutch Ajrakh", pageUrl: "https://kalavigyan.example/crafts/Kutch-Ajrakh" }],
  opening: [],
  sections: FIGURES.sections,
  sources: [],
  attribution: "KalaVigyan, IIT Kharagpur",
  answerUrl: "https://kalavigyan.example/ask?explainer=a&version=1"
};

type Motion = "allowed" | "system" | "page";

function viewPage(motion: Motion): string {
  const script = SCRIPT.exec(VIEW)?.[1] ?? "";
  const hash = `sha256-${createHash("sha256").update(script, "utf8").digest("base64")}`;
  const page = VIEW.replace("__KV_THEME__", THEME).replace("__KV_SCRIPT_HASH__", hash);
  return motion === "page" ? page.replace('<html lang="en">', '<html lang="en" data-reduced-motion="true">') : page;
}

async function shown(page: Page, motion: Motion, width = 1280): Promise<void> {
  await page.setViewportSize({ width, height: 800 });
  await page.emulateMedia({ reducedMotion: motion === "system" ? "reduce" : "no-preference" });
  await page.setContent(viewPage(motion));
  await page.evaluate((answer) => window.postMessage({ jsonrpc: "2.0", method: "ui/notifications/tool-result", params: { structuredContent: answer } }, "*"), ANSWER);
  await expect(page.locator("h1")).toHaveText(ANSWER.question);
}

async function centred(target: Locator): Promise<void> {
  await target.evaluate((node) => node.scrollIntoView({ block: "center" }));
  await target.page().mouse.move(1, 1);
}

async function held(page: Page, read: () => Promise<string | null>): Promise<boolean> {
  const before = await read();
  await page.waitForTimeout(QUIET_MS);
  return (await read()) === before;
}

const reaction = (page: Page) => page.locator('figure[data-figure="reaction"]');
const timeline = (page: Page) => page.locator('figure[data-figure="timeline"]');
const molecule = (page: Page) => page.locator('figure[data-figure="molecule"]');

test("the view plays on the web players' beats", () => {
  expect(VIEW).toContain(`reaction: ${STEP_SECONDS * 1000}`);
  expect(VIEW).toContain(`timeline: ${TIMELINE_STEP_MS}`);
});

test("an answer's reaction player plays once in view from its first step, loops, and has one Pause", async ({ page }) => {
  await shown(page, "allowed");
  const player = reaction(page);
  const play = player.locator(".kv-play");
  await expect(player).toHaveAttribute("data-step", "1");
  await centred(player);
  await expect(play).toHaveAttribute("aria-pressed", "true");
  await expect(play).toHaveText("Pause");
  await expect(player.locator(".kv-say")).toHaveAttribute("aria-live", "off");
  await expect(player).toHaveAttribute("data-step", "2", { timeout: PLAYED_MS });
  await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
  await expect(play).toHaveAttribute("aria-pressed", "false");
});

test("a step pressed is shown at once and playing goes on from it; Pause holds the step shown", async ({ page }) => {
  await shown(page, "allowed");
  const player = reaction(page);
  const play = player.locator(".kv-play");
  await centred(player);
  await expect(play).toHaveAttribute("aria-pressed", "true");
  await player.locator(".kv-rail button").nth(3).click();
  await expect(player).toHaveAttribute("data-step", "4");
  await expect(player.locator(".kv-rail button").nth(3)).toHaveAttribute("aria-pressed", "true");
  await expect(player).toHaveAttribute("data-step", "1", { timeout: PLAYED_MS });
  await play.click();
  await expect(play).toHaveAttribute("aria-pressed", "false");
  await expect(player.locator(".kv-say")).toHaveAttribute("aria-live", "polite");
  expect(await held(page, () => player.getAttribute("data-step"))).toBe(true);
  await player.locator(".kv-rail button").nth(2).click();
  await expect(player).toHaveAttribute("data-step", "3");
  await expect(play).toHaveAttribute("aria-pressed", "false");
});

test("a shown step's colour change moves only with motion allowed, and the rail moves by arrow keys", async ({ page }) => {
  await shown(page, "allowed");
  const player = reaction(page);
  await centred(player);
  await expect(player.locator(".kv-play")).toHaveAttribute("aria-pressed", "true");
  await player.locator(".kv-play").click();
  await player.locator(".kv-rail button").nth(2).click();
  const over = player.locator('.kv-panel[data-step="3"] .kv-swatch-after');
  await expect(over).toHaveAttribute("data-playing", "oxidise");
  expect(await over.evaluate((node) => getComputedStyle(node).animationName)).toBe("kv-oxidise");
  await page.keyboard.press("ArrowRight");
  await expect(player).toHaveAttribute("data-step", "4");
  await expect(player.locator(".kv-rail button").nth(3)).toBeFocused();
  await page.keyboard.press("Home");
  await expect(player).toHaveAttribute("data-step", "1");
});

for (const motion of ["system", "page"] as const) {
  test(`under the ${motion} reduced-motion switch nothing in the view moves; Play and Turn step once a press`, async ({ page }) => {
    await shown(page, motion);
    const player = reaction(page);
    const play = player.locator(".kv-play");
    await centred(player);
    expect(await play.getAttribute("aria-pressed")).toBeNull();
    expect(await held(page, () => player.getAttribute("data-step"))).toBe(true);
    await play.click();
    await expect(player).toHaveAttribute("data-step", "2");
    await expect(player.locator(".kv-say")).toHaveText(/^Step 2 of 4: /);
    await player.locator(".kv-rail button").nth(2).click();
    expect(await player.locator('.kv-panel[data-step="3"] .kv-swatch-after').evaluate((node) => getComputedStyle(node).animationName)).toBe("none");
    const turning = molecule(page);
    await centred(turning);
    const yaw = await turning.getAttribute("data-yaw");
    expect(await held(page, () => turning.getAttribute("data-yaw"))).toBe(true);
    await turning.locator(".kv-play").click();
    await expect(turning).toHaveAttribute("data-yaw", String((Number(yaw) + 90) % 360));
    expect(await page.evaluate(() => document.getAnimations().filter((animation) => animation.playState === "running").length)).toBe(0);
  });
}

test("the timeline has no slider: it rests on its last year, a point pressed jumps there, Play steps through and Space toggles", async ({ page }) => {
  await shown(page, "allowed");
  const dated = timeline(page);
  await expect(dated.locator("input")).toHaveCount(0);
  const points = dated.locator(".kv-track button");
  await expect(points).toHaveCount(3);
  await expect(dated).toHaveAttribute("data-step", "3");
  await expect(dated.locator(".kv-year")).toHaveText("2001");
  await centred(dated);
  await expect(dated.locator(".kv-play")).toHaveAttribute("aria-pressed", "true");
  await expect(dated).toHaveAttribute("data-step", "1");
  await points.nth(1).click();
  await expect(dated).toHaveAttribute("data-step", "2");
  await expect(points.nth(1)).toHaveAttribute("aria-pressed", "true");
  await expect(dated.locator(".kv-year")).toHaveText("1586");
  await points.nth(1).focus();
  await page.keyboard.press(" ");
  await expect(dated.locator(".kv-play")).toHaveAttribute("aria-pressed", "false");
  await page.keyboard.press(" ");
  await expect(dated.locator(".kv-play")).toHaveAttribute("aria-pressed", "true");
});

test("a molecule turns slowly once in view, holds under the pointer and on Pause", async ({ page }) => {
  await shown(page, "allowed");
  const turning = molecule(page);
  await expect(turning.locator("svg circle")).toHaveCount(26);
  await centred(turning);
  const yaw = await turning.getAttribute("data-yaw");
  await expect(turning).not.toHaveAttribute("data-yaw", yaw ?? "", { timeout: PLAYED_MS });
  await expect(turning.locator(".kv-play")).toHaveText("Pause");
  await turning.locator("svg").hover();
  expect(await held(page, () => turning.getAttribute("data-yaw"))).toBe(true);
  await page.mouse.move(1, 1);
  await turning.locator(".kv-play").click();
  await page.mouse.move(1, 1);
  await turning.locator(".kv-play").evaluate((node) => (node as HTMLElement).blur());
  await expect(turning.locator(".kv-play")).toHaveAttribute("aria-pressed", "false");
  expect(await held(page, () => turning.getAttribute("data-yaw"))).toBe(true);
});

test("each figure draws its own sentences once, in its steps, and the paragraph keeps the rest", async ({ page }) => {
  await shown(page, "allowed");
  const texts = FIGURES.sections.flatMap((section) => section.sentences.map((sentence) => sentence.text));
  const body = await page.evaluate(() => document.querySelector("main")?.textContent ?? "");
  for (const text of new Set(texts)) {
    const said = texts.reduce((count, other) => count + other.split(text).length - 1, 0);
    expect(body.split(text).length - 1, text).toBe(said);
  }
  await expect(page.locator('figure[data-figure="stages"] .kv-rail button')).toHaveCount(4);
  await expect(page.locator('figure[data-figure="dips"]')).toHaveCount(2);
});

for (const width of [320, 390]) {
  test(`no name, formula or lane of the view's figures scrolls or widens the page at ${width}px`, async ({ page }) => {
    await shown(page, "allowed", width);
    const scrolling = await page.evaluate(() =>
      [...document.querySelectorAll(".kv-fig, .kv-fig *")]
        .filter((node) => {
          const style = getComputedStyle(node);
          return ["auto", "scroll"].includes(style.overflowX) || ["auto", "scroll"].includes(style.overflowY);
        })
        .map((node) => node.className)
    );
    expect(scrolling).toEqual([]);
    const wide = await page.evaluate(() => [...document.querySelectorAll(".kv-fig *")].filter((node) => node.getBoundingClientRect().right > window.innerWidth + 1).map((node) => node.textContent?.slice(0, 40)));
    expect(wide).toEqual([]);
    expect(await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth)).toBeLessThanOrEqual(0);
  });
}
