import { languageCodeShape } from "@/lib/answerLanguages";
import { answerSentenceShape, citationShape, craftLinkShape, HTTPS_URL, INSTANT, shownLevelShape, sourceRefShape, UUID, type CraftLink } from "@/lib/answerShapes";
import { MATERIAL_KINDS, MATERIAL_ROLES, STAGE_TYPES } from "@/lib/scienceContract";
import { integer, list, matching, nullable, object, oneOf, optional, ShapeError, tagged, text, type Shape } from "@/lib/shape";
import type { AnswerSentence, Citation, EvidenceLevel, SourceRef } from "@/lib/types";

export const DEPTHS = ["BASIC", "DETAILED", "EXPERT"] as const;
export const DISCIPLINES = [
  "OVERVIEW",
  "PROCESS",
  "CHEMISTRY",
  "PHYSICS",
  "MATERIALS",
  "GEOGRAPHY",
  "GEOLOGY",
  "CLIMATE",
  "ECOLOGY",
  "BOTANY",
  "HISTORY",
  "ECONOMICS",
  "DESIGN",
  "HEALTH"
] as const;
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
  "designs"
] as const;
export const BUILT_BLOCK_KINDS = ["prose", "process_ladder", "images"] as const;
export const WORKING_SECTION_STATES = ["RESEARCHING", "WRITING", "CHECKING"] as const;
export const FINAL_SECTION_STATES = ["READY", "EMPTY"] as const;
export const MEDIA_DISPLAYS = ["INLINE", "LINK_CARD"] as const;
export const IMAGE_RELEVANCE = ["TEXT", "VISION"] as const;
export const TERM_BASES = ["STORED", "WIKIPEDIA", "WEB_SEARCH"] as const;

export type Depth = (typeof DEPTHS)[number];
export type Discipline = (typeof DISCIPLINES)[number];
export type BlockKind = (typeof BLOCK_KINDS)[number];
export type WorkingSectionState = (typeof WORKING_SECTION_STATES)[number];
export type FinalSectionState = (typeof FINAL_SECTION_STATES)[number];

export type TermSpan = { text: string; termKey: string };
export type ExplainerSentence = AnswerSentence & { terms: TermSpan[] };
export type ReuseMarker = { pieceId: string; storedAt: string };
type BlockEnvelope<K extends BlockKind> = { id: string; kind: K; version: 1; reuse: ReuseMarker | null };
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
export type MediaRef = {
  id: string;
  display: (typeof MEDIA_DISPLAYS)[number];
  provider: string;
  pageUrl: string;
  imageUrl: string;
  width: number | null;
  height: number | null;
  title: string;
  alt: string;
  author: string | null;
  site: string;
  credit: string | null;
  licence: string | null;
  licenceUrl: string | null;
  sourceId: string | null;
  retrievedAt: string;
};
export type ImageItem = { media: MediaRef; claimIds: string[]; relevance: (typeof IMAGE_RELEVANCE)[number] };
export type ImagesBlock = BlockEnvelope<"images"> & { items: ImageItem[] };
export type ExplainerBlock = ProseBlock | ProcessLadderBlock | ImagesBlock;
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
const BLOCK_ID = matching(/^[a-z0-9]+(?:[.-][a-z0-9]+)*$/, "a block id");
const TERM_KEY = matching(/^[a-z0-9]+(?:-[a-z0-9]+)*$/, "a term key");
const termSpanShape: Shape<TermSpan> = object<TermSpan>({ text, termKey: TERM_KEY });
export const explainerSentenceShape: Shape<ExplainerSentence> = {
  expected: "a cited sentence with its marked terms",
  parse(value, path) {
    if (typeof value !== "object" || value === null || Array.isArray(value)) throw new ShapeError(path, "an object");
    const { terms, ...sentence } = value as Record<string, unknown>;
    return { ...answerSentenceShape.parse(sentence, path), terms: list(termSpanShape).parse(terms, path ? `${path}.terms` : "terms") };
  }
};

function envelope<K extends BlockKind>(kind: K) {
  return {
    id: BLOCK_ID,
    kind: oneOf([kind] as const) as Shape<K>,
    version: oneOf([1] as const),
    reuse: nullable(object<ReuseMarker>({ pieceId: UUID, storedAt: INSTANT }))
  };
}

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

export const mediaRefShape: Shape<MediaRef> = object<MediaRef>({
  id: UUID,
  display: oneOf(MEDIA_DISPLAYS),
  provider: matching(/^[a-z][a-z0-9_]{1,39}$/, "a provider name"),
  pageUrl: HTTPS_URL,
  imageUrl: HTTPS_URL,
  width: nullable(integer),
  height: nullable(integer),
  title: text,
  alt: text,
  author: nullable(text),
  site: text,
  credit: nullable(text),
  licence: nullable(text),
  licenceUrl: nullable(HTTPS_URL),
  sourceId: nullable(text),
  retrievedAt: INSTANT
});

export const explainerBlockShape: Shape<ExplainerBlock> = tagged<ExplainerBlock>("kind", {
  prose: object<ProseBlock>({ ...envelope("prose"), sentences: list(explainerSentenceShape, 1) }),
  process_ladder: object<ProcessLadderBlock>({ ...envelope("process_ladder"), craft: craftLinkShape, processId: UUID, stages: list(ladderStageShape, 1) }),
  images: object<ImagesBlock>({
    ...envelope("images"),
    items: list(object<ImageItem>({ media: mediaRefShape, claimIds: list(UUID, 1), relevance: oneOf(IMAGE_RELEVANCE) }), 1)
  })
} satisfies Record<(typeof BUILT_BLOCK_KINDS)[number], Shape<ExplainerBlock>>);

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
  wikidataId: nullable(matching(/^Q[1-9]\d*$/, "a Wikidata id")),
  basis: oneOf(TERM_BASES),
  summary: list(answerSentenceShape, 1),
  sources: list(sourceRefShape),
  checkedAt: INSTANT
});
