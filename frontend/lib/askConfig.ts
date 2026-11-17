import { apiFetch } from "@/lib/api";
import { answerLanguagesOf, ENGLISH, type AnswerLanguage } from "@/lib/answerLanguages";
import { DEPTHS, type Depth } from "@/lib/explainerContract";
import type { UnderstoodPart } from "@/lib/explainerView";
import { listenLanguagesOf } from "@/lib/listen";
import { list, nullable, object, oneOf, ShapeError, text } from "@/lib/shape";
import type { VoiceAvailability } from "@/lib/voiceContract";
import { NO_VOICE, voiceAvailabilityOf } from "@/lib/voiceRules";

export type DepthOption = { depth: Depth; label: string };

export type AskDepths = { depths: DepthOption[]; defaultDepth: Depth | null };

export type AskConfig = AskDepths & {
  voice: VoiceAvailability;
  languages: AnswerLanguage[];
  listenLanguages: string[];
};

const NO_DEPTHS: AskDepths = { depths: [], defaultDepth: null };

export const FALLBACK_ASK_CONFIG: AskConfig = {
  ...NO_DEPTHS,
  voice: NO_VOICE,
  languages: [ENGLISH],
  listenLanguages: []
};

export type RawAskConfig = { depths?: unknown; defaultDepth?: unknown; voice?: unknown; languages?: unknown; listen?: unknown };

const depthOptionShape = object<DepthOption>({ depth: oneOf(DEPTHS), label: text });

export function fetchAskConfig(): Promise<RawAskConfig> {
  return apiFetch<RawAskConfig>("/answers/config");
}

export function askDepthsOf(depths: unknown, defaultDepth: unknown): AskDepths {
  if (depths === undefined && defaultDepth === undefined) return NO_DEPTHS;
  try {
    const options = list(depthOptionShape).parse(depths, "answers/config depths");
    const chosen = nullable(oneOf(DEPTHS)).parse(defaultDepth, "answers/config defaultDepth");
    if (new Set(options.map((option) => option.depth)).size !== options.length) throw new ShapeError("answers/config depths", "each depth once");
    if (chosen !== null && !options.some((option) => option.depth === chosen)) throw new ShapeError("answers/config defaultDepth", "one of the listed depths");
    return { depths: options, defaultDepth: chosen };
  } catch (error) {
    if (!(error instanceof ShapeError)) throw error;
    console.error(error);
    return NO_DEPTHS;
  }
}

export function normaliseAskConfig(raw: RawAskConfig | null | undefined): AskConfig {
  return {
    ...askDepthsOf(raw?.depths, raw?.defaultDepth),
    voice: voiceAvailabilityOf(raw?.voice),
    languages: answerLanguagesOf(raw?.languages),
    listenLanguages: listenLanguagesOf(raw?.listen)
  };
}

export function changeableParts(config: AskConfig): ReadonlySet<UnderstoodPart> {
  const parts: UnderstoodPart[] = ["craft"];
  if (config.depths.length > 1) parts.push("depth");
  if (config.languages.length > 1) parts.push("language");
  return new Set(parts);
}
