import { answerSentenceShape, craftLinkShape, sourceRefShape, type CraftLink } from "@/lib/answerShapes";
import { catalogueSummaryShape, type CatalogueSummary } from "@/lib/craftCatalogueContract";
import { heroImageShape, type HeroImage } from "@/lib/craftPageContext";
import { integer, list, nullable, number, object, oneOf, parseShape, ShapeError, text, type Shape } from "@/lib/shape";
import type { AnswerSentence, SourceRef } from "@/lib/types";

export const PUBLIC_SUMMARY_PATH = "/public/summary";
export const PUBLIC_SUMMARY_SCHEMA_VERSION = 1;
export const FEATURED_CRAFTS_MAX = 3;

export type FeaturedCraft = { craft: CraftLink; localName: string | null; hero: HeroImage | null; lede: AnswerSentence };
export type Specimen = { craft: CraftLink; sentence: AnswerSentence };
export type PlacedPoint = { key: string; name: string; latitude: number; longitude: number; total: number; curated: CraftLink[] };
export type PublicSummary = {
  schemaVersion: typeof PUBLIC_SUMMARY_SCHEMA_VERSION;
  counts: CatalogueSummary;
  featured: FeaturedCraft[];
  specimen: Specimen | null;
  sources: SourceRef[];
  points: PlacedPoint[];
};

const featuredShape: Shape<FeaturedCraft> = object<FeaturedCraft>({
  craft: craftLinkShape,
  localName: nullable(text),
  hero: nullable(heroImageShape),
  lede: answerSentenceShape
});

const pointShape: Shape<PlacedPoint> = object<PlacedPoint>({
  key: text,
  name: text,
  latitude: number,
  longitude: number,
  total: integer,
  curated: list(craftLinkShape)
});

export const publicSummaryShape: Shape<PublicSummary> = object<PublicSummary>({
  schemaVersion: oneOf([PUBLIC_SUMMARY_SCHEMA_VERSION] as const),
  counts: catalogueSummaryShape,
  featured: list(featuredShape),
  specimen: nullable(object<Specimen>({ craft: craftLinkShape, sentence: answerSentenceShape })),
  sources: list(sourceRefShape),
  points: list(pointShape)
});

export function summarySentences(summary: PublicSummary): AnswerSentence[] {
  return [...summary.featured.map((entry) => entry.lede), ...(summary.specimen ? [summary.specimen.sentence] : [])];
}

export function parsePublicSummary(raw: unknown): PublicSummary {
  const summary = parseShape(publicSummaryShape, raw);
  if (summary.featured.length > FEATURED_CRAFTS_MAX) throw new ShapeError("featured", `at most ${FEATURED_CRAFTS_MAX} crafts`);
  const cited = [...new Set(summarySentences(summary).flatMap((sentence) => sentence.citations.map((citation) => citation.sourceId)))];
  const listed = summary.sources.map((source) => source.id);
  if (cited.join("\n") !== listed.join("\n")) throw new ShapeError("sources", "the cited sources, once each, in the order first cited");
  return summary;
}
