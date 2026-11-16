import { API_BASE, APP_PLATFORM, APP_VERSION, APP_VERSION_CODE, ApiError, describeApiBody, statusFallback } from "@/lib/api";
import type { AnswerMode, AnswerPayload, AnswerReaction, AnswerSection, AnswerSentence, AnswerStatus, CraftMatch, SourceRef } from "@/lib/types";

export const ANSWER_STREAM_PATH = "/answers/stream";

export type AskRequest = {
  question: string;
  mode: AnswerMode;
  craftSlug?: string | null;
  language?: string | null;
  conversationId?: string | null;
};

export type AnswerEvent =
  | { type: "match"; data: CraftMatch }
  | { type: "status"; data: AnswerStatus }
  | { type: "not_enough_evidence"; data: { message: string } }
  | { type: "source"; data: SourceRef }
  | { type: "section"; data: { id: string; heading: string; original?: string } }
  | { type: "sentence"; data: { sectionId: string; sentence: AnswerSentence } }
  | { type: "open_question"; data: { sectionId: string; heading?: string; sentence: AnswerSentence } }
  | { type: "reaction"; data: AnswerReaction }
  | { type: "follow_ups"; data: { items: string[] } }
  | { type: "done"; data: { answerId: string | null } }
  | { type: "error"; data: { message: string } };

export type AnswerPhase = "idle" | "matching" | "streaming" | "done" | "ambiguous" | "empty" | "failed";

export type AnswerState = {
  phase: AnswerPhase;
  match: CraftMatch | null;
  status: AnswerStatus | null;
  payload: AnswerPayload;
  error: string | null;
  notice: string | null;
};

const SETTLED: ReadonlySet<AnswerPhase> = new Set(["ambiguous", "empty", "failed"]);

export function emptyAnswer(question = "", mode: AnswerMode = "HYBRID", language = "en"): AnswerState {
  return {
    phase: "idle",
    match: null,
    status: null,
    error: null,
    notice: null,
    payload: {
      answerId: null,
      question,
      mode,
      language,
      craft: null,
      sections: [],
      openQuestions: [],
      reactions: [],
      sources: [],
      followUps: []
    }
  };
}

function appendSentence(sections: AnswerSection[], sectionId: string, sentence: AnswerSentence, heading = ""): AnswerSection[] {
  if (sentence.citations.length === 0) return sections;
  const index = sections.findIndex((section) => section.id === sectionId);
  if (index < 0) return [...sections, { id: sectionId, heading, sentences: [sentence] }];
  const target = sections[index];
  if (target.sentences.some((existing) => existing.id === sentence.id)) return sections;
  const next = [...sections];
  next[index] = { ...target, sentences: [...target.sentences, sentence] };
  return next;
}

export function reduceAnswer(state: AnswerState, event: AnswerEvent): AnswerState {
  const payload = state.payload;
  switch (event.type) {
    case "match": {
      const match = event.data;
      if (match.status === "AMBIGUOUS") return { ...state, match, phase: "ambiguous" };
      return {
        ...state,
        match,
        phase: "streaming",
        payload: { ...payload, craft: match.status === "RESOLVED" ? match.craft : null }
      };
    }
    case "status":
      if (SETTLED.has(state.phase)) return state;
      return { ...state, status: event.data };
    case "not_enough_evidence":
      return { ...state, phase: "empty", status: null, notice: event.data.message };
    case "source":
      if (payload.sources.some((source) => source.id === event.data.id)) return state;
      return { ...state, payload: { ...payload, sources: [...payload.sources, event.data] } };
    case "section":
      if (payload.sections.some((section) => section.id === event.data.id)) return state;
      return { ...state, phase: "streaming", payload: { ...payload, sections: [...payload.sections, { ...event.data, sentences: [] }] } };
    case "sentence":
      return { ...state, phase: "streaming", payload: { ...payload, sections: appendSentence(payload.sections, event.data.sectionId, event.data.sentence) } };
    case "open_question":
      return {
        ...state,
        payload: {
          ...payload,
          openQuestions: appendSentence(payload.openQuestions, event.data.sectionId, event.data.sentence, event.data.heading ?? "")
        }
      };
    case "reaction":
      if (payload.reactions.some((reaction) => reaction.id === event.data.id)) return state;
      return { ...state, payload: { ...payload, reactions: [...payload.reactions, event.data] } };
    case "follow_ups":
      return { ...state, payload: { ...payload, followUps: event.data.items } };
    case "done":
      return {
        ...state,
        phase: SETTLED.has(state.phase) ? state.phase : "done",
        status: null,
        payload: { ...payload, answerId: event.data.answerId ?? payload.answerId }
      };
    case "error":
      return { ...state, phase: "failed", status: null, error: event.data.message };
    default:
      return state;
  }
}

