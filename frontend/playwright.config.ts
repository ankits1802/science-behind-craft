import { defineConfig, devices } from "@playwright/test";

const BASE_URL = process.env.E2E_BASE_URL ?? "http://localhost:3000";
const LOCAL = /^https?:\/\/(localhost|127\.0\.0\.1)(:|\/|$)/.test(BASE_URL);
const SMOKE = process.env.E2E_SMOKE === "1";

export default defineConfig({
  testDir: "./e2e",
  timeout: 60_000,
  expect: { timeout: 10_000 },
  fullyParallel: true,
  workers: Number(process.env.E2E_WORKERS ?? 2),
  retries: Number(process.env.E2E_RETRIES ?? 0),
  reporter: [["list"]],
  use: {
    baseURL: BASE_URL,
    screenshot: "only-on-failure",
    trace: "retain-on-failure"
  },
  projects: [
    { name: "unit", testMatch: /-unit\.spec\.ts$/ },
    { name: "desktop", testMatch: /smoke\.spec\.ts$/, use: { ...devices["Desktop Chrome"] } },
    { name: "phone", testMatch: /smoke\.spec\.ts$/, use: { ...devices["Pixel 7"] } }
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
