import { expect, test } from "@playwright/test";

import type { Scheme } from "./matrix";
import { passPreviewProtection, roleSiteRefusal } from "./preview";
import { ROLE_SCREENS_TIMEOUT_MS, baseUrl, previewBypassToken, roleCredentials, type RoleAccount } from "./run";
import { ScreenRun } from "./screenRun";
import { submitSignIn } from "./signIn";

type RoleScreen = { account: RoleAccount; label: string; name: string; path: string; heading: string };

const ROLE_SCREENS: readonly RoleScreen[] = [
  { account: "PROFESSOR", label: "Professor", name: "Lessons", path: "/lessons", heading: "Lessons" },
  { account: "ADMIN", label: "Admin", name: "Settings hub", path: "/admin", heading: "Settings hub" }
];

for (const screen of ROLE_SCREENS) {
  test(`the ${screen.label} account sees ${screen.path}`, async ({ page }, testInfo) => {
    const refusal = roleSiteRefusal(baseUrl());
    test.skip(refusal !== null, refusal ?? "");
    const account = roleCredentials(screen.account);
    const prefix = `E2E_${screen.account}`;
    test.skip(account === null, `Set ${prefix}_EMAIL, ${prefix}_PASSWORD and ${prefix}_TOTP_SECRET to visit ${screen.path}.`);
    if (!account) return;
    test.setTimeout(ROLE_SCREENS_TIMEOUT_MS);
    const metadata = testInfo.project.metadata as { label?: string; scheme?: Scheme };
    const run = new ScreenRun(page, `${metadata.label ?? testInfo.project.name} ${screen.label}`, { scheme: metadata.scheme ?? null });
    await passPreviewProtection(page.context(), baseUrl(), previewBypassToken());
    await run.watch();
    await run.visit("Login", "/login");
    await run.step("Signed in", async () => {
      run.markSignedIn(null);
      const user = await submitSignIn(page, account);
      run.markSignedIn(user.role);
      return user.role === screen.account ? [] : [`the ${screen.label} E2E account is ${user.role}`];
    });
    await run.visit(screen.name, screen.path, async () => {
      await expect(page.getByRole("heading", { name: screen.heading, level: 1 })).toBeVisible();
      return [];
    });
    run.write();
    expect(run.problemCount(), run.problemText()).toBe(0);
  });
}
