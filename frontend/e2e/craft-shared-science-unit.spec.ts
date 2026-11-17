import { expect, test } from "@playwright/test";
import { createElement } from "react";

import { CraftSharedScience } from "@/components/craft/CraftSharedScience";
import { craftTabs, CRAFT_TAB_LABEL } from "@/lib/craftPageView";
import { parseShape } from "@/lib/shape";
import { sharedScienceShape } from "@/lib/sharedScienceContract";

import { curatedPage } from "./craftPageFixture";
import { attribute, shownText, withApp } from "./explainerRender";
import { readRepo } from "./phaseBFixture";

const GOLDEN = JSON.parse(readRepo("shared", "learning.shared-science.golden.json")) as { craft: unknown };
const SCIENCE = parseShape(sharedScienceShape, GOLDEN.craft);

test("the craft page offers Shared science after Region only when the route names shared concepts", () => {
  expect(CRAFT_TAB_LABEL.science).toBe("Shared science");
  const page = curatedPage();
  expect(craftTabs(page, { sources: true, evidence: false, science: true })).toEqual(["overview", "process", "region", "science", "sources"]);
  expect(craftTabs(page, { sources: true, evidence: false, science: false })).not.toContain("science");
});

test("the Shared science tab draws the craft's concepts with every sharing craft and its numbered sources", () => {
  const html = withApp(createElement(CraftSharedScience, { science: SCIENCE }));
  expect(SCIENCE.nodes.map((node) => node.termKey)).toEqual(["alum", "indigo"]);
  expect(attribute(html, "concept-graph", "data-concept")).toEqual(["alum"]);
  const alum = SCIENCE.nodes[0];
  expect(attribute(html, "concept-list-craft", "data-focus")).toEqual(alum.crafts.map((entry) => (entry.craft.slug === SCIENCE.craft.slug ? "true" : "false")));
  for (const entry of alum.crafts) expect(html).toContain(`href="${entry.craft.path}"`);
  const listed = [...html.matchAll(/id="shared-science-source-(\d+)"/g)].map((match) => Number(match[1]));
  expect(listed).toEqual(SCIENCE.sources.map((_, index) => index + 1));
  expect(shownText(html)).toContain(alum.label);
  expect(html).toContain("min-w-0");
});
