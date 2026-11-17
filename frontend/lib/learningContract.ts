import { languageCodeShape } from "@/lib/answerLanguages";
import { craftLinkShape, INSTANT, UUID, type CraftLink } from "@/lib/answerShapes";
import { DISCIPLINES, type Discipline } from "@/lib/explainerBlockBase";
import { DEPTHS, explainerShape, SECTION_ID, type Depth, type Explainer } from "@/lib/explainerContract";
import { integer, list, matching, nullable, object, oneOf, text, type Shape } from "@/lib/shape";

export const SECTION_CHANGES = ["ADDED", "DEEPENED"] as const;
export const NOTIFICATION_KINDS = ["ANSWER_IMPROVED"] as const;
export const EXPLAINER_PATH = (explainerId: string) => `/explainers/${encodeURIComponent(explainerId)}`;
export const EXPLAINER_VERSIONS_PATH = (explainerId: string) => `${EXPLAINER_PATH(explainerId)}/versions`;
export const EXPLAINER_VERSION_PATH = (explainerId: string, version: number) => `${EXPLAINER_VERSIONS_PATH(explainerId)}/${version}`;
export const SAVED_EXPLAINERS_PATH = "/saved-explainers";
export const SAVED_EXPLAINER_PATH = (explainerId: string) => `${SAVED_EXPLAINERS_PATH}/${encodeURIComponent(explainerId)}`;
export const NOTIFICATIONS_PATH = "/notifications";
export const NOTIFICATION_READ_PATH = (id: string) => `${NOTIFICATIONS_PATH}/${encodeURIComponent(id)}/read`;
export const NOTIFICATIONS_READ_ALL_PATH = `${NOTIFICATIONS_PATH}/read-all`;

export type BuildsOn = { explainerId: string; version: number; facets: Discipline[] };
export type SectionPlace = { id: string; order: number };
export type BuildsOnEvent = { explainerId: string; version: number; sections: SectionPlace[] };
export type SectionChange = { sectionId: string; change: (typeof SECTION_CHANGES)[number]; blockIds: string[] };
export type VersionMark = {
  explainerId: string;
  version: number;
  answerId: string;
  basedOn: number | null;
  question: string;
  changes: SectionChange[];
  createdAt: string;
};
export type ExplainerHistory = { schemaVersion: 1; explainerId: string; versions: VersionMark[] };
export type ExplainerVersionDocument = { schemaVersion: 1; mark: VersionMark; explainer: Explainer };
export type SavedExplainer = {
  explainerId: string;
  question: string;
  craft: CraftLink | null;
  facets: Discipline[];
  depth: Depth;
  language: string;
  latestVersion: number;
  seenVersion: number;
  savedAt: string;
  checkedAt: string | null;
};
export type SavedExplainerList = { schemaVersion: 1; items: SavedExplainer[] };
export type FacetNews = { facet: Discipline; newClaims: number };
export type AnswerImproved = {
  explainerId: string;
  version: number;
  question: string;
  craft: CraftLink;
  news: FacetNews[];
  checkedAt: string;
};
export type Notification = {
  id: string;
  kind: (typeof NOTIFICATION_KINDS)[number];
  createdAt: string;
  readAt: string | null;
  payload: AnswerImproved;
};
export type NotificationList = { schemaVersion: 1; items: Notification[]; unread: number };

const discipline = oneOf(DISCIPLINES);
const VERSION = integer;

export const buildsOnShape: Shape<BuildsOn> = object<BuildsOn>({ explainerId: UUID, version: VERSION, facets: list(discipline) });

export const buildsOnEventShape: Shape<BuildsOnEvent> = object<BuildsOnEvent>({
  explainerId: UUID,
  version: VERSION,
  sections: list(object<SectionPlace>({ id: SECTION_ID, order: integer }), 1)
});

export const versionMarkShape: Shape<VersionMark> = object<VersionMark>({
  explainerId: UUID,
  version: VERSION,
  answerId: UUID,
  basedOn: nullable(VERSION),
  question: text,
  changes: list(
    object<SectionChange>({ sectionId: SECTION_ID, change: oneOf(SECTION_CHANGES), blockIds: list(matching(/^[a-z0-9]+(?:[.-][a-z0-9]+)*$/, "a block id"), 1) })
  ),
  createdAt: INSTANT
});

export const explainerHistoryShape: Shape<ExplainerHistory> = object<ExplainerHistory>({
  schemaVersion: oneOf([1] as const),
  explainerId: UUID,
  versions: list(versionMarkShape, 1)
});

export const explainerVersionDocumentShape: Shape<ExplainerVersionDocument> = object<ExplainerVersionDocument>({
  schemaVersion: oneOf([1] as const),
  mark: versionMarkShape,
  explainer: explainerShape
});

export const savedExplainerListShape: Shape<SavedExplainerList> = object<SavedExplainerList>({
  schemaVersion: oneOf([1] as const),
  items: list(
    object<SavedExplainer>({
      explainerId: UUID,
      question: text,
      craft: nullable(craftLinkShape),
      facets: list(discipline, 1),
      depth: oneOf(DEPTHS),
      language: languageCodeShape,
      latestVersion: VERSION,
      seenVersion: VERSION,
      savedAt: INSTANT,
      checkedAt: nullable(INSTANT)
    })
  )
});

export const answerImprovedShape: Shape<AnswerImproved> = object<AnswerImproved>({
  explainerId: UUID,
  version: VERSION,
  question: text,
  craft: craftLinkShape,
  news: list(object<FacetNews>({ facet: discipline, newClaims: integer }), 1),
  checkedAt: INSTANT
});

export const notificationListShape: Shape<NotificationList> = object<NotificationList>({
  schemaVersion: oneOf([1] as const),
  items: list(
    object<Notification>({ id: UUID, kind: oneOf(NOTIFICATION_KINDS), createdAt: INSTANT, readAt: nullable(INSTANT), payload: answerImprovedShape })
  ),
  unread: integer
});

export function hasNewerVersion(saved: SavedExplainer): boolean {
  return saved.latestVersion > saved.seenVersion;
}
