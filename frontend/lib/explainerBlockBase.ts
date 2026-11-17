import { answerSentenceShape, INSTANT, UUID } from "@/lib/answerShapes";
import { list, matching, nullable, object, oneOf, ShapeError, text, type Shape } from "@/lib/shape";
import type { AnswerSentence } from "@/lib/types";

export type TermSpan = { text: string; termKey: string };
export type ExplainerSentence = AnswerSentence & { terms: TermSpan[] };
export type ReuseMarker = { pieceId: string; storedAt: string };
export type BlockEnvelope<K extends string> = { id: string; kind: K; version: 1; reuse: ReuseMarker | null };

export const BLOCK_ID = matching(/^[a-z0-9]+(?:[.-][a-z0-9]+)*$/, "a block id");
export const TERM_KEY = matching(/^[a-z0-9]+(?:-[a-z0-9]+)*$/, "a term key");
export const WIKIDATA_ID = matching(/^Q[1-9]\d*$/, "a Wikidata id");

const termSpanShape: Shape<TermSpan> = object<TermSpan>({ text, termKey: TERM_KEY });

export const explainerSentenceShape: Shape<ExplainerSentence> = {
  expected: "a cited sentence with its marked terms",
  parse(value, path) {
    if (typeof value !== "object" || value === null || Array.isArray(value)) throw new ShapeError(path, "an object");
    const { terms, ...sentence } = value as Record<string, unknown>;
    return { ...answerSentenceShape.parse(sentence, path), terms: list(termSpanShape).parse(terms, path ? `${path}.terms` : "terms") };
  }
};

export function envelope<K extends string>(kind: K) {
  return {
    id: BLOCK_ID,
    kind: oneOf([kind] as const) as Shape<K>,
    version: oneOf([1] as const),
    reuse: nullable(object<ReuseMarker>({ pieceId: UUID, storedAt: INSTANT }))
  };
}
