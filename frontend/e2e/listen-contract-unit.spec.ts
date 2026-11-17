import { readFileSync } from "node:fs";
import { join } from "node:path";

import { expect, test } from "@playwright/test";

import { explainerShape } from "@/lib/explainerContract";
import { checkedScript, listenLanguagesOf, listenMark, scriptDuration, wordRanges } from "@/lib/listen";
import { parseShape, ShapeError } from "@/lib/shape";

const SHARED = join(__dirname, "..", "..", "shared");

function golden(name: string): Record<string, unknown> {
  return JSON.parse(readFileSync(join(SHARED, name), "utf8"));
}

const ANSWER_ID = "0c5e7a1d-2b3f-4c6d-8e9f-a0b1c2d3e4f5";

test("the client reads the listen script exactly as the backend writes it", () => {
  const raw = golden("listen.script.golden.json");
  const script = checkedScript(raw, ANSWER_ID, "en");
  expect(script).toEqual(raw);
  expect(script.tracks.map((track) => track.blockId)).toEqual(["s2.b1"]);
  expect(scriptDuration(script)).toBeCloseTo(14.7, 6);
});

test("every timed word is found in order in the sentence the reader sees", () => {
  const script = checkedScript(golden("listen.script.golden.json"), ANSWER_ID, "en");
  const explainer = parseShape(explainerShape, golden("explainer.document.golden.json"));
  const water = explainer.sections.flatMap((section) => section.blocks).find((block) => block.id === "s2.b1");
  if (!water || water.kind !== "prose") throw new Error("the water block is prose");
  for (const sentence of water.sentences) {
    const words = script.tracks[0].words.filter((word) => word.sentenceId === sentence.id);
    expect(words.length).toBeGreaterThan(0);
    expect(wordRanges(sentence.text, words)).not.toContain(null);
  }
});

test("the word being read is marked from the track's timings", () => {
  const script = checkedScript(golden("listen.script.golden.json"), ANSWER_ID, "en");
  expect(listenMark(script, { track: 0, time: 0.5 })).toMatchObject({ sentenceId: "s2.b1.1", wordIndex: 1 });
  expect(listenMark(script, { track: 0, time: 6.2 })?.sentenceId).toBe("s2.b1.1");
  expect(listenMark(script, { track: 0, time: 6.25 })?.sentenceId).toBe("s2.b1.2");
});

test("a script for another answer or language is refused", () => {
  const raw = golden("listen.script.golden.json");
  expect(() => checkedScript(raw, "00000000-0000-0000-0000-000000000000", "en")).toThrow(ShapeError);
  expect(() => checkedScript(raw, ANSWER_ID, "hi")).toThrow(ShapeError);
});

test("the config's listen offer gives the languages Listen speaks, or none", () => {
  expect(listenLanguagesOf({ languages: ["en", "hi", "ur"] })).toEqual(["en", "hi", "ur"]);
  expect(listenLanguagesOf({ languages: [] })).toEqual([]);
  expect(listenLanguagesOf(undefined)).toEqual([]);
});
