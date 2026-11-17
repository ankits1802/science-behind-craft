import { languageCodeShape } from "@/lib/answerLanguages";
import { craftLinkShape, HTTPS_URL, INSTANT, sourceRefShape, UUID, type CraftLink } from "@/lib/answerShapes";
import { explainerSentenceShape, mediaRefShape, type ExplainerSentence, type MediaRef } from "@/lib/explainerBlockBase";
import { SECTION_ID } from "@/lib/explainerContract";
import { quizBlockShape, type QuizBlock } from "@/lib/explainerLearning";
import { EXPLAINER_VERSION_PATH } from "@/lib/learningContract";
import { boolean, integer, list, matching, nullable, object, oneOf, optional, text, type Shape } from "@/lib/shape";
import type { SourceRef } from "@/lib/types";

export const SLIDE_KINDS = ["TITLE", "SECTION", "QUIZ", "READING", "SOURCES"] as const;
export const LESSON_FORMATS = ["html", "pptx", "pdf"] as const;
export const CITATION_FORMATS = ["bib", "ris", "txt", "json"] as const;
export const LESSONS_PATH = "/lessons";
export const LESSON_PATH = (lessonId: string) => `${LESSONS_PATH}/${encodeURIComponent(lessonId)}`;
export const LESSON_FILE_PATH = (lessonId: string, format: LessonFormat) => `${LESSON_PATH(lessonId)}/files/${format}`;
export const EXPLAINER_PDF_PATH = (explainerId: string, version: number) => `${EXPLAINER_VERSION_PATH(explainerId, version)}/pdf`;
export const CITATIONS_PATH = (explainerId: string, version: number) => `${EXPLAINER_VERSION_PATH(explainerId, version)}/citations`;
export const CITATIONS_FILE_PATH = (explainerId: string, version: number, format: CitationFormat) =>
  `${CITATIONS_PATH(explainerId, version)}/${format}`;

export type LessonFormat = (typeof LESSON_FORMATS)[number];
export type CitationFormat = (typeof CITATION_FORMATS)[number];
export type LessonRequest = { explainerId: string; version: number; title: string | null; sectionIds: string[]; quiz: boolean };
export type Slide = {
  number: number;
  kind: (typeof SLIDE_KINDS)[number];
  title: string;
  sectionId: string | null;
  blockIds: string[];
  bullets: ExplainerSentence[];
  image: MediaRef | null;
  question: number | null;
};
export type ReadingItem = { source: SourceRef; citedBy: number };
export type LessonPack = {
  schemaVersion: 1;
  id: string;
  explainerId: string;
  version: number;
  title: string;
  craft: CraftLink | null;
  language: string;
  createdAt: string;
  slides: Slide[];
  readingList: ReadingItem[];
  quiz: QuizBlock | null;
  sources: SourceRef[];
};
export type LessonSummary = {
  id: string;
  title: string;
  explainerId: string;
  version: number;
  craft: CraftLink | null;
  createdAt: string;
  slideCount: number;
};
export type LessonList = { schemaVersion: 1; items: LessonSummary[] };
export type CslName = { literal: string };
export type CslItem = {
  id: string;
  type: string;
  title: string;
  author: CslName[];
  issued?: { "date-parts": number[][] };
  accessed?: { "date-parts": number[][] };
  publisher?: string;
  version?: string;
  DOI?: string;
  URL?: string;
};
export type CitationEntry = {
  number: number;
  sourceId: string | null;
  datasetCode: string | null;
  csl: CslItem;
  apa: string;
  bibtex: string;
  ris: string;
};
export type ExportLink = { schemaVersion: 1; format: LessonFormat; fileName: string; url: string; expiresAt: string };
export type CitationExport = { schemaVersion: 1; explainerId: string; version: number; entries: CitationEntry[] };

export const lessonRequestShape: Shape<LessonRequest> = object<LessonRequest>({
  explainerId: UUID,
  version: integer,
  title: nullable(text),
  sectionIds: list(SECTION_ID, 1),
  quiz: boolean
});

const slideShape: Shape<Slide> = object<Slide>({
  number: integer,
  kind: oneOf(SLIDE_KINDS),
  title: text,
  sectionId: nullable(SECTION_ID),
  blockIds: list(text),
  bullets: list(explainerSentenceShape),
  image: nullable(mediaRefShape),
  question: nullable(integer)
});

export const lessonPackShape: Shape<LessonPack> = object<LessonPack>({
  schemaVersion: oneOf([1] as const),
  id: UUID,
  explainerId: UUID,
  version: integer,
  title: text,
  craft: nullable(craftLinkShape),
  language: languageCodeShape,
  createdAt: INSTANT,
  slides: list(slideShape, 3),
  readingList: list(object<ReadingItem>({ source: sourceRefShape, citedBy: integer }), 1),
  quiz: nullable(quizBlockShape),
  sources: list(sourceRefShape)
});

export const lessonListShape: Shape<LessonList> = object<LessonList>({
  schemaVersion: oneOf([1] as const),
  items: list(
    object<LessonSummary>({
      id: UUID,
      title: text,
      explainerId: UUID,
      version: integer,
      craft: nullable(craftLinkShape),
      createdAt: INSTANT,
      slideCount: integer
    })
  )
});

const cslItemShape: Shape<CslItem> = object<CslItem>({
  id: matching(/^kv[1-9]\d*$/, "a citation key"),
  type: text,
  title: text,
  author: list(object<CslName>({ literal: text })),
  issued: optional(object<{ "date-parts": number[][] }>({ "date-parts": list(list(integer, 1), 1) })),
  accessed: optional(object<{ "date-parts": number[][] }>({ "date-parts": list(list(integer, 1), 1) })),
  publisher: optional(text),
  version: optional(text),
  DOI: optional(text),
  URL: optional(HTTPS_URL)
});

export const citationExportShape: Shape<CitationExport> = object<CitationExport>({
  schemaVersion: oneOf([1] as const),
  explainerId: UUID,
  version: integer,
  entries: list(
    object<CitationEntry>({
      number: integer,
      sourceId: nullable(text),
      datasetCode: nullable(text),
      csl: cslItemShape,
      apa: text,
      bibtex: text,
      ris: text
    }),
    1
  )
});

export const exportLinkShape: Shape<ExportLink> = object<ExportLink>({
  schemaVersion: oneOf([1] as const),
  format: oneOf(LESSON_FORMATS),
  fileName: matching(/^[A-Za-z0-9_.-]+$/, "a file name"),
  url: HTTPS_URL,
  expiresAt: INSTANT
});
