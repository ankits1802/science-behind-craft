import { craftLinkShape, sourceRefShape, type CraftLink } from "@/lib/answerShapes";
import { conceptNodeShape, type ConceptNode } from "@/lib/explainerLearning";
import { list, object, oneOf, type Shape } from "@/lib/shape";
import type { SourceRef } from "@/lib/types";

export const CRAFT_SHARED_SCIENCE_PATH = (slug: string) => `/crafts/${encodeURIComponent(slug)}/shared-science`;
export const SHARED_CONCEPT_PATH = (termKey: string, craft?: string) =>
  `/shared-science/${encodeURIComponent(termKey)}${craft ? `?craft=${encodeURIComponent(craft)}` : ""}`;

export type SharedScience = { schemaVersion: 1; craft: CraftLink; nodes: ConceptNode[]; sources: SourceRef[] };
export type SharedConcept = { schemaVersion: 1; node: ConceptNode; sources: SourceRef[] };

export const sharedScienceShape: Shape<SharedScience> = object<SharedScience>({
  schemaVersion: oneOf([1] as const),
  craft: craftLinkShape,
  nodes: list(conceptNodeShape),
  sources: list(sourceRefShape)
});

export const sharedConceptShape: Shape<SharedConcept> = object<SharedConcept>({
  schemaVersion: oneOf([1] as const),
  node: conceptNodeShape,
  sources: list(sourceRefShape)
});
