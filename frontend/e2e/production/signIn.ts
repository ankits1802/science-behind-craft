import type { Page } from "@playwright/test";

import type { User } from "@/lib/types";

import { clip } from "./checks";
import type { Credentials } from "./run";
import { settle } from "./screenRun";

const SIGN_IN_PATH = "/api/auth/login";
const SIGN_IN_TIMEOUT_MS = 60_000;

type SignInAnswer = { user?: User; two_factor_required?: boolean; detail?: unknown };

async function fillSecretly(page: Page, label: string, value: string): Promise<void> {
  try {
    await page.getByLabel(label, { exact: true }).fill(value);
  } catch {
    throw new Error(`could not fill the ${label} field on the sign-in form`);
  }
}

export async function submitSignIn(page: Page, account: Credentials): Promise<User> {
  await fillSecretly(page, "Email", account.email);
  await fillSecretly(page, "Password", account.password);
  const answered = page.waitForResponse(
    (response) => new URL(response.url()).pathname === SIGN_IN_PATH && response.request().method() === "POST",
    { timeout: SIGN_IN_TIMEOUT_MS }
  );
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  const response = await answered;
  const body = (await response.json().catch(() => ({}))) as SignInAnswer;
  if (!response.ok()) {
    const detail = typeof body.detail === "string" ? `: ${clip(body.detail)}` : "";
    throw new Error(`sign-in answered ${response.status()}${detail}`);
  }
  if (body.two_factor_required) throw new Error("the E2E account asks for two-step verification; run provision_e2e_account again");
  if (!body.user) throw new Error("sign-in answered without the account");
  await page.waitForURL((url) => url.pathname !== "/login", { timeout: SIGN_IN_TIMEOUT_MS });
  return body.user;
}

export async function signIn(page: Page, account: Credentials): Promise<User> {
  await page.goto("/login", { waitUntil: "domcontentloaded" });
  await settle(page);
  return submitSignIn(page, account);
}
