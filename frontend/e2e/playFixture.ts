import { BLOCK_SHAPES, type BlockByKind, type TypedBlockKind } from "@/lib/explainerContract";
import { parseShape } from "@/lib/shape";
import type { SourceRef } from "@/lib/types";

import { readRepo } from "./phaseBFixture";

type PhaseCFixture = {
  sandbox: { attribute: string; csp: string; dataElementId: string; maxBytes: number };
  sections: { id: string; blocks: { id: string; kind: string }[] }[];
  sources: SourceRef[];
};

export const PHASE_C = JSON.parse(readRepo("shared", "explainer.phase-c.golden.json")) as PhaseCFixture;

export function phaseCBlock<K extends TypedBlockKind>(kind: K, id: string): BlockByKind[K] {
  const found = PHASE_C.sections.flatMap((section) => section.blocks).find((block) => block.id === id);
  if (!found || found.kind !== kind) throw new Error(`the phase C fixture has a ${kind} block ${id}`);
  return parseShape(BLOCK_SHAPES[kind], structuredClone(found));
}
