import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { join } from "node:path";

import { expect, test } from "@playwright/test";
import { NextRequest } from "next/server";

import { GET as callbackRoute } from "@/app/login/callback/route";
import { ApiError } from "@/lib/api";
import {
  CONFIRM_RETURN_PATH,
  OIDC_TAB_LOST,
  PENDING_KEY,
  beginSignIn,
  configuredOidcProviders,
  parseCallbackFragment,
  type PendingSignIn
} from "@/lib/oidcSignIn";
import { confirmReturn, fetchFirstPasswordNonce, providerConfirmationRequired } from "@/lib/passwordChange";
import { CONFIRM_PROVIDER_HEADER, MIN_PASSWORD_LENGTH, firstPasswordBody, passwordRuleLine, setFirstPassword } from "@/lib/signIn";

const read = (...parts: string[]) => readFileSync(join(__dirname, "..", ...parts), "utf8");
const CARD = read("components", "settings", "ChangePasswordCard.tsx");
const CONFIRM = read("components", "settings", "ConfirmItsYou.tsx");
const SETTINGS = read("app", "(protected)", "settings", "page.tsx");

const SERVER_NONCE = "first-password-nonce-0123456789abcdefghijklmnop";
const WEB = "https://kalavigyan.vercel.app";
const NEW_PASSWORD = "a-first-password-of-my-own";

class MemoryStorage {
  values = new Map<string, string>();
  getItem(key: string) {
    return this.values.get(key) ?? null;
  }
  setItem(key: string, value: string) {
    this.values.set(key, value);
  }
  removeItem(key: string) {
    this.values.delete(key);
  }
}

type Sent = { url: string; method: string | undefined; body: unknown };

async function withFetch<T>(answer: unknown, run: () => Promise<T>): Promise<{ result: T; sent: Sent[] }> {
  const sent: Sent[] = [];
  const realFetch = globalThis.fetch;
  globalThis.fetch = async (input, init) => {
    sent.push({ url: String(input), method: init?.method, body: init?.body ? JSON.parse(String(init.body)) : null });
    return new Response(JSON.stringify(answer), { headers: { "content-type": "application/json" } });
  };
  try {
    return { result: await run(), sent };
  } finally {
    globalThis.fetch = realFetch;
  }
}

const digestOf = (text: string) => createHash("sha256").update(text).digest("base64url");

test("the confirmation nonce is asked of our own API, with no body for the account to name", async () => {
  const answer = { nonce: SERVER_NONCE, expiresAt: "2026-11-17T10:10:00+00:00", provider: "YAHOO", clientId: "y-id" };
  const { result, sent } = await withFetch(answer, () => fetchFirstPasswordNonce());
  expect(result).toEqual(answer);
  expect(sent).toEqual([{ url: "/api/auth/first-password/nonce", method: "POST", body: null }]);
});

test("a Yahoo confirmation leaves with the server's nonce and comes back to Settings with the proof", async () => {
  const storage = new MemoryStorage();
  const [yahoo] = configuredOidcProviders({ yahooClientId: "y-id" });
  const leaving = new URL(await beginSignIn(yahoo, WEB, { rawNonce: SERVER_NONCE, purpose: "confirm", storage }));
  const pending = JSON.parse(storage.getItem(PENDING_KEY) ?? "{}") as PendingSignIn;
  expect(leaving.searchParams.get("nonce")).toBe(digestOf(SERVER_NONCE));
  expect(leaving.searchParams.get("redirect_uri")).toBe("https://kalavigyan.vercel.app/login/callback");
  expect(pending.state.startsWith("pw.")).toBe(true);

  const back = callbackRoute(new NextRequest(`${WEB}/login/callback?code=yahoo-code&state=${pending.state}&iss=x`));
  expect(back.status).toBe(302);
  const landed = new URL(back.headers.get("location") ?? "");
  expect(landed.pathname).toBe("/settings");
  expect(CONFIRM_RETURN_PATH).toBe("/settings");
  expect(landed.hash).toBe(`#oidc=code%3Dyahoo-code%26state%3D${pending.state}`);

  const callback = parseCallbackFragment(landed.hash);
  if (!callback) throw new Error("the landing address carries no callback");
  expect(confirmReturn(callback, storage)).toEqual({
    proof: {
      oidcProvider: "YAHOO",
      oidcCode: "yahoo-code",
      oidcCodeVerifier: pending.codeVerifier,
      oidcRedirectUri: "https://kalavigyan.vercel.app/login/callback",
      oidcNonce: SERVER_NONCE
    }
  });
  expect(confirmReturn(callback, storage)).toEqual({ error: OIDC_TAB_LOST });
});

