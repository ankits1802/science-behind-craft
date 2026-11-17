import { readFileSync } from "node:fs";
import { join } from "node:path";

import { expect, test } from "@playwright/test";

import { splitSseBuffer } from "@/lib/answerStream";
import { explainerEventOf } from "@/lib/explainerStream";

import { KNOWN_ANSWER_QUESTIONS, answerProblems, answerRecord, knownAnswerOutcome, pageSentenceProblems, parseTappedStream, scriptProblems, type KnownAnswerQuestion } from "./production/answers";
import { NAV_BY_ROLE, gapCopyFindings, labelProblems } from "./production/checks";
import type { AnswersReport, ScreensReport } from "./production/report";
import { runFileName } from "./production/run";
import type { TappedChunk, TappedStream } from "./production/streamTap";
import { summaryMarkdown } from "./production/summaryMarkdown";
import { FRAME_DOCUMENT_START, NO_CONCEPT_NOTE, type FrameSeen } from "./production/generatedExplainer";
import { RIVERS_NOT_LOADED_NOTE } from "./production/waterStory";
import { PHASE_C, phaseCBlock } from "./playFixture";

const SHARED = join(__dirname, "..", "..", "shared");
const GOLDEN = readFileSync(join(SHARED, "explainer.stream.golden.sse"), "utf8");
const [ENGLISH, HINDI, WATER, INDIGO] = KNOWN_ANSWER_QUESTIONS;
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

function stream(text: string, language: string, depth = "DETAILED"): TappedStream {
  return {
    url: "/api/answers/stream",
    body: JSON.stringify({ question: "q", depth, craftSlug: "Kutch-Ajrakh", language }),
    requestedAt: 1_000,
    respondedAt: 1_100,
    status: 200,
    chunks: chunked(text, 64, 1_200),
    endedAt: 9_000,
    failure: null
  };
}

function recordOf(text: string, question: KnownAnswerQuestion, streamsOpened = 1) {
  return answerRecord({ question, stream: stream(text, question.language, question.depth), streamsOpened, clickedAt: 1_000, waited: null });
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
  record.pageSentences = 1;
  record.pageSentenceIds = ["p9"];
  record.pageSentencesWithoutChip = 0;
  expect(answerProblems(record, ENGLISH)).toEqual(["1 streamed sentences are not on the page: p1", "1 sentences on the page never arrived in the stream: p9"]);
  record.pageSentenceIds = ["p1"];
  expect(answerProblems(record, ENGLISH)).toEqual([]);
});

test("a sentence a block repeats word for word counts as shown once its twin is on the page", () => {
  const twins = ["t1", "t2"].map((id) => ({ id, text: "Indigo came from Sindh.", level: "PROVISIONAL", citations: [CITATION], terms: [] }));
  const prose = block("block", { sectionId: "s1", block: { id: "s1.b1", kind: "prose", version: 1, reuse: null, sentences: twins } });
  const record = recordOf([block("source", SOURCE), prose, block("done", { answerId: null })].join(""), ENGLISH);
  record.pageSentences = 1;
  record.pageSentencesWithoutChip = 0;
  record.pageSentenceIds = ["t1"];
  expect(pageSentenceProblems(record)).toEqual([]);
  record.pageSentenceIds = [];
  expect(pageSentenceProblems(record)).toEqual(["2 streamed sentences are not on the page: t1, t2"]);
});

