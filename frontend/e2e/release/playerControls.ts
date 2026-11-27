import { AxeBuilder } from "@axe-core/playwright";
import type { Locator, Page } from "@playwright/test";

import { clip } from "../production/checks";

import { expectedProblems, heldProblems, otherStep, unchangedProblems } from "./controlPlan";
import { changedFrom, reached, type ControlWatch } from "./controlWatch";
import { documentDrawn } from "./documentControls";
import { earlierAnswerReactionPlayer, earlierDipPlayer, earlierMolecule, earlierReactionPlayer, kitPlaysInView } from "./earlierPlayers";

const QUICK_MS = 5_000;
const PLAY_MS = 9_000;
const HOLD_MS = 4_500;
const MOLECULE_MS = 30_000;
const KIT_PLAYER = "figure.rp";
const ANSWER_PLAYER = '[data-testid="reaction-player"]';
const DIP_PLAYER = "figure.vat";
const SHARED_DIP = '[data-component="shared/chemistry/indigo-vat-dip"]';
const BORROWED_DIP = "the page draws the shared indigo vat dip, whose facts it does not hold";
const CHOICE = '.seg[data-choice] button[data-v][aria-pressed="false"]';
const EXPERIMENT = '[data-x][aria-pressed="false"]';
const KIT_MOLECULE = ".mol[data-cid]";
const ANSWER_MOLECULE = '[data-testid="molecule-3d"]';
const CAST = `${ANSWER_PLAYER} [data-testid="species-cast"]`;
const FRAME = '[data-testid="molecule-frame"]';
const GUARD = '[data-testid="molecule-guard"]';
const CLEAR = "rgba(0, 0, 0, 0)";
const DARK = "dark";
const DRAG_SHARES = [0.3, 0.45, 0.6, 0.75];

export type Present = { kit: boolean; answer: boolean };
export type DipCheck = { step: string; problems: (page: Page) => Promise<string[]> };
type CanvasRead = { corner: number; drawn: number; checksum: string; backdrop: string };
type WellRead = { theme: string; sunk: string; well: string; frame: string };

function attribute(target: Locator, name: string): () => Promise<string> {
  return async () => (await target.getAttribute(name)) ?? "";
}

async function present(page: Page, kit: string, answer: string): Promise<Present> {
  return { kit: (await page.locator(kit).count()) > 0, answer: (await page.locator(answer).count()) > 0 };
}

async function centred(target: Locator): Promise<void> {
  await target.evaluate((node) => node.scrollIntoView({ block: "center" }));
  await target.page().mouse.move(1, 1);
}

async function pausedProblems(control: string, read: () => Promise<string>, page: Page): Promise<string[]> {
  const before = await read();
  await page.waitForTimeout(HOLD_MS);
  return heldProblems(control, before, await read());
}

export async function kitReactionPlayer(page: Page): Promise<string[]> {
  const player = page.locator(KIT_PLAYER).first();
  if (!(await kitPlaysInView(page))) return earlierReactionPlayer(player);
  await centred(player);
  const step = attribute(player, "data-step");
  const steps = Number(await player.getAttribute("data-steps"));
  const play = player.locator(".rp-play");
  const pressed = attribute(play, "aria-pressed");
  const playing = await reached(pressed, "true", QUICK_MS);
  const before = await step();
  const moved = await changedFrom(step, before, PLAY_MS);
  const target = otherStep(Number(moved), steps);
  if (target === null) return [`the reaction player has ${steps} step`];
  await player.locator(".rp-rail button").nth(target - 1).click();
  const chosen = await reached(step, String(target), QUICK_MS);
  const still = await pressed();
  await play.click();
  const paused = await reached(pressed, "false", QUICK_MS);
  return [
    ...expectedProblems("the reaction player in view", "true", playing),
    ...unchangedProblems("the reaction player while playing", before, moved),
    ...expectedProblems(`the reaction player's step ${target}`, String(target), chosen),
    ...expectedProblems("the reaction player after a step is pressed", "true", still),
    ...expectedProblems("the reaction player's Pause", "false", paused),
    ...(await pausedProblems("the paused reaction player", step, page))
  ];
}

