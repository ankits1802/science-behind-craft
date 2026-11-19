import { expect, test } from "@playwright/test";

import { defaultHint, isDefault, MODE_LABELS, ORIGIN_COPY, PROPOSAL_ORIGINS, reviewSwitchViewShape, type ReviewSwitchView } from "../lib/reviewSwitchContract";
import { parseShape, ShapeError } from "../lib/shape";

const SERVER_VIEW = {
  current: { research: "AUTO", contribution: "APPROVAL", agent: "AUTO" },
  defaults: { research: "AUTO", contribution: "APPROVAL", agent: "APPROVAL" }
};

test("the server's view of the switch is read with the owner's defaults", () => {
  const view: ReviewSwitchView = parseShape(reviewSwitchViewShape, SERVER_VIEW);
  expect(view.defaults).toEqual({ research: "AUTO", contribution: "APPROVAL", agent: "APPROVAL" });
  expect(view.current.agent).toBe("AUTO");
});

test("a mode the client does not know is refused rather than shown", () => {
  const odd = { ...SERVER_VIEW, current: { ...SERVER_VIEW.current, agent: "SOMETIMES" } };
  expect(() => parseShape(reviewSwitchViewShape, odd)).toThrow(ShapeError);
});

test("the defaults are restored only when some origin differs from them", () => {
  const view = parseShape(reviewSwitchViewShape, SERVER_VIEW);
  expect(isDefault(view)).toBe(false);
  expect(isDefault({ ...view, current: { ...view.defaults } })).toBe(true);
});

test("each origin says what it covers and names its default in words", () => {
  const view = parseShape(reviewSwitchViewShape, SERVER_VIEW);
  expect(PROPOSAL_ORIGINS.map((origin) => ORIGIN_COPY[origin].label)).toEqual(["Our research", "Contributors", "Outside agents"]);
  expect(defaultHint(view, "research")).toBe("Default: publish, review after");
  expect(defaultHint(view, "agent")).toBe("Default: approve first");
  expect(MODE_LABELS).toEqual({ AUTO: "Publish, review after", APPROVAL: "Approve first" });
});
