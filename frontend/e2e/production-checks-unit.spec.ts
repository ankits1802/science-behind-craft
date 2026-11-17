import { readFileSync } from "node:fs";
import { join } from "node:path";

import { expect, test } from "@playwright/test";

import { splitSseBuffer } from "@/lib/answerStream";
import { explainerEventOf } from "@/lib/explainerStream";

import { KNOWN_ANSWER_QUESTIONS, answerProblems, answerRecord, knownAnswerOutcome, parseTappedStream, scriptProblems, type KnownAnswerQuestion } from "./production/answers";
import { NAV_BY_ROLE, gapCopyFindings, labelProblems } from "./production/checks";
import type { AnswersReport, ScreensReport } from "./production/report";
import { runFileName } from "./production/run";
import type { TappedChunk, TappedStream } from "./production/streamTap";
import { summaryMarkdown } from "./production/summaryMarkdown";
import { RIVERS_NOT_LOADED_NOTE } from "./production/waterStory";

const SHARED = join(__dirname, "..", "..", "shared");
const GOLDEN = readFileSync(join(SHARED, "explainer.stream.golden.sse"), "utf8");
const [ENGLISH, HINDI, WATER] = KNOWN_ANSWER_QUESTIONS;
const PHASE_B = JSON.parse(readFileSync(join(SHARED, "explainer.phase-b.golden.json"), "utf8")) as {
  sections: { blocks: Record<string, unknown>[] }[];
  sources: Record<string, unknown>[];
};
const STORY = PHASE_B.sections.flatMap((section) => section.blocks).find((found) => found.id === "s1.b1") as Record<string, unknown>;
const CITATION = { id: "c1", claimId: "k1", sourceId: "s1", quote: "alum", locator: null, context: null, evidence: "QUOTED", level: "PROVISIONAL" };
const SOURCE = { id: "s1", kind: "PAPER", title: "Mordants", authors: [], year: 2020, doi: null, url: "https://example.org/m", publisher: null, licence: null, attribution: null, reliability: "B" };

function chunked(text: string, size: number, start = 1_000, step = 10): TappedChunk[] {
  const chunks: TappedChunk[] = [];
  for (let offset = 0; offset < text.length; offset += size) chunks.push({ at: start + step * chunks.length, text: text.slice(offset, offset + size) });
  return chunks;
}

function block(name: string, data: unknown): string {
  return `event: ${name}\ndata: ${JSON.stringify(data)}\n\n`;
}

function sentence(id: string, text: string, extra: Record<string, unknown> = {}, citations: unknown[] = [CITATION]): string {
  const prose = { id: `s1.${id}`, kind: "prose", version: 1, reuse: null, sentences: [{ id, text, level: "PROVISIONAL", citations, terms: [], ...extra }] };
  return block("block", { sectionId: "s1", block: prose });
}

function stream(text: string, language: string): TappedStream {
  return {
    url: "/api/answers/stream",
    body: JSON.stringify({ question: "q", depth: "DETAILED", craftSlug: "Kutch-Ajrakh", language }),
    requestedAt: 1_000,
    respondedAt: 1_100,
    status: 200,
    chunks: chunked(text, 64, 1_200),
    endedAt: 9_000,
    failure: null
  };
}

function recordOf(text: string, question: KnownAnswerQuestion, streamsOpened = 1) {
  return answerRecord({ question, stream: stream(text, question.language), streamsOpened, clickedAt: 1_000, waited: null });
}

const HINDI_ANSWER = [
  block("source", SOURCE),
  block("section_started", { id: "s1", discipline: "CHEMISTRY", title: "रंगबंधक", original: "Mordants", order: 1, state: "WRITING" }),
  sentence("t1", "फिटकरी कपड़े पर लाल रंग को पक्का करती है।", { translated: true, original: "Alum fixes the red on the cloth." }),
  sentence("t2", "Alum forms a lake with alizarin at 60 °C."),
  block("done", { answerId: null })
].join("");

test("a tapped stream parses the same in any chunking, counting heartbeats and silence", () => {
  const whole = splitSseBuffer(GOLDEN).blocks.map(explainerEventOf).filter((event) => event !== null);
  for (const size of [1, 7, 64, GOLDEN.length]) {
    const parsed = parseTappedStream(chunked(GOLDEN, size), 1_000);
    expect(parsed.events.map(({ event }) => event)).toEqual(whole);
    expect(parsed.heartbeats).toBe(1);
    expect(parsed.unparsed).toBe(0);
  }
  const silent = parseTappedStream([{ at: 1_500, text: ": keep-alive\n\n" }, { at: 61_500, text: block("done", { answerId: null }) }], 1_000);
  expect(silent.longestSilenceMs).toBe(60_000);
  expect(silent.heartbeats).toBe(1);
});