export async function answerReactionPlayer(page: Page): Promise<string[]> {
  const player = page.locator(ANSWER_PLAYER).first();
  if ((await player.getAttribute("data-plays")) === null) return earlierAnswerReactionPlayer(player);
  await centred(player);
  const step = attribute(player, "data-step");
  if ((await step()) === "all") return ["the figure's reaction player shows every step at once and cannot be played"];
  const play = player.getByTestId("reaction-play");
  const pressed = attribute(play, "aria-pressed");
  const playing = await reached(pressed, "true", QUICK_MS);
  const before = await step();
  const moved = await changedFrom(step, before, PLAY_MS);
  const target = otherStep(Number(moved), await player.getByTestId("reaction-step").count());
  if (target === null) return ["the figure's reaction player has one step"];
  await player.getByTestId("reaction-step").nth(target - 1).getByRole("button").click();
  const chosen = await reached(step, String(target), QUICK_MS);
  const still = await pressed();
  await play.click();
  const paused = await reached(pressed, "false", QUICK_MS);
  return [
    ...expectedProblems("the figure's reaction player in view", "true", playing),
    ...unchangedProblems("the figure's reaction player while playing", before, moved),
    ...expectedProblems(`the figure's reaction player's step ${target}`, String(target), chosen),
    ...expectedProblems("the figure's reaction player after a step is pressed", "true", still),
    ...expectedProblems("the figure's reaction player's Pause", "false", paused),
    ...(await pausedProblems("the paused figure reaction player", step, page))
  ];
}

export async function dipPlayer(page: Page): Promise<string[]> {
  const player = page.locator(DIP_PLAYER).first();
  if (!(await kitPlaysInView(page))) return earlierDipPlayer(player);
  await centred(player);
  const button = player.locator(".vat-dip");
  const pressed = attribute(button, "aria-pressed");
  const playing = await reached(pressed, "true", QUICK_MS);
  const pose = async () => `${await player.getAttribute("data-dips")} ${await player.getAttribute("data-pose")}`;
  const before = await pose();
  const moved = await changedFrom(pose, before, PLAY_MS);
  await button.click();
  const paused = await reached(pressed, "false", QUICK_MS);
  return [
    ...expectedProblems("the dip player in view", "true", playing),
    ...unchangedProblems("the dip player while playing", before, moved),
    ...expectedProblems("the dip player's Pause", "false", paused),
    ...(await pausedProblems("the paused dip player", pose, page))
  ];
}

async function pressPinned(page: Page, pinned: string, label: string): Promise<string[]> {
  const control = page.locator(pinned).first();
  await control.scrollIntoViewIfNeeded();
  await control.click();
  return expectedProblems(label, "true", await reached(attribute(control, "aria-pressed"), "true", QUICK_MS));
}

export async function whatIf(page: Page): Promise<string[]> {
  const problems: string[] = [];
  const experiment = page.locator(`${EXPERIMENT}:visible`).first();
  if (await experiment.count()) problems.push(...(await pressPinned(page, `[data-x="${await experiment.getAttribute("data-x")}"]`, "an experiment's tab")));
  const choice = page.locator(`${CHOICE}:visible`).first();
  if ((await choice.count()) === 0) return [...problems, "the document offers no what-if choice to press"];
  const group = await choice.evaluate((node) => node.closest("[data-choice]")?.getAttribute("data-choice") ?? "");
  const pinned = `.seg[data-choice="${group}"] button[data-v="${await choice.getAttribute("data-v")}"]`;
  return [...problems, ...(await pressPinned(page, pinned, "a what-if choice"))];
}

export async function kitMolecule(page: Page): Promise<string[]> {
  const molecule = page.locator(KIT_MOLECULE).first();
  if (!(await kitPlaysInView(page))) return earlierMolecule(page, molecule);
  await centred(molecule);
  const turned = attribute(molecule.locator(".mol-dial"), "aria-valuenow");
  const before = await turned();
  const after = await changedFrom(turned, before, QUICK_MS);
  const pause = molecule.locator(".mol-turn");
  await pause.click();
  const paused = await reached(attribute(pause, "aria-pressed"), "false", QUICK_MS);
  await pause.evaluate((node) => (node as HTMLElement).blur());
  await page.mouse.move(1, 1);
  return [
    ...unchangedProblems("the 3D molecule in view", before, after),
    ...expectedProblems("the 3D molecule's Pause", "false", paused),
    ...(await pausedProblems("the paused 3D molecule", turned, page))
  ];
}

