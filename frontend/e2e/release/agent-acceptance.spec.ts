import { writeFileSync } from "node:fs";

import { test } from "@playwright/test";

import { roleCredentials } from "../production/run";

import { CONTRIBUTION_SCOPE } from "./mcpContribution";
import { signIn, tokenFile } from "./mcpSignIn";

const TOKEN_FILE_ENV = "ACCEPTANCE_TOKEN_FILE";
const PROFESSOR_SECRETS = "Set E2E_PROFESSOR_EMAIL, E2E_PROFESSOR_PASSWORD and E2E_PROFESSOR_TOTP_SECRET: the run signs in as a contributor";
const RUN_TIMEOUT_MS = 5 * 60_000;
const OWNER_ONLY = 0o600;

test("the Professor signs a contributor's MCP client in with the contribute scope and keeps its tokens for the run", async ({ page }) => {
  test.setTimeout(RUN_TIMEOUT_MS);
  const account = roleCredentials("PROFESSOR");
  if (!account) throw new Error(PROFESSOR_SECRETS);
  const file = process.env[TOKEN_FILE_ENV];
  if (!file) throw new Error(`Set ${TOKEN_FILE_ENV} to the file the run reads its tokens from`);
  const signed = await test.step("the Professor approves the client on the consent page", () => signIn(page, account, CONTRIBUTION_SCOPE));
  writeFileSync(file, `${JSON.stringify(tokenFile(signed, new Date()), null, 2)}\n`, { encoding: "utf8", mode: OWNER_ONLY });
});
