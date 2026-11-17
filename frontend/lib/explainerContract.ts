import { languageCodeShape } from "@/lib/answerLanguages";
import { answerSentenceShape, citationShape, craftLinkShape, INSTANT, shownLevelShape, sourceRefShape, UUID, type CraftLink } from "@/lib/answerShapes";
import {
  DISCIPLINES,
  envelope,
  explainerSentenceShape,
  IMAGE_RELEVANCE,
  mediaRefShape,
  TERM_KEY,
  WIKIDATA_ID,
  type BlockEnvelope,
  type Discipline,
  type ExplainerSentence,
  type MediaRef
} from "@/lib/explainerBlockBase";
import { expertViewBlockShape, type ExpertViewBlock } from "@/lib/explainerExperts";
import {
  climateRiskBlockShape,
  marketGiBlockShape,
  measureBlockShape,
  type ClimateRiskBlock,
  type MarketGiBlock,
  type MeasureBlock
} from "@/lib/explainerInsight";
import {
  compareBlockShape,
  conceptGraphBlockShape,
  quizBlockShape,
  type CompareBlock,
  type ConceptGraphBlock,
  type QuizBlock
} from "@/lib/explainerLearning";
import {
  materialCardBlockShape,
  molecule3dBlockShape,
  reactionPlayerBlockShape,
  type MaterialCardBlock,
  type Molecule3dBlock,
  type ReactionPlayerBlock
} from "@/lib/explainerMatter";
import {
  mapLayerBlockShape,
  regionStoryBlockShape,
  seasonsBlockShape,
  supplyMapBlockShape,
  type MapLayerBlock,
  type RegionStoryBlock,
  type SeasonsBlock,
  type SupplyMapBlock
} from "@/lib/explainerPlace";
import {
  simulationBlockShape,
  timelineMapBlockShape,
  whatIfBlockShape,
  zoomStoryBlockShape,
  type SimulationBlock,
  type TimelineMapBlock,
  type WhatIfBlock,
  type ZoomStoryBlock
} from "@/lib/explainerPlay";
import { MATERIAL_KINDS, MATERIAL_ROLES, STAGE_TYPES } from "@/lib/scienceContract";
import { integer, list, matching, nullable, object, oneOf, optional, tagged, text, type Shape } from "@/lib/shape";
import type { AnswerSentence, Citation, EvidenceLevel, SourceRef } from "@/lib/types";

export { DISCIPLINES, type Discipline };
export const DEPTHS = ["BASIC", "DETAILED", "EXPERT"] as const;
export const BLOCK_KINDS = [
  "prose",
  "process_ladder",
  "region_story",
  "map_layer",
  "reaction_player",
  "material_card",
  "molecule_3d",
  "images",
  "simulation",
  "what_if",
  "timeline_map",
  "zoom_story",
  "expert_view",
  "seasons",
  "supply_map",
  "compare",
  "in_practice",
  "quiz",
  "open_questions",
  "artisan_voice",
  "designs",
  "concept_graph",
  "measure",
  "market_gi",
  "climate_risk"
] as const;
export const BUILT_BLOCK_KINDS = ["prose", "process_ladder", "images", "region_story", "map_layer", "expert_view", "seasons", "supply_map", "reaction_player", "material_card", "molecule_3d", "compare", "concept_graph", "climate_risk", "measure", "market_gi", "simulation", "what_if", "zoom_story", "timeline_map"] as const;
export const WORKING_SECTION_STATES = ["RESEARCHING", "WRITING", "CHECKING"] as const;
export const FINAL_SECTION_STATES = ["READY", "EMPTY"] as const;
export const TERM_BASES = ["STORED", "WIKIPEDIA", "WEB_SEARCH"] as const;

export type Depth = (typeof DEPTHS)[number];
export type BlockKind = (typeof BLOCK_KINDS)[number];
export type WorkingSectionState = (typeof WORKING_SECTION_STATES)[number];
export type FinalSectionState = (typeof FINAL_SECTION_STATES)[number];

