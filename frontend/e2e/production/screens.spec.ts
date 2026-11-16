import { expect, test } from "@playwright/test";

import { CRAFT_TAB_LABEL, type CraftTab } from "@/lib/craftProfile";
import type { User } from "@/lib/types";

import { CRAFT_SLUG, NOT_FOUND_PATH, SCREENS_TIMEOUT_MS, credentials } from "./run";
import { barProblems, chooseFirstLayer, menuProblems, modeProblems, openCraftTab } from "./screenChecks";
import { ScreenRun } from "./screenRun";
import { submitSignIn } from "./signIn";

const CRAFT_TABS_SHOWN: readonly CraftTab[] = ["process", "region"];

test("every screen of production at this width", async ({ page }, testInfo) => {
  test.setTimeout(SCREENS_TIMEOUT_MS);
  const account = credentials();
  const run = new ScreenRun(page, String(testInfo.project.metadata.width ?? testInfo.project.name));
  const session: { user: User | null } = { user: null };

  await run.visit("Landing", "/", async () => {
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
    return [];
  });
  await run.visit("Login", "/login", async () => {
    await expect(page.getByRole("button", { name: "Sign in", exact: true })).toBeVisible();
    return [];
  });
  await run.step("Signed in", async () => {
    run.markSignedIn(null);
    session.user = await submitSignIn(page, account);
    run.markSignedIn(session.user.role);
    return [];
  });

  const signedIn = session.user;
  if (signedIn) {
    run.checkEveryScreen(() => menuProblems(page, signedIn));
    await run.visit("Ask", "/ask", async () => [...(await barProblems(page, signedIn)), ...(await modeProblems(page, signedIn))]);
    await run.visit("Crafts", "/crafts", async () => {
      await expect(page.getByRole("heading", { name: "Crafts", level: 1 })).toBeVisible();
      return [];
    });
    await run.visit(`Craft ${CRAFT_TAB_LABEL.overview}`, `/crafts/${CRAFT_SLUG}`, async () => {
      await expect(page.getByTestId("craft-panel-overview")).toBeVisible();
      return [];
    });
    for (const tab of CRAFT_TABS_SHOWN) {
      await run.step(`Craft ${CRAFT_TAB_LABEL[tab]}`, async () => {
        if (!(await openCraftTab(page, CRAFT_TAB_LABEL[tab], `craft-panel-${tab}`))) run.note(`no ${CRAFT_TAB_LABEL[tab]} tab`);
        return [];
      });
    }
    await run.visit("Map", "/map");
    await run.step("Map layer", async () => {
      const chosen = await chooseFirstLayer(page);
      if (chosen.layer) run.note(`layer: ${chosen.layer}`);
      return chosen.problems;
    });
    await run.visit("Settings", "/settings", async () => {
      await expect(page.getByRole("heading", { name: "Settings", level: 1 })).toBeVisible();
      return [];
    });
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
