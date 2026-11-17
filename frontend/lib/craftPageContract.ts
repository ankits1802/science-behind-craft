import { apiFetch } from "@/lib/api";
import { citationShape, CRAFT_PATH, INSTANT, sourceRefShape, storedLevelShape, UUID, type CraftLink, type StoredLevel } from "@/lib/answerShapes";
import { mediaRefShape, termSpanShape, TERM_KEY, WIKIDATA_ID, type MediaRef, type TermSpan } from "@/lib/explainerBlockBase";
import { PLACE_ROLES } from "@/lib/districtCraftsContract";
import { DISCIPLINES, type Discipline } from "@/lib/explainerContract";
import { MATERIAL_KINDS, MATERIAL_ROLES, REACTION_KINDS, STAGE_TYPES } from "@/lib/scienceContract";
import { boolean, integer, list, nullable, object, oneOf, parseShape, ShapeError, text, type Shape } from "@/lib/shape";
import type { Citation, SourceRef } from "@/lib/types";

export const CRAFT_PAGE_PATH = (slug: string) => `/crafts/${encodeURIComponent(slug)}/page`;

export const PROVENANCES = ["CURATED", "SEED", "FROM_ANSWERS", "RESEARCHER"] as const;
export const SECTION_BASES = ["CURATED", "STORED_CLAIMS"] as const;
export const SUBJECT_KINDS = ["CRAFT", "STAGE", "MATERIAL", "TOOL", "PLACE", "COMMUNITY", "TERM", "CONCEPT"] as const;
export const TIMING_KINDS = ["DURATION", "SEASON"] as const;
export const SPECIES_ROLES = ["REACTANT", "PRODUCT"] as const;
export const CRAFT_GI_STATUSES = ["GI", "NON_GI"] as const;
export const COVERAGE_CLASSES = ["FULL", "THIN"] as const;
export const PLACE_KINDS = ["VILLAGE", "TOWN", "DISTRICT", "STATE", "COUNTRY", "REGION", "RIVER"] as const;
export const GROUP_KINDS = ["COMMUNITY", "PERSON", "ORGANISATION"] as const;

export type Provenance = (typeof PROVENANCES)[number];
export type SubjectKind = (typeof SUBJECT_KINDS)[number];
export type PlaceRole = (typeof PLACE_ROLES)[number];
export type PlaceKind = (typeof PLACE_KINDS)[number];
export type GroupKind = (typeof GROUP_KINDS)[number];

