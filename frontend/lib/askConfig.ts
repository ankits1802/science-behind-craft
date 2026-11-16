import { apiFetch } from "@/lib/api";
import { answerLanguagesOf, ENGLISH, type AnswerLanguage } from "@/lib/answerLanguages";
import type { AnswerMode } from "@/lib/types";
import type { VoiceAvailability } from "@/lib/voiceContract";
import { NO_VOICE, voiceAvailabilityOf } from "@/lib/voiceRules";

export type AskConfig = {
  modes: AnswerMode[];
  defaultMode: AnswerMode;
  voice: VoiceAvailability;
  languages: AnswerLanguage[];
};

export const FALLBACK_ASK_CONFIG: AskConfig = {
  modes: ["VERIFIED", "HYBRID"],
  defaultMode: "HYBRID",
  voice: NO_VOICE,
  languages: [ENGLISH]
};

export const MODE_LABEL: Record<AnswerMode, string> = {
  VERIFIED: "Verified only",
  HYBRID: "Hybrid",
  DEEP: "Deep"
};

export type RawAskConfig = Partial<Omit<AskConfig, "voice" | "languages">> & { voice?: unknown; languages?: unknown };

export function fetchAskConfig(): Promise<RawAskConfig> {
  return apiFetch<RawAskConfig>("/answers/config");
}

export function normaliseAskConfig(raw: RawAskConfig | null | undefined): AskConfig {
  const modes = Array.isArray(raw?.modes) && raw.modes.length > 0 ? raw.modes.filter((mode): mode is AnswerMode => mode in MODE_LABEL) : FALLBACK_ASK_CONFIG.modes;
  const defaultMode = raw?.defaultMode && modes.includes(raw.defaultMode) ? raw.defaultMode : modes.includes("HYBRID") ? "HYBRID" : modes[0];
  return {
    modes,
    defaultMode,
    voice: voiceAvailabilityOf(raw?.voice),
    languages: answerLanguagesOf(raw?.languages)
  };
}