export async function answerMolecule(page: Page): Promise<string[]> {
  const molecule = page.locator(ANSWER_MOLECULE).first();
  await molecule.scrollIntoViewIfNeeded();
  const status = await reached(attribute(molecule, "data-status"), "ready", MOLECULE_MS);
  return expectedProblems("the figure's 3D molecule", "ready", status);
}

async function drawnDip(page: Page): Promise<string[]> {
  return (await page.locator(DIP_PLAYER).count()) ? dipPlayer(page) : ["the document draws no dip player"];
}

async function unborrowedDip(page: Page): Promise<string[]> {
  const borrowed = (await page.locator(SHARED_DIP).count()) ? [BORROWED_DIP] : [];
  const own = (await page.locator(DIP_PLAYER).count()) ? await dipPlayer(page) : [];
  return [...borrowed, ...own];
}

const DIP_DRAWN: DipCheck = { step: "Dip player", problems: drawnDip };
export const DIP_UNBORROWED: DipCheck = { step: "No borrowed dip player", problems: unborrowedDip };

export async function playerSession(watch: ControlWatch, page: Page, dip: DipCheck = DIP_DRAWN): Promise<void> {
  const reaction = await present(page, KIT_PLAYER, ANSWER_PLAYER);
  const molecule = await present(page, KIT_MOLECULE, ANSWER_MOLECULE);
  if (!reaction.kit && !reaction.answer) await watch.step("Reaction player", async () => ["the document draws no reaction player"]);
  if (reaction.kit) await watch.step("Reaction player steps and play", () => kitReactionPlayer(page));
  if (reaction.answer) await watch.step("Figure reaction player steps and play", () => answerReactionPlayer(page));
  await watch.step(dip.step, () => dip.problems(page));
  if (molecule.kit) await watch.step("3D molecule turns", () => kitMolecule(page));
  if (molecule.answer) await watch.step("Figure 3D molecule reports ready", () => answerMolecule(page));
  if (!molecule.kit && !molecule.answer) await watch.step("3D molecule", async () => ["the document draws no 3D molecule"]);
}

function readCanvas(frame: Element): CanvasRead | null {
  const canvas = frame.querySelector("canvas");
  if (!canvas || canvas.width === 0 || canvas.height === 0) return null;
  const copy = document.createElement("canvas");
  copy.width = canvas.width;
  copy.height = canvas.height;
  const context = copy.getContext("2d");
  if (!context) return null;
  context.drawImage(canvas, 0, 0);
  const pixels = context.getImageData(0, 0, copy.width, copy.height).data;
  let drawn = 0;
  let checksum = 0;
  for (let at = 0; at < pixels.length; at += 4) {
    if (pixels[at + 3] > 0) drawn += 1;
    checksum = (checksum * 31 + pixels[at] + 3 * pixels[at + 1] + 7 * pixels[at + 2] + 11 * pixels[at + 3]) % 2147483647;
  }
  return { corner: pixels[3], drawn, checksum: String(checksum), backdrop: getComputedStyle(canvas).backgroundColor };
}

function readWell(frame: Element): WellRead {
  const root = document.documentElement;
  const channels = getComputedStyle(root).getPropertyValue("--c-sunk").trim().split(/\s+/);
  const well = frame.parentElement ? getComputedStyle(frame.parentElement).backgroundColor : "";
  return { theme: root.getAttribute("data-theme") ?? "", sunk: `rgb(${channels.join(", ")})`, well, frame: getComputedStyle(frame).backgroundColor };
}

export async function castContrast(page: Page): Promise<string[]> {
  const cast = page.locator(CAST).first();
  if ((await cast.count()) === 0) return ["the figure's reaction player shows no species cast on a phone"];
  await cast.scrollIntoViewIfNeeded();
  const theme = await page.evaluate(() => document.documentElement.getAttribute("data-theme") ?? "");
  const checked = await new AxeBuilder({ page }).include(CAST).withRules(["color-contrast"]).analyze();
  const judged = [...checked.passes, ...checked.violations].reduce((count, rule) => count + rule.nodes.length, 0);
  const failing = checked.violations.flatMap((rule) => rule.nodes.map((node) => `the species cast fails ${rule.id} at ${node.target.join(" ")}: ${clip(node.failureSummary ?? "")}`));
  return [...expectedProblems("the page's theme on a dark phone", DARK, theme), ...(judged > 0 ? [] : ["axe judged no text in the species cast"]), ...failing];
}

