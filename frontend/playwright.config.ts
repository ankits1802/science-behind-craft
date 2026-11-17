import { defineConfig, devices, type Project } from "@playwright/test";

const BASE_URL = process.env.E2E_BASE_URL ?? "http://localhost:3000";
const LOCAL = /^https?:\/\/(localhost|127\.0\.0\.1)(:|\/|$)/.test(BASE_URL);
const SMOKE = process.env.E2E_SMOKE === "1";
const PRODUCTION = process.env.E2E_PRODUCTION === "1";

const PRODUCTION_SPECS = /[\\/]e2e[\\/]production[\\/]/;
const SCREENS_SPEC = /[\\/]e2e[\\/]production[\\/]screens\.spec\.ts$/;
const QUESTIONS_SPEC = /[\\/]e2e[\\/]production[\\/]questions\.spec\.ts$/;

if (PRODUCTION && !process.env.E2E_BASE_URL) throw new Error("E2E_PRODUCTION=1 needs E2E_BASE_URL");

const PRODUCTION_USE = {
  baseURL: BASE_URL,
  locale: "en-IN",
  timezoneId: "Asia/Kolkata",
  screenshot: "off",
  trace: "off",
  video: "off",
  actionTimeout: 30_000
} as const;

const PRODUCTION_PROJECTS: Project[] = [
  {
    name: "production-desktop",
    testMatch: [SCREENS_SPEC, QUESTIONS_SPEC],
    retries: 0,
    metadata: { width: "Desktop" },
    use: { ...devices["Desktop Chrome"], ...PRODUCTION_USE, viewport: { width: 1440, height: 900 }, screen: { width: 1440, height: 900 } }
  },
  {
    name: "production-tablet",
    testMatch: SCREENS_SPEC,
    retries: 0,
    metadata: { width: "Tablet" },
    use: { ...devices["Galaxy Tab S9"], ...PRODUCTION_USE, viewport: { width: 834, height: 1194 }, screen: { width: 834, height: 1194 } }
  },
  {
    name: "production-phone",
    testMatch: SCREENS_SPEC,
    retries: 0,
    metadata: { width: "Phone" },
    use: { ...devices["Pixel 7"], ...PRODUCTION_USE, viewport: { width: 390, height: 844 }, screen: { width: 390, height: 844 } }
  }
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
