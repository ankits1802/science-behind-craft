import { boolean, integer, list, nullable, object, text, type Shape } from "@/lib/shape";

export type SectionFact = { id: string; text: string };
export type ReviewedSentence = { text: string; facts: SectionFact[] };
export type SectionCheck = { check: string; passed: boolean; reasons: string[] };
export type SectionSubject = { kind: string; slug: string };

export type SectionReview = {
  subject: SectionSubject;
  subjectName: string;
  pageUrl: string;
  field: string;
  proposed: ReviewedSentence[];
  published: ReviewedSentence[];
  publishedVersion: number | null;
  note: string | null;
  taskKey: string | null;
  checks: SectionCheck[];
  stale: string | null;
};

const sentenceShape: Shape<ReviewedSentence> = object<ReviewedSentence>({
  text,
  facts: list(object<SectionFact>({ id: text, text }))
});

export const sectionReviewShape: Shape<SectionReview> = object<SectionReview>({
  subject: object<SectionSubject>({ kind: text, slug: text }),
  subjectName: text,
  pageUrl: text,
  field: text,
  proposed: list(sentenceShape),
  published: list(sentenceShape),
  publishedVersion: nullable(integer),
  note: nullable(text),
  taskKey: nullable(text),
  checks: list(object<SectionCheck>({ check: text, passed: boolean, reasons: list(text) })),
  stale: nullable(text)
});
