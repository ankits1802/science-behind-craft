import { citationShape, INSTANT, UUID } from "@/lib/answerShapes";
import { BLOCK_ID, type ReuseMarker } from "@/lib/explainerBlockBase";
import { PARTIAL_DATE } from "@/lib/explainerInsight";
import { integer, list, matching, nullable, object, oneOf, ShapeError, text, type Shape } from "@/lib/shape";
import type { Citation } from "@/lib/types";

export const VOICE_ORIGINS = ["DESIGNER", "FIELD_REPOSITORY", "KALAVIGYAN"] as const;
export const VOICE_ROLES = ["ARTISAN", "DESIGNER"] as const;
export const VOICE_ENGLISH_SOURCES = ["ORIGINAL", "MACHINE", "EDITED", "REVIEWED"] as const;
export const VOICE_QUOTE_MAX_CHARS = 600;
export const VOICE_LANGUAGE = matching(/^(?:und|[a-z]{2,3}(?:-[A-Za-z0-9]{1,8})*)$/, "a BCP 47 language tag or und");

export type VoiceOrigin = (typeof VOICE_ORIGINS)[number];
export type VoiceSpeaker = {
  name: string | null;
  line: string;
  role: (typeof VOICE_ROLES)[number];
  yearsInCraft: number | null;
  district: string | null;
  state: string | null;
};
export type VoiceQuote = {
  itemId: string;
  origin: VoiceOrigin;
  speaker: VoiceSpeaker;
  quote: string;
  language: string;
  english: string | null;
  englishSource: (typeof VOICE_ENGLISH_SOURCES)[number] | null;
  sourceId: string;
  locator: string;
  workshop: string | null;
  recordedOn: string;
  corroboratedBy: Citation[];
};
export type ArtisanVoiceBlock = {
  id: string;
  kind: "artisan_voice";
  version: 2;
  reuse: ReuseMarker | null;
  quotes: VoiceQuote[];
  removed: number;
};

const QUOTE_TEXT: Shape<string> = {
  expected: `a quote of at most ${VOICE_QUOTE_MAX_CHARS} characters`,
  parse(value, path) {
    const quote = text.parse(value, path);
    if (quote.length > VOICE_QUOTE_MAX_CHARS) throw new ShapeError(path, `at most ${VOICE_QUOTE_MAX_CHARS} characters`);
    return quote;
  }
};

export const voiceSpeakerShape: Shape<VoiceSpeaker> = object<VoiceSpeaker>({
  name: nullable(text),
  line: text,
  role: oneOf(VOICE_ROLES),
  yearsInCraft: nullable(integer),
  district: nullable(text),
  state: nullable(text)
});

const voiceFields = {
  itemId: text,
  origin: oneOf(VOICE_ORIGINS),
  speaker: voiceSpeakerShape,
  quote: QUOTE_TEXT,
  language: VOICE_LANGUAGE,
  english: nullable(text),
  englishSource: nullable(oneOf(VOICE_ENGLISH_SOURCES)),
  sourceId: text,
  locator: text,
  workshop: nullable(text),
  recordedOn: PARTIAL_DATE,
  corroboratedBy: list(citationShape)
};

export const voiceQuoteShape: Shape<VoiceQuote> = checkedVoice(object<VoiceQuote>(voiceFields));

export function voiceQuoteFields() {
  return voiceFields;
}

export function checkedVoice<T extends VoiceQuote>(shape: Shape<T>): Shape<T> {
  return {
    expected: shape.expected,
    parse(value, path) {
      const quote = shape.parse(value, path);
      if ((quote.english === null) !== (quote.englishSource === null)) throw new ShapeError(path, "english and englishSource together");
      return quote;
    }
  };
}

export const artisanVoiceBlockShape: Shape<ArtisanVoiceBlock> = {
  expected: "an artisan voice block, version 2",
  parse(value, path) {
    const block = object<ArtisanVoiceBlock>({
      id: BLOCK_ID,
      kind: oneOf(["artisan_voice"] as const),
      version: oneOf([2] as const),
      reuse: nullable(object<ReuseMarker>({ pieceId: UUID, storedAt: INSTANT })),
      quotes: list(voiceQuoteShape),
      removed: integer
    }).parse(value, path);
    if (block.removed < 0) throw new ShapeError(path ? `${path}.removed` : "removed", "never negative");
    if (block.quotes.length === 0 && block.removed === 0) throw new ShapeError(path ? `${path}.quotes` : "quotes", "a quote, or a count of removed quotes");
    return block;
  }
};