const KNOWN_EVENTS = new Set(["match", "status", "not_enough_evidence", "source", "section", "sentence", "open_question", "reaction", "follow_ups", "done", "error"]);

export function sseFields(block: string): { name: string; data: string | null } {
  let name = "message";
  const data: string[] = [];
  for (const raw of block.split("\n")) {
    const line = raw.endsWith("\r") ? raw.slice(0, -1) : raw;
    if (!line || line.startsWith(":")) continue;
    const colon = line.indexOf(":");
    const field = colon < 0 ? line : line.slice(0, colon);
    const value = colon < 0 ? "" : line.slice(colon + 1).replace(/^ /, "");
    if (field === "event") name = value;
    else if (field === "data") data.push(value);
  }
  return { name, data: data.length ? data.join("\n") : null };
}

export function parseSseBlock(block: string): AnswerEvent | null {
  const { name, data } = sseFields(block);
  if (!KNOWN_EVENTS.has(name) || data === null) return null;
  try {
    return { type: name, data: JSON.parse(data) } as AnswerEvent;
  } catch {
    return null;
  }
}

export function splitSseBuffer(buffer: string): { blocks: string[]; rest: string } {
  const normalised = buffer.replace(/\r\n/g, "\n");
  const parts = normalised.split("\n\n");
  const rest = parts.pop() ?? "";
  return { blocks: parts, rest };
}

export async function openEventStream(path: string, init: { body: BodyInit; json: boolean; signal?: AbortSignal; fallback: string }): Promise<ReadableStream<Uint8Array>> {
  const headers = new Headers({ Accept: "text/event-stream" });
  if (init.json) headers.set("Content-Type", "application/json");
  headers.set("X-Client-Time", new Date().toISOString());
  headers.set("X-App-Version", APP_VERSION);
  headers.set("X-App-Platform", APP_PLATFORM);
  if (APP_VERSION_CODE) headers.set("X-App-Version-Code", APP_VERSION_CODE);

  const response = await fetch(`${API_BASE}/api${path}`, { method: "POST", headers, body: init.body, cache: "no-store", signal: init.signal });

  if (!response.ok || !response.body) {
    const contentType = response.headers.get("content-type") ?? "";
    const body = contentType.includes("application/json") ? await response.json().catch(() => null) : await response.text().catch(() => "");
    throw new ApiError(response.status, describeApiBody(body, statusFallback(response.status, init.fallback)), body, response.headers);
  }
  return response.body;
}

export async function readSseBlocks(stream: ReadableStream<Uint8Array>, onBlock: (block: string) => void): Promise<void> {
  const reader = stream.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const { blocks, rest } = splitSseBuffer(buffer);
    buffer = rest;
    for (const block of blocks) onBlock(block);
  }
  buffer += decoder.decode();
  if (buffer.trim()) onBlock(buffer);
}

export async function streamAnswer(request: AskRequest, onEvent: (event: AnswerEvent) => void, signal?: AbortSignal): Promise<void> {
  const stream = await openEventStream(ANSWER_STREAM_PATH, { body: JSON.stringify(request), json: true, signal, fallback: "Couldn't answer that. Try again." });
  await readSseBlocks(stream, (block) => {
    const event = parseSseBlock(block);
    if (event) onEvent(event);
  });
}