test("the golden English answer records its sentences, citations and sources and passes", () => {
  const record = recordOf(GOLDEN, ENGLISH);
  expect(record.endedWith).toBe("done");
  expect(record.sentenceCount).toBe(record.sentences.length);
  expect(record.citedSentenceCount).toBeGreaterThan(0);
  expect(record.uncitedSentenceCount).toBe(0);
  expect(record.sources.length).toBeGreaterThan(0);
  expect(record.knownAnswerFound).toBe(true);
  expect(record.timing.heartbeats).toBe(1);
  expect(record.timing.firstByteMs).toBe(200);
  expect(answerProblems(record, ENGLISH)).toEqual([]);
});

test("a Hindi answer passes with Devanagari translations and English fallbacks", () => {
  const record = recordOf(HINDI_ANSWER, HINDI);
  expect(record.scripts).toEqual({ translated: 1, englishFallback: 1, other: 0 });
  expect(answerProblems(record, HINDI)).toEqual([]);
});

test("the Hindi rule refuses a translated sentence in Latin, a missing original and a mixed fallback", () => {
  const latin = recordOf(sentence("x1", "Alum fixes the red.", { translated: true, original: "Alum fixes the red." }), HINDI);
  expect(scriptProblems(latin.sentences, "Deva")).toEqual(["sentence x1 is marked translated but is written in Latn"]);
  const bare = recordOf(sentence("x2", "फिटकरी रंग पक्का करती है।", { translated: true }), HINDI);
  expect(scriptProblems(bare.sentences, "Deva")).toEqual(["sentence x2 is translated but carries no English original"]);
  const untranslated = recordOf(sentence("x3", "फिटकरी रंग पक्का करती है।"), HINDI);
  expect(scriptProblems(untranslated.sentences, "Deva")).toEqual(["sentence x3 is neither in Deva nor an English fallback"]);
});

test("an answer without done, with an uncited sentence or opened twice fails", () => {
  const cut = recordOf([block("source", SOURCE), sentence("e1", "Alum is the mordant.")].join(""), ENGLISH);
  expect(answerProblems(cut, ENGLISH)).toContain("the stream ended with closed, not done");
  const uncited = recordOf([sentence("e2", "Alum is the mordant.", {}, []), block("done", { answerId: null })].join(""), ENGLISH);
  expect(answerProblems(uncited, ENGLISH)).toEqual(expect.arrayContaining(["no cited sentence arrived", "1 stream frames broke the explainer contract"]));
  const retired = recordOf([block("source", SOURCE), block("sentence", { sectionId: "a", sentence: {} }), sentence("e6", "Alum is the mordant."), block("done", { answerId: null })].join(""), ENGLISH);
  expect(answerProblems(retired, ENGLISH)).toEqual(["1 stream frames broke the explainer contract"]);
  const twice = recordOf([block("source", SOURCE), sentence("e3", "Alum is the mordant."), block("done", { answerId: null })].join(""), ENGLISH, 2);
  expect(answerProblems(twice, ENGLISH)).toEqual(["the question opened 2 answer streams, not 1"]);
  const orphan = recordOf([sentence("e4", "Alum is the mordant."), block("done", { answerId: null })].join(""), ENGLISH);
  expect(answerProblems(orphan, ENGLISH)).toEqual(["1 cited sources never arrived as source events"]);
  const wrong = recordOf([block("source", SOURCE), sentence("e5", "Iron darkens the black."), block("done", { answerId: null })].join(""), ENGLISH);
  expect(answerProblems(wrong, ENGLISH)).toEqual(["no sentence names alum, the known mordant"]);
});

function waterAnswer(...frames: string[]): string {
  return [block("source", SOURCE), ...PHASE_B.sources.map((source) => block("source", source)), ...frames, block("done", { answerId: null })].join("");
}

test("the water question passes only when a region story with a river path and cited steps arrives", () => {
  const story = recordOf(waterAnswer(block("block", { sectionId: "s1", block: STORY })), WATER);
  expect(story.regionStory).toEqual({ blocks: 1, withRiver: 1, steps: 4, citedSteps: 4 });
  expect(story.knownAnswerFound).toBe(true);
  expect(answerProblems(story, WATER, { riversLoaded: true })).toEqual([]);
  const riverless = recordOf(waterAnswer(block("block", { sectionId: "s1", block: { ...STORY, river: null } })), WATER);
  expect(riverless.knownAnswerFound).toBe(false);
  expect(answerProblems(riverless, WATER)).toEqual(["1 region stories arrived without a river path"]);
});

test("without a region story the water question fails once rivers are loaded, and before that only records the absence", () => {
  const absent = recordOf(waterAnswer(sentence("w1", "Alum is the mordant.")), WATER);
  expect(absent.regionStory.blocks).toBe(0);
  expect(answerProblems(absent, WATER)).toEqual([]);
  expect(knownAnswerOutcome(absent, WATER).notes).toEqual([RIVERS_NOT_LOADED_NOTE]);
  expect(answerProblems(absent, WATER, { riversLoaded: true })).toEqual(["no region story arrived although the river lines are loaded"]);
  expect(knownAnswerOutcome(absent, WATER, { riversLoaded: true }).notes).toEqual([]);
  expect(answerProblems(recordOf(waterAnswer(sentence("w1", "Alum is the mordant.")), ENGLISH), ENGLISH)).toEqual([]);
});

