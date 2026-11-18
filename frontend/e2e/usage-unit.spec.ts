import { expect, test } from "@playwright/test";

import { remainingLabel } from "@/lib/mediaView";
import { ceilingShare, formatUsd, monthlyCeiling, type UsageReport } from "@/lib/usage";

function report(changes: Partial<UsageReport> = {}): UsageReport {
  return {
    from: "2026-11-01T00:00:00+05:30",
    to: "2026-11-18T12:00:00+05:30",
    ceilingUsd: null,
    spentThisMonthUsd: "412.5",
    spentUsd: 412.5,
    calls: 1200,
    failures: 3,
    byTask: [],
    byProvider: [],
    byDay: [],
    ...changes
  };
}

test("with no monthly ceiling the report keeps the month's spend and claims no share of a limit", () => {
  const uncapped = report();
  expect(monthlyCeiling(uncapped)).toBeNull();
  expect(ceilingShare(uncapped)).toBeNull();
  expect(formatUsd(uncapped.spentThisMonthUsd)).toBe("$412.50");
});

test("a ceiling set again in the AI budget shows the share used", () => {
  const capped = report({ ceilingUsd: "800" });
  expect(monthlyCeiling(capped)).toBe(800);
  expect(ceilingShare(capped)).toBeCloseTo(51.5625, 6);
});

test("a kind with no daily limit shows no count of what is left", () => {
  expect(remainingLabel({ kind: "IMAGE", remainingToday: null })).toBeNull();
});