export async function moleculeInDark(page: Page): Promise<string[]> {
  const molecule = page.locator(ANSWER_MOLECULE).first();
  await molecule.scrollIntoViewIfNeeded();
  const status = await reached(attribute(molecule, "data-status"), "ready", MOLECULE_MS);
  if (status !== "ready") return expectedProblems("the figure's 3D molecule on a dark phone", "ready", status);
  const frame = molecule.locator(FRAME);
  const well = await frame.evaluate(readWell);
  const canvas = await frame.evaluate(readCanvas);
  if (!canvas) return ["the figure's 3D molecule draws no canvas on a dark phone"];
  return [
    ...expectedProblems("the page's theme on a dark phone", DARK, well.theme),
    ...expectedProblems("the 3D molecule's well on a dark phone", well.sunk, well.well),
    ...expectedProblems("the 3D molecule frame's own background", CLEAR, well.frame),
    ...expectedProblems("the 3D molecule canvas's own background", CLEAR, canvas.backdrop),
    ...expectedProblems("the 3D molecule canvas's corner alpha", "0", String(canvas.corner)),
    ...(canvas.drawn > 0 ? [] : ["the 3D molecule canvas holds no drawn pixel"])
  ];
}

async function touchDrag(page: Page, target: Locator): Promise<void> {
  const box = await target.boundingBox();
  if (!box) return;
  const [start, ...moves] = DRAG_SHARES.map((share) => ({ x: box.x + box.width * share, y: box.y + box.height / 2 }));
  const session = await page.context().newCDPSession(page);
  try {
    await session.send("Input.dispatchTouchEvent", { type: "touchStart", touchPoints: [start] });
    for (const point of moves) await session.send("Input.dispatchTouchEvent", { type: "touchMove", touchPoints: [point] });
    await session.send("Input.dispatchTouchEvent", { type: "touchEnd", touchPoints: [] });
  } finally {
    await session.detach();
  }
}

export async function exploreByTouch(page: Page): Promise<string[]> {
  const molecule = page.locator(ANSWER_MOLECULE).first();
  const explore = molecule.getByRole("button", { name: "Explore", exact: true });
  if ((await explore.count()) === 0) return ["the figure's 3D molecule offers no Explore on a phone"];
  const frame = molecule.locator(FRAME);
  const pixels = async () => (await frame.evaluate(readCanvas))?.checksum ?? "";
  await explore.tap();
  const pressed = await reached(attribute(explore, "aria-pressed"), "true", QUICK_MS);
  const covers = await reached(async () => String(await molecule.locator(GUARD).count()), "0", QUICK_MS);
  const before = await pixels();
  await touchDrag(page, frame);
  const after = await changedFrom(pixels, before, QUICK_MS);
  return [
    ...expectedProblems("the 3D molecule's Explore after a tap", "true", pressed),
    ...expectedProblems("the covers over the 3D molecule after Explore", "0", covers),
    ...unchangedProblems("the 3D molecule dragged by one finger", before, after)
  ];
}

export async function darkTouchSession(watch: ControlWatch, page: Page): Promise<void> {
  await watch.step("Document drawn with its controls", () => documentDrawn(page));
  const cast = (await page.locator(CAST).count()) > 0;
  const molecule = (await page.locator(ANSWER_MOLECULE).count()) > 0;
  if (cast) await watch.step("Figure species cast readable in dark", () => castContrast(page));
  if (molecule) await watch.step("Figure 3D molecule clear on the dark page", () => moleculeInDark(page));
  if (molecule) await watch.step("Figure 3D molecule explored by touch", () => exploreByTouch(page));
  if (cast || molecule) return;
  await watch.step("Figure players in dark and by touch", async () => {
    watch.note("the document draws neither a figure reaction player's species cast nor a figure 3D molecule");
    return [];
  });
}
