import { auth } from "@modelcontextprotocol/client";
import type { Page } from "@playwright/test";

import type { Credentials } from "../production/run";

import { approveInBrowser } from "./consent";
import type { HeldTokens } from "./mcpClientRules";
import { MCP_PATH } from "./mcpContract";
import { ExchangeLog, MemoryOAuthProvider, REDIRECT_URI, callbackOf } from "./mcpOAuth";
import { apiOrigin } from "./site";

export const TOKEN_FILE_SCHEMA_VERSION = 1;

export type SignedIn = { api: string; server: string; token: string; refreshToken: string; clientId: string; expiresIn: number };

export type TokenFile = {
  schemaVersion: number;
  api: string;
  server: string;
  clientId: string;
  accessToken: string;
  refreshToken: string;
  expiresAt: string;
};

export async function signIn(page: Page, account: Credentials, scope: string): Promise<SignedIn> {
  const api = apiOrigin();
  const server = new URL(MCP_PATH, api);
  const provider = new MemoryOAuthProvider(scope);
  const log = new ExchangeLog();
  const first = await auth(provider, { serverUrl: server, scope, fetchFn: log.fetch });
  if (first !== "REDIRECT" || !provider.authorizationUrl) throw new Error(`auth answered ${first}; a first sign-in redirects`);
  const { redirectTo } = await approveInBrowser(page, provider.authorizationUrl, account, REDIRECT_URI);
  const back = callbackOf(redirectTo);
  const second = await auth(provider, { serverUrl: server, authorizationCode: back.code, iss: back.iss ?? undefined, fetchFn: log.fetch });
  const tokens: HeldTokens | undefined = provider.tokens();
  const token = tokens?.access_token;
  if (second !== "AUTHORIZED" || !token) throw new Error(`the token exchange answered ${second}`);
  return {
    api,
    server: server.href,
    token,
    refreshToken: tokens?.refresh_token ?? "",
    clientId: provider.clientInformation()?.client_id ?? "",
    expiresIn: tokens?.expires_in ?? 0
  };
}

export function tokenFile(signed: SignedIn, now: Date): TokenFile {
  const missing = [signed.refreshToken ? null : "refresh token", signed.clientId ? null : "client id", signed.expiresIn > 0 ? null : "lifetime"].filter(Boolean);
  if (missing.length > 0) throw new Error(`the sign-in returned no ${missing.join(", ")}; the run cannot keep its connection`);
  return {
    schemaVersion: TOKEN_FILE_SCHEMA_VERSION,
    api: signed.api,
    server: signed.server,
    clientId: signed.clientId,
    accessToken: signed.token,
    refreshToken: signed.refreshToken,
    expiresAt: new Date(now.getTime() + signed.expiresIn * 1000).toISOString()
  };
}
