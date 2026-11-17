import type { ExplainerBlock } from "@/lib/explainerContract";
import { SANDBOX_ATTRIBUTE, SANDBOX_CSP } from "@/lib/explainerPlay";

import type { CheckOutcome } from "./waterStory";

export type FrameSeen = { sandbox: string | null; policyFirst: boolean; drawn: boolean; peerless: boolean };

export type GeneratedExplainerRecord = {
  blocks: number;
  values: number;
  valuesWithoutBasis: number;
  frames: FrameSeen[] | null;
  frameRequests: string[];
  frameRefusals: string[];
};

export const NO_GENERATED_EXPLAINER: GeneratedExplainerRecord = { blocks: 0, values: 0, valuesWithoutBasis: 0, frames: null, frameRequests: [], frameRefusals: [] };
export const NO_CONCEPT_NOTE = "No generated explainer arrived: the builder chose no concept for this answer, so its absence is recorded and not failed.";
export const FRAME_DOCUMENT_START = `<!doctype html><html lang="en"><head><meta http-equiv="Content-Security-Policy" content="${SANDBOX_CSP}">`;

export function withGeneratedExplainer(record: GeneratedExplainerRecord, block: ExplainerBlock): GeneratedExplainerRecord {
  if (block.kind !== "simulation") return record;
  const unbased = block.values.filter((value) => value.citations.length === 0 && value.datasetCode === null).length;
  return { ...record, blocks: record.blocks + 1, values: record.values + block.values.length, valuesWithoutBasis: record.valuesWithoutBasis + unbased };
}

export function generatedExplainerFound(record: GeneratedExplainerRecord): boolean {
  return record.blocks > 0;
}

function frameProblems(frames: readonly FrameSeen[], blocks: number): string[] {
  const problems: string[] = [];
  if (frames.length !== blocks) problems.push(`the stream sent ${blocks} generated explainers; the page draws ${frames.length} sandboxed frames`);
  const loose = frames.filter((frame) => frame.sandbox !== SANDBOX_ATTRIBUTE || !frame.policyFirst).length;
  if (loose > 0) problems.push(`${loose} generated explainer frames lack sandbox="${SANDBOX_ATTRIBUTE}" or the policy as their first head element`);
  const blank = frames.filter((frame) => !frame.drawn).length;
  if (blank > 0) problems.push(`${blank} generated explainer frames drew nothing`);
  const open = frames.filter((frame) => !frame.peerless).length;
  if (open > 0) problems.push(`${open} generated explainer frames still offer a peer connection`);
  return problems;
}

export function generatedExplainerOutcome(record: GeneratedExplainerRecord): CheckOutcome {
  if (record.blocks === 0) return { problems: [], notes: [NO_CONCEPT_NOTE] };
  const problems: string[] = [];
  if (record.valuesWithoutBasis > 0) problems.push(`${record.valuesWithoutBasis} generated explainer values rest on no citation or dataset row`);
  if (record.frames !== null) problems.push(...frameProblems(record.frames, record.blocks));
  if (record.frameRequests.length > 0) problems.push(`a generated explainer frame attempted ${record.frameRequests.length} network requests: ${record.frameRequests.join(", ")}`);
  if (record.frameRefusals.length > 0) problems.push(`a generated explainer frame attempted ${record.frameRefusals.length} loads its policy refused: ${record.frameRefusals.join(" | ")}`);
  return { problems, notes: [] };
}
