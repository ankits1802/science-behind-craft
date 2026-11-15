import { apiFetch } from "@/lib/api";
import type { AnswerMode } from "@/lib/types";

export type AskConfig = {
  modes: AnswerMode[];
  defaultMode: AnswerMode;
  voice: { configured: boolean; languages: string[] };
  languages: { code: string; label: string }[];
};

export const FALLBACK_ASK_CONFIG: AskConfig = {
  modes: ["VERIFIED", "HYBRID"],
  defaultMode: "HYBRID",
  voice: { configured: false, languages: [] },
  languages: [{ code: "en", label: "English" }]
};

export const MODE_LABEL: Record<AnswerMode, string> = {
  VERIFIED: "Verified only",
  HYBRID: "Hybrid",
  DEEP: "Deep"
};

export function fetchAskConfig(): Promise<AskConfig> {
  return apiFetch<AskConfig>("/answers/config");
}

export function normaliseAskConfig(raw: Partial<AskConfig> | null | undefined): AskConfig {
  const modes = Array.isArray(raw?.modes) && raw.modes.length > 0 ? raw.modes.filter((mode): mode is AnswerMode => mode in MODE_LABEL) : FALLBACK_ASK_CONFIG.modes;
  const defaultMode = raw?.defaultMode && modes.includes(raw.defaultMode) ? raw.defaultMode : modes.includes("HYBRID") ? "HYBRID" : modes[0];
  return {
    modes,
    defaultMode,
    voice: { configured: Boolean(raw?.voice?.configured), languages: raw?.voice?.languages ?? [] },
    languages: Array.isArray(raw?.languages) && raw.languages.length > 0 ? raw.languages : FALLBACK_ASK_CONFIG.languages
  };
}
