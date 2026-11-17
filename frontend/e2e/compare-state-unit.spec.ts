import { expect, test } from "@playwright/test";

import { ApiError } from "@/lib/api";
import { compareState, NOTHING_CITED, UNKNOWN_CRAFT } from "@/lib/comparePage";
import { craftComparisonShape } from "@/lib/compareContract";
import { parseShape } from "@/lib/shape";

import { readRepo } from "./phaseBFixture";
import { gapCopyFindings } from "./production/checks";

const COMPARISON = parseShape(craftComparisonShape, JSON.parse(readRepo("shared", "learning.compare.golden.json")));
const BACKEND_UNKNOWN_CRAFT = /^NOT_FOUND_DETAIL = "(.+)"$/m.exec(readRepo("backend", "app", "services", "answering.py"))?.[1];

test("an unknown craft, a comparison with nothing cited and a failed request are told apart", () => {
  expect(compareState(false, null, null)).toBe("idle");
  expect(compareState(true, null, null)).toBe("loading");
  expect(compareState(true, null, new ApiError(404, UNKNOWN_CRAFT, { detail: UNKNOWN_CRAFT }))).toBe("unknown");
  expect(compareState(true, null, new ApiError(503, "Try again later.", null))).toBe("failed");
  expect(compareState(true, null, new TypeError("network"))).toBe("failed");
  expect(compareState(true, { comparison: null }, null)).toBe("empty");
  expect(compareState(true, { comparison: COMPARISON }, null)).toBe("shown");
});

test("the compare page's own lines admit no gap and name an unknown craft as the server does", () => {
  expect(UNKNOWN_CRAFT).toBe(BACKEND_UNKNOWN_CRAFT);
  expect(NOTHING_CITED).not.toMatch(/\byet\b/i);
  expect(gapCopyFindings(`${NOTHING_CITED} ${UNKNOWN_CRAFT}`)).toEqual([]);
});
