import { readFileSync } from "node:fs";
import { join } from "node:path";

import { BLOCK_SHAPES, type BlockByKind, type TypedBlockKind } from "@/lib/explainerContract";
import { parseShape } from "@/lib/shape";
import type { SourceRef } from "@/lib/types";

export const ROOT = join(__dirname, "..", "..");

export function readRepo(...parts: string[]): string {
  return readFileSync(join(ROOT, ...parts), "utf8");
}

type PhaseBFixture = { sections: { id: string; blocks: { id: string; kind: string }[] }[]; sources: SourceRef[] };

export const PHASE_B = JSON.parse(readRepo("shared", "explainer.phase-b.golden.json")) as PhaseBFixture;

export function phaseBBlock<K extends TypedBlockKind>(kind: K, id: string): BlockByKind[K] {
  const found = PHASE_B.sections.flatMap((section) => section.blocks).find((block) => block.id === id);
  if (!found || found.kind !== kind) throw new Error(`the phase B fixture has a ${kind} block ${id}`);
  return parseShape(BLOCK_SHAPES[kind], structuredClone(found));
}
