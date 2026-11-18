import { apiFetch } from "@/lib/api";
import { craftLinkShape, HTTPS_URL, INSTANT, UUID, type CraftLink } from "@/lib/answerShapes";
import { checkedVoice, voiceQuoteFields, VOICE_ENGLISH_SOURCES, VOICE_LANGUAGE, type VoiceQuote } from "@/lib/explainerVoices";
import { boolean, integer, list, matching, nullable, object, oneOf, parseShape, ShapeError, text, type Shape } from "@/lib/shape";

export const FIELD_ORIGINS = ["DESIGNER", "FIELD_REPOSITORY"] as const;
export const STAGE_LINK_KINDS = ["DESIGN_STAGE", "QUESTION", "RECORD"] as const;
export const PHOTO_GROUP_KINDS = ["PRODUCT", "TOOL", "PROCESS", "PROCESS_STEP", "PROTOTYPE", "DESIGN_STAGE", "CRAFT", "PERSON", "SESSION", "WORKSHOP"] as const;
export const FIELD_LIST_KINDS = ["quotes", "images"] as const;
export const LINE_ROLES = ["ARTISAN", "DESIGNER", "RESEARCHER", "OTHER"] as const;
export const FIELD_LIST_PAGE_SIZE = 25;

export type FieldListKind = (typeof FIELD_LIST_KINDS)[number];
export type VoiceStage = { kind: (typeof STAGE_LINK_KINDS)[number]; key: string | null; label: string };
export type PageVoice = VoiceQuote & { stage: VoiceStage | null; citation: string; recordingId: string | null };
export type PhotoGroup = { kind: (typeof PHOTO_GROUP_KINDS)[number]; key: string; label: string };
export type PageFieldPhoto = {
  itemId: string;
  origin: (typeof FIELD_ORIGINS)[number];
  imageUrl: string;
  width: number;
  height: number;
  caption: string | null;
  alt: string;
  credit: string;
  credited: string[];
  workshop: string | null;
  takenOn: string | null;
  groups: PhotoGroup[];
  statement: string;
  rightsHolder: string;
  licence: null;
};
export type FieldVoicesTotals = { quotes: number; images: number };
export type FieldVoicesList = {
  schemaVersion: 1;
  craft: CraftLink;
  kind: FieldListKind;
  total: number;
  cursor: string | null;
  nextCursor: string | null;
  quotes: PageVoice[];
  images: PageFieldPhoto[];
};
export type TranscriptSpeaker = { key: string; label: string; role: (typeof LINE_ROLES)[number] | null };
export type TranscriptLine = {
  id: string;
  position: number;
  speakerKey: string | null;
  locator: string;
  language: string;
  text: string;
  english: string | null;
  englishSource: (typeof VOICE_ENGLISH_SOURCES)[number] | null;
  quotable: boolean;
};
export type FieldTranscript = {
  schemaVersion: 1;
  id: string;
  origin: (typeof FIELD_ORIGINS)[number];
  publisher: string;
  title: string;
  mediaType: "AUDIO" | "VIDEO";
  recordedAt: string;
  durationMs: number | null;
  crafts: CraftLink[];
  workshop: string | null;
  context: string[];
  stage: VoiceStage | null;
  speakers: TranscriptSpeaker[];
  lines: TranscriptLine[];
  english: string | null;
  englishSource: "MACHINE" | "EDITED" | null;
  sourceId: string;
  citation: string;
};

const CALENDAR_DAY = matching(/^\d{4}-\d{2}-\d{2}$/, "a date");
const COUNT: Shape<number> = {
  expected: "a count from 0",
  parse(value, path) {
    const whole = integer.parse(value, path);
    if (whole < 0) throw new ShapeError(path, "a count from 0");
    return whole;
  }
};
const NO_LICENCE: Shape<null> = {
  expected: "null: not openly licensed",
  parse(value, path) {
    if (value !== null) throw new ShapeError(path, "null: field photographs are not openly licensed");
    return null;
  }
};

export const voiceStageShape: Shape<VoiceStage> = object<VoiceStage>({ kind: oneOf(STAGE_LINK_KINDS), key: nullable(text), label: text });

export const pageVoiceShape: Shape<PageVoice> = checkedVoice(
  object<PageVoice>({ ...voiceQuoteFields(), stage: nullable(voiceStageShape), citation: text, recordingId: nullable(UUID) })
);

