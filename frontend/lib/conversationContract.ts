import { apiFetch } from "@/lib/api";
import { answerLanguageShape, type AnswerLanguage } from "@/lib/answerLanguages";
import { answerSentenceShape, craftLinkShape, INSTANT, sourceRefShape, type CraftLink } from "@/lib/answerShapes";
import { openEventStream, readSseBlocks, sseFields } from "@/lib/answerStream";
import { boolean, integer, list, nullable, object, oneOf, parseShape, tagged, text, type Shape } from "@/lib/shape";
import type { AnswerSentence, SourceRef } from "@/lib/types";

export const CONVERSATIONS_PATH = "/artisan/conversations";
export const CONVERSATION_TURN_PATH = (id: string) => `/artisan/conversations/${encodeURIComponent(id)}/turns`;
export const CONVERSATION_END_PATH = (id: string) => `/artisan/conversations/${encodeURIComponent(id)}/end`;
export const INTERVIEW_TOPICS = ["PROCESS", "MATERIALS", "TIMING", "TOOLS", "HISTORY", "CHANGE"] as const;
export const TURN_STEPS = ["transcribing", "thinking", "speaking"] as const;
export const EXTRACTION_ON_END = ["PENDING", "NONE"] as const;

export type InterviewTopic = (typeof INTERVIEW_TOPICS)[number];
export type ConversationAvailability = {
  configured: boolean;
  transport: "AGENT" | "RELAY" | null;
  languages: AnswerLanguage[];
  noticeVersion: string | null;
  consentRequired: boolean;
  remainingSeconds: number | null;
  crafts: CraftLink[];
};
type StartedCommon = {
  conversationId: string;
  voiceSessionId: string;
  craft: CraftLink;
  language: string;
  maxDurationSeconds: number;
  remainingSeconds: number | null;
  maxTurns: number;
  expiresAt: string;
};
export type RelayConversationStarted = StartedCommon & {
  transport: "RELAY";
  maxTurnSeconds: number;
  maxAudioBytes: number;
  audioBitsPerSecond: number;
  audioTypes: string[];
  opening: { turnId: string; text: string; speechPath: string };
};
export type AgentConversationStarted = StartedCommon & { transport: "AGENT"; conversationToken: string };
export type ConversationStarted = RelayConversationStarted | AgentConversationStarted;
export type ConversationReply = {
  turnId: string;
  answerId: string | null;
  sentences: AnswerSentence[];
  question: string;
  english: string;
  topic: InterviewTopic;
  text: string;
  speechPath: string;
};
export type ConversationTurnEvent =
  | { type: "heard"; data: { turnId: string; text: string; language: string; continued: boolean } }
  | { type: "status"; data: { step: (typeof TURN_STEPS)[number] } }
  | { type: "source"; data: SourceRef }
  | { type: "reply"; data: ConversationReply }
  | { type: "closing"; data: { turnId: string; text: string; speechPath: string } }
  | { type: "done"; data: { turnId: string; billedSeconds: number; remainingSeconds: number | null; sessionEnded: boolean } }
  | { type: "error"; data: { message: string } };
export type ConversationEnded = { conversationId: string; endedAt: string; turnCount: number; billedSeconds: number; extraction: (typeof EXTRACTION_ON_END)[number] };

export const availabilityShape: Shape<ConversationAvailability> = object({
  configured: boolean,
  transport: nullable(oneOf(["AGENT", "RELAY"] as const)),
  languages: list(answerLanguageShape),
  noticeVersion: nullable(text),
  consentRequired: boolean,
  remainingSeconds: nullable(integer),
  crafts: list(craftLinkShape)
});

const common = {
  conversationId: text,
  voiceSessionId: text,
  craft: craftLinkShape,
  language: text,
  maxDurationSeconds: integer,
  remainingSeconds: nullable(integer),
  maxTurns: integer,
  expiresAt: INSTANT
};

export const startedShape: Shape<ConversationStarted> = tagged<ConversationStarted>("transport", {
  RELAY: object<RelayConversationStarted>({
    ...common,
    transport: oneOf(["RELAY"] as const),
    maxTurnSeconds: integer,
    maxAudioBytes: integer,
    audioBitsPerSecond: integer,
    audioTypes: list(text, 1),
    opening: object({ turnId: text, text, speechPath: text })
  }),
  AGENT: object<AgentConversationStarted>({ ...common, transport: oneOf(["AGENT"] as const), conversationToken: text })
});

const speech = { turnId: text, text, speechPath: text };
const EVENT_SHAPES: Record<ConversationTurnEvent["type"], Shape<unknown>> = {
  heard: object({ turnId: text, text, language: text, continued: boolean }),
  status: object({ step: oneOf(TURN_STEPS) }),
  source: sourceRefShape,
  reply: object<ConversationReply>({
    ...speech,
    answerId: nullable(text),
    sentences: list(answerSentenceShape),
    question: text,
    english: text,
    topic: oneOf(INTERVIEW_TOPICS)
  }),
  closing: object(speech),
  done: object({ turnId: text, billedSeconds: integer, remainingSeconds: nullable(integer), sessionEnded: boolean }),
  error: object({ message: text })
};

export const endedShape: Shape<ConversationEnded> = object({
  conversationId: text,
  endedAt: INSTANT,
  turnCount: integer,
  billedSeconds: integer,
  extraction: oneOf(EXTRACTION_ON_END)
});

export function parseTurnBlock(block: string): ConversationTurnEvent | null {
  const { name, data } = sseFields(block);
  if (!name || data === null || !(name in EVENT_SHAPES)) return null;
  const type = name as ConversationTurnEvent["type"];
  return { type, data: parseShape(EVENT_SHAPES[type], JSON.parse(data)) } as ConversationTurnEvent;
}

export async function startConversation(craftSlug: string, language: string, noticeVersion: string): Promise<ConversationStarted> {
  const raw = await apiFetch<unknown>(CONVERSATIONS_PATH, { method: "POST", body: JSON.stringify({ craftSlug, language, noticeVersion }) });
  return parseShape(startedShape, raw);
}

export async function streamConversationTurn(
  conversationId: string,
  recording: File,
  continued: boolean,
  onEvent: (event: ConversationTurnEvent) => void
): Promise<void> {
  const form = new FormData();
  form.append("audio", recording, recording.name);
  if (continued) form.append("continued", "true");
  const stream = await openEventStream(CONVERSATION_TURN_PATH(conversationId), { body: form, json: false, fallback: "Couldn't hear that. Try again." });
  await readSseBlocks(stream, (block) => {
    const event = parseTurnBlock(block);
    if (event) onEvent(event);
  });
}

export async function endConversation(conversationId: string): Promise<ConversationEnded> {
  return parseShape(endedShape, await apiFetch<unknown>(CONVERSATION_END_PATH(conversationId), { method: "POST" }));
}
