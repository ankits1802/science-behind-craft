import { expect, type Locator, type Page, type Response } from "@playwright/test";

import { checkedCraftPage, CRAFT_PAGE_PATH, craftPageShape } from "@/lib/craftPageContract";
import { ROLE_LABELS } from "@/lib/permissions";
import { parseShape } from "@/lib/shape";
import type { User } from "@/lib/types";

import { DESKTOP_NAV_MIN_WIDTH, NO_LAYER_LABEL, clip, curatedOverviewProblems, labelProblems, navExpectation, overviewNote, type OverviewServed } from "./checks";
import { answersScript } from "./stuckPage";

const LAYER_TIMEOUT_MS = 30_000;
const CLICK_TIMEOUT_MS = 30_000;
const ANSWER_TIMEOUT_MS = 5_000;
const STEADY_GAP_MS = 500;
const CALL_LOG_LINES = 6;
const CRAFT_PAGE_TIMEOUT_MS = 30_000;
const COMPARE_TIMEOUT_MS = 30_000;

function wideNav(page: Page): boolean {
  return (page.viewportSize()?.width ?? 0) >= DESKTOP_NAV_MIN_WIDTH;
}

function unexpectedRole(user: User): string {
  return `the E2E account is ${user.role}; it must be STUDENT or RESEARCHER, the roles without two-step`;
}

export async function menuProblems(page: Page, user: User): Promise<string[]> {
  const expected = navExpectation(user.role);
  if (!expected) return [unexpectedRole(user)];
  const opener = page.getByRole("button", { name: wideNav(page) ? "Toggle navigation menu" : "Open menu", exact: true });
  const refused = await clickProblems(page, opener, "the menu button");
  if (refused.length > 0) return refused;
  const sheet = page.getByRole("dialog", { name: "Navigation" });
  await expect(sheet).toBeVisible();
  const problems = labelProblems("the menu", expected.menu, await sheet.locator("a").allInnerTexts());
  if (!(await sheet.innerText()).includes(ROLE_LABELS[user.role])) problems.push(`the menu does not name the role ${ROLE_LABELS[user.role]}`);
  if ((await page.locator('a[href^="/admin"]').count()) > 0) problems.push("an admin link is on the page for a role without admin areas");
  await page.keyboard.press("Escape");
  await expect(sheet).toBeHidden();
  return problems;
}

export async function barProblems(page: Page, user: User): Promise<string[]> {
  const expected = navExpectation(user.role);
  if (!expected) return [unexpectedRole(user)];
  await page.evaluate(() => window.scrollTo(0, 0));
  await expect(page.locator(wideNav(page) ? 'nav[aria-label="Primary"]' : 'nav[aria-label="Main"]')).toBeVisible();
  const bar = wideNav(page)
    ? await page.locator('nav[aria-label="Primary"] a').allInnerTexts()
    : await page.locator('nav[aria-label="Main"] a').evaluateAll((links) => links.map((link) => link.getAttribute("aria-label") ?? ""));
  return labelProblems("the navigation bar", expected.bar, bar);
}

export async function depthProblems(page: Page, user: User): Promise<string[]> {
  const expected = navExpectation(user.role);
  if (!expected) return [];
  const shown = await page.getByRole("group", { name: "Depth" }).getByRole("button").allInnerTexts();
  return labelProblems("the Depth choice", expected.depths, shown);
}

export function craftPageResponse(page: Page, slug: string): Promise<Response | null> {
  const path = `/api${CRAFT_PAGE_PATH(slug)}`;
  return page.waitForResponse((response) => new URL(response.url()).pathname === path, { timeout: CRAFT_PAGE_TIMEOUT_MS }).catch(() => null);
}

export async function overviewOutcome(page: Page, served: Promise<Response | null>): Promise<{ problems: string[]; note: string | null }> {
  await expect(page.getByTestId("craft-panel-overview")).toBeVisible();
  const response = await served;
  if (!response) return { problems: [`the craft page route did not answer in ${CRAFT_PAGE_TIMEOUT_MS / 1000} s`], note: null };
  if (!response.ok()) return { problems: [`the craft page route answered ${response.status()}`], note: null };
  const body = checkedCraftPage(parseShape(craftPageShape, await response.json()));
  const summary: OverviewServed = {
    curated: body.curated,
    version: body.curation?.version ?? null,
    coverage: body.curation?.coverage ?? null,
    lede: body.overview.lede.length,
    keyFacts: body.overview.keyFacts.length
  };
  const shown = {
    lede: await page.getByTestId("craft-lede").getByTestId("answer-sentence").count(),
    keyFacts: await page.getByTestId("craft-key-facts").getByTestId("craft-fact").count()
  };
  return { problems: curatedOverviewProblems(summary, shown), note: overviewNote(summary) };
}