test("a cancelled confirmation says so and carries no proof", async () => {
  const storage = new MemoryStorage();
  const [yahoo] = configuredOidcProviders({ yahooClientId: "y-id" });
  await beginSignIn(yahoo, WEB, { rawNonce: SERVER_NONCE, purpose: "confirm", storage });
  const pending = JSON.parse(storage.getItem(PENDING_KEY) ?? "{}") as PendingSignIn;
  expect(confirmReturn({ code: null, state: pending.state, error: "access_denied" }, storage)).toEqual({
    error: "Yahoo sign-in was cancelled."
  });
});

test("a first password sends the Yahoo proof's five fields to change-password", async () => {
  const proof = {
    oidcProvider: "YAHOO" as const,
    oidcCode: "yahoo-code",
    oidcCodeVerifier: "v".repeat(64),
    oidcRedirectUri: "https://kalavigyan.vercel.app/login/callback",
    oidcNonce: SERVER_NONCE
  };
  const { sent } = await withFetch({ ok: true }, () => setFirstPassword(NEW_PASSWORD, proof));
  expect(sent).toEqual([
    {
      url: "/api/auth/change-password",
      method: "POST",
      body: {
        newPassword: NEW_PASSWORD,
        oidcProvider: "YAHOO",
        oidcCode: "yahoo-code",
        oidcCodeVerifier: "v".repeat(64),
        oidcRedirectUri: "https://kalavigyan.vercel.app/login/callback",
        oidcNonce: SERVER_NONCE
      }
    }
  ]);
});

test("a first password sends the Google ID token, and the two-step code only when there is one", async () => {
  const { sent } = await withFetch({ ok: true }, () => setFirstPassword(NEW_PASSWORD, { googleIdToken: "g-token" }, " 123456 "));
  expect(sent[0].body).toEqual({ newPassword: NEW_PASSWORD, googleIdToken: "g-token", twoFactorCode: "123456" });
  expect(firstPasswordBody(NEW_PASSWORD, { googleIdToken: "g-token" }, "  ")).toEqual({
    newPassword: NEW_PASSWORD,
    googleIdToken: "g-token"
  });
});

test("a refused proof names the provider to confirm with again", () => {
  const named = new Headers({ [CONFIRM_PROVIDER_HEADER]: "YAHOO" });
  expect(providerConfirmationRequired(new ApiError(400, "That Yahoo sign-in didn't match", null, named))).toBe("YAHOO");
  expect(providerConfirmationRequired(new ApiError(400, "Current password is incorrect", null))).toBeNull();
});

test("the confirm step asks the server for its nonce and never makes one up", () => {
  expect(CONFIRM).toContain("await fetchFirstPasswordNonce()");
  expect(CONFIRM).toContain('{ rawNonce: nonce, purpose: "confirm" }');
  expect(CONFIRM).toContain("useGoogleNonce(fetchGoogleConfirmNonce)");
  expect(CONFIRM).toMatch(/<GoogleSignInButton\s+clientId=\{clientId\}\s+nonce=\{nonce\}\s+disabled=\{!nonce\}/);
  expect(CONFIRM).not.toContain("randomToken(");
});

test("Settings takes the proof off the address before using it, and drops a proof a wrong code spent", () => {
  expect(SETTINGS).toContain("<ChangePasswordCard />");
  expect(CARD).toContain('import { ConfirmItsYou } from "@/components/settings/ConfirmItsYou";');
  const from = CARD.indexOf("parseCallbackFragment(window.location.hash)");
  const stripped = CARD.indexOf("window.history.replaceState", from);
  expect(from).toBeGreaterThan(-1);
  expect(stripped).toBeGreaterThan(from);
  expect(stripped).toBeLessThan(CARD.indexOf("confirmReturn(callback)", from));
  expect(CARD).toMatch(/twoFactorCodeRequired\(err\)\) \{[\s\S]*?if \(askCode\) setProof\(null\);/);
});

test("the client asks for the ten characters every password route of the API requires", () => {
  expect(MIN_PASSWORD_LENGTH).toBe(10);
  expect(passwordRuleLine()).toBe("At least 10 characters.");
});
