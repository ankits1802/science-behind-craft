import { defineConfig, devices, type Project } from "@playwright/test";

import { IPHONE, QUESTIONS_SCHEME, QUESTIONS_WIDTH, SCHEMES, SCREEN_WIDTHS, contextOptions, projectName, runLabel, type Scheme, type Width } from "./e2e/production/matrix";
import { isPreview, siteRefusal } from "./e2e/production/preview";

const BASE_URL = process.env.E2E_BASE_URL ?? "http://localhost:3000";
const LOCAL = /^https?:\/\/(localhost|127\.0\.0\.1)(:|\/|$)/.test(BASE_URL);
const SMOKE = process.env.E2E_SMOKE === "1";
const PRODUCTION = process.env.E2E_PRODUCTION === "1";

const PRODUCTION_SPECS = /[\\/]e2e[\\/]production[\\/]/;
const SCREENS_SPEC = /[\\/]e2e[\\/]production[\\/]screens\.spec\.ts$/;
const QUESTIONS_SPEC = /[\\/]e2e[\\/]production[\\/]questions\.spec\.ts$/;
const ROLES_SPEC = /[\\/]e2e[\\/]production[\\/]roles\.spec\.ts$/;

if (PRODUCTION && !process.env.E2E_BASE_URL) throw new Error("E2E_PRODUCTION=1 needs E2E_BASE_URL");
const REFUSED_SITE = PRODUCTION ? siteRefusal(BASE_URL) : null;
if (REFUSED_SITE) throw new Error(REFUSED_SITE);

const RUN_USE = {
  baseURL: BASE_URL,
  screenshot: "off",
  trace: "off",
  video: "off",
  actionTimeout: 30_000
} as const;

function productionProject(width: Width, scheme: Scheme, specs: RegExp[]): Project {
  return {
    name: projectName(width, scheme),
    testMatch: specs,
    retries: 0,
    metadata: { label: runLabel(width, scheme), scheme },
    use: { ...devices[width.device], ...contextOptions(width, scheme), ...RUN_USE }
  };
}

function specsFor(width: Width, scheme: Scheme): RegExp[] {
  return width === QUESTIONS_WIDTH && scheme === QUESTIONS_SCHEME ? [SCREENS_SPEC, QUESTIONS_SPEC, ROLES_SPEC] : [SCREENS_SPEC];
}

const PRODUCTION_PROJECTS: Project[] = [
  ...SCREEN_WIDTHS.flatMap((width) => SCHEMES.map((scheme) => productionProject(width, scheme, specsFor(width, scheme)))),
  ...(isPreview(BASE_URL) ? [productionProject(IPHONE, "light", [SCREENS_SPEC])] : [])
];

export default defineConfig({
  testDir: "./e2e",
  timeout: 60_000,
  expect: { timeout: 10_000 },
  fullyParallel: true,
  workers: Number(process.env.E2E_WORKERS ?? 2),
  retries: Number(process.env.E2E_RETRIES ?? 0),
  reporter: [["list"]],
  globalTeardown: PRODUCTION ? "./e2e/production/teardown.ts" : undefined,
  use: {
    baseURL: BASE_URL,
    screenshot: "only-on-failure",
    trace: "retain-on-failure"
  },
  projects: [
    { name: "unit", testMatch: /-unit\.spec\.ts$/, testIgnore: PRODUCTION_SPECS },
    { name: "desktop", testMatch: /smoke\.spec\.ts$/, testIgnore: PRODUCTION_SPECS, use: { ...devices["Desktop Chrome"] } },
    { name: "phone", testMatch: /smoke\.spec\.ts$/, testIgnore: PRODUCTION_SPECS, use: { ...devices["Pixel 7"] } },
    ...(PRODUCTION ? PRODUCTION_PROJECTS : [])
  ],
  webServer:
    SMOKE && LOCAL
      ? {
          command: "npm run start",
          url: BASE_URL,
          reuseExistingServer: false,
          timeout: 120_000
        }
      : undefined
});