export type PageCraft = CraftLink & {
  id: string;
  localName: string | null;
  categoryName: string | null;
  subCategoryName: string | null;
  giStatus: (typeof CRAFT_GI_STATUSES)[number] | null;
  stateOfPractice: string[];
  stateOfOrigin: string[];
};
export type SearchedFor = { query: string; site: string };
export type CurationHeader = { version: number; curatedAt: string; coverage: (typeof COVERAGE_CLASSES)[number]; searched: SearchedFor[] };
export type SubjectRef = { id: string | null; name: string; kind: SubjectKind };
export type PageClaim = {
  id: string;
  text: string;
  level: StoredLevel;
  discipline: Discipline;
  subject: SubjectRef;
  provenance: Provenance;
  sourcesDiffer: boolean;
  citations: Citation[];
};
export type PageSentence = { id: string; text: string; level: StoredLevel; claimIds: string[]; terms: TermSpan[] };
export type KeyFact = { label: string; value: string; claimIds: string[] };
export type OverviewSection = { discipline: Discipline; title: string; basis: (typeof SECTION_BASES)[number]; sentences: PageSentence[] };
export type PageOverview = { lede: PageSentence[]; keyFacts: KeyFact[]; sections: OverviewSection[] };
export type DifferRow = { about: string; claimIds: string[] };
export type PageArea = { lgd: number | null; name: string };
export type PagePlace = {
  key: string;
  name: string;
  kind: PlaceKind;
  role: PlaceRole;
  district: PageArea | null;
  state: PageArea | null;
  country: string;
  wikidataId: string | null;
  claimIds: string[];
};
export type PageCommunity = { key: string; kind: GroupKind; name: string; localNames: string[]; honours: string[]; place: string | null; claimIds: string[] };
export type StageItem = {
  id: string;
  name: string;
  kind: (typeof MATERIAL_KINDS)[number];
  role: (typeof MATERIAL_ROLES)[number];
  localNames: string[];
  claimIds: string[];
};
export type StageTiming = { kind: (typeof TIMING_KINDS)[number]; text: string; claimId: string };
export type PageSpecies = { role: (typeof SPECIES_ROLES)[number]; name: string | null; formula: string | null; coefficient: number | null };
export type PageReaction = {
  id: string | null;
  kind: (typeof REACTION_KINDS)[number];
  label: string;
  species: PageSpecies[];
  balanced: boolean;
  equation: string | null;
  claimIds: string[];
};
export type PageStage = {
  id: string;
  order: number | null;
  name: string;
  localName: string | null;
  stageType: (typeof STAGE_TYPES)[number];
  claimIds: string[];
  materials: StageItem[];
  tools: StageItem[];
  timing: StageTiming[];
  reactions: PageReaction[];
};
export type PageProcess = { processId: string | null; stages: PageStage[]; reactions: PageReaction[] };
export type PageTerm = { key: string | null; label: string; names: string[]; meaning: string | null; language: string | null; script: string | null; claimIds: string[] };
export type PagePicture = { media: MediaRef; caption: string; stageId: string | null; claimIds: string[] };
export type PageQuestion = { key: string | null; question: string; settledBy: string | null; claimIds: string[] };
export type EvidenceEntry = { claimId: string; foldedIds: string[] };
export type EvidenceSubject = { subject: SubjectRef; entries: EvidenceEntry[] };
export type EvidenceGroup = { discipline: Discipline; title: string; subjects: EvidenceSubject[] };
export type PageEvidence = { groups: EvidenceGroup[]; hypotheses: EvidenceEntry[] };
export type CraftPage = {
  schemaVersion: 1;
  craft: PageCraft;
  curated: boolean;
  curation: CurationHeader | null;
  overview: PageOverview;
  sourcesDiffer: DifferRow[];
  places: PagePlace[];
  communities: PageCommunity[];
  process: PageProcess;
  glossary: PageTerm[];
  pictures: PagePicture[];
  openQuestions: PageQuestion[];
  evidence: PageEvidence | null;
  claims: PageClaim[];
  sources: SourceRef[];
};

const CLAIM_IDS = list(UUID, 1);
const POSITIVE: Shape<number> = {
  expected: "a whole number from 1",
  parse(value, path) {
    const whole = integer.parse(value, path);
    if (whole < 1) throw new ShapeError(path, "a whole number from 1");
    return whole;
  }
};

const sentenceShape: Shape<PageSentence> = object<PageSentence>({ id: text, text, level: storedLevelShape, claimIds: CLAIM_IDS, terms: list(termSpanShape) });
const areaShape: Shape<PageArea> = object<PageArea>({ lgd: nullable(integer), name: text });
const subjectShape: Shape<SubjectRef> = object<SubjectRef>({ id: nullable(UUID), name: text, kind: oneOf(SUBJECT_KINDS) });
const entryShape: Shape<EvidenceEntry> = object<EvidenceEntry>({ claimId: UUID, foldedIds: list(UUID) });

const stageItemShape: Shape<StageItem> = object<StageItem>({
  id: UUID,
  name: text,
  kind: oneOf(MATERIAL_KINDS),
  role: oneOf(MATERIAL_ROLES),
  localNames: list(text),
  claimIds: CLAIM_IDS
});

const reactionShape: Shape<PageReaction> = object<PageReaction>({
  id: nullable(UUID),
  kind: oneOf(REACTION_KINDS),
  label: text,
  species: list(object<PageSpecies>({ role: oneOf(SPECIES_ROLES), name: nullable(text), formula: nullable(text), coefficient: nullable(POSITIVE) }), 2),
  balanced: boolean,
  equation: nullable(text),
  claimIds: CLAIM_IDS
});

