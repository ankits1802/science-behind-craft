import { readFileSync } from "node:fs";
import { join } from "node:path";

import { expect, test } from "@playwright/test";

import { tokenFile, type SignedIn } from "./mcpSignIn";

const GOLDEN = JSON.parse(readFileSync(join(__dirname, "..", "..", "..", "shared", "agent-acceptance.token.golden.json"), "utf8")) as unknown;
const SIGNED: SignedIn = {
  api: "https://api.example",
  server: "https://api.example/api/mcp",
  token: "kvmcp_at_golden-not-a-token",
  refreshToken: "kvmcp_rt_golden-not-a-token",
  clientId: "0b7f6f0e-3c1a-4c55-9a43-0f2b6a1e9d11",
  expiresIn: 3600
};
const SIGNED_AT = new Date("2026-11-26T10:00:00.000Z");

test("the token file the run reads is the sign-in's tokens with the hour they expire", () => {
  expect(tokenFile(SIGNED, SIGNED_AT)).toEqual(GOLDEN);
});

test("a sign-in without a refresh token, a client id or a lifetime cannot keep the run's connection", () => {
  expect(() => tokenFile({ ...SIGNED, refreshToken: "" }, SIGNED_AT)).toThrow(/returned no refresh token/);
  expect(() => tokenFile({ ...SIGNED, clientId: "" }, SIGNED_AT)).toThrow(/returned no client id/);
  expect(() => tokenFile({ ...SIGNED, expiresIn: 0 }, SIGNED_AT)).toThrow(/returned no lifetime/);
});
