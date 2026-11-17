import { citationShape, craftLinkShape, shownLevelShape, sourceRefShape, storedLevelShape, UUID, type CraftLink, type StoredLevel } from "@/lib/answerShapes";
import { boolean, integer, list, nullable, number, object, oneOf, text, type Shape } from "@/lib/shape";
import type { Citation, EvidenceLevel, SourceRef } from "@/lib/types";

export const SCIENCE_PROCESS_PATH = (slug: string) => `/crafts/${encodeURIComponent(slug)}/process`;

export const STAGE_TYPES = ["PREP", "SCOUR", "MORDANT", "DYE", "RESIST", "PRINT", "WASH", "DRY", "SHAPE", "CARVE", "FIRE", "CAST", "FINISH", "OTHER"] as const;
export const MATERIAL_KINDS = ["FIBRE", "DYE", "MORDANT", "MINERAL", "CLAY", "METAL", "WOOD", "RESIN", "FUEL", "WATER", "OTHER"] as const;
export const MATERIAL_ROLES = ["INPUT", "MORDANT", "DYE", "RESIST", "BINDER", "FLUX", "FUEL", "TOOL", "PRODUCT", "OTHER"] as const;
export const REACTION_KINDS = [
  "REDOX",
  "ACID_BASE",
  "COMPLEXATION",
  "PRECIPITATION",
  "DEHYDRATION",
  "DEHYDROXYLATION",
  "PHASE_CHANGE",
  "POLYMERISATION",
  "HYDROLYSIS",
  "OTHER"
] as const;
export const CONDITION_QUANTITIES = ["TEMPERATURE", "PH", "DURATION", "CONCENTRATION", "PRESSURE"] as const;
export const ENVELOPE_STATUSES = ["WITHIN", "OUTSIDE", "NONE"] as const;
export const UNBALANCED_REASON = "unbalanced";

export type CitedClaim = { id: string; text: string; level: StoredLevel; citations: Citation[] };
export type CompoundRef = { id: string; name: string; formula: string | null; pubchemCid: number | null };
export type StageMaterial = {
  id: string;
  name: string;
  kind: (typeof MATERIAL_KINDS)[number];
  role: (typeof MATERIAL_ROLES)[number];
  quantityText: string | null;
  compound: CompoundRef | null;
  level: StoredLevel;
  claims: CitedClaim[];
};
export type EnvelopeCheck = { status: (typeof ENVELOPE_STATUSES)[number]; min: number | null; max: number | null };
export type ConditionReading = { claimId: string; min: number | null; max: number | null; stated: string; envelope: EnvelopeCheck };
export type StageCondition = {
  id: string;
  label: string;
  quantity: (typeof CONDITION_QUANTITIES)[number];
  unit: string;
  readings: ConditionReading[];
  sourcesDiffer: boolean;
  level: StoredLevel;
  claims: CitedClaim[];
};
export type ReactionSpecies = { role: "REACTANT" | "PRODUCT"; formula: string | null; name: string | null; coefficient: number | null; compoundId: string | null };
export type ProcessReaction = {
  id: string;
  kind: (typeof REACTION_KINDS)[number];
  label: string;
  species: ReactionSpecies[];
  balanced: boolean;
  equation: string | null;
  checkerVersion: string | null;
  conditions: StageCondition[];
  deltaH: { kjPerMol: number; claimId: string } | null;
  level: StoredLevel;
  levelReason: string | null;
  claims: CitedClaim[];
};
export type ProcessStageView = {
  id: string;
  ordinal: number;
  name: string;
  stageType: (typeof STAGE_TYPES)[number];
  level: EvidenceLevel;
  claims: CitedClaim[];
  materials: StageMaterial[];
  conditions: StageCondition[];
  reactions: ProcessReaction[];
};
export type ProcessVariant = { id: string; name: string; variant: string | null; stages: ProcessStageView[] };
export type CraftProcess = { schemaVersion: 1; craft: CraftLink; processes: ProcessVariant[]; sources: SourceRef[] };

const citedClaimShape: Shape<CitedClaim> = object<CitedClaim>({ id: UUID, text, level: storedLevelShape, citations: list(citationShape, 1) });

const conditionShape: Shape<StageCondition> = object<StageCondition>({
  id: text,
  label: text,
  quantity: oneOf(CONDITION_QUANTITIES),
  unit: text,
  readings: list(
    object<ConditionReading>({
      claimId: UUID,
      min: nullable(number),
      max: nullable(number),
      stated: text,
      envelope: object<EnvelopeCheck>({ status: oneOf(ENVELOPE_STATUSES), min: nullable(number), max: nullable(number) })
    }),
    1
  ),
  sourcesDiffer: boolean,
  level: storedLevelShape,
  claims: list(citedClaimShape, 1)
});

export const reactionSpeciesShape: Shape<ReactionSpecies> = object<ReactionSpecies>({
  role: oneOf(["REACTANT", "PRODUCT"] as const),
  formula: nullable(text),
  name: nullable(text),
  coefficient: nullable(integer),
  compoundId: nullable(UUID)
});

const reactionShape: Shape<ProcessReaction> = object<ProcessReaction>({
  id: UUID,
  kind: oneOf(REACTION_KINDS),
  label: text,
  species: list(reactionSpeciesShape, 2),
  balanced: boolean,
  equation: nullable(text),
  checkerVersion: nullable(text),
  conditions: list(conditionShape),
  deltaH: nullable(object<{ kjPerMol: number; claimId: string }>({ kjPerMol: number, claimId: UUID })),
  level: storedLevelShape,
  levelReason: nullable(text),
  claims: list(citedClaimShape, 1)
});

const materialShape: Shape<StageMaterial> = object<StageMaterial>({
  id: UUID,
  name: text,
  kind: oneOf(MATERIAL_KINDS),
  role: oneOf(MATERIAL_ROLES),
  quantityText: nullable(text),
  compound: nullable(object<CompoundRef>({ id: UUID, name: text, formula: nullable(text), pubchemCid: nullable(integer) })),
  level: storedLevelShape,
  claims: list(citedClaimShape, 1)
});

const stageShape: Shape<ProcessStageView> = object<ProcessStageView>({
  id: UUID,
  ordinal: integer,
  name: text,
  stageType: oneOf(STAGE_TYPES),
  level: shownLevelShape,
  claims: list(citedClaimShape),
  materials: list(materialShape),
  conditions: list(conditionShape),
  reactions: list(reactionShape)
});

export const craftProcessShape: Shape<CraftProcess> = object<CraftProcess>({
  schemaVersion: oneOf([1] as const),
  craft: craftLinkShape,
  processes: list(object<ProcessVariant>({ id: UUID, name: text, variant: nullable(text), stages: list(stageShape) })),
  sources: list(sourceRefShape)
});