const stageShape: Shape<PageStage> = object<PageStage>({
  id: UUID,
  order: nullable(POSITIVE),
  name: text,
  localName: nullable(text),
  stageType: oneOf(STAGE_TYPES),
  claimIds: CLAIM_IDS,
  materials: list(stageItemShape),
  tools: list(stageItemShape),
  timing: list(object<StageTiming>({ kind: oneOf(TIMING_KINDS), text, claimId: UUID })),
  reactions: list(reactionShape)
});

const overviewShape: Shape<PageOverview> = object<PageOverview>({
  lede: list(sentenceShape),
  keyFacts: list(object<KeyFact>({ label: text, value: text, claimIds: CLAIM_IDS })),
  sections: list(object<OverviewSection>({ discipline: oneOf(DISCIPLINES), title: text, basis: oneOf(SECTION_BASES), sentences: list(sentenceShape, 1) }))
});

const placeShape: Shape<PagePlace> = object<PagePlace>({
  key: text,
  name: text,
  kind: oneOf(PLACE_KINDS),
  role: oneOf(PLACE_ROLES),
  district: nullable(areaShape),
  state: nullable(areaShape),
  country: text,
  wikidataId: nullable(WIKIDATA_ID),
  claimIds: CLAIM_IDS
});

const communityShape: Shape<PageCommunity> = object<PageCommunity>({
  key: text,
  kind: oneOf(GROUP_KINDS),
  name: text,
  localNames: list(text),
  honours: list(text),
  place: nullable(text),
  claimIds: CLAIM_IDS
});

const claimShape: Shape<PageClaim> = object<PageClaim>({
  id: UUID,
  text,
  level: storedLevelShape,
  discipline: oneOf(DISCIPLINES),
  subject: subjectShape,
  provenance: oneOf(PROVENANCES),
  sourcesDiffer: boolean,
  citations: list(citationShape, 1)
});

export const craftPageShape: Shape<CraftPage> = object<CraftPage>({
  schemaVersion: oneOf([1] as const),
  craft: object<PageCraft>({
    slug: text,
    name: text,
    path: CRAFT_PATH,
    id: UUID,
    localName: nullable(text),
    categoryName: nullable(text),
    subCategoryName: nullable(text),
    giStatus: nullable(oneOf(CRAFT_GI_STATUSES)),
    stateOfPractice: list(text),
    stateOfOrigin: list(text)
  }),
  curated: boolean,
  curation: nullable(
    object<CurationHeader>({
      version: POSITIVE,
      curatedAt: INSTANT,
      coverage: oneOf(COVERAGE_CLASSES),
      searched: list(object<SearchedFor>({ query: text, site: text }))
    })
  ),
  overview: overviewShape,
  sourcesDiffer: list(object<DifferRow>({ about: text, claimIds: list(UUID, 2) })),
  places: list(placeShape),
  communities: list(communityShape),
  process: object<PageProcess>({ processId: nullable(UUID), stages: list(stageShape), reactions: list(reactionShape) }),
  glossary: list(
    object<PageTerm>({ key: nullable(TERM_KEY), label: text, names: list(text), meaning: nullable(text), language: nullable(text), script: nullable(text), claimIds: list(UUID) })
  ),
  pictures: list(object<PagePicture>({ media: mediaRefShape, caption: text, stageId: nullable(UUID), claimIds: list(UUID) })),
  openQuestions: list(object<PageQuestion>({ key: nullable(text), question: text, settledBy: nullable(text), claimIds: CLAIM_IDS })),
  evidence: nullable(
    object<PageEvidence>({
      groups: list(object<EvidenceGroup>({ discipline: oneOf(DISCIPLINES), title: text, subjects: list(object<EvidenceSubject>({ subject: subjectShape, entries: list(entryShape, 1) }), 1) })),
      hypotheses: list(entryShape)
    })
  ),
  claims: list(claimShape),
  sources: list(sourceRefShape)
});

