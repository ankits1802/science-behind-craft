import { expect, test } from "@playwright/test";

test("the landing page offers sign-in and access", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1 })).toContainText("crafts");
  await expect(page.getByRole("link", { name: "Request access" }).first()).toBeVisible();
  await expect(page.getByRole("link", { name: "Sign in" }).first()).toBeVisible();
});

test("sign in has email, password and one primary action", async ({ page }) => {
  await page.goto("/login");
  await expect(page.getByRole("heading", { name: "Welcome back" })).toBeVisible();
  await expect(page.getByLabel("Email")).toBeVisible();
  await expect(page.getByLabel("Password", { exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: "Sign in" })).toBeVisible();
});

test("request access needs the privacy notice ticked", async ({ page }) => {
  await page.goto("/signup");
  await expect(page.getByRole("heading", { name: "Request access" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Request access" })).toBeDisabled();
  await page.getByLabel("I agree to the").check();
  await expect(page.getByRole("button", { name: "Request access" })).toBeEnabled();
});

test("no page scrolls sideways at phone width", async ({ page }) => {
  for (const path of ["/", "/login", "/signup"]) {
    await page.goto(path);
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
    expect(overflow, path).toBeLessThanOrEqual(1);
  }
});
