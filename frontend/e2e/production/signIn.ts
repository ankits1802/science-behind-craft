import type { Page } from "@playwright/test";

import type { User } from "@/lib/types";

import { settle } from "./capture";
import { clip } from "./checks";
import type { Credentials } from "./run";
import { totpCode } from "./twoStep";

const SIGN_IN_PATH = "/api/auth/login";
const TWO_STEP_PATH = "/api/auth/two-factor/verify";
const TWO_STEP_CODE = "6-digit code";
const SIGN_IN_TIMEOUT_MS = 60_000;

type SignInAnswer = { user?: User; two_factor_required?: boolean; detail?: unknown };

async function fillSecretly(page: Page, label: string, value: string): Promise<void> {
  try {
    await page.getByLabel(label, { exact: true }).fill(value);
  } catch {
    throw new Error(`could not fill the ${label} field on the sign-in form`);
  }
}

async function answerOf(page: Page, path: string, submit: () => Promise<void>): Promise<SignInAnswer> {
  const answered = page.waitForResponse((response) => new URL(response.url()).pathname === path && response.request().method() === "POST", {
    timeout: SIGN_IN_TIMEOUT_MS
  });
  await submit();
  const response = await answered;
  const body = (await response.json().catch(() => ({}))) as SignInAnswer;
  if (response.ok()) return body;
  const detail = typeof body.detail === "string" ? `: ${clip(body.detail)}` : "";
  throw new Error(`${path === SIGN_IN_PATH ? "sign-in" : "two-step verification"} answered ${response.status()}${detail}`);
}

async function passTwoStep(page: Page, totpSecret: string | undefined): Promise<SignInAnswer> {
  if (!totpSecret) throw new Error("the E2E account asks for two-step verification; run provision_e2e_account again");
  return answerOf(page, TWO_STEP_PATH, async () => {
    await page.getByRole("group", { name: TWO_STEP_CODE }).getByRole("textbox").first().click();
    await page.keyboard.type(totpCode(totpSecret, Date.now()));
  });
}

export async function submitSignIn(page: Page, account: Credentials): Promise<User> {
  await fillSecretly(page, "Email", account.email);
  await fillSecretly(page, "Password", account.password);
  const first = await answerOf(page, SIGN_IN_PATH, () => page.getByRole("button", { name: "Sign in", exact: true }).click());
  const body = first.two_factor_required ? await passTwoStep(page, account.totpSecret) : first;
  if (!body.user) throw new Error("sign-in answered without the account");
  await page.waitForURL((url) => url.pathname !== "/login", { timeout: SIGN_IN_TIMEOUT_MS });
  return body.user;
}

export async function signIn(page: Page, account: Credentials): Promise<User> {
  await page.goto("/login", { waitUntil: "domcontentloaded" });
  await settle(page);
  return submitSignIn(page, account);
}
