import { answerLanguageShape, languageCodeShape, type AnswerLanguage } from "@/lib/answerLanguages";
import { answerSentenceShape, answerStatusShape, craftLinkShape, INSTANT, sourceRefShape, UUID, type CraftLink } from "@/lib/answerShapes";
import { sseFields } from "@/lib/answerStream";
import { boolean, integer, list, matching, nullable, object, oneOf, ShapeError, tagged, text, type Shape } from "@/lib/shape";
import type { AnswerSentence, AnswerStatus, SourceRef } from "@/lib/types";

export const VOICE_SESSION_PATH = "/voice/session";
export const VOICE_SESSION_END_PATH = (id: string) => `/voice/session/${encodeURIComponent(id)}/end`;
export const VOICE_TRANSCRIPT_PATH = (id: string) => `/voice/session/${encodeURIComponent(id)}/transcript`;
export const VOICE_TURN_PATH = (id: string) => `/voice/session/${encodeURIComponent(id)}/turns`;
export const VOICE_NOTICE_PATH = "/voice/notice";
export const CONSENT_PATH = "/auth/consent";
export const VOICE_CONSENT_HEADER = "x-voice-consent-required";

export const VOICE_MODES = ["VERIFIED", "HYBRID"] as const;
export const RELAY_AUDIO_TYPES = ["audio/webm", "audio/ogg", "audio/mp4", "audio/wav"] as const;
export const CLIENT_TOOL_NAMES = ["show_on_map", "open_stage", "show_sources", "offer_image"] as const;
export const MAX_SPOKEN_WORDS = 60;
export const MIN_START_SECONDS = 30;

export type VoiceLanguage = string;
export type VoiceMode = (typeof VOICE_MODES)[number];
export type VoiceAvailability = {
  configured: boolean;
  transport: "AGENT" | "RELAY" | null;
  languages: AnswerLanguage[];
  noticeVersion: string | null;
  consentRequired: boolean;
  remainingSeconds: number | null;
};
export type VoiceNotice = { version: string; title: string; body: string; publishedAt: string | null };
export type VoiceSessionRequest = { craftSlug: string | null; mode: VoiceMode; language: VoiceLanguage };
type SessionCommon = {
  voiceSessionId: string;
  mode: VoiceMode;
  language: VoiceLanguage;
  craft: CraftLink | null;
  maxDurationSeconds: number;
  remainingSeconds: number | null;
  maxTurns: number;
  expiresAt: string;
};
export type AgentSessionStarted = SessionCommon & { transport: "AGENT"; conversationToken: string };
export type RelaySessionStarted = SessionCommon & {
  transport: "RELAY";
  maxTurnSeconds: number;
  maxAudioBytes: number;
  audioBitsPerSecond: number;
  audioTypes: string[];
};
export type VoiceSessionStarted = AgentSessionStarted | RelaySessionStarted;
export type VoiceSessionEnded = { voiceSessionId: string; endedAt: string; turnCount: number; reservedSeconds: number; billedSeconds: number | null };
export type ClientToolCall =
  | { name: "show_on_map"; parameters: { craftSlug: string } }
  | { name: "open_stage"; parameters: { stageId: string } }
  | { name: "show_sources"; parameters: { answerId: string } }
  | { name: "offer_image"; parameters: { stageId: string } };
export type VoiceTurn = {
  turnId: string;
  ordinal: number;
  heard: string;
  answerId: string | null;
  sentences: AnswerSentence[];
  spoken: string;
  actions: ClientToolCall[];
};
export type VoiceTranscript = {
  voiceSessionId: string;
  language: VoiceLanguage;
  mode: VoiceMode;
  craft: CraftLink | null;
  retentionUntil: string;
  turns: VoiceTurn[];
  sources: SourceRef[];
};
export type VoiceTurnDone = { turnId: string; answerId: string | null; billedSeconds: number; remainingSeconds: number | null; sessionEnded: boolean };
export type VoiceTurnEvent =
  | { type: "heard"; data: { text: string; language: VoiceLanguage } }
  | { type: "status"; data: AnswerStatus }
  | { type: "source"; data: SourceRef }
  | { type: "sentence"; data: { sentence: AnswerSentence } }
  | { type: "action"; data: ClientToolCall }
  | { type: "spoken"; data: { text: string; speechPath: string } }
  | { type: "error"; data: { message: string } }
  | { type: "done"; data: VoiceTurnDone };

const LANGUAGE = languageCodeShape;
const MODE = oneOf(VOICE_MODES);
const SECONDS = nullable(integer);

