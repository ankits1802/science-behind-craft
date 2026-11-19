import { readFileSync } from "node:fs";
import { join } from "node:path";

import { createElement } from "react";

import { expect, test } from "@playwright/test";

import { CraftEvidence } from "@/components/craft/CraftEvidence";
import { CraftOverview } from "@/components/craft/CraftOverview";
import { CraftCommunities, CraftPlaces } from "@/components/craft/CraftPlaces";
import { CraftReference } from "@/components/craft/CraftReference";
import { CraftRegionTab } from "@/components/craft/CraftRegionTab";
import { CraftSourcesTab } from "@/components/craft/CraftSourcesTab";
import { ProcessTimeline } from "@/components/craft/ProcessTimeline";
import type { CraftPage, PageReaction } from "@/lib/craftPageContract";
import { pageSourceNumbers, sourceGroups } from "@/lib/craftPageView";
import { craftRegionShape } from "@/lib/regionContract";
import { checkedRegion } from "@/lib/regionView";
import { parseShape } from "@/lib/shape";

import { curatedPage, drawn, emptyPage, pageEvidence, uncuratedPage } from "./craftPageFixture";
import { attribute, FIXED_WIDE_WIDTH, gridTracks, shownText, withApp } from "./explainerRender";
import { gapCopyFindings } from "./production/checks";

const count = (html: string, testId: string) => html.split(`data-testid="${testId}"`).length - 1;
const text = (html: string) => shownText(html.replace(/<!-- -->/g, "").replace(/<[^>]+>/g, " ")).replace(/\s+/g, " ");

function overview(page: CraftPage): string {
  return drawn(page, createElement(CraftOverview, { page }));
}

function process(page: CraftPage): string {
  return drawn(page, createElement(ProcessTimeline, { process: page.process, pictures: page.pictures }));
}

function layoutProblems(html: string): string[] {
  const grids = [...html.matchAll(/grid-cols-\[([^\]]+)\]/g)].map((found) => found[1]);
  const fixed = grids.filter((tracks) => !tracks.split("_").includes("minmax(0,1fr)"));
  return [...fixed.map((tracks) => `grid-cols-[${tracks}]`), ...(FIXED_WIDE_WIDTH.test(html) ? ["a fixed wide width"] : [])];
}

function tabLabels(html: string): string[] {
  return [...html.matchAll(/role="tab"[^>]*>(.*?)<\/button>/g)].map((found) => text(found[1]).trim());
}

function reference(page: CraftPage, requested: string): string {
  return withApp(createElement(CraftReference, { page, requested, onTab: () => undefined, voice: null }));
}

test("the page offers the tabs its response fills, and a tab it does not offer falls back to Overview", () => {
  const page = curatedPage();
  const reader = reference(page, "profile");
  expect(tabLabels(reader)).toEqual(["Overview", "Process", "Region", "Sources", "All evidence"]);
  expect(count(reader, "craft-panel-overview")).toBe(1);
  const steps = reference(page, "process");
  expect(count(steps, "craft-panel-process")).toBe(1);
  expect(count(steps, "process-stage")).toBe(14);
  const bare = reference(emptyPage(), "process");
  expect(tabLabels(bare)).toEqual(["Overview", "Region"]);
  expect(count(bare, "craft-register")).toBe(1);
});

test("a curated overview shows its lede, key facts with citations, pictures with credits, sections and tappable terms", () => {
  const page = curatedPage();
  const html = overview(page);
  expect(count(html, "craft-lede")).toBe(1);
  expect(count(html, "craft-key-facts")).toBe(1);
  expect(count(html, "craft-fact")).toBe(8);
  expect(count(html, "craft-section")).toBe(7);
  expect(attribute(html, "craft-section", "data-basis")).toEqual(Array(7).fill("CURATED"));
  expect(count(html, "answer-sentence")).toBe(3 + 38);
  expect(count(html, "term-span")).toBe(13 + 17);
  expect(count(html, "craft-picture")).toBe(10 - 1);
  expect(html).toContain("Visdaviva");
  expect(html).toContain('href="https://creativecommons.org/licenses/by-sa/3.0/"');
  expect(html).toContain('href="https://commons.wikimedia.org/wiki/File:Ajrak_Craft_artisan.jpeg"');
  expect(text(html)).toContain("Registered geographical indication, application 1050, certificate dated 22 April 2024");
  expect(count(html, "craft-register")).toBe(0);
});

