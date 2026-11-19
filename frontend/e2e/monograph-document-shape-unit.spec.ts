import { expect, test } from "@playwright/test";

import { MONOGRAPH_DOCUMENT_PATH } from "../lib/monographDocument";
import { CATEGORY_MONOGRAPH_DOCUMENT_PATH, monographDocumentPath, parseMonographDocument } from "../lib/monographDocumentShape";
import { ShapeError } from "../lib/shape";

import { fixtureDocument, PICTURE, QUIZ } from "./monographFixture";

const json = (value: unknown): unknown => JSON.parse(JSON.stringify(value));

test("a monograph document parses as the API sends it", () => {
  const parsed = parseMonographDocument(json(fixtureDocument()));
  expect(parsed.subjectSlug).toBe("Test-Craft");
  expect(parsed.content.units.u0003.nodes[0]).toEqual({ m: "s", c: ["Test cloth is printed with a resist and dyed in ", { m: "cite", key: "t:1", g: ["g2", "g1"], c: ["indigo."] }] });
  expect(Object.keys(parsed.specs)).toEqual([QUIZ, "test-craft/overview/ask-next"]);
});

test("a component drawn both from a spec and a fragment is refused, as the backend refuses it", () => {
  const document = fixtureDocument();
  document.fragments[QUIZ] = "<div></div>";
  expect(() => parseMonographDocument(json(document))).toThrow(/a spec or a fragment, not both/);
});

test("a spec or fragment for a component the content lacks is refused", () => {
  const document = fixtureDocument();
  document.fragments["test-craft/overview/missing"] = "<div></div>";
  expect(() => parseMonographDocument(json(document))).toThrow(/a component the content lists/);
});

test("a field the contract lacks, a mark without its name and a bad slug are refused", () => {
  expect(() => parseMonographDocument({ ...json(fixtureDocument()) as object, extra: 1 })).toThrow(ShapeError);
  const unnamed = fixtureDocument();
  unnamed.content.units.u0001.nodes = [{ c: ["x"] } as never];
  expect(() => parseMonographDocument(json(unnamed))).toThrow(/a mark with m/);
  expect(() => parseMonographDocument({ ...(json(fixtureDocument()) as object), subjectSlug: "a b" })).toThrow(/a subject slug/);
  expect(() => parseMonographDocument({ ...(json(fixtureDocument()) as object), version: 0 })).toThrow(/1 or more/);
});

test("the preview reads the craft and the category document from their own API paths", () => {
  expect(monographDocumentPath("craft", "Kutch-Ajrakh")).toBe(MONOGRAPH_DOCUMENT_PATH("Kutch-Ajrakh"));
  expect(monographDocumentPath("craft", "Kutch-Ajrakh")).toBe("/crafts/Kutch-Ajrakh/monograph");
  expect(monographDocumentPath("category", "textiles")).toBe("/categories/textiles/monograph");
  expect(CATEGORY_MONOGRAPH_DOCUMENT_PATH("a/b")).toBe("/categories/a%2Fb/monograph");
  expect(fixtureDocument().fragments[PICTURE]).toContain("figure");
});
