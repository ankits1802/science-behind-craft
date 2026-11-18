import { citationShape, craftLinkShape, sourceRefShape, UUID, type CraftLink } from "@/lib/answerShapes";
import { mediaRefShape, type MediaRef } from "@/lib/explainerBlockBase";
import { PARTIAL_DATE } from "@/lib/explainerInsight";
import { boolean, integer, list, nullable, object, oneOf, ShapeError, text, type Shape } from "@/lib/shape";
import type { Citation, SourceRef } from "@/lib/types";

export const DEPTH_BASES = ["CURATED", "STORED_CLAIMS", "REGISTER"] as const;
export const EVENT_KINDS = ["STATED", "GI_FILED", "GI_REGISTERED", "PRICE", "WORKFORCE"] as const;
export const PICTURE_ROLES = ["HERO", "OVERVIEW", "STAGE"] as const;
export const ENVIRONMENT_FACTORS = ["WATER", "SOIL", "CLIMATE", "LANDFORM", "VEGETATION", "OTHER"] as const;
export const COVERAGE_CLASSES = ["FULL", "THIN"] as const;
export const CRAFT_GI_STATUSES = ["GI", "NON_GI"] as const;
export const DIFFER_WEIGHTS = [1, 2, 3] as const;
export const SAME_FAMILY_MAX = 6;

export type DepthBasis = (typeof DEPTH_BASES)[number];
export type EventKind = (typeof EVENT_KINDS)[number];
export type PictureRole = (typeof PICTURE_ROLES)[number];
export type EnvironmentFactor = (typeof ENVIRONMENT_FACTORS)[number];
type Coverage = (typeof COVERAGE_CLASSES)[number];
type GiStatus = (typeof CRAFT_GI_STATUSES)[number];

export type LocalName = { name: string; language: string | null; script: string | null; claimIds: string[] };
export type PageTabs = { process: boolean; region: boolean; sharedScience: boolean; sources: boolean; evidence: boolean };
export type PageDepth = { basis: DepthBasis; coverage: Coverage | null; claims: number; sources: number; stages: number; pictures: number };
export type PageGi = {
  status: GiStatus | null;
  applicationNumber: string | null;
  certificateNumber: string | null;
  filedOn: string | null;
  registeredOn: string | null;
  journalIssue: string | null;
  proprietors: string[];
  authorisedUserCount: number | null;
  claimIds: string[];
};
export type PageEvent = { kind: EventKind; start: number; end: number; date: string | null; place: string | null; claimIds: string[] };
export type StepPlace = { key: string; name: string };
export type EnvironmentStep = { factor: EnvironmentFactor; place: StepPlace | null; claimIds: string[] };
export type HeroImage = { media: MediaRef; caption: string };
export type RelativeLede = { text: string; citations: Citation[]; sources: SourceRef[] };
export type PageRelative = {
  craft: CraftLink;
  displayName: string;
  giStatus: GiStatus | null;
  stateOfPractice: string[];
  basis: DepthBasis;
  coverage: Coverage | null;
  claims: number;
  hero: HeroImage | null;
  lede: RelativeLede | null;
};

const COUNT: Shape<number> = {
  expected: "a whole number from 0",
  parse(value, path) {
    const whole = integer.parse(value, path);
    if (whole < 0) throw new ShapeError(path, "a whole number from 0");
    return whole;
  }
};
const CLAIM_IDS = list(UUID, 1);

export const localNameShape: Shape<LocalName> = object<LocalName>({ name: text, language: nullable(text), script: nullable(text), claimIds: CLAIM_IDS });

export const pageTabsShape: Shape<PageTabs> = object<PageTabs>({ process: boolean, region: boolean, sharedScience: boolean, sources: boolean, evidence: boolean });

export const pageDepthShape: Shape<PageDepth> = object<PageDepth>({
  basis: oneOf(DEPTH_BASES),
  coverage: nullable(oneOf(COVERAGE_CLASSES)),
  claims: COUNT,
  sources: COUNT,
  stages: COUNT,
  pictures: COUNT
});

export const pageGiShape: Shape<PageGi> = object<PageGi>({
  status: nullable(oneOf(CRAFT_GI_STATUSES)),
  applicationNumber: nullable(text),
  certificateNumber: nullable(text),
  filedOn: nullable(PARTIAL_DATE),
  registeredOn: nullable(PARTIAL_DATE),
  journalIssue: nullable(text),
  proprietors: list(text),
  authorisedUserCount: nullable(COUNT),
  claimIds: list(UUID)
});

export const pageEventShape: Shape<PageEvent> = object<PageEvent>({
  kind: oneOf(EVENT_KINDS),
  start: integer,
  end: integer,
  date: nullable(PARTIAL_DATE),
  place: nullable(text),
  claimIds: CLAIM_IDS
});

export const environmentStepShape: Shape<EnvironmentStep> = object<EnvironmentStep>({
  factor: oneOf(ENVIRONMENT_FACTORS),
  place: nullable(object<StepPlace>({ key: text, name: text })),
  claimIds: CLAIM_IDS
});

export const heroImageShape: Shape<HeroImage> = object<HeroImage>({ media: mediaRefShape, caption: text });

export const pageRelativeShape: Shape<PageRelative> = object<PageRelative>({
  craft: craftLinkShape,
  displayName: text,
  giStatus: nullable(oneOf(CRAFT_GI_STATUSES)),
  stateOfPractice: list(text),
  basis: oneOf(DEPTH_BASES),
  coverage: nullable(oneOf(COVERAGE_CLASSES)),
  claims: COUNT,
  hero: nullable(heroImageShape),
  lede: nullable(object<RelativeLede>({ text, citations: list(citationShape, 1), sources: list(sourceRefShape) }))
});

export function checkDepth(depth: PageDepth | PageRelative, path: string): void {
  if ((depth.basis === "CURATED") !== (depth.coverage !== null)) throw new ShapeError(path, "a coverage class exactly when the page is curated");
}

export function checkEvents(events: readonly PageEvent[]): void {
  events.forEach((event, index) => {
    if (event.start > event.end) throw new ShapeError(`events[${index}]`, "a span running forward in time");
    const year = event.date === null ? null : Number(event.date.slice(0, 4));
    if (year !== null && (year < event.start || year > event.end)) throw new ShapeError(`events[${index}].date`, "a date inside the event's span");
  });
}

export function checkRelatives(slug: string, relatives: readonly PageRelative[]): void {
  if (relatives.length > SAME_FAMILY_MAX) throw new ShapeError("sameFamily", `at most ${SAME_FAMILY_MAX} crafts`);
  relatives.forEach((relative, index) => {
    const path = `sameFamily[${index}]`;
    if (relative.craft.slug === slug) throw new ShapeError(path, "another craft than the page's own");
    checkDepth(relative, path);
    if (relative.hero && relative.hero.media.display !== "INLINE") throw new ShapeError(`${path}.hero`, "a picture shown inline");
    if (!relative.lede) return;
    const cited = [...new Set(relative.lede.citations.map((citation) => citation.sourceId))];
    if (cited.join(" ") !== relative.lede.sources.map((source) => source.id).join(" ")) throw new ShapeError(`${path}.lede`, "each cited source once, in order of first citation");
  });
}
