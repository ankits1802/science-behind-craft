import { sourceRefShape } from "@/lib/answerShapes";
import type { Discipline } from "@/lib/explainerBlockBase";
import { compareBlockShape, type CompareBlock } from "@/lib/explainerLearning";
import { list, object, oneOf, type Shape } from "@/lib/shape";
import type { SourceRef } from "@/lib/types";

export type CraftComparison = { schemaVersion: 1; comparison: CompareBlock; sources: SourceRef[] };

export function craftComparePath(slugs: string[], facets: Discipline[] = []): string {
  const query = new URLSearchParams([...slugs.map((slug) => ["crafts", slug]), ...facets.map((facet) => ["facets", facet])]);
  return `/compare?${query.toString()}`;
}

export const craftComparisonShape: Shape<CraftComparison> = object<CraftComparison>({
  schemaVersion: oneOf([1] as const),
  comparison: compareBlockShape,
  sources: list(sourceRefShape, 1)
});
