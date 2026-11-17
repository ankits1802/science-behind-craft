import { expect, test } from "@playwright/test";

import { hasRenderer } from "@/components/answer/blockRenderers";
import { BLOCK_SHAPES, BUILT_BLOCK_KINDS, explainerBlockShape, type ExplainerBlock, type TypedBlockKind } from "@/lib/explainerContract";
import { CONVERSION_BASES, type MeasureBlock } from "@/lib/explainerInsight";
import { QUIZ_BLANK, quizPrompt, type CompareBlock, type QuizBlock } from "@/lib/explainerLearning";
import { parseExplainerStreamBlock } from "@/lib/explainerStream";
import { parseShape, ShapeError } from "@/lib/shape";

import { readRepo } from "./phaseBFixture";

type Fixture = { sections: { id: string; blocks: Record<string, unknown>[] }[]; sources: { id: string }[] };

const FIXTURE = JSON.parse(readRepo("shared", "explainer.phase-d.golden.json")) as Fixture;
const PHASE_D_KINDS = ["climate_risk", "compare", "concept_graph", "market_gi", "measure", "quiz"];

function fixtureBlocks(): Record<string, unknown>[] {
  return FIXTURE.sections.flatMap((section) => section.blocks);
}

function fixtureBlock(id: string): Record<string, unknown> {
  const found = fixtureBlocks().find((block) => block.id === id);
  if (!found) throw new Error(`the phase D fixture has block ${id}`);
  return structuredClone(found);
}

function parsed<K extends TypedBlockKind>(kind: K, value: unknown) {
  return parseShape(BLOCK_SHAPES[kind], value);
}

test("every phase D fixture block parses with its kind's shape, exactly as the backend writes it", () => {
  const kinds = [...new Set(fixtureBlocks().map((block) => String(block.kind)))].sort();
  expect(kinds).toEqual(PHASE_D_KINDS);
  for (const block of fixtureBlocks()) expect(parsed(block.kind as TypedBlockKind, block)).toEqual(block);
});

test("phase D kinds are refused by the built parser and the stream until their builders join, and each has its renderer", () => {
  const built: readonly string[] = BUILT_BLOCK_KINDS;
  const frame = (sectionId: string, block: unknown) => `event: block\ndata: ${JSON.stringify({ sectionId, block })}`;
  for (const block of fixtureBlocks()) {
    const event = frame(String(block.id).split(".")[0], block);
    if (built.includes(String(block.kind))) {
      expect(parseShape(explainerBlockShape, block)).toEqual(block);
      expect(parseExplainerStreamBlock(event)?.type).toBe("block");
    } else {
      expect(() => parseShape(explainerBlockShape, block)).toThrow(ShapeError);
      expect(() => parseExplainerStreamBlock(event)).toThrow(ShapeError);
    }
    expect(hasRenderer(parsed(block.kind as TypedBlockKind, block) as unknown as ExplainerBlock)).toBe(true);
  }
});

test("compare and the concept graph are built, and a quiz is never streamed in an answer", () => {
  const built: readonly string[] = BUILT_BLOCK_KINDS;
  expect(built).toEqual(expect.arrayContaining(["compare", "concept_graph"]));
  expect(built).not.toContain("quiz");
});

test("a quiz question is its keyed sentence with the key blanked, and every option is a marked term", () => {
  const quiz = parsed("quiz", fixtureBlock("s1.b1")) as QuizBlock;
  for (const question of quiz.questions) {
    const keyed = question.options[question.answer];
    expect(question.prompt).toBe(quizPrompt(keyed.sentence.text, keyed.text));
    expect(question.prompt).toContain(QUIZ_BLANK);
    for (const option of question.options) {
      expect(option.sentence.terms).toContainEqual({ text: option.text, termKey: option.termKey });
    }
  }
  expect(quizPrompt("Kut is black.", "alum")).toBeNull();
  const block = fixtureBlock("s1.b1");
  const questions = block.questions as Record<string, unknown>[];
  expect(() => parsed("quiz", { ...block, questions: [{ ...questions[0], explanation: "x" }] })).toThrow(ShapeError);
});

test("a compare row may leave a craft's cell empty and names a stored piece only by id", () => {
  const compare = parsed("compare", fixtureBlock("s3.b1")) as CompareBlock;
  expect(compare.crafts.map((craft) => craft.slug)).toEqual(["Kutch-Ajrakh", "Bagru-Hand-Block-Print"]);
  expect(compare.rows[2].cells[0]?.pieceId).toBe("7d4e2c10-5a6b-4c7d-9e8f-0a1b2c3d4e5f");
  const block = fixtureBlock("s3.b1");
  const rows = block.rows as Record<string, unknown>[];
  const withEmpty = { ...block, rows: [{ ...rows[0], cells: [(rows[0].cells as unknown[])[0], null] }] };
  expect((parsed("compare", withEmpty) as CompareBlock).rows[0].cells[1]).toBeNull();
  expect(() => parsed("compare", { ...block, rows: [{ ...rows[0], aspect: "Mordant" }] })).toThrow(ShapeError);
});

test("a measure carries its conversion basis and the dataset row of an exact definition", () => {
  const measure = parsed("measure", fixtureBlock("s4.b1")) as MeasureBlock;
  const row = measure.rows[0];
  expect(CONVERSION_BASES).toContain(row.conversion.basis);
  expect([row.metric.low, row.metric.high, row.metric.unit]).toEqual([3.05, 4.57, "m"]);
  expect(row.conversion.dataset?.code).toBe("NIST_SP_811_2008");
  expect(row.conversion.region).toBeNull();
});

test("every citation in the fixture names a listed source", () => {
  const listed = new Set(FIXTURE.sources.map((source) => source.id));
  const cited = JSON.stringify(FIXTURE.sections).match(/"sourceId":"[0-9a-f-]{36}"/g) ?? [];
  expect(cited.length).toBeGreaterThan(0);
  for (const entry of cited) expect(listed.has(entry.slice(12, -1))).toBe(true);
});
