import { expect, test } from "@playwright/test";

import {
  CONTRIBUTION_STATEMENT,
  SOURCE_CRAFTS_MAX,
  closedReading,
  documentHolds,
  fieldClaims,
  freeField,
  pageKind,
  pageSlots,
  proposalArguments,
  queuedProposal,
  quoteFrom,
  readerFactProblems,
  readerProblems,
  readText,
  recordHolds,
  sourceChoices,
  sourceCrafts,
  unlistedSlugs
} from "./mcpContribution";

const STUDY = { id: "s1", url: "https://www.jeb.co.in/journal_issues/200701_jan07/paper_14.pdf", title: "Genotoxicity of textile dyes used in Sanganer", licence: null };
const JUNK = { id: "s2", url: "https://example.org/aa.pdf", title: "aa.MDI", licence: null };
const PLAIN = { id: "s3", url: "http://example.org/plain", title: "A plain web page here", licence: null };
const CLAIM = "0d7c0000-0000-4000-8000-000000000001";
const SLOT = { slug: "Agates-Of-Cambay", field: "CLIMATE" };
const HELD = ["OVERVIEW", "PROCESS", "CLIMATE", "POLICY"];

function coverage(slug: string, free: string[]): Record<string, unknown> {
  return { subjectSlug: slug, fields: HELD.map((field) => ({ field, claims: free.includes(field) ? 0 : 4 })) };
}
const SHOWN_REPLY = {
  outcome: "PUBLISHED",
  claimId: CLAIM,
  message: "Published, and approved at once because your account reviews contributions. Readers see it now at https://kalavigyan.example/crafts/Sanganeri-Hand-Block-Printing among the page's cited Policy facts.",
  readers: { shown: true, reason: null }
};

test("only https sources with a title of three words or more are tried", () => {
  expect(sourceChoices({ sources: [JUNK, PLAIN, STUDY] })).toEqual([{ url: STUDY.url, title: STUDY.title, licence: null }]);
});

test("a quote is a digit-free sentence of a closed reading, cut at a sentence end", () => {
  const reading = {
    readable: true,
    openLicence: false,
    passages: [{ text: "Table 2. Results of 12 dyes. Most textile dyes used in the hand block printing units have not been evaluated for health impact. Short one." }]
  };
  expect(readText({ text: reading, quotes: [] })).toEqual(reading);
  expect(closedReading(reading)).toBe(true);
  expect(closedReading({ ...reading, openLicence: true })).toBe(false);
  expect(quoteFrom(reading)).toBe("Most textile dyes used in the hand block printing units have not been evaluated for health impact.");
  expect(quoteFrom({ passages: [{ text: "Only 12 of 13 dyes, said in 2007." }] })).toBeNull();
});

test("a craft with a field that holds no fact is chosen, at its first free field", () => {
  const listing = { crafts: [coverage("Bagru-Hand-Block-Print", ["POLICY", "CLIMATE"]), coverage("Agates-Of-Cambay", ["CLIMATE"])] };
  expect(pageSlots(listing)).toEqual([SLOT, { slug: "Bagru-Hand-Block-Print", field: "CLIMATE" }]);
  expect(freeField(coverage("Agates-Of-Cambay", ["POLICY"]))).toBe("POLICY");
});

test("a craft whose every field holds a fact is passed over, and the choice never depends on the listing's order", () => {
  const full = coverage("Agates-Of-Cambay", []);
  expect(freeField(full)).toBeNull();
  const listing = { crafts: [coverage("Sanganeri-Hand-Block-Printing", []), full, coverage("Bidriware", ["HISTORY", "POLICY"])] };
  expect(pageSlots(listing)).toEqual([{ slug: "Bidriware", field: "POLICY" }]);
  expect(pageSlots({ crafts: [...(listing.crafts as unknown[])].reverse() })).toEqual(pageSlots(listing));
  expect(pageSlots({ crafts: [full] })).toEqual([]);
});

test("past the listed pages, the catalogue's other crafts are tried in slug order", () => {
  const listing = { crafts: [coverage("Bidriware", [])] };
  const catalogue = { crafts: [{ slug: "Tharu-Embroidery" }, { slug: "Bidriware" }, { slug: "Aipan-Art" }] };
  expect(unlistedSlugs(catalogue, listing)).toEqual(["Aipan-Art", "Tharu-Embroidery"]);
});

