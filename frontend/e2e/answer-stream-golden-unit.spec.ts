import { readFileSync } from "node:fs";
import { join } from "node:path";

import { expect, test } from "@playwright/test";

import { emptyAnswer, parseSseBlock, reduceAnswer, splitSseBuffer, type AnswerEvent, type AnswerState } from "@/lib/answerStream";

const SHARED = join(__dirname, "..", "..", "shared");

function eventsOf(name: string): AnswerEvent[] {
  const { blocks, rest } = splitSseBuffer(readFileSync(join(SHARED, name), "utf8"));
  expect(rest).toBe("");
  return blocks.map(parseSseBlock).filter((event): event is AnswerEvent => event !== null);
}

function reduced(name: string): AnswerState {
  return eventsOf(name).reduce(reduceAnswer, emptyAnswer("Why alum?", "HYBRID"));
}

test("the contract golden stream parses, skipping only the heartbeat", () => {
  expect(eventsOf("answer-stream.golden.sse").map((event) => event.type)).toEqual([
    "match",
    "status",
    "source",
    "section",
    "sentence",
    "open_question",
    "reaction",
    "follow_ups",
    "done"
  ]);
});

test("the contract golden stream reduces to a cited answer", () => {
  const state = reduced("answer-stream.golden.sse");
  expect(state.phase).toBe("done");
  expect(state.status).toBeNull();
  expect(state.payload.craft).toEqual({ slug: "Kutch-Ajrakh", name: "Kutch Ajrakh", path: "/crafts/Kutch-Ajrakh" });
  expect(state.payload.sources.map((source) => source.id)).toEqual(["5b0c7d2e-8a51-4f3e-9d6a-0c2f1e4b7a10"]);
  expect(state.payload.sections).toHaveLength(1);
  expect(state.payload.sections[0].sentences[0].citations[0].quote).toBe("alum forms a red lake with alizarin at about 60 °C");
  expect(state.payload.openQuestions[0].heading).toBe("Open questions");
  expect(state.payload.reactions[0].balanced).toBe(true);
  expect(state.payload.followUps).toEqual(["What happens at each step of Kutch Ajrakh?"]);
});

test("the backend's researched stream shows each step, then the cited answer", () => {
  const events = eventsOf("answer-stream.research.golden.sse");
  const steps = events.flatMap((event) => (event.type === "status" ? [event.data.step] : []));
  expect(steps).toEqual(["RESOLVING", "PLANNING", "SEARCHING_STORED", "RESEARCHING", "READING", "COMPOSING", "WRITING_BACK"]);
  const writing = events.slice(0, events.findIndex((event) => event.type === "source")).reduce(reduceAnswer, emptyAnswer("Why alum?", "HYBRID"));
  expect(writing.phase).toBe("streaming");
  expect(writing.status).toEqual({ step: "WRITING_BACK", message: "Saving 3 sources for the next question" });
  const state = reduced("answer-stream.research.golden.sse");
  expect(state.phase).toBe("done");
  expect(state.status).toBeNull();
  expect(state.payload.answerId).toBe("0b1c2d3e-4f50-4617-8293-a4b5c6d7e8f9");
  expect(state.payload.sections.map((section) => [section.heading, section.sentences.map((sentence) => sentence.id)])).toEqual([
    ["Mordant", ["s1.1", "s1.2"]],
    ["Fastness", ["s2.1"]]
  ]);
  expect(state.payload.sources.map((source) => source.kind)).toEqual(["BOOK", "PAPER", "WEB_PAGE"]);
  expect(state.payload.sections[0].sentences[1].citations[0].sourceId).toBe(state.payload.sources[1].id);
  expect(state.payload.openQuestions[0].sentences[0].citations[0].evidence).toBe("INFERRED");
  expect(state.payload.followUps).toEqual(["How is the alum bath prepared for Kutch Ajrakh?"]);
});

test("the backend's not-enough-evidence stream settles on the empty state with what was searched", () => {
  const state = reduced("answer-stream.not-enough.golden.sse");
  expect(state.phase).toBe("empty");
  expect(state.error).toBeNull();
  expect(state.status).toBeNull();
  expect(state.notice).toContain('T3 "Kutch Ajrakh alum mordant"');
  expect(state.payload.sections).toEqual([]);
});
