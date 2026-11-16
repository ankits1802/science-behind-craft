import { sourceNumbers } from "@/lib/citations";
import type { AnswerSentence, SourceRef } from "@/lib/types";
import type { ClientToolCall, VoiceTranscript, VoiceTurn, VoiceTurnEvent } from "@/lib/voiceContract";

export type TurnDraft = {
  heard: string | null;
  sentences: AnswerSentence[];
  actions: ClientToolCall[];
  spoken: string | null;
};

export type VoiceConversation = {
  turns: VoiceTurn[];
  sources: SourceRef[];
  draft: TurnDraft | null;
  heardLive: string | null;
  status: string | null;
  problem: string | null;
};

export const EMPTY_CONVERSATION: VoiceConversation = { turns: [], sources: [], draft: null, heardLive: null, status: null, problem: null };

const EMPTY_DRAFT: TurnDraft = { heard: null, sentences: [], actions: [], spoken: null };

function withDraft(conversation: VoiceConversation, change: Partial<TurnDraft>): VoiceConversation {
  return { ...conversation, draft: { ...(conversation.draft ?? EMPTY_DRAFT), ...change } };
}

function closedTurn(conversation: VoiceConversation, turnId: string, answerId: string | null): VoiceTurn | null {
  const draft = conversation.draft;
  if (!draft?.heard) return null;
  return {
    turnId,
    ordinal: conversation.turns.length + 1,
    heard: draft.heard,
    answerId,
    sentences: draft.sentences,
    spoken: draft.spoken ?? "",
    actions: draft.actions
  };
}

export function reduceRelayEvent(conversation: VoiceConversation, event: VoiceTurnEvent): VoiceConversation {
  const draft = conversation.draft ?? EMPTY_DRAFT;
  switch (event.type) {
    case "heard":
      return { ...conversation, draft: { ...EMPTY_DRAFT, heard: event.data.text }, problem: null };
    case "status":
      return { ...conversation, status: event.data.message };
    case "source":
      if (conversation.sources.some((source) => source.id === event.data.id)) return conversation;
      return { ...conversation, sources: [...conversation.sources, event.data] };
    case "sentence":
      if (draft.sentences.some((sentence) => sentence.id === event.data.sentence.id)) return conversation;
      return withDraft(conversation, { sentences: [...draft.sentences, event.data.sentence] });
    case "action":
      return withDraft(conversation, { actions: [...draft.actions, event.data] });
    case "spoken":
      return withDraft(conversation, { spoken: event.data.text });
    case "error":
      return { ...conversation, problem: event.data.message };
    case "done": {
      const turn = closedTurn(conversation, event.data.turnId, event.data.answerId);
      return { ...conversation, turns: turn ? [...conversation.turns, turn] : conversation.turns, draft: null, status: null };
    }
  }
}

export function withTranscript(conversation: VoiceConversation, transcript: VoiceTranscript): VoiceConversation {
  const grew = transcript.turns.length > conversation.turns.length;
  return {
    ...conversation,
    turns: transcript.turns,
    sources: transcript.sources,
    heardLive: grew ? null : conversation.heardLive
  };
}

export function conversationSourceNumbers(conversation: VoiceConversation): Map<string, number> {
  const sections = conversation.turns.map((turn) => ({ id: turn.turnId, heading: "", sentences: turn.sentences }));
  if (conversation.draft) sections.push({ id: "draft", heading: "", sentences: conversation.draft.sentences });
  return sourceNumbers(sections);
}

export function answerIdsOf(turns: readonly VoiceTurn[]): Set<string> {
  return new Set(turns.flatMap((turn) => (turn.answerId ? [turn.answerId] : [])));
}

export function sourcesOfAnswer(turns: readonly VoiceTurn[], answerId: string): Set<string> {
  const turn = turns.find((candidate) => candidate.answerId === answerId);
  return new Set(turn?.sentences.flatMap((sentence) => sentence.citations.map((citation) => citation.sourceId)) ?? []);
}
