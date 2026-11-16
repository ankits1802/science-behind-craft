import { expect, type Page } from "@playwright/test";

import { MODE_LABEL } from "@/lib/askConfig";
import { ROLE_LABELS } from "@/lib/permissions";
import type { User } from "@/lib/types";

import { DESKTOP_NAV_MIN_WIDTH, NO_LAYER_LABEL, labelProblems, navExpectation } from "./checks";

const LAYER_TIMEOUT_MS = 30_000;

function wideNav(page: Page): boolean {
  return (page.viewportSize()?.width ?? 0) >= DESKTOP_NAV_MIN_WIDTH;
}

function unexpectedRole(user: User): string {
  return `the E2E account is ${user.role}; it must be STUDENT or RESEARCHER, the roles without two-step`;
}

export async function menuProblems(page: Page, user: User): Promise<string[]> {
  const expected = navExpectation(user.role);
  if (!expected) return [unexpectedRole(user)];
  await page.getByRole("button", { name: wideNav(page) ? "Toggle navigation menu" : "Open menu", exact: true }).click();
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

export async function modeProblems(page: Page, user: User): Promise<string[]> {
  const expected = navExpectation(user.role);
  if (!expected) return [];
  const shown = await page.getByRole("group", { name: "Mode" }).getByRole("button").allInnerTexts();
  return labelProblems("the Mode choice", expected.modes.map((mode) => MODE_LABEL[mode]), shown);
}

export async function openCraftTab(page: Page, label: string, panel: string): Promise<boolean> {
  const tab = page.getByRole("tab", { name: label, exact: true });
  if ((await tab.count()) === 0) return false;
  await tab.click();
  await expect(tab).toHaveAttribute("aria-selected", "true");
  await expect(page.getByTestId(panel)).toBeVisible();
  return true;
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