test("every overview fact, sentence and side of a disagreement carries a citation chip", () => {
  const html = overview(curatedPage());
  for (const block of html.split('data-testid="craft-fact"').slice(1)) expect(block.split("</div>")[0]).toContain('data-testid="citation-chip"');
  for (const sentence of html.split('data-testid="answer-sentence"').slice(1)) expect(sentence.split('data-testid="answer-sentence"')[0]).toContain('data-testid="citation-chip"');
  expect(count(html, "craft-differ-row")).toBe(14);
  const rows = html.split('data-testid="craft-differ-row"').slice(1).map((row) => row.split("</li></ul>")[0]);
  const stages = rows.find((row) => text(row).includes("How many stages the ajrakh process has")) ?? "";
  expect(stages.split("<li ").length - 1).toBe(3);
  expect(stages.split('data-testid="citation-chip"').length - 1).toBeGreaterThanOrEqual(3);
});

test("open questions show their hypotheses with chips, and what would settle them", () => {
  const html = overview(curatedPage());
  expect(count(html, "craft-open-question")).toBe(4);
  expect(text(html)).toContain("Where does the word ajrakh come from?");
  expect(text(html)).toContain("Would settle it: Mongabay reports");
  expect(count(html, "craft-term")).toBe(17);
});

test("a thin dossier shows what was searched; a full one does not", () => {
  expect(count(overview(curatedPage()), "craft-searched")).toBe(0);
  const thin = curatedPage((body) => {
    if (body.curation) body.curation.coverage = "THIN";
  });
  const html = overview(thin);
  expect(count(html, "craft-searched")).toBe(1);
  expect(text(html)).toContain("Kutch Ajrakh GI journal 188 application 1050");
});

test("an uncurated craft draws its stored sections and the register, with no gap copy", () => {
  const page = uncuratedPage();
  const html = overview(page);
  expect(count(html, "craft-lede")).toBe(0);
  expect(count(html, "craft-register")).toBe(1);
  expect(attribute(html, "craft-section", "data-basis").every((basis) => basis === "STORED_CLAIMS")).toBe(true);
  expect(count(html, "craft-section")).toBe(page.overview.sections.length);
  expect(count(html, "craft-term")).toBe(17);
  expect(html).not.toContain("Would settle it");
  expect(gapCopyFindings(text(html))).toEqual([]);
  expect(text(html)).not.toMatch(/curated|dossier|no source/i);
});

test("a craft with nothing stored draws the register alone, cleanly", () => {
  const html = overview(emptyPage());
  expect(count(html, "craft-register")).toBe(1);
  expect(count(html, "craft-section")).toBe(0);
  expect(text(html)).toContain("Hand Block Printing");
  expect(gapCopyFindings(text(html))).toEqual([]);
  expect(text(html)).not.toMatch(/curated|dossier|no source|nothing/i);
});

test("the process numbers ordered stages and lists the unordered apart, with materials, tools, timing and chemistry", () => {
  const html = process(curatedPage());
  expect(count(html, "process-stage")).toBe(14);
  expect(attribute(html, "process-stage", "data-ordered")).toEqual([...Array(11).fill("true"), ...Array(3).fill("false")]);
  expect(count(html, "process-unordered")).toBe(1);
  expect(text(html).match(/Step \d+: /g)).toEqual(Array.from({ length: 11 }, (_, index) => `Step ${index + 1}: `));
  expect(count(html, "process-tool")).toBe(3);
  expect(count(html, "process-timing")).toBe(3);
  expect(text(html)).toContain("at least three days");
  expect(count(html, "process-reaction")).toBe(2);
  expect(attribute(html, "process-reaction", "data-balanced")).toEqual(["false", "false"]);
  expect(html).not.toContain('role="math"');
  expect(text(html)).not.toMatch(/\b(Image|Video|Generate|Research)\b/);
});

test("a balanced reaction draws its equation; process-level reactions follow the stages", () => {
  const balanced: PageReaction = {
    id: null,
    kind: "PRECIPITATION",
    label: "iron + tannin → iron tannate",
    species: [
      { role: "REACTANT", name: "Iron(II) sulfate", formula: "FeSO4", coefficient: 1 },
      { role: "PRODUCT", name: "Iron(II) ion", formula: "Fe^2+", coefficient: 1 }
    ],
    balanced: true,
    equation: "FeSO4 -> Fe^2+ + SO4^2-",
    claimIds: ["76c28e36-98a9-52a3-b09f-80250bab237c"]
  };
  const page = curatedPage((body) => (body.process.reactions = [balanced]));
  const html = process(page);
  expect(count(html, "process-reactions")).toBe(1);
  expect(html).toContain('role="math"');
  expect(text(html)).toContain("Iron(II) sulfate → Iron(II) ion");
});

