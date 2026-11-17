import { BLOCK_SHAPES, type BlockByKind, type TypedBlockKind } from "@/lib/explainerContract";
import { parseShape } from "@/lib/shape";
import type { SourceRef } from "@/lib/types";

import { readRepo } from "./phaseBFixture";

type PhaseDFixture = { sections: { id: string; discipline: string; blocks: { id: string; kind: string }[] }[]; sources: SourceRef[] };

export const PHASE_D = JSON.parse(readRepo("shared", "explainer.phase-d.golden.json")) as PhaseDFixture;

export function phaseDBlock<K extends TypedBlockKind>(kind: K, id: string): BlockByKind[K] {
  const found = PHASE_D.sections.flatMap((section) => section.blocks).find((block) => block.id === id);
  if (!found || found.kind !== kind) throw new Error(`the phase D fixture has a ${kind} block ${id}`);
  return parseShape(BLOCK_SHAPES[kind], structuredClone(found));
}
