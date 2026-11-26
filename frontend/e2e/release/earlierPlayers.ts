import type { Locator, Page } from "@playwright/test";

import { endsOnItsOwn, expectedProblems, nextDips, otherStep, unchangedProblems } from "./controlPlan";
import { changedFrom, reached } from "./controlWatch";

const QUICK_MS = 5_000;
const PLAY_MS = 9_000;

function attribute(target: Locator, name: string): () => Promise<string> {
  return async () => (await target.getAttribute(name)) ?? "";
}

export async function kitPlaysInView(page: Page): Promise<boolean> {
  return page.evaluate(() => typeof (window as Window & { KV?: { seen?: unknown } }).KV?.seen === "function");
}

async function pauseProblems(play: Locator, at: number, steps: number): Promise<string[]> {
  const pressed = attribute(play, "aria-pressed");
  if (endsOnItsOwn(at, steps)) return expectedProblems("the reaction player at its last step", "false", await reached(pressed, "false", QUICK_MS));
  await play.click();
  return expectedProblems("the reaction player's Pause", "false", await reached(pressed, "false", QUICK_MS));
}

export async function earlierReactionPlayer(player: Locator): Promise<string[]> {
  await player.scrollIntoViewIfNeeded();
  const step = attribute(player, "data-step");
  const steps = Number(await player.getAttribute("data-steps"));
  const target = otherStep(Number(await step()), steps);
  if (target === null) return [`the reaction player has ${steps} step`];
  const rail = player.locator(".rp-rail button");
  await rail.nth(target - 1).click();
  const chosen = await reached(step, String(target), QUICK_MS);
  await rail.first().click();
  const first = await reached(step, "1", QUICK_MS);
  const play = player.locator(".rp-play");
  await play.click();
  const playing = await reached(attribute(play, "aria-pressed"), "true", QUICK_MS);
  const moved = await changedFrom(step, first, PLAY_MS);
  return [
    ...expectedProblems(`the reaction player's step ${target}`, String(target), chosen),
    ...expectedProblems("the reaction player's first step", "1", first),
    ...expectedProblems("the reaction player's Play", "true", playing),
    ...unchangedProblems("the reaction player while playing", first, moved),
    ...(await pauseProblems(play, Number(moved), steps))
  ];
}

export async function earlierDipPlayer(player: Locator): Promise<string[]> {
  await player.scrollIntoViewIfNeeded();
  const dips = attribute(player, "data-dips");
  const before = Number(await dips());
  await player.locator(".vat-dip").click();
  const after = await reached(dips, String(nextDips(before)), QUICK_MS);
  return expectedProblems("the dip player", String(nextDips(before)), after);
}

export async function earlierMolecule(page: Page, molecule: Locator): Promise<string[]> {
  await molecule.scrollIntoViewIfNeeded();
  const turned = attribute(molecule.locator(".mol-dial"), "aria-valuenow");
  await page.waitForTimeout(QUICK_MS / 5);
  const before = await turned();
  await molecule.locator(".mol-turn").click();
  const after = await changedFrom(turned, before, QUICK_MS);
  return unchangedProblems("the 3D molecule's Turn", before, after);
}

export async function earlierAnswerReactionPlayer(player: Locator): Promise<string[]> {
  await player.scrollIntoViewIfNeeded();
  const step = attribute(player, "data-step");
  const before = await step();
  if (before === "all") return ["the figure's reaction player shows every step at once and cannot be played"];
  await player.getByRole("button", { name: "Next step" }).click();
  const next = await changedFrom(step, before, QUICK_MS);
  await player.getByTestId("reaction-step").first().getByRole("button").click();
  const chosen = await reached(step, "1", QUICK_MS);
  await player.getByTestId("reaction-play").click();
  const pause = await player.getByTestId("reaction-pause").waitFor({ state: "visible", timeout: QUICK_MS }).then(
    () => [],
    () => ["the figure's reaction player shows no Pause after Play"]
  );
  const moved = await changedFrom(step, chosen, PLAY_MS);
  const pauseButton = player.getByTestId("reaction-pause");
  if (await pauseButton.isVisible()) await pauseButton.click();
  return [
    ...unchangedProblems("the figure's reaction player's Next step", before, next),
    ...expectedProblems("the figure's reaction player's first step", "1", chosen),
    ...pause,
    ...unchangedProblems("the figure's reaction player while playing", chosen, moved)
  ];
}
