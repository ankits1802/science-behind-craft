import { expect, test, type Page } from "@playwright/test";

import { compareHref } from "@/lib/comparePage";
import { CRAFT_TAB_LABEL, type CraftTab } from "@/lib/craftPageView";
import { recordLoadFailure } from "@/lib/recordView";
import type { User } from "@/lib/types";

import type { Scheme } from "./matrix";
import { passPreviewProtection } from "./preview";
import {
  ALL_INDIA_CRAFT_SLUG,
  COMPARED_CRAFTS,
  CRAFT_SLUG,
  EMPTY_CRAFT_SLUG,
  NOT_FOUND_PATH,
  PRINTED_CRAFT_SLUG,
  SCREENS_TIMEOUT_MS,
  UNKNOWN_CRAFT_SLUG,
  baseUrl,
  credentials,
  previewBypassToken
} from "./run";
import { barProblems, chooseFirstLayer, comparisonProblems, craftPageResponse, depthProblems, menuProblems, openCraftTab, overviewOutcome } from "./screenChecks";
import { ScreenRun } from "./screenRun";
import { submitSignIn } from "./signIn";

const CRAFT_TABS_SHOWN: readonly [CraftTab, string][] = [
  ["process", "process-stage"],
  ["region", "craft-region-map"],
  ["science", "concept-graph"],
  ["sources", "craft-source"],
  ["evidence", "evidence-entry"]
];
const OTHER_CRAFTS: readonly [string, string][] = [
  ["Empty craft", EMPTY_CRAFT_SLUG],
  ["All India craft", ALL_INDIA_CRAFT_SLUG],
  ["Printed craft", PRINTED_CRAFT_SLUG]
];
const UNKNOWN_CRAFT_TEXT = recordLoadFailure("craft", 404);

function heading(page: Page, name: string | null): () => Promise<string[]> {
  return async () => {
    await expect(name ? page.getByRole("heading", { name, level: 1 }) : page.getByRole("heading", { level: 1 }).first()).toBeVisible();
    return [];
  };
}

async function signedOutScreens(run: ScreenRun, page: Page): Promise<void> {
  await run.visit("Landing", "/", heading(page, null));
  await run.visit("Sign up", "/signup", heading(page, "Request access"));
  await run.visit("Forgot password", "/forgot-password", heading(page, "Forgot your password?"));
  await run.visit("Privacy", "/privacy", heading(page, null));
  await run.visit("Session ended", "/session-ended", async () => {
    await expect(page.getByTestId("error-session")).toBeVisible();
    return [];
  });
  await run.visit("Login", "/login", async () => {
    await expect(page.getByRole("button", { name: "Sign in", exact: true })).toBeVisible();
    return [];
  });
}

async function craftScreens(run: ScreenRun, page: Page, slug: string, name: string): Promise<void> {
  const served = craftPageResponse(page, slug);
  await run.visit(name, `/crafts/${slug}`, async () => {
    const outcome = await overviewOutcome(page, served);
    if (outcome.note) run.note(outcome.note);
    return outcome.problems;
  });
}

async function craftTabs(run: ScreenRun, page: Page): Promise<void> {
  for (const [tab, content] of CRAFT_TABS_SHOWN) {
    await run.step(`Craft ${CRAFT_TAB_LABEL[tab]}`, async () => {
      const opened = await openCraftTab(page, CRAFT_TAB_LABEL[tab], `craft-panel-${tab}`, content);
      if (opened === null) run.note(`no ${CRAFT_TAB_LABEL[tab]} tab`);
      return opened ?? [];
    });
  }
}

async function readingScreens(run: ScreenRun, page: Page, user: User): Promise<void> {
  await run.visit("Ask", "/ask", async () => [...(await barProblems(page, user)), ...(await depthProblems(page, user))]);
  await run.visit("Crafts", "/crafts", heading(page, "Crafts"));
  await craftScreens(run, page, CRAFT_SLUG, `Craft ${CRAFT_TAB_LABEL.overview}`);
  await craftTabs(run, page);
  for (const [name, slug] of OTHER_CRAFTS) await craftScreens(run, page, slug, name);
  await run.visit(
    "Unknown craft",
    `/crafts/${UNKNOWN_CRAFT_SLUG}`,
    async () => {
      await expect(page.getByRole("alert").filter({ hasText: UNKNOWN_CRAFT_TEXT })).toBeVisible();
      return [];
    },
    { expectedResponses: [{ pathPrefix: `/api/crafts/${UNKNOWN_CRAFT_SLUG}`, status: 404 }], expectedAlert: UNKNOWN_CRAFT_TEXT }
  );
}

async function toolScreens(run: ScreenRun, page: Page): Promise<void> {
  await run.visit("Compare", "/compare", heading(page, "Compare crafts"));
  await run.visit("Compare pair", compareHref(COMPARED_CRAFTS), () => comparisonProblems(page));
  await run.visit("Saved", "/saved", heading(page, "Saved"));
  await run.visit("Map", "/map");
  await run.step("Map layer", async () => {
    const chosen = await chooseFirstLayer(page);
    if (chosen.layer) run.note(`layer: ${chosen.layer}`);
    return chosen.problems;
  });
  await run.visit("Settings", "/settings", heading(page, "Settings"));
}

test("every screen of production at this width", async ({ page }, testInfo) => {
  test.setTimeout(SCREENS_TIMEOUT_MS);
  const account = credentials();
  const metadata = testInfo.project.metadata as { label?: string; scheme?: Scheme };
  const run = new ScreenRun(page, metadata.label ?? testInfo.project.name, { scheme: metadata.scheme ?? null });
  await passPreviewProtection(page.context(), baseUrl(), previewBypassToken());
  await run.watch();
  const session: { user: User | null } = { user: null };

  await signedOutScreens(run, page);
  await run.step("Signed in", async () => {
    run.markSignedIn(null);
    session.user = await submitSignIn(page, account);
    run.markSignedIn(session.user.role);
    return [];
  });

  const signedIn = session.user;
  if (signedIn) {
    run.checkEveryScreen(() => menuProblems(page, signedIn));
    await readingScreens(run, page, signedIn);
    await toolScreens(run, page);
    run.checkEveryScreen(null);
  }
  await run.visit("Not found", NOT_FOUND_PATH, async () => {
    await expect(page.getByTestId("error-not-found")).toBeVisible();
    return [];
  }, { expectStatus: 404 });

  run.write();
  expect(signedIn, "the E2E account could not sign in, so the signed-in screens were not visited").not.toBeNull();
  expect(run.problemCount(), run.problemText()).toBe(0);
});