export async function fetchCraftPage(slug: string): Promise<CraftPage> {
  return checkedCraftPage(parseShape(craftPageShape, await apiFetch<unknown>(CRAFT_PAGE_PATH(slug))));
}

export function referencedClaimIds(page: CraftPage): string[] {
  const { overview, process } = page;
  const sentences = [...overview.lede, ...overview.sections.flatMap((section) => section.sentences)];
  const rows = [...overview.keyFacts, ...page.sourcesDiffer, ...page.places, ...page.communities, ...page.glossary, ...page.pictures, ...page.openQuestions];
  const reactions = [...process.reactions, ...process.stages.flatMap((stage) => stage.reactions)];
  const items = process.stages.flatMap((stage) => [...stage.materials, ...stage.tools]);
  return [
    ...[...sentences, ...rows, ...reactions, ...items, ...process.stages].flatMap((row) => row.claimIds),
    ...process.stages.flatMap((stage) => stage.timing.map((timing) => timing.claimId))
  ];
}

function checkCitedOnly(page: CraftPage, levels: Map<string, StoredLevel>): void {
  const cited = new Set(referencedClaimIds(page));
  for (const id of levels.keys()) if (!cited.has(id)) throw new ShapeError(`claim ${id}`, "a claim a shown part cites, since the page carries no evidence");
}

function checkEvidence(evidence: PageEvidence, levels: Map<string, StoredLevel>): void {
  const filed: [EvidenceEntry, boolean][] = [
    ...evidence.groups.flatMap((group) => group.subjects.flatMap((subject) => subject.entries.map((entry) => [entry, false] as [EvidenceEntry, boolean]))),
    ...evidence.hypotheses.map((entry) => [entry, true] as [EvidenceEntry, boolean])
  ];
  const seen = new Set<string>();
  for (const [entry, hypotheses] of filed) {
    for (const id of [entry.claimId, ...entry.foldedIds]) {
      const level = levels.get(id);
      if (!level) throw new ShapeError(`evidence ${id}`, "a claim the page lists");
      if ((level === "HYPOTHESIS") !== hypotheses) throw new ShapeError(`evidence ${id}`, "hypotheses filed apart from facts");
      if (seen.has(id)) throw new ShapeError(`evidence ${id}`, "each claim filed once");
      seen.add(id);
    }
  }
  if (seen.size !== levels.size) throw new ShapeError("evidence", "every listed claim filed");
}

export function checkedCraftPage(page: CraftPage): CraftPage {
  if (page.curated !== (page.curation !== null)) throw new ShapeError("curation", "a header exactly when the page is curated");
  const levels = new Map(page.claims.map((claim) => [claim.id, claim.level]));
  if (levels.size !== page.claims.length) throw new ShapeError("claims", "each claim listed once");
  for (const id of referencedClaimIds(page)) if (!levels.has(id)) throw new ShapeError(`claim ${id}`, "a claim the page lists");
  const sources = new Set(page.sources.map((source) => source.id));
  for (const claim of page.claims) {
    for (const citation of claim.citations) if (!sources.has(citation.sourceId)) throw new ShapeError(`claim ${claim.id}`, `source ${citation.sourceId} listed`);
  }
  for (const sentence of [...page.overview.lede, ...page.overview.sections.flatMap((section) => section.sentences)]) {
    if (sentence.level === "HYPOTHESIS") throw new ShapeError(`sentence ${sentence.id}`, "a sentence resting on facts, never a hypothesis");
  }
  for (const reaction of [...page.process.reactions, ...page.process.stages.flatMap((stage) => stage.reactions)]) {
    if ((reaction.equation !== null) !== reaction.balanced) throw new ShapeError(`reaction ${reaction.label}`, "an equation only when balanced");
  }
  if (page.evidence === null) checkCitedOnly(page, levels);
  else checkEvidence(page.evidence, levels);
  return page;
}