export const pageFieldPhotoShape: Shape<PageFieldPhoto> = object<PageFieldPhoto>({
  itemId: text,
  origin: oneOf(FIELD_ORIGINS),
  imageUrl: HTTPS_URL,
  width: integer,
  height: integer,
  caption: nullable(text),
  alt: text,
  credit: text,
  credited: list(text),
  workshop: nullable(text),
  takenOn: nullable(CALENDAR_DAY),
  groups: list(object<PhotoGroup>({ kind: oneOf(PHOTO_GROUP_KINDS), key: text, label: text }), 1),
  statement: text,
  rightsHolder: text,
  licence: NO_LICENCE
});

export const fieldVoicesTotalsShape: Shape<FieldVoicesTotals> = object<FieldVoicesTotals>({ quotes: COUNT, images: COUNT });

export const fieldVoicesListShape: Shape<FieldVoicesList> = {
  expected: "a page of a craft's field voices",
  parse(value, path) {
    const page = object<FieldVoicesList>({
      schemaVersion: oneOf([1] as const),
      craft: craftLinkShape,
      kind: oneOf(FIELD_LIST_KINDS),
      total: COUNT,
      cursor: nullable(text),
      nextCursor: nullable(text),
      quotes: list(pageVoiceShape),
      images: list(pageFieldPhotoShape)
    }).parse(value, path);
    const other = page.kind === "quotes" ? page.images : page.quotes;
    if (other.length) throw new ShapeError(path, `a ${page.kind} page holds only ${page.kind}`);
    if (page.quotes.length + page.images.length > FIELD_LIST_PAGE_SIZE) throw new ShapeError(path, `at most ${FIELD_LIST_PAGE_SIZE} items`);
    return page;
  }
};

export const fieldTranscriptShape: Shape<FieldTranscript> = {
  expected: "a field recording's transcript",
  parse(value, path) {
    const transcript = object<FieldTranscript>({
      schemaVersion: oneOf([1] as const),
      id: UUID,
      origin: oneOf(FIELD_ORIGINS),
      publisher: text,
      title: text,
      mediaType: oneOf(["AUDIO", "VIDEO"] as const),
      recordedAt: INSTANT,
      durationMs: nullable(integer),
      crafts: list(craftLinkShape),
      workshop: nullable(text),
      context: list(text),
      stage: nullable(voiceStageShape),
      speakers: list(object<TranscriptSpeaker>({ key: text, label: text, role: nullable(oneOf(LINE_ROLES)) })),
      lines: list(
        object<TranscriptLine>({
          id: text,
          position: COUNT,
          speakerKey: nullable(text),
          locator: text,
          language: VOICE_LANGUAGE,
          text,
          english: nullable(text),
          englishSource: nullable(oneOf(VOICE_ENGLISH_SOURCES)),
          quotable: boolean
        }),
        1
      ),
      english: nullable(text),
      englishSource: nullable(oneOf(["MACHINE", "EDITED"] as const)),
      sourceId: UUID,
      citation: text
    }).parse(value, path);
    const keys = new Set(transcript.speakers.map((speaker) => speaker.key));
    for (const line of transcript.lines) {
      if (line.speakerKey !== null && !keys.has(line.speakerKey)) throw new ShapeError(`${path}.lines`, `a speaker the transcript lists, not ${line.speakerKey}`);
    }
    return transcript;
  }
};

export const FIELD_VOICES_PATH = (slug: string, kind: FieldListKind, cursor: string | null) =>
  `/crafts/${encodeURIComponent(slug)}/field-voices?kind=${kind}${cursor === null ? "" : `&cursor=${encodeURIComponent(cursor)}`}`;
export const FIELD_TRANSCRIPT_PATH = (id: string) => `/field-voices/recordings/${encodeURIComponent(id)}`;

export async function fetchFieldVoices(slug: string, kind: FieldListKind, cursor: string | null): Promise<FieldVoicesList> {
  return parseShape(fieldVoicesListShape, await apiFetch<unknown>(FIELD_VOICES_PATH(slug, kind, cursor)));
}

export async function fetchFieldTranscript(id: string): Promise<FieldTranscript> {
  return parseShape(fieldTranscriptShape, await apiFetch<unknown>(FIELD_TRANSCRIPT_PATH(id)));
}
