import type { Page } from "@playwright/test";

import { DEFERRED_ATTRIBUTE } from "../../components/monograph/kitGate";
import { REST_UNREAD } from "../../lib/monographRestRead";

export type PageReadiness = "ready" | "unread" | "waiting";

export const READY_TIMEOUT_MS = 60_000;
export const UNREAD_PROBLEM = "the rest of the page could not be read, so its later chapters are not drawn";
export const WAITING_PROBLEM = `the rest of the page was not drawn and its kit not bound within ${READY_TIMEOUT_MS / 1000} s`;

export async function pageReadiness(page: Page, timeout: number = READY_TIMEOUT_MS): Promise<PageReadiness> {
  const holder = `[${DEFERRED_ATTRIBUTE}]`;
  const drawn = await page.waitForFunction((waiting) => "KV" in window && document.querySelector(waiting) === null, holder, { timeout }).then(
    () => true,
    () => false
  );
  if (!drawn) return "waiting";
  const unread = await page.evaluate((said) => (document.body.textContent ?? "").includes(said), REST_UNREAD);
  return unread ? "unread" : "ready";
}

export function readinessProblem(readiness: PageReadiness): string | null {
  if (readiness === "unread") return UNREAD_PROBLEM;
  return readiness === "waiting" ? WAITING_PROBLEM : null;
}