test("places show their roles at village or district level, and people their places and honours", () => {
  const page = curatedPage();
  const html = drawn(page, createElement("div", null, createElement(CraftPlaces, { places: page.places }), createElement(CraftCommunities, { communities: page.communities })));
  expect(count(html, "craft-place")).toBe(7);
  expect(text(html)).toContain("Village · Kachchh district, Gujarat");
  expect(text(html)).toContain("Historic centre");
  expect(text(html)).toContain("Material source");
  expect(count(html, "craft-community")).toBe(8);
  expect(text(html)).toContain("National Award (1981)");
  expect(text(html)).toContain("Person · Dhamadka");
});

test("the Region tab draws the map, the places, the people and the district environment", () => {
  const page = curatedPage();
  const body = JSON.parse(readFileSync(join(__dirname, "..", "..", "shared", "region.craft.golden.json"), "utf8"));
  const region = checkedRegion(parseShape(craftRegionShape, body));
  const html = drawn(page, createElement(CraftRegionTab, { page, region: { data: region, failure: null, retry: () => undefined } }));
  expect(count(html, "craft-region-map")).toBe(1);
  expect(count(html, "craft-place")).toBe(7);
  expect(count(html, "craft-community")).toBe(8);
  expect(count(html, "region-place")).toBe(region.places.length);
  expect(text(html)).toContain("Land, water and climate");
  expect(layoutProblems(html)).toEqual([]);
});

test("sources list under their reliability grade with their numbers", () => {
  const page = curatedPage();
  const numbers = pageSourceNumbers(page, []);
  const html = drawn(page, createElement(CraftSourcesTab, { groups: sourceGroups(page.sources, numbers), numbers }));
  expect(attribute(html, "craft-source-group", "data-reliability")).toEqual(["A", "B", "C", "D"]);
  expect(count(html, "craft-source")).toBe(24 + 5 + 7);
  expect(text(html)).toContain("A · peer-reviewed or official 21 sources");
  expect(text(html)).toContain("[1] Geographical Indications Journal No. 188");
});

test("All evidence lists every claim once by discipline and subject, hypotheses apart, each tagged with where it came from", () => {
  const page = curatedPage();
  const html = drawn(page, createElement(CraftEvidence, { evidence: pageEvidence(page) }));
  expect(count(html, "evidence-claim")).toBe(143 + 4);
  expect(count(html, "evidence-group")).toBe(11);
  expect(count(html, "evidence-hypotheses")).toBe(1);
  expect(attribute(html, "evidence-provenance", "data-testid")).toHaveLength(143 + 4);
  expect(html.split('data-testid="evidence-hypotheses"')[1].split('data-testid="evidence-claim"').length - 1).toBe(5);
  const seed = uncuratedPage();
  expect(text(drawn(seed, createElement(CraftEvidence, { evidence: pageEvidence(seed) })))).toContain("Seed");
});

test("near-duplicates fold under the strongest claim", () => {
  const page = curatedPage((body) => {
    const subject = pageEvidence(body).groups[0].subjects[0];
    const [kept, folded] = subject.entries;
    subject.entries = [{ claimId: kept.claimId, foldedIds: [folded.claimId] }, ...subject.entries.slice(2)];
  });
  const html = drawn(page, createElement(CraftEvidence, { evidence: pageEvidence(page) }));
  expect(count(html, "evidence-folded")).toBe(1);
  expect(text(html)).toContain("1 similar claim");
  expect(count(html, "evidence-claim")).toBe(143 + 4);
});

test("no grid on the craft page can widen a phone page", () => {
  const page = curatedPage();
  const numbers = pageSourceNumbers(page, []);
  const html = [
    overview(page),
    process(page),
    drawn(page, createElement(CraftPlaces, { places: page.places })),
    drawn(page, createElement(CraftCommunities, { communities: page.communities })),
    drawn(page, createElement(CraftSourcesTab, { groups: sourceGroups(page.sources, numbers), numbers })),
    drawn(page, createElement(CraftEvidence, { evidence: pageEvidence(page) }))
  ].join("");
  expect(gridTracks(html).length).toBeGreaterThan(0);
  expect(layoutProblems(html)).toEqual([]);
  expect(html.match(/class="[^"]*\bmin-w-0\b/g)?.length ?? 0).toBeGreaterThan(20);
});
