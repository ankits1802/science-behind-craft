import { expect, test, type Locator, type Page } from "@playwright/test";

import { KIT_JS, LONG_NAME, playersDocument, playersHtml, type Motion } from "./playersFixture";

const SWITCHES = ["system", "page"] as const;
const QUIET_MS = 4200;

async function opened(page: Page, motion: Motion, width = 1440, long = false): Promise<void> {
  await page.setViewportSize({ width, height: 900 });
  await page.emulateMedia({ reducedMotion: motion === "system" ? "reduce" : "no-preference" });
  await page.setContent(playersHtml(motion, playersDocument({ long })), { waitUntil: "domcontentloaded" });
  await page.addScriptTag({ content: KIT_JS });
  for (const scope of ["chem", "pt"]) await expect(page.locator(`#${scope}-theme-toggle[aria-pressed]`)).toBeAttached();
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

test("a reaction player starts playing when it comes into view, from its first step, with one Pause", async ({ page }) => {
  await opened(page, "allowed");
  const player = page.locator("figure.rp");
  const play = player.locator(".rp-play");
  await centred(player);
  await expect(play).toHaveAttribute("aria-pressed", "true");
  await expect(play).toHaveText("Pause");
  await expect(player).toHaveAttribute("data-step", "1");
  await expect(player.locator(".rp-status")).toHaveAttribute("aria-live", "off");
  await expect(player).toHaveAttribute("data-step", "2", { timeout: 6000 });
  await expect(player).toHaveAttribute("data-step", "1", { timeout: 6000 });
});

test("a step pressed while it plays is shown at once and the player plays on from it; Pause holds it", async ({ page }) => {
  await opened(page, "allowed");
  const player = page.locator("figure.rp");
  const play = player.locator(".rp-play");
  await centred(player);
  await expect(play).toHaveAttribute("aria-pressed", "true");
  await player.locator(".rp-rail button").nth(1).click();
  await expect(player).toHaveAttribute("data-step", "2");
  await expect(play).toHaveAttribute("aria-pressed", "true");
  await expect(player).toHaveAttribute("data-step", "1", { timeout: 6000 });
  await play.click();
  await expect(play).toHaveAttribute("aria-pressed", "false");
  await expect(play).toHaveText("Play");
  await expect(player.locator(".rp-status")).toHaveAttribute("aria-live", "polite");
  expect(await held(page, () => player.getAttribute("data-step"))).toBe(true);
  await player.locator(".rp-rail button").nth(1).click();
  await expect(player).toHaveAttribute("data-step", "2");
  await expect(play).toHaveAttribute("aria-pressed", "false");
});

test("a shown reaction step brings in its species: the reagent arrives, the bond breaks, the product forms", async ({ page }) => {
  await opened(page, "allowed");
  const player = page.locator("figure.rp");
  await centred(player);
  await expect(player).toHaveAttribute("data-step", "1");
  const step = player.locator('.rx[data-i="1"]');
  await expect(step.locator('[data-kit-part="species"]')).toHaveCount(3);
  await expect(step.locator('[data-kit-break]')).toHaveCount(1);
  await player.locator(".rp-rail button").first().click();
  const names = await step.evaluate((node) => [".kv-rx-meet", ".kv-rx-arrive", ".kv-rx-break", ".kv-rx-arrow", ".kv-rx-form"].map((selector) => getComputedStyle(node.querySelector(selector)!).animationName));
  expect(names).toEqual(["kv-rx-meet", "kv-rx-arrive", "kv-rx-break", "kv-rx-arrow", "kv-rx-form"]);
  const lane = await player.locator(".rp-chem").first().evaluate((node) => [...node.querySelectorAll(".lane > *")].map((item) => getComputedStyle(item).animationName));
  expect(lane).toEqual(["chem-lane-in", "chem-lane-arr", "chem-rx-new"]);
});

for (const motion of SWITCHES) {
  test(`under the ${motion} reduced-motion switch nothing plays, each step rests on its end state and Play shows the next at once`, async ({ page }) => {
    await opened(page, motion);
    const player = page.locator("figure.rp");
    const play = player.locator(".rp-play");
    await centred(player);
    expect(await held(page, () => player.getAttribute("data-step"))).toBe(true);
    await expect(player).toHaveAttribute("data-step", "2");
    await expect(play).toHaveAttribute("aria-pressed", "false");
    await play.click();
    await expect(player).toHaveAttribute("data-step", "1");
    await expect(play).toHaveAttribute("aria-pressed", "false");
    await expect(player.locator(".rp-status")).toContainText("Step 1 of 2");
    await expect(page.locator("[data-kit-move][data-playing]")).toHaveCount(0);
    const moving = await page.evaluate(() => [...document.querySelectorAll("[data-kit-move], .rp-chem .lane > *")].map((node) => getComputedStyle(node).animationName));
    expect(new Set(moving)).toEqual(new Set(["none"]));
    const shown = await player.locator('.rx[data-i="1"]').evaluate((node) => [...node.querySelectorAll(".kv-rx-form, .kv-rx-arrive")].map((part) => getComputedStyle(part).opacity));
    expect(new Set(shown)).toEqual(new Set(["1"]));
  });
}

test("a long species name, formula and state wrap inside the lane at 320px and no part of the player scrolls", async ({ page }) => {
  await opened(page, "system", 320, true);
  const player = page.locator("figure.rp");
  await centred(player);
  const found = await player.evaluate((figure) => {
    const box = figure.getBoundingClientRect();
    const scrolls = [...figure.querySelectorAll("*")].filter((node) => {
      const style = getComputedStyle(node);
      const scrolling = /(auto|scroll)/.test(style.overflowX + style.overflowY);
      return scrolling && (node.scrollWidth > node.clientWidth + 1 || node.scrollHeight > node.clientHeight + 1);
    });
    const outside = [...figure.querySelectorAll(".rp-chem:not(.kv-off) *")].filter((node) => {
      const rect = node.getBoundingClientRect();
      return rect.width > 0 && (rect.right > box.right + 0.5 || rect.left < box.left - 0.5);
    });
    return { scrolls: scrolls.length, outside: outside.map((node) => node.className) };
  });
  expect(found).toEqual({ scrolls: 0, outside: [] });
  const lines = await player.locator(".rp-chem:not(.kv-off) .lane .spc").evaluateAll((cards) =>
    cards.map((card) => {
      const name = card.querySelector(".nm")!;
      return Math.round(name.getBoundingClientRect().height / parseFloat(getComputedStyle(name).lineHeight));
    })
  );
  expect(lines[0]).toBeGreaterThan(1);
  expect(lines[lines.length - 1]).toBe(1);
  await expect(player.locator(".rp-chem:not(.kv-off) .nm").first()).toHaveText(LONG_NAME);
});

test("a dip player plays its dips on its own in view, its one button pausing it", async ({ page }) => {
  await opened(page, "allowed");
  const dip = page.locator("figure.vat");
  const button = dip.locator(".vat-dip");
  await centred(dip);
  await expect(button).toHaveAttribute("aria-pressed", "true");
  await expect(button).toHaveText("Pause");
  await expect(dip).toHaveAttribute("data-dips", "1");
  await expect(dip.locator(".vat-status")).toHaveAttribute("aria-live", "off");
  await button.click();
  await expect(button).toHaveAttribute("aria-pressed", "false");
  await expect(button).toHaveText("Play");
  await expect(dip.locator(".vs").last()).toHaveAttribute("aria-current", "step");
  expect(await held(page, () => dip.getAttribute("data-dips"))).toBe(true);
});

for (const motion of SWITCHES) {
  test(`under the ${motion} switch a dip player rests, and Dip again still steps one phase a press`, async ({ page }) => {
    await opened(page, motion);
    const dip = page.locator("figure.vat");
    const button = dip.locator(".vat-dip");
    await centred(dip);
    expect(await held(page, () => dip.getAttribute("data-dips"))).toBe(true);
    await expect(button).toHaveText("Dip again");
    await expect(button).not.toHaveAttribute("aria-pressed", /.*/);
    await button.click();
    await expect(dip.locator(".vs").first()).toHaveAttribute("aria-current", "step");
  });
}

test("a stage player that is not Kutch Ajrakh's plays its stages in view and a stage pressed plays on from there", async ({ page }) => {
  await opened(page, "allowed");
  const stages = page.locator('[data-comp="cloth"]');
  const play = stages.locator("[data-play]");
  const count = await stages.locator(".rb").count();
  await centred(stages.locator(".lc-stagebox"));
  await expect(play).toHaveAttribute("aria-pressed", "true");
  await expect(play.locator("span")).toHaveText("Pause");
  await expect(stages.locator("[data-k]")).toHaveText(`Stage 1 of ${count}`);
  await expect(stages.locator(".rb").first()).toHaveAttribute("aria-pressed", "true");
  await expect(stages.locator(".lc-step").first()).toHaveAttribute("aria-current", "step");
  await expect(stages.locator(".lc-big .lc-band")).toHaveCount(1);
  await stages.locator(".rb").nth(2).click();
  await expect(stages.locator("[data-k]")).toHaveText(`Stage 3 of ${count}`);
  await expect(play).toHaveAttribute("aria-pressed", "true");
  await expect(stages.locator("[data-k]")).toHaveText(`Stage 4 of ${count}`, { timeout: 6000 });
  await play.click();
  await expect(play).toHaveAttribute("aria-pressed", "false");
  await expect(play.locator("span")).toHaveText("Play the stages");
  expect(await held(page, () => stages.locator("[data-k]").textContent())).toBe(true);
});

for (const motion of SWITCHES) {
  test(`under the ${motion} switch a stage player rests on its last stage and Play shows the next at once`, async ({ page }) => {
    await opened(page, motion);
    const stages = page.locator('[data-comp="cloth"]');
    const count = await stages.locator(".rb").count();
    await centred(stages.locator(".lc-stagebox"));
    expect(await held(page, () => stages.locator("[data-k]").textContent())).toBe(true);
    await expect(stages.locator("[data-k]")).toHaveText(`Stage ${count} of ${count}`);
    await stages.locator("[data-play]").click();
    await expect(stages.locator("[data-k]")).toHaveText(`Stage 1 of ${count}`);
    await expect(stages.locator("[data-play]")).toHaveAttribute("aria-pressed", "false");
    await expect(stages.locator(".lc-band")).toHaveCount(0);
  });
}

test("a molecule turns slowly on its own in view, and holds still under the pointer, in focus or paused", async ({ page }) => {
  await opened(page, "allowed");
  const molecule = page.locator(".mol[data-cid]");
  const dial = molecule.locator(".mol-dial");
  const turn = molecule.locator(".mol-turn");
  await centred(molecule);
  await expect(turn).toHaveAttribute("aria-pressed", "true");
  await expect(turn).toHaveText("Pause");
  const start = await dial.getAttribute("aria-valuenow");
  await expect.poll(() => dial.getAttribute("aria-valuenow"), { timeout: 5000 }).not.toBe(start);
  await dial.hover();
  expect(await held(page, () => dial.getAttribute("aria-valuenow"))).toBe(true);
  await page.mouse.move(1, 1);
  await dial.focus();
  expect(await held(page, () => dial.getAttribute("aria-valuenow"))).toBe(true);
  await turn.click();
  await expect(turn).toHaveAttribute("aria-pressed", "false");
  await expect(turn).toHaveText("Turn");
  await turn.evaluate((node) => (node as HTMLElement).blur());
  await page.mouse.move(1, 1);
  expect(await held(page, () => dial.getAttribute("aria-valuenow"))).toBe(true);
});

for (const motion of SWITCHES) {
  test(`under the ${motion} switch a molecule rests at its angle and Turn turns it a quarter at once`, async ({ page }) => {
    await opened(page, motion);
    const molecule = page.locator(".mol[data-cid]");
    const dial = molecule.locator(".mol-dial");
    await centred(molecule);
    expect(await held(page, () => dial.getAttribute("aria-valuenow"))).toBe(true);
    await expect(molecule.locator(".mol-turn")).toHaveText("Turn");
    const before = Number(await dial.getAttribute("aria-valuenow"));
    await molecule.locator(".mol-turn").click();
    await expect(dial).toHaveAttribute("aria-valuenow", String((before + 90) % 360));
  });
}
