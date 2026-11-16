import { expect, test } from "@playwright/test";

import { emptyAnswer, parseSseBlock, reduceAnswer, splitSseBuffer, type AnswerEvent } from "@/lib/answerStream";
import type { AnswerSentence, Citation } from "@/lib/types";

const citation: Citation = {
  id: "c1",
  claimId: "claim-1",
  sourceId: "s1",
  quote: "alum forms a lake with alizarin",
  locator: "p. 12",
  context: "In practice alum forms a lake with alizarin on the fibre.",
  evidence: "QUOTED",
  level: "PROVISIONAL"
};

const sentence = (id: string, citations: Citation[] = [citation]): AnswerSentence => ({
  id,
  text: `Sentence ${id}.`,
  level: "PROVISIONAL",
  citations
});

test("an SSE block parses into a typed event", () => {
  const event = parseSseBlock('event: section\ndata: {"id":"a","heading":"Mordant"}');
  expect(event).toEqual({ type: "section", data: { id: "a", heading: "Mordant" } });
});

test("unknown events, comments and broken JSON are ignored", () => {
  expect(parseSseBlock(": keep-alive")).toBeNull();
  expect(parseSseBlock("event: ping\ndata: {}")).toBeNull();
  expect(parseSseBlock("event: section\ndata: {not json")).toBeNull();
});

test("multi-line data is joined before parsing", () => {
  const event = parseSseBlock('event: follow_ups\ndata: {"items":\ndata: ["Why?"]}');
  expect(event).toEqual({ type: "follow_ups", data: { items: ["Why?"] } });
});

test("the buffer splitter keeps an unfinished block for the next chunk", () => {
  const { blocks, rest } = splitSseBuffer('event: done\r\ndata: {"answerId":"x"}\r\n\r\nevent: sec');
  expect(blocks).toEqual(['event: done\ndata: {"answerId":"x"}']);
  expect(rest).toBe("event: sec");
});

test("a sentence without a citation is never shown", () => {
  let state = emptyAnswer("q");
  state = reduceAnswer(state, { type: "section", data: { id: "a", heading: "Mordant" } });
  state = reduceAnswer(state, { type: "sentence", data: { sectionId: "a", sentence: sentence("1", []) } });
  state = reduceAnswer(state, { type: "sentence", data: { sectionId: "a", sentence: sentence("2") } });
  expect(state.payload.sections[0].sentences.map((row) => row.id)).toEqual(["2"]);
});

test("an ambiguous match stops the answer and keeps the candidates", () => {
  const event: AnswerEvent = {
    type: "match",
    data: { status: "AMBIGUOUS", candidates: [{ slug: "ajrakh", name: "Ajrakh" }, { slug: "bagru", name: "Bagru" }] }
  };
  const state = reduceAnswer(emptyAnswer("q"), event);
  expect(state.phase).toBe("ambiguous");
  expect(reduceAnswer(state, { type: "done", data: { answerId: null } }).phase).toBe("ambiguous");
});

test("the closing done keeps the server's answer id and a failure stays a failure", () => {
  let state = reduceAnswer(emptyAnswer("q"), { type: "done", data: { answerId: "ans-1" } });
  state = reduceAnswer(state, { type: "done", data: { answerId: null } });
  expect(state.payload.answerId).toBe("ans-1");
  const failed = reduceAnswer(emptyAnswer("q"), { type: "error", data: { message: "Budget reached." } });
  expect(reduceAnswer(failed, { type: "done", data: { answerId: null } }).phase).toBe("failed");
});

test("hypotheses land in open questions, not in the answer body", () => {
  const state = reduceAnswer(emptyAnswer("q"), {
    type: "open_question",
    data: { sectionId: "open", sentence: { ...sentence("h"), level: "HYPOTHESIS", citations: [{ ...citation, evidence: "INFERRED", level: "HYPOTHESIS" }] } }
  });
  expect(state.payload.sections).toHaveLength(0);
  expect(state.payload.openQuestions[0].sentences[0].id).toBe("h");
});

test("a status step is shown while the answer is being researched and cleared when it settles", () => {
  let state = reduceAnswer({ ...emptyAnswer("q"), phase: "matching" }, { type: "status", data: { step: "RESOLVING", message: "Finding the craft" } });
  expect(state.phase).toBe("matching");
  expect(state.status).toEqual({ step: "RESOLVING", message: "Finding the craft" });
  state = reduceAnswer(state, { type: "status", data: { step: "READING", message: "Reading the best of 4 sources found" } });
  expect(state.status?.step).toBe("READING");
  expect(reduceAnswer(state, { type: "done", data: { answerId: null } }).status).toBeNull();
  expect(reduceAnswer(state, { type: "error", data: { message: "Research failed just now." } }).status).toBeNull();
});

test("not enough evidence is its own settled state, not an error", () => {
  let state = reduceAnswer(emptyAnswer("q"), { type: "not_enough_evidence", data: { message: "There is not enough cited evidence yet." } });
  state = reduceAnswer(state, { type: "status", data: { step: "COMPOSING", message: "late" } });
  state = reduceAnswer(state, { type: "done", data: { answerId: "ans-2" } });
  expect(state.phase).toBe("empty");
  expect(state.notice).toBe("There is not enough cited evidence yet.");
  expect(state.error).toBeNull();
  expect(state.status).toBeNull();
  expect(state.payload.answerId).toBe("ans-2");
});

test("the new event names parse and a heartbeat between them is skipped", () => {
  const { blocks } = splitSseBuffer('event: status\ndata: {"step":"PLANNING","message":"Planning"}\n\n: keep-alive\n\nevent: not_enough_evidence\ndata: {"message":"m"}\n\n');
  expect(blocks.map(parseSseBlock)).toEqual([{ type: "status", data: { step: "PLANNING", message: "Planning" } }, null, { type: "not_enough_evidence", data: { message: "m" } }]);
});
