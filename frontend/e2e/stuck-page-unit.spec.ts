import { expect, test } from "@playwright/test";

import { answersScript, stuckStack, watchScript } from "./production/stuckPage";

test("a page whose script never yields is caught, and its stack names the function that spins", async ({ page }) => {
  await page.setContent('<button type="button" onclick="setTimeout(function spinForever() { for (;;) {} }, 0)">Spin</button>');
  const watcher = await watchScript(page);
  expect(await answersScript(page, 2_000)).toBe(true);
  await page.getByRole("button", { name: "Spin" }).click();
  await new Promise((resolve) => setTimeout(resolve, 300));
  expect(await answersScript(page, 2_000)).toBe(false);
  const stack = await stuckStack(watcher);
  expect(stack[0]).toContain("stuck in spinForever");
  await page.close({ runBeforeUnload: false });
});