test("a stepped block needs only the sentence of the level it shows on the page", () => {
  const story = { ...phaseCBlock("zoom_story", "s3.b1"), id: "s1.zoom" };
  const levels = story.levels.map((level) => level.sentence.id);
  const record = recordOf([block("source", SOURCE), sentence("p1", "Alum is the mordant."), block("block", { sectionId: "s1", block: story }), block("done", { answerId: null })].join(""), ENGLISH);
  expect(levels.length).toBeGreaterThan(1);
  expect(record.sentences.filter((entry) => entry.blockKind === "zoom_story").map((entry) => entry.blockId)).toEqual(levels.map(() => "s1.zoom"));
  record.pageSentences = 2;
  record.pageSentencesWithoutChip = 0;
  record.pageSentenceIds = ["p1", levels[1]];
  expect(pageSentenceProblems(record)).toEqual([]);
  record.pageSentenceIds = ["p1"];
  expect(pageSentenceProblems(record)).toEqual([`the stepped block s1.zoom shows none of its ${levels.length} sentences`]);
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
    questions: [recordOf(HINDI_ANSWER, HINDI), { ...recordOf(waterAnswer(sentence("w2", "Alum is the mordant.")), WATER), notes: [RIVERS_NOT_LOADED_NOTE] }],
    exports: null
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

function indigoAnswer(...frames: string[]): string {
  return [block("source", SOURCE), ...PHASE_C.sources.map((source) => block("source", source)), sentence("i1", "Indigo turns blue as it meets the air."), ...frames, block("done", { answerId: null })].join("");
}

const DRAWN_FRAME: FrameSeen = { sandbox: "allow-scripts", policyFirst: true, drawn: true, peerless: true };

test("the four known-answer questions ask the mordant, the water and indigo at their depths", () => {
  expect(KNOWN_ANSWER_QUESTIONS.map((question) => [question.label, question.depth, question.check])).toEqual([
    ["English", "DETAILED", "MORDANT"],
    ["Hindi", "DETAILED", "MORDANT"],
    ["Water", "DETAILED", "WATER_STORY"],
    ["Indigo", "EXPERT", "GENERATED_EXPLAINER"]
  ]);
  expect(INDIGO.question).toBe("How does indigo turn blue on Kutch Ajrakh cloth?");
  expect(FRAME_DOCUMENT_START).toContain("webrtc 'block'");
  const detailed = answerRecord({ question: INDIGO, stream: stream(indigoAnswer(), "en"), streamsOpened: 1, clickedAt: 1_000, waited: null });
  expect(answerProblems(detailed, INDIGO)).toContain("the request asked at DETAILED, not EXPERT");
});

test("indigo passes when its generated explainer draws in the sandbox and its frame reaches nothing", () => {
  const generated = block("block", { sectionId: "s1", block: phaseCBlock("simulation", "s1.b1") });
  const record = recordOf(indigoAnswer(generated), INDIGO);
  expect(record.generatedExplainer).toMatchObject({ blocks: 1, values: 2, valuesWithoutBasis: 0 });
  expect(record.knownAnswerFound).toBe(true);
  expect(answerProblems({ ...record, generatedExplainer: { ...record.generatedExplainer, frames: [DRAWN_FRAME] } }, INDIGO)).toEqual([]);
  const leaking = { ...record.generatedExplainer, frames: [DRAWN_FRAME], frameRequests: ["https://example.org/leak"], frameRefusals: ["Refused to connect to 'https://example.org/'"] };
  expect(answerProblems({ ...record, generatedExplainer: leaking }, INDIGO)).toEqual([
    "a generated explainer frame attempted 1 network requests: https://example.org/leak",
    "a generated explainer frame attempted 1 loads its policy refused: Refused to connect to 'https://example.org/'"
  ]);
  const broken = { ...record.generatedExplainer, frames: [{ sandbox: "allow-scripts allow-same-origin", policyFirst: false, drawn: false, peerless: false }, DRAWN_FRAME] };
  expect(answerProblems({ ...record, generatedExplainer: broken }, INDIGO)).toEqual([
    "the stream sent 1 generated explainers; the page draws 2 sandboxed frames",
    '1 generated explainer frames lack sandbox="allow-scripts" or the policy as their first head element',
    "1 generated explainer frames drew nothing",
    "1 generated explainer frames still offer a peer connection"
  ]);
});

test("without a generated explainer the indigo question records that the builder chose no concept and does not fail", () => {
  const record = recordOf(indigoAnswer(), INDIGO);
  expect(record.generatedExplainer.blocks).toBe(0);
  expect(record.knownAnswerFound).toBe(false);
  expect(answerProblems({ ...record, generatedExplainer: { ...record.generatedExplainer, frames: [] } }, INDIGO)).toEqual([]);
  expect(knownAnswerOutcome(record, INDIGO).notes).toEqual([NO_CONCEPT_NOTE]);
});