export async function comparisonProblems(page: Page): Promise<string[]> {
  const table = page.getByTestId("comparison");
  const outcome = table.or(page.getByTestId("compare-empty")).or(page.getByTestId("compare-unknown")).or(page.getByRole("alert"));
  await expect(outcome.first()).toBeVisible({ timeout: COMPARE_TIMEOUT_MS });
  if (await table.isVisible()) return [];
  return [`the pair shows no comparison: "${clip(await outcome.first().innerText())}"`];
}

export async function openCraftTab(page: Page, label: string, panel: string, content: string): Promise<string[] | null> {
  const tab = page.getByRole("tab", { name: label, exact: true });
  if ((await tab.count()) === 0) return null;
  const refused = await clickProblems(page, tab, `the ${label} tab`);
  if (refused.length > 0) return refused;
  await expect(tab).toHaveAttribute("aria-selected", "true");
  await expect(page.getByTestId(panel)).toBeVisible();
  await expect(page.getByTestId(panel).getByTestId(content).first()).toBeVisible();
  return [];
}

async function clickProblems(page: Page, target: Locator, label: string): Promise<string[]> {
  const refused = await target.click({ timeout: CLICK_TIMEOUT_MS }).then(
    () => null,
    (error: unknown) => error
  );
  if (refused === null) return [];
  return [`${label} took no click in ${CLICK_TIMEOUT_MS / 1000} s`, ...(await clickDiagnosis(page, target, refused))];
}

async function clickDiagnosis(page: Page, target: Locator, error: unknown): Promise<string[]> {
  const log = callLog(error);
  const answers = await answersScript(page, ANSWER_TIMEOUT_MS);
  if (!answers) return [`the page ran no script for ${ANSWER_TIMEOUT_MS / 1000} s, so its main thread is stuck`, ...log];
  const before = await target.boundingBox();
  await page.waitForTimeout(STEADY_GAP_MS);
  const after = await target.boundingBox();
  const moved = JSON.stringify(before) !== JSON.stringify(after);
  const covering = await target.evaluate(coveringElement);
  return [clip(`box ${JSON.stringify(after)}${moved ? `, moved from ${JSON.stringify(before)}` : ", steady"}; at its centre: ${covering}`, 400), ...log];
}

function coveringElement(node: Element): string {
  const box = node.getBoundingClientRect();
  const hit = document.elementFromPoint(box.x + box.width / 2, box.y + box.height / 2);
  if (hit === null) return `nothing (viewport ${window.innerWidth}x${window.innerHeight})`;
  if (node.contains(hit)) return "the target itself";
  const marks = ["id", "data-testid", "aria-label", "role", "class"].map((name) => (hit.getAttribute(name) ? `${name}=${hit.getAttribute(name)}` : "")).filter(Boolean);
  return `<${hit.tagName.toLowerCase()} ${marks.join(" ")}>`;
}

function callLog(error: unknown): string[] {
  const message = error instanceof Error ? error.message : String(error);
  const lines = message.split("\n").map((line) => line.trim()).filter((line) => line.startsWith("- "));
  return lines.slice(-CALL_LOG_LINES).map((line) => clip(`call log ${line}`, 400));
}

export async function chooseFirstLayer(page: Page): Promise<{ problems: string[]; layer: string | null }> {
  const picker = page.getByTestId("layer-picker");
  if ((await picker.count()) === 0) return { problems: ["the map offers no environment layer to choose"], layer: null };
  await picker.locator("[data-searchable-select]").click();
  const option = page.getByRole("option").filter({ hasNotText: NO_LAYER_LABEL }).first();
  const layer = (await option.innerText()).trim();
  await option.click();
  await page.waitForURL(/[?&]layer=/, { timeout: LAYER_TIMEOUT_MS });
  await expect(page.getByTestId("choropleth-legend")).toBeVisible({ timeout: LAYER_TIMEOUT_MS });
  await expect(page.getByTestId("district-fills")).toBeAttached({ timeout: LAYER_TIMEOUT_MS });
  return { problems: [], layer };
}
