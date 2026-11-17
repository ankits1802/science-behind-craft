import { expect, test } from "@playwright/test";

import { craftComparePath, craftComparisonShape } from "@/lib/compareContract";
import { QUIZ_BLANK, quizPrompt } from "@/lib/explainerLearning";
import { answerQuizPath, explainerQuizShape } from "@/lib/quizContract";
import { parseShape, ShapeError } from "@/lib/shape";
import { SHARED_CONCEPT_PATH } from "@/lib/sharedScienceContract";

import { readRepo } from "./phaseBFixture";

type Golden = Record<string, unknown>;

function golden(name: string): Golden {
  return JSON.parse(readRepo("shared", name)) as Golden;
}

const QUIZ = golden("learning.quiz.golden.json");
const COMPARE = golden("learning.compare.golden.json");

test("an explainer's quiz parses exactly and each prompt is its keyed sentence with the key blanked", () => {
  const quiz = parseShape(explainerQuizShape, QUIZ);
  expect(quiz as unknown).toEqual(QUIZ);
  for (const question of quiz.quiz.questions) {
    const keyed = question.options[question.answer];
    expect(question.prompt).toContain(QUIZ_BLANK);
    expect(quizPrompt(keyed.sentence.text, keyed.text)).toBe(question.prompt);
  }
  expect(() => parseShape(explainerQuizShape, { ...QUIZ, schemaVersion: 2 })).toThrow(ShapeError);
});

test("a comparison parses exactly and refuses a row with one cell", () => {
  const comparison = parseShape(craftComparisonShape, COMPARE);
  expect(comparison as unknown).toEqual(COMPARE);
  expect(comparison.comparison.crafts.map((craft) => craft.slug)).toEqual(["Kutch-Ajrakh", "Bagru-Hand-Block-Print"]);
  const broken = structuredClone(COMPARE) as { comparison: { rows: { cells: unknown[] }[] } };
  broken.comparison.rows[0].cells = broken.comparison.rows[0].cells.slice(0, 1);
  expect(() => parseShape(craftComparisonShape, broken)).toThrow(ShapeError);
});

test("the quiz, compare and shared-concept routes are named once and escaped", () => {
  expect(answerQuizPath("a b")).toBe("/answers/a%20b/quiz");
  expect(answerQuizPath("a1", ["s1", "s3"])).toBe("/answers/a1/quiz?sections=s1&sections=s3");
  expect(craftComparePath(["Kutch-Ajrakh", "Bagru-Hand-Block-Print"])).toBe(
    "/compare?crafts=Kutch-Ajrakh&crafts=Bagru-Hand-Block-Print"
  );
  expect(craftComparePath(["a", "b"], ["MATERIALS"])).toBe("/compare?crafts=a&crafts=b&facets=MATERIALS");
  expect(SHARED_CONCEPT_PATH("alum")).toBe("/shared-science/alum");
  expect(SHARED_CONCEPT_PATH("alum", "Kutch-Ajrakh")).toBe("/shared-science/alum?craft=Kutch-Ajrakh");
});