test("the page must show every streamed sentence with a citation chip", () => {
  const record = recordOf([block("source", SOURCE), sentence("p1", "Alum is the mordant."), block("done", { answerId: null })].join(""), ENGLISH);
  record.pageSentences = 2;
  record.pageSentencesWithoutChip = 1;
  expect(answerProblems(record, ENGLISH)).toEqual(["1 sentences on the page show no citation", "the page shows 2 sentences; the stream sent 1"]);
});

test("gap copy is found with its context and ordinary copy is not", () => {
  expect(gapCopyFindings("Voice calls are coming soon to every craft.")).toEqual(["Voice calls are coming soon to every craft."]);
  expect(gapCopyFindings("Region data isn't available yet for this place")).toHaveLength(1);
  expect(gapCopyFindings("This screen is not built")).toHaveLength(1);
  expect(gapCopyFindings("Ask about any Indian craft. Sign in. No source found.")).toEqual([]);
});

test("nav labels must match the role exactly and in order", () => {
  expect(labelProblems("the menu", ["Ask", "Map"], [" Ask ", "Map"])).toEqual([]);
  expect(labelProblems("the menu", ["Ask", "Map"], ["Map", "Ask"])).toEqual(["the menu shows [Map, Ask]; this role should see [Ask, Map]"]);
  expect(NAV_BY_ROLE.RESEARCHER?.depths).toEqual(["Basic", "Detailed", "Expert"]);
  expect(NAV_BY_ROLE.STUDENT?.depths).toEqual(["Basic", "Detailed", "Expert"]);
  expect(NAV_BY_ROLE.PROFESSOR).toBeUndefined();
});

test("run files follow the naming golden rows", () => {
  const rows = JSON.parse(readFileSync(join(SHARED, "naming-golden.json"), "utf8")).evalRunFiles as {
    startedAt: string;
    subject: string;
    what: string;
    ext: string;
    sequence?: string;
    fileName: string;
  }[];
  const before = process.env.E2E_RUN_STARTED_AT;
  try {
    for (const row of rows) {
      process.env.E2E_RUN_STARTED_AT = row.startedAt;
      expect(runFileName(row)).toBe(row.fileName);
    }
  } finally {
    if (before === undefined) delete process.env.E2E_RUN_STARTED_AT;
    else process.env.E2E_RUN_STARTED_AT = before;
  }
});

test("the step summary orders widths from widest and escapes table cells", () => {
  const screens = (width: string, px: number, problems: string[]): ScreensReport => ({
    kind: "screens",
    width,
    viewport: { width: px, height: 800 },
    baseUrl: "https://example.org",
    runId: "7",
    startedAt: "2026-11-17T09:00:00Z",
    role: "RESEARCHER",
    problemCount: problems.length,
    screens: [{ name: "Ask", path: "/ask", screenshot: null, durationMs: 1, problems, notes: [] }]
  });
  const answers: AnswersReport = {
    kind: "answers",
    baseUrl: "https://example.org",
    runId: "7",
    startedAt: "2026-11-17T09:00:00Z",
    role: "RESEARCHER",
    problemCount: 0,
    unasked: [],
    questions: [recordOf(HINDI_ANSWER, HINDI), { ...recordOf(waterAnswer(sentence("w2", "Alum is the mordant.")), WATER), notes: [RIVERS_NOT_LOADED_NOTE] }]
  };
  const markdown = summaryMarkdown([screens("Phone", 390, ["a | b"]), screens("Desktop", 1440, [])], {
    runId: "7",
    baseUrl: "https://example.org",
    startedAt: "2026-11-17T09:00:00Z",
    questionsRequested: true
  });
  expect(markdown).toContain("| Screen | Desktop | Phone |");
  expect(markdown).toContain("| Ask | Pass | Fail (1) |");
  expect(markdown).toContain("- Phone · Ask: a \\| b");
  const withAnswers = summaryMarkdown([screens("Desktop", 1440, []), answers], { runId: null, baseUrl: null, startedAt: "x", questionsRequested: true });
  expect(withAnswers).toContain("| Question | Ended | Sentences | Cited | Citations | Sources | Known answer | Script | Done in | Result |");
  expect(withAnswers).toContain("| Hindi | done | 2 | 2 | 2 | 1 | Yes | 1 translated, 1 English, 0 other |");
  expect(withAnswers).toContain(`#### Answer notes\n\n- Water: ${RIVERS_NOT_LOADED_NOTE}`);
});
