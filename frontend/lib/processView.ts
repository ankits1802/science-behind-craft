import { formatNumber, formatRange } from "@/lib/measure";
import {
  UNBALANCED_REASON,
  type CitedClaim,
  type ConditionReading,
  type CraftProcess,
  type ProcessReaction,
  type ProcessStageView,
  type ProcessVariant,
  type ReactionSpecies,
  type StageCondition,
  type StageMaterial
} from "@/lib/scienceContract";
import { ShapeError } from "@/lib/shape";
import type { Citation } from "@/lib/types";

export const STAGE_TYPE_LABEL: Record<ProcessStageView["stageType"], string> = {
  PREP: "Preparation",
  SCOUR: "Scouring",
  MORDANT: "Mordanting",
  DYE: "Dyeing",
  RESIST: "Resist",
  PRINT: "Printing",
  WASH: "Washing",
  DRY: "Drying",
  SHAPE: "Shaping",
  CARVE: "Carving",
  FIRE: "Firing",
  CAST: "Casting",
  FINISH: "Finishing",
  OTHER: "Step"
};

export const MATERIAL_ROLE_LABEL: Record<StageMaterial["role"], string> = {
  INPUT: "Input",
  MORDANT: "Mordant",
  DYE: "Dye",
  RESIST: "Resist",
  BINDER: "Binder",
  FLUX: "Flux",
  FUEL: "Fuel",
  TOOL: "Tool",
  PRODUCT: "Product",
  OTHER: "Other"
};

export const MATERIAL_KIND_LABEL: Record<StageMaterial["kind"], string> = {
  FIBRE: "Fibre",
  DYE: "Dye",
  MORDANT: "Mordant",
  MINERAL: "Mineral",
  CLAY: "Clay",
  METAL: "Metal",
  WOOD: "Wood",
  RESIN: "Resin",
  FUEL: "Fuel",
  WATER: "Water",
  OTHER: "Other"
};

export const REACTION_KIND_LABEL: Record<ProcessReaction["kind"], string> = {
  REDOX: "Redox",
  ACID_BASE: "Acid–base",
  COMPLEXATION: "Complexation",
  PRECIPITATION: "Precipitation",
  DEHYDRATION: "Dehydration",
  DEHYDROXYLATION: "Dehydroxylation",
  PHASE_CHANGE: "Phase change",
  POLYMERISATION: "Polymerisation",
  HYDROLYSIS: "Hydrolysis",
  OTHER: "Reaction"
};

export const QUANTITY_LABEL: Record<StageCondition["quantity"], string> = {
  TEMPERATURE: "Temperature",
  PH: "pH",
  DURATION: "Duration",
  CONCENTRATION: "Concentration",
  PRESSURE: "Pressure"
};

export function materialRoleText(role: StageMaterial["role"] | null, kind: StageMaterial["kind"] | null): string | null {
  const roleLabel = role ? MATERIAL_ROLE_LABEL[role] : null;
  const kindLabel = kind ? MATERIAL_KIND_LABEL[kind] : null;
  if (roleLabel && kindLabel && roleLabel !== kindLabel) return `${roleLabel} · ${kindLabel}`;
  return roleLabel ?? kindLabel;
}

const PUBCHEM_COMPOUND = "https://pubchem.ncbi.nlm.nih.gov/compound/";

export function shownVariants(process: CraftProcess): ProcessVariant[] {
  return process.processes
    .map((variant) => ({ ...variant, stages: variant.stages.slice().sort((a, b) => a.ordinal - b.ordinal) }))
    .filter((variant) => variant.stages.length > 0);
}

export function stageHasContent(stage: ProcessStageView): boolean {
  return stage.claims.length + stage.materials.length + stage.conditions.length + stage.reactions.length > 0;
}

export function citationsOf(claims: readonly CitedClaim[]): Citation[] {
  return claims.flatMap((claim) => claim.citations);
}

export function readingClaim(condition: StageCondition, reading: ConditionReading): CitedClaim {
  const claim = condition.claims.find((candidate) => candidate.id === reading.claimId);
  if (!claim) throw new ShapeError(`condition ${condition.id}`, `claim ${reading.claimId} among its claims`);
  return claim;
}

export function readingRange(condition: StageCondition, reading: ConditionReading): string | null {
  return formatRange(reading.min, reading.max, condition.unit);
}

export function isUnbalanced(reaction: ProcessReaction): boolean {
  return reaction.levelReason === UNBALANCED_REASON;
}

export type SpeciesTerm = Pick<ReactionSpecies, "role" | "formula" | "name" | "coefficient">;
export type SpeciesReaction = { species: readonly SpeciesTerm[]; balanced: boolean };

export function speciesSides<S extends SpeciesTerm>(reaction: { species: readonly S[] }): { reactants: S[]; products: S[] } {
  return {
    reactants: reaction.species.filter((species) => species.role === "REACTANT"),
    products: reaction.species.filter((species) => species.role === "PRODUCT")
  };
}

export function speciesName(species: SpeciesTerm): string {
  const name = species.name ?? species.formula;
  if (!name) throw new ShapeError("species", "a name or a formula");
  return name;
}

function spokenSide(species: readonly SpeciesTerm[], balanced: boolean): string {
  return species
    .map((entry) => (balanced && entry.coefficient !== null && entry.coefficient > 1 ? `${entry.coefficient} ${speciesName(entry)}` : speciesName(entry)))
    .join(" + ");
}

export function reactionSpoken(reaction: SpeciesReaction): string {
  const { reactants, products } = speciesSides(reaction);
  return `${spokenSide(reactants, reaction.balanced)} gives ${spokenSide(products, reaction.balanced)}`;
}

export function speciesNamesLine(reaction: { species: readonly SpeciesTerm[] }): string {
  const { reactants, products } = speciesSides(reaction);
  return `${reactants.map(speciesName).join(" · ")} → ${products.map(speciesName).join(" · ")}`;
}

export function deltaHClaim(reaction: ProcessReaction): CitedClaim | null {
  if (!reaction.deltaH) return null;
  const claimId = reaction.deltaH.claimId;
  const claim = reaction.claims.find((candidate) => candidate.id === claimId);
  if (!claim) throw new ShapeError(`reaction ${reaction.id}.deltaH`, `claim ${claimId} among its claims`);
  return claim;
}

export function deltaHText(kjPerMol: number): string {
  return `ΔH ${formatNumber(kjPerMol)} kJ/mol`;
}

export function pubchemHref(cid: number | null): string | null {
  return cid !== null && Number.isInteger(cid) && cid > 0 ? `${PUBCHEM_COMPOUND}${cid}` : null;
}

export function checkedProcess(process: CraftProcess): CraftProcess {
  for (const variant of process.processes) {
    for (const stage of variant.stages) {
      const conditions = [...stage.conditions, ...stage.reactions.flatMap((reaction) => reaction.conditions)];
      for (const condition of conditions) for (const reading of condition.readings) readingClaim(condition, reading);
      for (const reaction of stage.reactions) {
        deltaHClaim(reaction);
        for (const species of reaction.species) speciesName(species);
      }
    }
  }
  return process;
}
