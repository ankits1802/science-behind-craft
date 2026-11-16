import { ApiError, apiErrorMessage } from "@/lib/api";
import { AUTO_LANGUAGE, resolvedLanguage, type AnswerLanguage } from "@/lib/answerLanguages";
import { parseShape, ShapeError } from "@/lib/shape";
import type { AnswerMode } from "@/lib/types";
import {
  clientToolCallShape,
  MIN_START_SECONDS,
  voiceAvailabilityShape,
  type ClientToolCall,
  type VoiceAvailability,
  type VoiceMode
} from "@/lib/voiceContract";

export type VoiceSupport = { agent: boolean; relayTypes: readonly string[] };

export const NO_VOICE_SUPPORT: VoiceSupport = { agent: false, relayTypes: [] };

export const NO_VOICE: VoiceAvailability = {
  configured: false,
  transport: null,
  languages: [],
  noticeVersion: null,
  consentRequired: false,
  remainingSeconds: null
};

export function voiceAvailabilityOf(raw: unknown): VoiceAvailability {
  if (raw === undefined || raw === null) return NO_VOICE;
  try {
    return parseShape(voiceAvailabilityShape, raw);
  } catch (error) {
    if (!(error instanceof ShapeError)) throw error;
    console.error(new ShapeError(`answers/config voice.${error.path}`, error.expected));
    return NO_VOICE;
  }
}

export function voiceOffered(availability: VoiceAvailability, support: VoiceSupport): boolean {
  if (!availability.configured || availability.transport === null || availability.languages.length === 0) return false;
  if (availability.remainingSeconds !== null && availability.remainingSeconds < MIN_START_SECONDS) return false;
  return availability.transport === "AGENT" ? support.agent : support.relayTypes.length > 0;
}

export function voiceMode(mode: AnswerMode): VoiceMode {
  return mode === "VERIFIED" ? "VERIFIED" : "HYBRID";
}

export function voiceLanguage(availability: VoiceAvailability, choice: string, spoken = ""): AnswerLanguage | null {
  const offered = availability.languages;
  if (offered.length === 0) return null;
  const resolved = resolvedLanguage(choice, spoken, offered);
  return offered.find((language) => language.code === resolved.code) ?? offered[0];
}

export function voicePickerValue(availability: VoiceAvailability, choice: string, chosen: AnswerLanguage): string {
  if (choice === AUTO_LANGUAGE || availability.languages.some((language) => language.code === choice)) return choice;
  return chosen.code;
}

export type HeldFacts = {
  craftSlug: string | null;
  stageIds: ReadonlySet<string>;
  answerIds: ReadonlySet<string>;
  imageStageIds: ReadonlySet<string>;
};

export function toolCallOf(raw: unknown): ClientToolCall | null {
  try {
    return parseShape(clientToolCallShape, raw);
  } catch (error) {
    if (error instanceof ShapeError) return null;
    throw error;
  }
}

export function isHeldToolCall(call: ClientToolCall, held: HeldFacts): boolean {
  switch (call.name) {
    case "show_on_map":
      return held.craftSlug !== null && call.parameters.craftSlug === held.craftSlug;
    case "open_stage":
      return held.stageIds.has(call.parameters.stageId);
    case "show_sources":
      return held.answerIds.has(call.parameters.answerId);
    case "offer_image":
      return held.stageIds.has(call.parameters.stageId) && held.imageStageIds.has(call.parameters.stageId);
  }
}

export function toolCallSignature(call: ClientToolCall): string {
  return `${call.name}:${Object.values(call.parameters).join(",")}`;
}

export type ActionLedger = { applied: ReadonlySet<string>; prepaid: ReadonlyMap<string, number> };

export const EMPTY_LEDGER: ActionLedger = { applied: new Set(), prepaid: new Map() };

export function prepayAction(ledger: ActionLedger, call: ClientToolCall): ActionLedger {
  const signature = toolCallSignature(call);
  const prepaid = new Map(ledger.prepaid);
  prepaid.set(signature, (prepaid.get(signature) ?? 0) + 1);
  return { applied: ledger.applied, prepaid };
}

export function unappliedActions(turns: readonly { turnId: string; actions: readonly ClientToolCall[] }[], ledger: ActionLedger): { calls: ClientToolCall[]; ledger: ActionLedger } {
  const applied = new Set(ledger.applied);
  const prepaid = new Map(ledger.prepaid);
  const calls: ClientToolCall[] = [];
  for (const turn of turns) {
    turn.actions.forEach((call, index) => {
      const key = `${turn.turnId}#${index}`;
      if (applied.has(key)) return;
      applied.add(key);
      const signature = toolCallSignature(call);
      const credit = prepaid.get(signature) ?? 0;
      if (credit > 0) prepaid.set(signature, credit - 1);
      else calls.push(call);
    });
  }
  return { calls, ledger: { applied, prepaid } };
}

const MEDIA_ERRORS: Record<string, string> = {
  NotAllowedError: "Allow the microphone to talk.",
  SecurityError: "Allow the microphone to talk.",
  NotFoundError: "No microphone found.",
  NotReadableError: "The microphone is in use by another app."
};

export function isMediaRefusal(error: unknown): error is Error {
  return error instanceof Error && Object.hasOwn(MEDIA_ERRORS, error.name);
}

export function voiceFailure(error: unknown, fallback: string): string {
  if (error instanceof ApiError) return apiErrorMessage(error, fallback);
  if (isMediaRefusal(error)) return MEDIA_ERRORS[error.name];
  return fallback;
}

export function sessionGone(error: unknown): boolean {
  return error instanceof ApiError && (error.status === 404 || error.status === 410);
}