export const voiceAvailabilityShape: Shape<VoiceAvailability> = object<VoiceAvailability>({
  configured: boolean,
  transport: nullable(oneOf(["AGENT", "RELAY"] as const)),
  languages: list(answerLanguageShape),
  noticeVersion: nullable(text),
  consentRequired: boolean,
  remainingSeconds: SECONDS
});

export const voiceNoticeShape: Shape<VoiceNotice> = object<VoiceNotice>({
  version: text,
  title: text,
  body: text,
  publishedAt: nullable(text)
});

const common = {
  voiceSessionId: UUID,
  mode: MODE,
  language: LANGUAGE,
  craft: nullable(craftLinkShape),
  maxDurationSeconds: integer,
  remainingSeconds: SECONDS,
  maxTurns: integer,
  expiresAt: INSTANT
};

export const voiceSessionStartedShape: Shape<VoiceSessionStarted> = tagged<VoiceSessionStarted>("transport", {
  AGENT: object<AgentSessionStarted>({ ...common, transport: oneOf(["AGENT"] as const), conversationToken: text }),
  RELAY: object<RelaySessionStarted>({
    ...common,
    transport: oneOf(["RELAY"] as const),
    maxTurnSeconds: integer,
    maxAudioBytes: integer,
    audioBitsPerSecond: integer,
    audioTypes: list(text, 1)
  })
});

export const voiceSessionEndedShape: Shape<VoiceSessionEnded> = object<VoiceSessionEnded>({
  voiceSessionId: UUID,
  endedAt: INSTANT,
  turnCount: integer,
  reservedSeconds: integer,
  billedSeconds: SECONDS
});

export const clientToolCallShape: Shape<ClientToolCall> = tagged<ClientToolCall>("name", {
  show_on_map: object<Extract<ClientToolCall, { name: "show_on_map" }>>({
    name: oneOf(["show_on_map"] as const),
    parameters: object<{ craftSlug: string }>({ craftSlug: matching(/^\S{1,200}$/, "a craft slug") })
  }),
  open_stage: object<Extract<ClientToolCall, { name: "open_stage" }>>({
    name: oneOf(["open_stage"] as const),
    parameters: object<{ stageId: string }>({ stageId: UUID })
  }),
  show_sources: object<Extract<ClientToolCall, { name: "show_sources" }>>({
    name: oneOf(["show_sources"] as const),
    parameters: object<{ answerId: string }>({ answerId: UUID })
  }),
  offer_image: object<Extract<ClientToolCall, { name: "offer_image" }>>({
    name: oneOf(["offer_image"] as const),
    parameters: object<{ stageId: string }>({ stageId: UUID })
  })
});

export const voiceTranscriptShape: Shape<VoiceTranscript> = object<VoiceTranscript>({
  voiceSessionId: UUID,
  language: LANGUAGE,
  mode: MODE,
  craft: nullable(craftLinkShape),
  retentionUntil: INSTANT,
  turns: list(
    object<VoiceTurn>({
      turnId: UUID,
      ordinal: integer,
      heard: text,
      answerId: nullable(UUID),
      sentences: list(answerSentenceShape),
      spoken: text,
      actions: list(clientToolCallShape)
    })
  ),
  sources: list(sourceRefShape)
});

const TURN_EVENTS: { [K in VoiceTurnEvent["type"]]: Shape<Extract<VoiceTurnEvent, { type: K }>["data"]> } = {
  heard: object<{ text: string; language: VoiceLanguage }>({ text, language: LANGUAGE }),
  status: answerStatusShape,
  source: sourceRefShape,
  sentence: object<{ sentence: AnswerSentence }>({ sentence: answerSentenceShape }),
  action: clientToolCallShape,
  spoken: object<{ text: string; speechPath: string }>({ text, speechPath: matching(/^\/api\/voice\/session\/[0-9a-f-]{36}\/turns\/[0-9a-f-]{36}\/speech$/, "a speech path") }),
  error: object<{ message: string }>({ message: text }),
  done: object<VoiceTurnDone>({ turnId: UUID, answerId: nullable(UUID), billedSeconds: integer, remainingSeconds: SECONDS, sessionEnded: boolean })
};

function isTurnEvent(name: string): name is VoiceTurnEvent["type"] {
  return Object.hasOwn(TURN_EVENTS, name);
}

export function parseVoiceTurnBlock(block: string): VoiceTurnEvent | null {
  const { name, data } = sseFields(block);
  if (!isTurnEvent(name) || data === null) return null;
  let payload: unknown;
  try {
    payload = JSON.parse(data);
  } catch {
    throw new ShapeError(name, "a JSON payload");
  }
  return { type: name, data: TURN_EVENTS[name].parse(payload, name) } as VoiceTurnEvent;
}
