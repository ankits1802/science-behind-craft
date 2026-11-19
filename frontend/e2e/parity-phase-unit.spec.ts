import { expect, test } from "@playwright/test";

import { phaseMargin } from "./parity/parityPhase";

test("a gap of 31 CSS px is padded by 1 to the next multiple of 8", () => {
  expect(phaseMargin(112, 143)).toBe(1);
});

test("pages already on the same phase get no margin", () => {
  expect(phaseMargin(100, 100)).toBe(0);
  expect(phaseMargin(96, 112)).toBe(0);
});

test("a fractional gap is padded to the next multiple of 8", () => {
  expect(phaseMargin(100, 108.5)).toBe(7.5);
});
