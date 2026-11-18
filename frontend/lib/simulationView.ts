import { apiFetch } from "@/lib/api";
import { UUID } from "@/lib/answerShapes";
import { BLOCK_ID } from "@/lib/explainerBlockBase";
import type { SimulationBlock, SimulationReaction, SimulationValue } from "@/lib/explainerPlay";
import { formatDate } from "@/lib/format";
import { measureParts } from "@/lib/measure";
import type { RegionDataset } from "@/lib/regionContract";
import { boolean, object, parseShape, ShapeError, type Shape } from "@/lib/shape";

export const GENERATED_LABEL = "Generated explainer";

export type SimulationHidden = { answerId: string; blockId: string; pieceId: string; hidden: boolean };
export type ValueBasis = { kind: "stated"; stated: string } | { kind: "dataset"; dataset: RegionDataset };

const simulationHiddenShape: Shape<SimulationHidden> = object<SimulationHidden>({ answerId: UUID, blockId: BLOCK_ID, pieceId: UUID, hidden: boolean });

export function generatedCaption(block: Pick<SimulationBlock, "model" | "createdAt">): string {
  return `${GENERATED_LABEL} · ${block.model} · ${formatDate(block.createdAt)}`;
}

export function simulationValueText(value: Pick<SimulationValue, "value" | "unit">): string {
  const parts = measureParts(value.unit ?? "");
  const shown = String(Number((value.value * parts.scale).toFixed(9))).replace(/^-/, "−");
  return `${parts.prefix}${shown}${parts.suffix}`;
}

export function valueBasis(value: SimulationValue, datasets: readonly RegionDataset[]): ValueBasis | null {
  if (value.stated !== null && value.datasetCode === null && value.citations.length > 0) return { kind: "stated", stated: value.stated };
  const dataset = value.datasetCode === null ? undefined : datasets.find((entry) => entry.code === value.datasetCode);
  if (value.stated === null && value.citations.length === 0 && dataset) return { kind: "dataset", dataset };
  return null;
}

export function valueBases(block: Pick<SimulationBlock, "values" | "datasets">): ValueBasis[] | null {
  if (new Set(block.values.map((value) => value.key)).size !== block.values.length) return null;
  const bases = block.values.map((value) => valueBasis(value, block.datasets));
  return bases.every((basis): basis is ValueBasis => basis !== null) ? bases : null;
}

export function keptAsPiece(block: Pick<SimulationBlock, "reuse" | "values" | "grounds" | "reactions">): boolean {
  const grounded = (block.grounds?.length ?? 0) > 0 || (block.reactions?.length ?? 0) > 0;
  return block.reuse !== null || grounded || block.values.some((value) => value.citations.length > 0);
}

export function wordEquation(reaction: Pick<SimulationReaction, "species">): string {
  const side = (role: "REACTANT" | "PRODUCT") =>
    reaction.species
      .filter((species) => species.role === role)
      .map((species) => species.name ?? species.formula ?? "")
      .join(" + ");
  return `${side("REACTANT")} → ${side("PRODUCT")}`;
}

export function hiddenFrom(block: { kind: string; hidden?: boolean }, canHide: boolean): boolean {
  return block.kind === "simulation" && block.hidden === true && !canHide;
}

export function simulationHiddenPath(answerId: string, blockId: string): string {
  return `/answers/${encodeURIComponent(answerId)}/simulations/${encodeURIComponent(blockId)}/hidden`;
}

export async function setSimulationHidden(answerId: string, blockId: string, hidden: boolean): Promise<SimulationHidden> {
  const body = await apiFetch<unknown>(simulationHiddenPath(answerId, blockId), { method: "PUT", body: JSON.stringify({ hidden }) });
  const answer = parseShape(simulationHiddenShape, body);
  if (answer.answerId !== answerId || answer.blockId !== blockId) throw new ShapeError("hidden", `the simulation ${blockId} of the answer ${answerId}`);
  if (answer.hidden !== hidden) throw new ShapeError("hidden", String(hidden));
  return answer;
}