test("a generated page is read and a record page stands in for a craft with none, but an authored page is passed over", () => {
  expect(pageKind(200, { shell: null, content: { units: {} } })).toBe("document");
  expect(pageKind(404, { detail: "No document" })).toBe("record");
  expect(pageKind(200, { shell: "<main></main>" })).toBe("authored");
  expect(pageKind(503, null)).toBeNull();
  expect(recordHolds({ claims: [{ id: CLAIM }] }, CLAIM)).toBe(true);
  expect(recordHolds({ claims: [] }, CLAIM)).toBe(false);
});

test("the closed source is sought on the chosen craft first, then on the listed pages", () => {
  const listing = { crafts: [coverage("Bidriware", []), coverage("Agates-Of-Cambay", ["CLIMATE"]), coverage("Bagru-Hand-Block-Print", [])] };
  expect(sourceCrafts("Tharu-Embroidery", listing)).toEqual(["Tharu-Embroidery", "Agates-Of-Cambay", "Bagru-Hand-Block-Print"].slice(0, SOURCE_CRAFTS_MAX));
  expect(sourceCrafts("Bagru-Hand-Block-Print", listing)).toEqual(["Bagru-Hand-Block-Print", "Agates-Of-Cambay", "Bidriware"]);
});

test("the proposal is one test fact of the chosen craft's free field with its own key and the quote", () => {
  const body = proposalArguments(SLOT, { url: STUDY.url, title: STUDY.title, licence: null }, "a quote of forty characters or more, word for word", "1732");
  const [fact] = body.facts as Record<string, unknown>[];
  expect([fact.craft_slug, fact.field, fact.statement, fact.idempotency_key]).toEqual([SLOT.slug, SLOT.field, CONTRIBUTION_STATEMENT, "release-check:1732"]);
  expect(/\d/u.test(CONTRIBUTION_STATEMENT)).toBe(false);
  expect(queuedProposal({ items: [{ accepted: true, ticket: { proposalId: "p1" } }] })).toEqual({ id: "p1", problems: [] });
  expect(queuedProposal({ items: [{ accepted: false, problem: "terms needed" }] }).problems).toEqual(["propose_facts did not queue the fact: terms needed"]);
});

test("a published reply must say readers see the fact, and a hidden one fails the check", () => {
  expect(readerProblems(SHOWN_REPLY)).toEqual([]);
  expect(readerProblems({ ...SHOWN_REPLY, readers: { shown: false, reason: "NO_SHOWN_SOURCE" } })).toEqual([
    `the reply says readers cannot see the fact (NO_SHOWN_SOURCE): ${SHOWN_REPLY.message}`
  ]);
  expect(readerProblems({ ...SHOWN_REPLY, readers: undefined })).toEqual(["the reply does not say where readers see the fact"]);
});

test("a signed-out reader sees the fact cited by the closed page without its words, on the page and in the count", () => {
  const facts = { sources: [STUDY], facts: [{ id: CLAIM, citations: [{ sourceId: "s1", quote: null }] }] };
  const source = { url: STUDY.url, title: STUDY.title, licence: null };
  expect(readerFactProblems(facts, CLAIM, source)).toEqual([]);
  expect(readerFactProblems({ ...facts, facts: [{ id: CLAIM, citations: [{ sourceId: "s1", quote: "closed words" }] }] }, CLAIM, source)).toEqual([
    "a signed-out reader is shown the closed page's words"
  ]);
  expect(readerFactProblems({ ...facts, facts: [] }, CLAIM, source)).toEqual([`get_facts does not show fact ${CLAIM} to a signed-out reader`]);
  expect(documentHolds({ content: { units: { "fact-policy-1": { claimIds: [CLAIM] } } } }, CLAIM)).toBe(true);
  expect(documentHolds({ content: { units: {} } }, CLAIM)).toBe(false);
  expect(fieldClaims({ fields: [{ field: "POLICY", claims: 3 }] }, "POLICY")).toBe(3);
});
