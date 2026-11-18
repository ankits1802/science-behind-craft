import { expect, test } from "@playwright/test";

import { referencedClaimIds } from "@/lib/craftPageContract";
import { ShapeError } from "@/lib/shape";

import { curatedPage, registerPage, studentPage } from "./craftPageFixture";

test("a craft with no dossier still has a complete page: family, GI status, kin and three questions", () => {
  const page = registerPage();
  expect([page.curated, page.depth.basis, page.claims.length, page.sources.length]).toEqual([false, "REGISTER", 0, 0]);
  expect([page.craft.familyLabel, page.craft.kindLabel, page.giCard.status]).toEqual(["Textiles", "Hand block printing", "GI"]);
  expect(page.suggestedQuestions).toHaveLength(3);
  expect(page.suggestedQuestions.every((question) => question.includes(page.craft.displayName))).toBe(true);
  expect([page.tabs.process, page.tabs.region, page.tabs.sources, page.tabs.evidence]).toEqual([false, true, false, false]);
  const [first] = page.sameFamily;
  expect([first.craft.slug, first.basis, first.coverage]).toEqual(["Kutch-Ajrakh", "CURATED", "FULL"]);
  expect(first.hero?.media.display).toBe("INLINE");
  expect(first.lede?.sources.map((source) => source.id)).toEqual([...new Set(first.lede?.citations.map((citation) => citation.sourceId))]);
  for (const list of [page.events, page.environment, page.sourcesDiffer, page.places, page.pictures, page.craft.localNames]) expect(Array.isArray(list)).toBe(true);
});

test("the curated page carries its GI card, dated events, environment steps and stage disagreements", () => {
  const page = curatedPage();
  expect([page.giCard.applicationNumber, page.giCard.filedOn, page.giCard.registeredOn]).toEqual(["1050", "2023-01-31", "2024-04-22"]);
  const kinds = new Set(page.events.map((event) => event.kind));
  expect([...kinds].sort()).toEqual(["GI_FILED", "GI_REGISTERED", "PRICE", "STATED", "WORKFORCE"]);
  expect(page.events.map((event) => event.start)).toEqual([...page.events.map((event) => event.start)].sort((a, b) => a - b));
  expect(page.environment[0].place?.name).toBe("Dhamadka River (Suran)");
  const keys = new Set(page.sourcesDiffer.map((row) => row.key));
  expect(page.process.stages.flatMap((stage) => stage.differ).every((key) => keys.has(key))).toBe(true);
  expect(page.pictures.filter((picture) => picture.role === "HERO")).toHaveLength(1);
  expect(page.sameFamily.every((relative) => relative.craft.slug !== page.craft.slug)).toBe(true);
});

test("a Student's page keeps every claim the GI card, events and environment cite", () => {
  const page = studentPage();
  const listed = new Set(page.claims.map((claim) => claim.id));
  const context = [...page.giCard.claimIds, ...page.events.flatMap((event) => event.claimIds), ...page.environment.flatMap((step) => step.claimIds)];
  expect(context.length).toBeGreaterThan(0);
  expect(context.every((id) => listed.has(id))).toBe(true);
  expect(new Set(referencedClaimIds(page))).toEqual(listed);
  expect(page.tabs.evidence).toBe(false);
});

test("the client refuses a page whose new parts do not agree", () => {
  expect(() => curatedPage((body) => body.pictures.forEach((picture) => (picture.role = "HERO")))).toThrow(/one hero/);
  expect(() => curatedPage((body) => (body.process.stages[0].differ = ["differ-99"]))).toThrow(ShapeError);
  expect(() => curatedPage((body) => (body.depth = { ...body.depth, coverage: null }))).toThrow(/coverage class/);
  expect(() => curatedPage((body) => (body.events[0] = { ...body.events[0], date: String(body.events[0].end + 1) }))).toThrow(/inside the event/);
  expect(() => curatedPage((body) => (body.sameFamily[0] = { ...body.sameFamily[0], craft: { ...body.craft } }))).toThrow(ShapeError);
  expect(() => curatedPage((body) => (body.sourcesDiffer[1] = { ...body.sourcesDiffer[1], key: body.sourcesDiffer[0].key }))).toThrow(/own key/);
  expect(() => curatedPage((body) => (body.sourcesDiffer[0] = { ...body.sourcesDiffer[0], weight: 4 }))).toThrow(ShapeError);
  expect(() => curatedPage((body) => (body.communities[0] = { ...body.communities[0], placeKey: "nowhere" }))).toThrow(/not nowhere/);
  expect(() => curatedPage((body) => (body.environment[0] = { ...body.environment[0], place: { key: "nowhere", name: "Nowhere" } }))).toThrow(/not nowhere/);
  expect(() => curatedPage((body) => (body.environment[0] = { ...body.environment[0], factor: "WIND" as never }))).toThrow(ShapeError);
});

test("a craft page lists no local names until a dossier states the craft's own", () => {
  expect(curatedPage().craft.localNames).toEqual([]);
  expect(registerPage().craft.localNames).toEqual([]);
});