export type ProseBlock = BlockEnvelope<"prose"> & { sentences: ExplainerSentence[] };
export type LadderMaterial = {
  materialId: string;
  name: string;
  kind: (typeof MATERIAL_KINDS)[number];
  role: (typeof MATERIAL_ROLES)[number];
  citations: Citation[];
};
export type LadderCondition = { label: string; stated: string; citations: Citation[] };
export type LadderStage = {
  stageId: string;
  ordinal: number;
  name: string;
  stageType: (typeof STAGE_TYPES)[number];
  level: EvidenceLevel;
  sentences: ExplainerSentence[];
  materials: LadderMaterial[];
  conditions: LadderCondition[];
  reactionIds: string[];
};
export type ProcessLadderBlock = BlockEnvelope<"process_ladder"> & { craft: CraftLink; processId: string; stages: LadderStage[] };
export type ImageItem = { media: MediaRef; claimIds: string[]; relevance: (typeof IMAGE_RELEVANCE)[number] };
export type ImagesBlock = BlockEnvelope<"images"> & { items: ImageItem[] };
export type BlockByKind = {
  prose: ProseBlock;
  process_ladder: ProcessLadderBlock;
  region_story: RegionStoryBlock;
  map_layer: MapLayerBlock;
  reaction_player: ReactionPlayerBlock;
  material_card: MaterialCardBlock;
  molecule_3d: Molecule3dBlock;
  images: ImagesBlock;
  expert_view: ExpertViewBlock;
  seasons: SeasonsBlock;
  supply_map: SupplyMapBlock;
  simulation: SimulationBlock;
  what_if: WhatIfBlock;
  zoom_story: ZoomStoryBlock;
  timeline_map: TimelineMapBlock;
  quiz: QuizBlock;
  compare: CompareBlock;
  concept_graph: ConceptGraphBlock;
  measure: MeasureBlock;
  market_gi: MarketGiBlock;
  climate_risk: ClimateRiskBlock;
};
export type TypedBlockKind = keyof BlockByKind;
export type BuiltBlockKind = (typeof BUILT_BLOCK_KINDS)[number];
export type ExplainerBlock = BlockByKind[BuiltBlockKind];
export type ExplainerSection = {
  id: string;
  discipline: Discipline;
  title: string;
  original?: string;
  order: number;
  state: FinalSectionState;
  blocks: ExplainerBlock[];
  searched: string | null;
};
export type Understood = { crafts: CraftLink[]; candidates: CraftLink[]; depth: Depth; language: string };
export type Explainer = {
  schemaVersion: 1;
  answerId: string;
  question: string;
  understood: Understood;
  sections: ExplainerSection[];
  sources: SourceRef[];
  followUps: string[];
  createdAt: string;
};
export type Term = {
  schemaVersion: 1;
  key: string;
  label: string;
  language: string;
  localNames: string[];
  craftSlugs: string[];
  wikidataId: string | null;
  basis: (typeof TERM_BASES)[number];
  summary: AnswerSentence[];
  sources: SourceRef[];
  checkedAt: string;
};

export const SECTION_ID = matching(/^s[1-9]\d{0,2}$/, "a section id");

const ladderStageShape: Shape<LadderStage> = object<LadderStage>({
  stageId: UUID,
  ordinal: integer,
  name: text,
  stageType: oneOf(STAGE_TYPES),
  level: shownLevelShape,
  sentences: list(explainerSentenceShape, 1),
  materials: list(
    object<LadderMaterial>({ materialId: UUID, name: text, kind: oneOf(MATERIAL_KINDS), role: oneOf(MATERIAL_ROLES), citations: list(citationShape, 1) })
  ),
  conditions: list(object<LadderCondition>({ label: text, stated: text, citations: list(citationShape, 1) })),
  reactionIds: list(UUID)
});

export const BLOCK_SHAPES: { readonly [K in TypedBlockKind]: Shape<BlockByKind[K]> } = {
  prose: object<ProseBlock>({ ...envelope("prose"), sentences: list(explainerSentenceShape, 1) }),
  process_ladder: object<ProcessLadderBlock>({ ...envelope("process_ladder"), craft: craftLinkShape, processId: UUID, stages: list(ladderStageShape, 1) }),
  region_story: regionStoryBlockShape,
  map_layer: mapLayerBlockShape,
  reaction_player: reactionPlayerBlockShape,
  material_card: materialCardBlockShape,
  molecule_3d: molecule3dBlockShape,
  images: object<ImagesBlock>({
    ...envelope("images"),
    items: list(object<ImageItem>({ media: mediaRefShape, claimIds: list(UUID, 1), relevance: oneOf(IMAGE_RELEVANCE) }), 1)
  }),
  expert_view: expertViewBlockShape,
  seasons: seasonsBlockShape,
  supply_map: supplyMapBlockShape,
  simulation: simulationBlockShape,
  what_if: whatIfBlockShape,
  zoom_story: zoomStoryBlockShape,
  timeline_map: timelineMapBlockShape,
  quiz: quizBlockShape,
  compare: compareBlockShape,
  concept_graph: conceptGraphBlockShape,
  measure: measureBlockShape,
  market_gi: marketGiBlockShape,
  climate_risk: climateRiskBlockShape
};

export const explainerBlockShape: Shape<ExplainerBlock> = tagged<ExplainerBlock>(
  "kind",
  Object.fromEntries(BUILT_BLOCK_KINDS.map((kind) => [kind, BLOCK_SHAPES[kind]])) as Record<BuiltBlockKind, Shape<ExplainerBlock>>
);

export const understoodShape: Shape<Understood> = object<Understood>({
  crafts: list(craftLinkShape),
  candidates: list(craftLinkShape),
  depth: oneOf(DEPTHS),
  language: languageCodeShape
});

export const explainerSectionShape: Shape<ExplainerSection> = object<ExplainerSection>({
  id: SECTION_ID,
  discipline: oneOf(DISCIPLINES),
  title: text,
  original: optional(text),
  order: integer,
  state: oneOf(FINAL_SECTION_STATES),
  blocks: list(explainerBlockShape),
  searched: nullable(text)
});

export const explainerShape: Shape<Explainer> = object<Explainer>({
  schemaVersion: oneOf([1] as const),
  answerId: UUID,
  question: text,
  understood: understoodShape,
  sections: list(explainerSectionShape, 1),
  sources: list(sourceRefShape),
  followUps: list(text),
  createdAt: INSTANT
});

export const termShape: Shape<Term> = object<Term>({
  schemaVersion: oneOf([1] as const),
  key: TERM_KEY,
  label: text,
  language: languageCodeShape,
  localNames: list(text),
  craftSlugs: list(text),
  wikidataId: nullable(WIKIDATA_ID),
  basis: oneOf(TERM_BASES),
  summary: list(answerSentenceShape, 1),
  sources: list(sourceRefShape),
  checkedAt: INSTANT
});
