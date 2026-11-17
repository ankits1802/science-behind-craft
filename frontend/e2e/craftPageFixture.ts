import { readFileSync } from "node:fs";
import { join } from "node:path";

import { createElement, type ReactElement } from "react";

import type { CitationLookup } from "@/components/answer/CitationContext";
import { CraftClaimsProvider } from "@/components/craft/CraftClaims";
import { checkedCraftPage, craftPageShape, referencedClaimIds, type CraftPage, type OverviewSection, type PageClaim, type PageEvidence } from "@/lib/craftPageContract";
import { claimIndex, pageSourceNumbers, pageSourcesById } from "@/lib/craftPageView";
import { parseShape } from "@/lib/shape";

import { withApp } from "./explainerRender";

export const CRAFT_PAGE_GOLDEN = join(__dirname, "..", "..", "shared", "craft.page.golden.json");
export const STORED_SECTION_LIMIT = 8;

export function rawPage(): CraftPage {
  return JSON.parse(readFileSync(CRAFT_PAGE_GOLDEN, "utf8")) as CraftPage;
}

export function curatedPage(edit: (body: CraftPage) => void = () => undefined): CraftPage {
  const body = rawPage();
  edit(body);
  return checkedCraftPage(parseShape(craftPageShape, body));
}

export function pageEvidence(page: CraftPage): PageEvidence {
  if (page.evidence === null) throw new Error("this page carries no evidence");
  return page.evidence;
}

export function studentPage(): CraftPage {
  return curatedPage((body) => {
    const cited = new Set(referencedClaimIds(body));
    body.evidence = null;
    body.claims = body.claims.filter((claim) => cited.has(claim.id));
    const shown = new Set(body.claims.flatMap((claim) => claim.citations.map((citation) => citation.sourceId)));
    body.sources = body.sources.filter((source) => shown.has(source.id));
  });
}

function storedSections(claims: readonly PageClaim[], titles: Map<string, string>): OverviewSection[] {
  const sections = new Map<string, OverviewSection>();
  for (const claim of claims) {
    if (claim.level === "HYPOTHESIS") continue;
    const section = sections.get(claim.discipline) ?? { discipline: claim.discipline, title: titles.get(claim.discipline) ?? claim.discipline, basis: "STORED_CLAIMS", sentences: [] };
    if (section.sentences.length < STORED_SECTION_LIMIT) section.sentences.push({ id: claim.id, text: claim.text, level: claim.level, claimIds: [claim.id], terms: [] });
    sections.set(claim.discipline, section);
  }
  return [...sections.values()];
}

export function uncuratedPage(): CraftPage {
  return curatedPage((body) => {
    const titles = new Map((body.evidence?.groups ?? []).map((group) => [group.discipline, group.title]));
    body.claims = body.claims.map((claim) => ({ ...claim, provenance: "SEED", sourcesDiffer: false }));
    body.curated = false;
    body.curation = null;
    body.overview = { lede: [], keyFacts: [], sections: storedSections(body.claims, titles) };
    body.glossary = body.glossary.map((term) => ({ ...term, meaning: null, language: null, script: null, claimIds: [] }));
    body.sourcesDiffer = [];
    body.places = [];
    body.communities = [];
    body.openQuestions = [];
    body.pictures = [];
  });
}

export function emptyPage(): CraftPage {
  return curatedPage((body) => {
    body.curated = false;
    body.curation = null;
    body.overview = { lede: [], keyFacts: [], sections: [] };
    body.sourcesDiffer = [];
    body.places = [];
    body.communities = [];
    body.process = { processId: null, stages: [], reactions: [] };
    body.glossary = [];
    body.pictures = [];
    body.openQuestions = [];
    body.evidence = { groups: [], hypotheses: [] };
    body.claims = [];
    body.sources = [];
  });
}

export function pageLookup(page: CraftPage): CitationLookup {
  return { numbers: pageSourceNumbers(page, []), sourcesById: pageSourcesById(page, []), onOpen: () => undefined };
}

export function drawn(page: CraftPage, child: ReactElement): string {
  return withApp(createElement(CraftClaimsProvider, { value: claimIndex(page) }, child), pageLookup(page));
}
